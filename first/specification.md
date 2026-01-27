# FIRST Tech Challenge Team Contribution Analysis Specification

## Objective
Calculate the relative contributions (often referred to as OPR - Offensive Power Rating) of individual FIRST Tech Challenge (FTC) teams based on match results. The analysis separates scoring into components: Autonomous, Teleop, and Penalties.

## Input
- **Source URL**: A URL to the qualification matches of an event (e.g., `https://ftc-events.firstinspires.org/2025/ILKSQ1/qualifications`).

## Data Collection

### 1. Match List Parsing
- Access the provided Source URL.
- Identify all Qualification matches that have been played (contain scores).
- For each match, extract the Match Number and the URL to its detail page (e.g., `.../qualifications/3`).

### 2. Match Detail Parsing
For each match URL, scrape the following data:
- **Teams**:
    - Red Alliance Teams (Red1, Red2)
    - Blue Alliance Teams (Blue1, Blue2)
- **Score Components**:
    - **Autonomous**:
        - Red Alliance Auto Score
        - Blue Alliance Auto Score
    - **Teleop**:
        - Red Alliance Teleop Score
        - Blue Alliance Teleop Score
    - **Penalties**:
        - "Penalty Points Committed" by Red Alliance
        - "Penalty Points Committed" by Blue Alliance

### 3. Data Processing & Logic
- **Penalty Assignment**: 
  - Penalties are "assigned to the opposite team" to reflect points gained.
  - The value of "Penalty Points Committed" by the **Red Alliance** becomes the **Blue Alliance's Penalty Score**.
  - The value of "Penalty Points Committed" by the **Blue Alliance** becomes the **Red Alliance's Penalty Score**.

- **Target Vectors**:
  Construct data rows for each alliance in each match (2 rows per match).
  - `b_auto`: Autonomous Score
  - `b_teleop`: Teleop Score
  - `b_penalty`: Penalty Score (derived from opponent's committed penalties)

## Optimization Model (Least Squares)

The goal is to solve for the vector $x$ (team contributions) in the linear system $Ax = b$, where:
- $A$: A binary matrix where rows represent alliance-matches and columns represent teams. $A_{ij} = 1$ if team $j$ played in the alliance for entry $i$, else $0$.
- $b$: The observed score component for that alliance.
- $x$: The unknown contribution of each team.

Since the system is overdetermined, we minimize the squared error:
$$ \min_x || Ax - b ||^2 $$

This optimization should be performed independently for each component:
1.  **Autonomous Contribution** ($x_{auto}$)
2.  **Teleop Contribution** ($x_{teleop}$)
3.  **Penalty Contribution** ($x_{penalty}$) - Represents how many penalty points a team *causes* their opponents to gain (or arguably, draws from opponents, depending on interpretation. Given the assignment logic, this calculates "Points gained via penalties").

## Output
- A summary of calculated contributions for each team, broken down by component (Auto, Teleop, Penalty) and Total.
