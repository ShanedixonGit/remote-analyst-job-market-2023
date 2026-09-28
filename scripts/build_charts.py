"""Build the project charts from the query results in outputs/tables.

Charts read only the CSVs written by run_analysis.py, so a figure can never drift
away from the query behind it. Populations and denominators are looked up from the
data-quality step counts rather than written into the labels by hand.

Usage:
    python scripts/build_charts.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from collect_live_postings import AMBIGUOUS

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
LIVE_TABLES = ROOT / "outputs" / "live" / "tables"

SOURCE_NOTE = "Source: lukebarousse/data_jobs, 785,639 postings, calendar year 2023"

INK = "#1B2A32"
MUTED = "#6B7C85"
ACCENT = "#1F8F45"
ACCENT_SOFT = "#A9D6B8"
FLAG = "#B5502F"
GRID = "#DCE3E6"


def money(value: float, decimals: int = 0) -> str:
    """Format a salary, escaping the dollar sign so matplotlib skips mathtext."""
    return f"\\${value:,.{decimals}f}"


def population(step: str) -> int:
    """Look up a population size by label from the data-quality step counts."""
    df = pd.read_csv(TABLES / "06_data_quality_checks_1.csv")
    return int(df.loc[df["step"] == step, "postings"].iloc[0])


def theme() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.labelsize": 10,
            "xtick.color": MUTED,
            "ytick.color": INK,
            "xtick.labelsize": 9,
            "ytick.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.edgecolor": GRID,
            "figure.dpi": 150,
        }
    )


def frame(ax, title: str, subtitle: str, xlabel: str, ylabel: str = "") -> None:
    """Title block, axis labels and grid, shared by every chart.

    Title padding grows with the number of subtitle lines so the two never collide.
    """
    lines = subtitle.count("\n") + 1
    ax.set_title(title, fontsize=14, fontweight="bold", loc="left", pad=20 + 15 * lines)
    ax.text(
        0,
        1.012,
        subtitle,
        transform=ax.transAxes,
        fontsize=9.5,
        color=MUTED,
        va="bottom",
        linespacing=1.45,
    )
    ax.set_xlabel(xlabel, fontsize=9.5, color=MUTED, labelpad=8)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9.5, color=MUTED, labelpad=8)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)


def save(fig, ax, name: str, note: str = SOURCE_NOTE) -> None:
    """Write the figure, anchoring the source note below the x-axis label."""
    fig.canvas.draw()
    label_bottom = ax.xaxis.get_label().get_window_extent().transformed(
        fig.transFigure.inverted()
    ).y0
    fig.text(0.0, label_bottom - 0.055, note, fontsize=8, color=MUTED)
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / name
    fig.savefig(path, bbox_inches="tight", pad_inches=0.35, facecolor="white")
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")


def chart_top_paying_roles() -> None:
    df = pd.read_csv(TABLES / "01_top_paying_remote_roles.csv")
    median = pd.read_csv(TABLES / "06_data_quality_checks_4.csv")["median_all"].iloc[0]
    outlier = pd.read_csv(TABLES / "06_data_quality_checks_3.csv").iloc[0]

    df = df.sort_values("salary_year_avg")
    labels = [f"{t}\n{c}" for t, c in zip(df["job_title"], df["company_name"])]
    top = df["salary_year_avg"].max()
    colors = [FLAG if v == top else ACCENT for v in df["salary_year_avg"]]

    fig, ax = plt.subplots(figsize=(11.5, 7))
    bars = ax.barh(labels, df["salary_year_avg"], color=colors, height=0.66)

    ax.axvline(median, color=MUTED, linestyle="--", linewidth=1, zorder=1)
    ax.text(
        median + top * 0.008,
        -0.62,
        f"Population median {money(median)}",
        color=MUTED,
        fontsize=8.5,
        va="center",
    )

    for bar, value in zip(bars, df["salary_year_avg"]):
        ax.text(
            value + top * 0.012,
            bar.get_y() + bar.get_height() / 2,
            money(value),
            va="center",
            fontsize=9.5,
            color=INK,
        )

    ax.annotate(
        f"Single posting, advertised {outlier['job_via']},\n"
        f"{outlier['multiple_of_median']:.1f}x the population median.\n"
        "Read as a data-quality outlier, not a market signal.",
        xy=(top, len(df) - 1.35),
        xytext=(top * 0.46, len(df) - 4.6),
        fontsize=8.5,
        color=FLAG,
        linespacing=1.5,
        arrowprops=dict(arrowstyle="-", color=FLAG, linewidth=0.9),
    )

    ax.set_xlim(0, top * 1.15)
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"\\${x / 1000:,.0f}k")
    )
    frame(
        ax,
        "The highest-advertised remote Data Analyst salaries of 2023",
        f"Top 10 of {population('data analyst, remote, salaried'):,} fully remote Data"
        " Analyst postings that stated an annual salary",
        "Advertised average annual salary (USD)",
    )
    save(fig, ax, "01_top_paying_remote_roles.png")


def chart_skills_in_top_roles() -> None:
    df = pd.read_csv(TABLES / "02_skills_in_top_paying_roles.csv").sort_values(
        ["postings", "skill"], ascending=[True, False]
    )
    top10 = pd.read_csv(TABLES / "06_data_quality_checks_6.csv")
    n_with = int((top10["skills_listed"] > 0).sum())
    missing = " and ".join(
        money(v / 1000, 1).replace(".0", "") + "k"
        for v in top10.loc[top10["skills_listed"] == 0, "salary_year_avg"]
    )
    colors = [ACCENT if v >= 4 else ACCENT_SOFT for v in df["postings"]]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(df["skill"], df["postings"], color=colors, height=0.68)
    for bar, count, pct in zip(bars, df["postings"], df["coverage_pct"]):
        ax.text(
            count + 0.12,
            bar.get_y() + bar.get_height() / 2,
            f"{count}  ({pct:.0f}%)",
            va="center",
            fontsize=9,
            color=INK,
        )

    ax.set_xlim(0, df["postings"].max() * 1.22)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    frame(
        ax,
        "SQL is the only skill every top-paying role asks for",
        f"Skills listed by the {n_with} of the top 10 highest-paying remote postings that"
        f" record any skill.\nThe {missing} postings list no skills at all, so percentages"
        f" are of {n_with}, not 10.",
        f"Postings listing the skill (out of {n_with})",
    )
    save(fig, ax, "02_skills_in_top_paying_roles.png")


def chart_in_demand_skills() -> None:
    df = pd.read_csv(TABLES / "03_most_in_demand_skills.csv")
    leaders = int((df["share_of_pct"] >= 30).sum())
    spelled = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}.get(leaders, str(leaders))
    df = df.sort_values("postings")
    cutoff = df["share_of_pct"].nlargest(leaders).min()
    colors = [ACCENT if v >= cutoff else ACCENT_SOFT for v in df["share_of_pct"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df["skill"], df["postings"], color=colors, height=0.68)
    for bar, count, pct in zip(bars, df["postings"], df["share_of_pct"]):
        ax.text(
            count + df["postings"].max() * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,}  ({pct:.0f}%)",
            va="center",
            fontsize=9,
            color=INK,
        )

    ax.set_xlim(0, df["postings"].max() * 1.18)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x / 1000:,.0f}k"))
    frame(
        ax,
        f"{spelled} skills appear in at least 30% of remote analyst postings",
        f"Share of the {population('data analyst, remote, with skills'):,} remote Data"
        " Analyst postings that record any skill.\nNo salary filter: this measures how"
        " often a skill is asked for, not what it pays.",
        "Postings listing the skill",
    )
    save(fig, ax, "03_most_in_demand_skills.png")


def chart_optimal_skills() -> None:
    df = pd.read_csv(TABLES / "05_optimal_skills.csv")
    x_split = df["postings"].median()
    y_split = df["avg_salary"].median()
    strong = (df["postings"] >= x_split) & (df["avg_salary"] >= y_split)
    top_demand = df.loc[df["postings"].idxmax()]

    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.axvline(x_split, color=GRID, linewidth=1.2, zorder=1)
    ax.axhline(y_split, color=GRID, linewidth=1.2, zorder=1)

    ax.scatter(
        df.loc[~strong, "postings"],
        df.loc[~strong, "avg_salary"],
        s=54,
        color=MUTED,
        alpha=0.5,
        zorder=3,
        linewidths=0,
    )
    ax.scatter(
        df.loc[strong, "postings"],
        df.loc[strong, "avg_salary"],
        s=100,
        color=ACCENT,
        zorder=4,
        linewidths=0,
    )
    ax.scatter(
        [top_demand["postings"]],
        [top_demand["avg_salary"]],
        s=100,
        color=FLAG,
        zorder=5,
        linewidths=0,
    )

    # Offsets are set per point so no label overlaps a marker or another label.
    nudges = {
        "sql": (-10, -20),
        "excel": (0, -20),
        "python": (10, 4),
        "tableau": (-14, -20),
        "r": (0, 11),
        "power bi": (10, -4),
        "sas": (0, 11),
        "powerpoint": (10, -4),
        "looker": (0, 11),
        "word": (0, 11),
        "oracle": (-38, 6),
        "snowflake": (10, 2),
        "azure": (10, -8),
        "aws": (10, -4),
        "go": (10, -4),
        "sql server": (-52, -4),
        "sheets": (10, -4),
        "flow": (10, 2),
        "vba": (-26, -18),
        "spss": (-34, 4),
    }
    for _, row in df.iterrows():
        dx, dy = nudges.get(row["skill"], (10, 4))
        highlighted = bool(strong[row.name])
        ax.annotate(
            row["skill"],
            (row["postings"], row["avg_salary"]),
            textcoords="offset points",
            xytext=(dx, dy),
            fontsize=8.5,
            color=FLAG if row["skill"] == top_demand["skill"] else (INK if highlighted else MUTED),
            fontweight="bold" if highlighted or row["skill"] == top_demand["skill"] else "normal",
        )

    for x, y, text, color, ha in [
        (0.985, 0.965, "High demand and high pay", ACCENT, "right"),
        (0.985, 0.02, "High demand, lower pay", MUTED, "right"),
        (0.015, 0.965, "Niche, high pay", MUTED, "left"),
        (0.015, 0.02, "Niche, lower pay", MUTED, "left"),
    ]:
        ax.text(
            x, y, text, transform=ax.transAxes, ha=ha, fontsize=9,
            color=color, fontweight="bold" if color == ACCENT else "normal",
        )

    ax.set_xscale("log")
    ax.set_xlim(df["postings"].min() * 0.75, df["postings"].max() * 1.5)
    ax.set_ylim(df["avg_salary"].min() - 4500, df["avg_salary"].max() + 4500)
    ax.set_xticks([20, 30, 50, 100, 200, 400])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda y, _: f"\\${y / 1000:,.0f}k")
    )
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    frame(
        ax,
        "The most-requested skill is not the best-paid one",
        f"Skills listed in at least 10 of the"
        f" {population('data analyst, remote, salaried'):,} salaried remote Data Analyst"
        " postings.\nLines mark the median of each axis; demand is on a log scale."
        f" {top_demand['skill'].upper()} appears in"
        f" {top_demand['demand_pct']:.0f}% of postings but pays below the median.",
        "Postings listing the skill (log scale)",
        "Mean advertised annual salary (USD)",
    )
    save(fig, ax, "05_optimal_skills.png")


def chart_live_comparison() -> None:
    """2023 demand against the current live sample, on the same measure."""
    source = LIVE_TABLES / "07_skill_demand_all.csv"
    if not source.exists():
        print("skipped live comparison: run scripts/collect_live_postings.py first")
        return

    live = pd.read_csv(source)
    baseline = pd.read_csv(TABLES / "07_skill_demand_all.csv")
    base_n = population("data analyst, remote, with skills")
    live_n = int(
        pd.read_csv(LIVE_TABLES / "06_data_quality_checks_1.csv")
        .set_index("step")
        .loc["data analyst, remote, with skills", "postings"]
    )

    # The live extractor cannot read skills whose names are also ordinary words,
    # so those are dropped from both sides. Leaving them in would show R and SAS
    # falling to zero, which would be an artefact of the method, not a finding.
    top_2023 = pd.read_csv(TABLES / "03_most_in_demand_skills.csv")
    excluded = sorted(set(AMBIGUOUS) & set(top_2023["skill"]))
    baseline = baseline[~baseline["skill"].isin(AMBIGUOUS)]
    live = live[~live["skill"].isin(AMBIGUOUS)]

    # Full tables on both sides, so a skill outside one top 10 still shows its
    # real share rather than a zero.
    merged = (
        baseline.merge(live, on="skill", how="outer", suffixes=("_2023", "_live"))
        .fillna({"share_of_pct_2023": 0, "share_of_pct_live": 0})
    )
    merged["rank_on"] = merged[["share_of_pct_2023", "share_of_pct_live"]].max(axis=1)
    merged = merged.nlargest(10, "rank_on").sort_values("share_of_pct_2023")

    positions = range(len(merged))
    height = 0.38
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    ax.barh(
        [p + height / 2 for p in positions], merged["share_of_pct_2023"],
        height=height, color=ACCENT, label=f"2023 dataset (n={base_n:,})",
    )
    ax.barh(
        [p - height / 2 for p in positions], merged["share_of_pct_live"],
        height=height, color=MUTED, alpha=0.75, label=f"Live sample (n={live_n})",
    )
    ax.set_yticks(list(positions))
    ax.set_yticklabels(merged["skill"])

    span = max(merged["share_of_pct_2023"].max(), merged["share_of_pct_live"].max())
    for position, value in zip(positions, merged["share_of_pct_2023"]):
        ax.text(value + span * 0.012, position + height / 2, f"{value:.0f}%",
                va="center", fontsize=8.5, color=INK)
    for position, value in zip(positions, merged["share_of_pct_live"]):
        ax.text(value + span * 0.012, position - height / 2, f"{value:.0f}%",
                va="center", fontsize=8.5, color=MUTED)

    ax.set_xlim(0, span * 1.16)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    legend = ax.legend(loc="lower right", frameon=False, fontsize=9)
    for text in legend.get_texts():
        text.set_color(INK)
    frame(
        ax,
        "SQL leads in both datasets; the live sample is too small to rank the rest",
        f"Share of remote analyst postings listing each skill: {live_n} in the live sample"
        f" against {base_n:,} from 2023.\nDifferences below roughly 15 points are noise at"
        f" this sample size. Excludes {', '.join(excluded)}, which the\nlive keyword"
        " extractor cannot separate from ordinary words.",
        "Share of postings listing the skill",
    )
    save(
        fig, ax, "06_live_vs_2023_demand.png",
        note="Sources: lukebarousse/data_jobs (2023); Jobicy, Remote OK, Arbeitnow,"
        " Himalayas (live sample)",
    )


if __name__ == "__main__":
    theme()
    chart_top_paying_roles()
    chart_skills_in_top_roles()
    chart_in_demand_skills()
    chart_optimal_skills()
    chart_live_comparison()
