import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Generate health analysis health_graphs.")
    parser.add_argument("--countries", nargs="+", help="List of countries to graph (e.g., 'United States' 'China'). If not provided, defaults to a sample set.")
    parser.add_argument("--start-year", type=int, help="Start year for the graph.")
    parser.add_argument("--end-year", type=int, help="End year for the graph.")
    args = parser.parse_args()

    # Define file paths
    death_rate_file = "staticData/birth-rate-vs-death-rate/birth-rate-vs-death-rate.csv"
    health_exp_file = "staticData/life-expectancy-vs-health-expenditure/life-expectancy-vs-health-expenditure.csv"
    productivity_file = "staticData/productivity.csv"

    # Check if files exist
    if not os.path.exists(death_rate_file):
        print(f"Error: File not found at {death_rate_file}")
        return
    if not os.path.exists(health_exp_file):
        print(f"Error: File not found at {health_exp_file}")
        return
    if not os.path.exists(productivity_file):
        print(f"Error: File not found at {productivity_file}")
        return

    # Load data
    print("Loading data...")
    try:
        df_death = pd.read_csv(death_rate_file)
        df_health = pd.read_csv(health_exp_file)
        df_prod = pd.read_csv(productivity_file)
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return

    # Column names
    col_death_rate = "Death rate - Sex: all - Age: all - Variant: estimates"
    col_birth_rate = "Birth rate - Sex: all - Age: all - Variant: estimates"
    col_life_exp = "Life expectancy - Sex: all - Age: 0 - Variant: estimates"
    col_health_exp = "Health expenditure per capita - Total"
    
    # Rename columns for easier handling
    if col_death_rate in df_death.columns:
        df_death = df_death.rename(columns={col_death_rate: "death_rate"})
    if col_birth_rate in df_death.columns:
        df_death = df_death.rename(columns={col_birth_rate: "birth_rate"})
    if col_life_exp in df_health.columns:
        df_health = df_health.rename(columns={col_life_exp: "life_expectancy", col_health_exp: "health_expenditure"})

    df_prod = df_prod.rename(columns={"ref_area.label": "Entity", "time": "Year", "obs_value": "productivity"})

    # Merge datasets on Entity, Code, Year
    print("Merging data...")
    df_merged = pd.merge(df_death[["Entity", "Code", "Year", "death_rate", "birth_rate"]],
                         df_health[["Entity", "Code", "Year", "life_expectancy", "health_expenditure"]],
                         on=["Entity", "Code", "Year"],
                         how="inner")
    
    # Merge productivity data
    df_merged = pd.merge(df_merged,
                         df_prod[["Entity", "Year", "productivity"]],
                         on=["Entity", "Year"],
                         how="inner")

    # Filter out rows with missing data for our variables
    initial_count = len(df_merged)
    df_merged = df_merged.dropna(subset=["death_rate","birth_rate", "life_expectancy", "health_expenditure", "productivity"])
    final_count = len(df_merged)
    print(f"Data points after merging and cleaning: {final_count} (dropped {initial_count - final_count})")

    # Filter by Countries
    available_countries = df_merged["Entity"].unique()
    if args.countries:
        selected_countries = args.countries
    else:
        defaults = ["United States", "China", "India", "Germany", "Brazil", "Nigeria"]
        selected_countries = [c for c in defaults if c in available_countries]
        if not selected_countries:
             selected_countries = available_countries[:5] # Fallback to first 5
        print(f"No countries specified. Defaulting to: {selected_countries}")
    
    selected_countries = available_countries
    df_filtered = df_merged[df_merged["Entity"].isin(selected_countries)].copy()

    # Filter by Years
    if args.start_year:
        df_filtered = df_filtered[df_filtered["Year"] >= args.start_year]
    if args.end_year:
        df_filtered = df_filtered[df_filtered["Year"] <= args.end_year]

    if len(df_filtered) == 0:
        print("No data found for the specified criteria.")
        return

    # Calculate metric
    death_expense_vs_birth = 4
    df_filtered["effort"] = (death_expense_vs_birth*df_filtered["death_rate"]) + df_filtered["birth_rate"]
    df_filtered["expenditure_per_event"] = 1000*df_filtered["health_expenditure"] / df_filtered["effort"]
    df_filtered["hours_of_effort"] = df_filtered["expenditure_per_event"] / df_filtered["productivity"]

    # Sort by Year to ensure lines are drawn correctly
    df_filtered = df_filtered.sort_values(by=["Entity", "Year"])

    # Create palette
    unique_countries = df_filtered["Entity"].unique()
    default_colors = sns.color_palette("husl", len(unique_countries))
    palette = dict(zip(unique_countries, default_colors))
    if "Israel" in palette:
        palette["Israel"] = "red"

    # Plotting
    print("Generating graph...")
    plt.figure(figsize=(12, 8))
    sns.set_theme(style="whitegrid")

    sns.lineplot(
        data=df_filtered,
        x="hours_of_effort",
        y="life_expectancy",
        hue="Entity",
        marker="o",
        sort=False,
        palette=palette
    )
    
    # Custom Log scale with 85 as the base (ignoring values >= 85 if they exist)
    # The user specifically asked for 85.
    base = 85
    def forward(x):
        # Using np.log10(base - x) means values closer to base (85) are more spread out.
        # We use -np.log10(base - x) to keep the orientation correct (higher life expectancy higher on axis)
        return -np.log10(np.maximum(base - x, 0.01))
    
    def inverse(x):
        return base - 10**(-x)

    plt.gca().set_yscale('function', functions=(forward, inverse))
    
    # Set appropriate ticks
    y_ticks = [40, 50, 60, 70, 75, 80, 82, 83, 84, 84.5, 84.9]
    plt.gca().set_yticks(y_ticks)
    plt.gca().set_yticklabels([str(t) for t in y_ticks])

    plt.title(f"Life Expectancy vs. Hours of Effort ({df_filtered['Year'].min()} - {df_filtered['Year'].max()})")
    plt.xlabel(f"Hours of Effort per birth event (normalized with cost of {death_expense_vs_birth} births = 1 death)")
    plt.ylabel("Life Expectancy (Years) - Log scale relative to 85")
    plt.gca().get_legend().remove()
    plt.tight_layout()

    # Save plot
    output_file = os.path.join("health_graphs", f"health_graph_{death_expense_vs_birth}.png")
    plt.savefig(output_file)
    print(f"Graph saved to {output_file}")

if __name__ == "__main__":
    main()