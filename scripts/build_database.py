"""Download the source dataset and load it into a normalised local database.

The published source (lukebarousse/data_jobs on Hugging Face) is a single
denormalised CSV with no keys. This script splits it into the star schema
defined in sql/00_schema.sql, generating deterministic surrogate keys so that
repeated runs produce identical ids.

Usage:
    python scripts/build_database.py [--refresh]
"""

import argparse
import sys
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOURCE_CSV = DATA_DIR / "data_jobs.csv"
DATABASE = DATA_DIR / "job_market.duckdb"
SCHEMA = ROOT / "sql" / "00_schema.sql"
SOURCE_URL = (
    "https://huggingface.co/datasets/lukebarousse/data_jobs/resolve/main/data_jobs.csv"
)
EXPECTED_BYTES = 231_152_089


def download(refresh: bool) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if SOURCE_CSV.exists() and not refresh:
        print(f"source present: {SOURCE_CSV} ({SOURCE_CSV.stat().st_size:,} bytes)")
        return
    print(f"downloading {SOURCE_URL}")
    urllib.request.urlretrieve(SOURCE_URL, SOURCE_CSV)
    size = SOURCE_CSV.stat().st_size
    print(f"downloaded {size:,} bytes")
    if size != EXPECTED_BYTES:
        print(
            f"note: size differs from the verified snapshot ({EXPECTED_BYTES:,} bytes); "
            "the upstream dataset may have been revised",
            file=sys.stderr,
        )


def export_normalised_csv(con) -> None:
    """Write the four normalised tables out for loading into PostgreSQL."""
    target = DATA_DIR / "normalised"
    target.mkdir(exist_ok=True)
    for table in ("company_dim", "skills_dim", "job_postings_fact", "skills_job_dim"):
        path = target / f"{table}.csv"
        con.execute(f"COPY {table} TO '{path}' (HEADER, DELIMITER ',')")
        print(f"exported {path.relative_to(ROOT)}")


def load(export_csv: bool = False) -> None:
    if DATABASE.exists():
        DATABASE.unlink()
    con = duckdb.connect(str(DATABASE))
    con.execute(SCHEMA.read_text())

    # Full-row duplicates are the same posting scraped twice; keep one copy.
    con.execute(
        f"""
        CREATE TEMP TABLE staged AS
        SELECT DISTINCT * FROM read_csv('{SOURCE_CSV}', header = true, sample_size = -1)
        """
    )

    # Deterministic surrogate keys: ordering is fully specified so ids are stable.
    con.execute(
        """
        CREATE TEMP TABLE postings AS
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY job_posted_date, job_title_short, job_title, company_name,
                         job_location, job_via, salary_year_avg, job_skills
            ) AS job_id,
            *
        FROM staged
        """
    )

    con.execute(
        """
        INSERT INTO company_dim
        SELECT ROW_NUMBER() OVER (ORDER BY company_name) AS company_id, company_name
        FROM (SELECT DISTINCT company_name FROM postings WHERE company_name IS NOT NULL)
        """
    )

    con.execute(
        """
        CREATE TEMP TABLE posting_skill AS
        SELECT p.job_id, TRIM(s.skill) AS skills
        FROM postings AS p
        CROSS JOIN UNNEST(
            string_split(REPLACE(REPLACE(REPLACE(p.job_skills, '[', ''), ']', ''), '''', ''), ',')
        ) AS s (skill)
        WHERE p.job_skills IS NOT NULL AND TRIM(s.skill) <> ''
        """
    )

    con.execute(
        """
        INSERT INTO skills_dim
        SELECT ROW_NUMBER() OVER (ORDER BY skills) AS skill_id, skills
        FROM (SELECT DISTINCT skills FROM posting_skill)
        """
    )

    con.execute(
        """
        INSERT INTO job_postings_fact
        SELECT
            p.job_id,
            c.company_id,
            p.job_title_short,
            p.job_title,
            p.job_location,
            p.job_via,
            p.job_schedule_type,
            p.job_work_from_home,
            p.search_location,
            p.job_posted_date,
            p.job_no_degree_mention,
            p.job_health_insurance,
            p.job_country,
            p.salary_rate,
            CAST(p.salary_year_avg AS DECIMAL(12, 2)),
            CAST(p.salary_hour_avg AS DECIMAL(10, 2))
        FROM postings AS p
        JOIN company_dim AS c ON c.name = p.company_name
        """
    )

    con.execute(
        """
        INSERT INTO skills_job_dim
        SELECT DISTINCT ps.job_id, s.skill_id
        FROM posting_skill AS ps
        JOIN skills_dim AS s ON s.skills = ps.skills
        JOIN job_postings_fact AS f ON f.job_id = ps.job_id
        """
    )

    for table in ("company_dim", "skills_dim", "job_postings_fact", "skills_job_dim"):
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<20} {rows:>10,}")

    if export_csv:
        export_normalised_csv(con)

    lo, hi = con.execute(
        "SELECT MIN(job_posted_date)::DATE, MAX(job_posted_date)::DATE FROM job_postings_fact"
    ).fetchone()
    print(f"posting dates       {lo} to {hi}")
    con.close()
    print(f"database written to {DATABASE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true", help="re-download the source CSV"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="also write data/normalised/*.csv for loading into PostgreSQL",
    )
    args = parser.parse_args()
    download(args.refresh)
    load(export_csv=args.export_csv)
