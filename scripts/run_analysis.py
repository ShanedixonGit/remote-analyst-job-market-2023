"""Run the analysis queries against a database and write the results.

The same queries run against either dataset. That is the point of loading the live
postings into the same schema: the analysis is not reimplemented for live data, it
is re-pointed at it.

Usage:
    python scripts/run_analysis.py                 # 2023 dataset
    python scripts/run_analysis.py --dataset live  # live collected postings
"""

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"

DATASETS = {
    "2023": (ROOT / "data" / "job_market.duckdb", ROOT / "outputs" / "tables"),
    "live": (ROOT / "data" / "live_market.duckdb", ROOT / "outputs" / "live" / "tables"),
}


def statements(text: str) -> list[str]:
    """Split a script into statements, ignoring semicolons inside block comments."""
    out, buf, i, in_block = [], [], 0, False
    while i < len(text):
        if not in_block and text.startswith("/*", i):
            in_block = True
            buf.append(text[i : i + 2])
            i += 2
        elif in_block and text.startswith("*/", i):
            in_block = False
            buf.append(text[i : i + 2])
            i += 2
        elif not in_block and text[i] == ";":
            out.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(text[i])
            i += 1
    if "".join(buf).strip():
        out.append("".join(buf))
    return [s for s in (s.strip() for s in out) if s]


def main(dataset: str) -> None:
    database, out_dir = DATASETS[dataset]
    if not database.exists():
        builder = (
            "scripts/build_database.py" if dataset == "2023"
            else "scripts/collect_live_postings.py"
        )
        raise SystemExit(f"{database.name} not found - run {builder} first")

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.csv"):
        stale.unlink()

    print(f"dataset: {dataset} ({database.name})")
    con = duckdb.connect(str(database), read_only=True)
    for path in sorted(SQL_DIR.glob("*.sql")):
        if path.name.startswith("00_"):
            continue
        parts = statements(path.read_text())
        for index, statement in enumerate(parts, start=1):
            suffix = f"_{index}" if len(parts) > 1 else ""
            target = out_dir / f"{path.stem}{suffix}.csv"
            con.sql(statement).write_csv(str(target))
            rows = con.sql(f"SELECT COUNT(*) FROM ({statement})").fetchone()[0]
            note = "  (no rows: measure unavailable in this dataset)" if rows == 0 else ""
            print(f"  {target.name:<40} {rows:>5} rows{note}")
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", choices=sorted(DATASETS), default="2023",
        help="which database to analyse (default 2023)",
    )
    main(parser.parse_args().dataset)
