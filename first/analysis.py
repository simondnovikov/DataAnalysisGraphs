import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from scipy.optimize import lsq_linear
import sys
import urllib.parse

"""
FTC Team Contribution (OPR) Analysis Script
This script calculates the Offensive Power Rating (OPR) for FTC teams and applies it
to predict match outcomes, showing actual vs predicted results for all matches.
"""

def get_matches_info(event_url):
    """Parses the qualification matches page to find links and participating teams."""
    print(f"Fetching match list from {event_url}...")
    response = requests.get(event_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    matches = []
    # Find all rows in the match table
    for row in soup.find_all('tr', id=lambda x: x and x.startswith('match')):
        # Match detail link
        td_num = row.find('td', class_='match-number-link')
        if not td_num:
            continue
            
        link_tag = td_num.find('a', href=True)
        if link_tag:
            match_num = link_tag.text.strip().split()[-1]
            match_url = urllib.parse.urljoin(event_url, link_tag['href'])
        else:
            # Match hasn't been played, might not be a link yet
            match_num = td_num.text.strip().split()[-1]
            match_url = None
        
        teams = {'red': [], 'blue': []}
        
        # Red alliance cells (lightred)
        for td in row.find_all('td', class_=lambda x: x and 'lightred' in x):
            team_cell = td.find('span', class_='team-cell')
            if team_cell:
                # Check if team is crossed out (has <s> tag)
                if not team_cell.find('s'):
                    team_link = team_cell.find('a')
                    if team_link:
                        teams['red'].append(team_link.text.strip())
        
        # Blue alliance cells (lightblue)
        for td in row.find_all('td', class_=lambda x: x and 'lightblue' in x):
            team_cell = td.find('span', class_='team-cell')
            if team_cell:
                # Check if team is crossed out (has <s> tag)
                if not team_cell.find('s'):
                    team_link = team_cell.find('a')
                    if team_link:
                        teams['blue'].append(team_link.text.strip())
        
        matches.append({
            'match_num': match_num,
            'url': match_url,
            'teams': teams
        })
        
    return matches

def parse_match_scores(match_url):
    """Fetches score breakdown for a specific match. Returns None if match not played."""
    response = requests.get(match_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    scores = {
        'red': {'auto': 0, 'teleop': 0, 'penalty_committed': 0},
        'blue': {'auto': 0, 'teleop': 0, 'penalty_committed': 0}
    }
    
    table = soup.find('table', class_='table-striped')
    if not table:
        return None
        
    rows = table.find_all('tr')
    found_data = False
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            red_val = cols[0].text.strip()
            label = cols[1].text.strip().lower()
            blue_val = cols[2].text.strip()
            
            try:
                if 'autonomous' == label:
                    scores['red']['auto'] = int(red_val)
                    scores['blue']['auto'] = int(blue_val)
                    found_data = True
                elif 'teleop' == label:
                    scores['red']['teleop'] = int(red_val)
                    scores['blue']['teleop'] = int(blue_val)
                    found_data = True
                elif 'penalty points committed' == label:
                    scores['red']['penalty_committed'] = int(red_val)
                    scores['blue']['penalty_committed'] = int(blue_val)
                    found_data = True
            except ValueError:
                continue

    return scores if found_data else None

def calculate_opr(matches):
    """Solves the Ax=b system for team contributions using Least Squares."""
    # Unique teams from all matches to ensure the OPR map is complete
    all_teams = set()
    for m in matches:
        all_teams.update(m['teams']['red'])
        all_teams.update(m['teams']['blue'])
    
    sorted_teams = sorted(list(all_teams), key=int)
    team_to_idx = {team: i for i, team in enumerate(sorted_teams)}
    num_teams = len(sorted_teams)
    
    A = []
    b_auto = []
    b_teleop = []
    b_penalty = []
    
    for m in matches:
        if 'scores' not in m or not m['scores']:
            continue
        if not m['teams']['red'] or not m['teams']['blue']:
            continue
            
        # Red Alliance row
        row_red = np.zeros(num_teams)
        for t in m['teams']['red']:
            row_red[team_to_idx[t]] = 1
        A.append(row_red)
        b_auto.append(m['scores']['red']['auto'])
        b_teleop.append(m['scores']['red']['teleop'])
        b_penalty.append(m['scores']['red']['penalty_committed'])
        
        # Blue Alliance row
        row_blue = np.zeros(num_teams)
        for t in m['teams']['blue']:
            row_blue[team_to_idx[t]] = 1
        A.append(row_blue)
        b_auto.append(m['scores']['blue']['auto'])
        b_teleop.append(m['scores']['blue']['teleop'])
        b_penalty.append(m['scores']['blue']['penalty_committed'])

    if not A:
         return pd.DataFrame(), {}

    A = np.array(A)
    results = pd.DataFrame({'Team': sorted_teams})
    opr_map = {team: {} for team in sorted_teams}
    
    for name, b in [('Auto', b_auto), ('Teleop', b_teleop), ('Penalty', b_penalty)]:
        b = np.array(b)
        res = lsq_linear(A, b, bounds=(0, np.inf))
        results[name] = res.x
        for i, team in enumerate(sorted_teams):
            opr_map[team][name] = res.x[i]

    results['Non-Penalty Total'] = results['Auto'] + results['Teleop']
    results['Total'] = results['Auto'] + results['Teleop'] - results['Penalty']
    
    for team in sorted_teams:
        opr_map[team]['Non-Penalty Total'] = results[results['Team'] == team]['Non-Penalty Total'].values[0]
        opr_map[team]['Total'] = results[results['Team'] == team]['Total'].values[0]

    return results.sort_values(by='Total', ascending=False), opr_map

def predict_matches(matches, opr_map):
    """Predicts scores for all matches using OPR map."""
    predictions = []
    
    for m in matches:
        red_teams = m['teams']['red']
        blue_teams = m['teams']['blue']
        
        if not red_teams and not blue_teams:
            continue
            
        pred = {
            'Match': m['match_num'],
            'Red Teams': ", ".join(red_teams),
            'Blue Teams': ", ".join(blue_teams),
        }
        
        # Calculate predicted totals
        red_np_total = sum(opr_map.get(t, {}).get('Non-Penalty Total', 0) for t in red_teams)
        red_penalty_gained = sum(opr_map.get(t, {}).get('Penalty', 0) for t in blue_teams)
        pred['Red Pred NP'] = red_np_total
        pred['Red Pred Total'] = red_np_total + red_penalty_gained
        
        blue_np_total = sum(opr_map.get(t, {}).get('Non-Penalty Total', 0) for t in blue_teams)
        blue_penalty_gained = sum(opr_map.get(t, {}).get('Penalty', 0) for t in red_teams)
        pred['Blue Pred NP'] = blue_np_total
        pred['Blue Pred Total'] = blue_np_total + blue_penalty_gained
        
        # Add actual scores if available
        if 'scores' in m and m['scores']:
            pred['Red Act NP'] = m['scores']['red']['auto'] + m['scores']['red']['teleop']
            pred['Red Act Total'] = pred['Red Act NP'] + m['scores']['blue']['penalty_committed']
            pred['Blue Act NP'] = m['scores']['blue']['auto'] + m['scores']['blue']['teleop']
            pred['Blue Act Total'] = pred['Blue Act NP'] + m['scores']['red']['penalty_committed']
        else:
            pred['Red Act NP'] = np.nan
            pred['Red Act Total'] = np.nan
            pred['Blue Act NP'] = np.nan
            pred['Blue Act Total'] = np.nan
            
        predictions.append(pred)
        
    return pd.DataFrame(predictions)

def main():
    url = "https://ftc-events.firstinspires.org/2025/ILKSQ1/qualifications"
    url = "https://ftc-events.firstinspires.org/2025/USTXNIM3/qualifications"
    url = "https://ftc-events.firstinspires.org/2025/ILKSQ2/qualifications/"
    if len(sys.argv) > 1:
        url = sys.argv[1]
        
    all_matches = get_matches_info(url)
    print(f"Found {len(all_matches)} matches.")
    
    # Identify played matches and get scores
    played_count = 0
    for m in all_matches:
        if not m['url']:
            continue
        try:
            scores = parse_match_scores(m['url'])
            if scores:
                m['scores'] = scores
                played_count += 1
        except Exception:
            pass
    
    print(f"Successfully parsed data for {played_count} played matches.")
    
    if played_count == 0:
        print("No played matches found to calculate OPR.")
        return

    results, opr_map = calculate_opr(all_matches)
    
    print("\nTeam Contributions (OPR):")
    pd.options.display.float_format = '{:.2f}'.format
    print(results.to_string(index=False))
    
    print("\nMatch Predictions (Actual vs Predicted):")
    predictions = predict_matches(all_matches, opr_map)
    
    cols = ['Match', 
            'Red Teams', 'Red Act NP', 'Red Pred NP', 'Red Act Total', 'Red Pred Total',
            'Blue Teams', 'Blue Act NP', 'Blue Pred NP', 'Blue Act Total', 'Blue Pred Total']
    
    print(predictions[cols].to_string(index=False))

    parts = url.strip('/').split('/')
    game_name = "unknown"
    for i, part in enumerate(parts):
        if part.isdigit() and len(part) == 4 and i + 1 < len(parts):
            game_name = parts[i+1]
            break
            
    num_matches = played_count
    opr_filename = f"{game_name}_{num_matches}_opr_results.csv"
    results.to_csv(opr_filename, index=False)
    print(f"\nSaved OPR results to {opr_filename}")
    
    match_filename = f"{game_name}_{num_matches}_match_results.csv"
    predictions[cols].to_csv(match_filename, index=False)
    print(f"Saved match predictions to {match_filename}")

if __name__ == "__main__":
    main()