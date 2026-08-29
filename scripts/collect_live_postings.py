"""Collect current job postings from public APIs into the project's star schema.

The live database is built with the same sql/00_schema.sql and the same skill
vocabulary as the 2023 database, so the analysis queries in sql/ run against it
unchanged. That is the point: one schema, one set of queries, two datasets.

Sources (all keyless, all public APIs, no scraping of pages that forbid it):
    Arbeitnow   https://www.arbeitnow.com/api/job-board-api
    Jobicy      https://jobicy.com/api/v2/remote-jobs
    RemoteOK    https://remoteok.com/api
    Himalayas   https://himalayas.app/jobs/api

Coverage
    None of these publishes a salary field with meaningful coverage for analyst
    roles. Postings therefore load with salary_year_avg NULL, and the salary
    queries return no rows rather than a number built on nothing. Demand queries
    work normally. The coverage report printed at the end states this per run.

Usage:
    python scripts/collect_live_postings.py [--pages 15]
"""

import argparse
import html
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BASE_DB = DATA_DIR / "job_market.duckdb"
LIVE_DB = DATA_DIR / "live_market.duckdb"
SCHEMA = ROOT / "sql" / "00_schema.sql"

USER_AGENT = "remote-analyst-job-market-2023 (portfolio project)"

# Titles this project analyses, matched as whole words against the posting title.
ROLE_PATTERN = re.compile(
    r"\b(data analyst|analyst|analytics|business intelligence|bi developer"
    r"|data scientist|data engineer)\b",
    re.I,
)

# Skill names that are also ordinary English or German words. Keyword matching
# cannot separate "R" the language from "R" mid-sentence, so these are excluded
# rather than reported with known false positives.
AMBIGUOUS = {
    "r", "c", "go", "ai", "bi", "word", "flow", "sheets", "access", "express",
    "unify", "sas", "swift", "ruby", "julia", "dart", "crystal", "chef", "puppet",
}

ATTRIBUTION = (
    "Live postings: Arbeitnow (arbeitnow.com), Jobicy (jobicy.com), "
    "Remote OK (remoteok.com), Himalayas (himalayas.app)"
)


def get(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def strip_html(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", markup or "")).strip()


def clean(value) -> str | None:
    text = (value or "").strip()
    return text or None


def from_arbeitnow(pages: int) -> list[dict]:
    out, url, seen = [], "https://www.arbeitnow.com/api/job-board-api", 0
    while url and seen < pages:
        payload = get(url)
        for job in payload.get("data", []):
            out.append(
                {
                    "source": "arbeitnow",
                    "title": clean(job.get("title")),
                    "company": clean(job.get("company_name")),
                    "location": clean(job.get("location")),
                    "remote": bool(job.get("remote")),
                    "schedule": "|".join(job.get("job_types") or []) or None,
                    "posted": job.get("created_at"),
                    "text": strip_html(job.get("description")),
                    "url": clean(job.get("url")),
                }
            )
        url = payload.get("links", {}).get("next")
        seen += 1
    return out


def from_jobicy() -> list[dict]:
    out = []
    for industry in ("data-science", "business", "engineering"):
        payload = get(
            f"https://jobicy.com/api/v2/remote-jobs?count=100&industry={industry}"
        )
        for job in payload.get("jobs", []):
            out.append(
                {
                    "source": "jobicy",
                    "title": clean(job.get("jobTitle")),
                    "company": clean(job.get("companyName")),
                    "location": clean(job.get("jobGeo")),
                    "remote": True,
                    "schedule": "|".join(job.get("jobType") or []) or None,
                    "posted": job.get("pubDate"),
                    "text": strip_html(job.get("jobDescription")),
                    "url": clean(job.get("url")),
                }
            )
    return out


def from_remoteok() -> list[dict]:
    payload = get("https://remoteok.com/api")
    rows = payload[1:] if isinstance(payload, list) else []
    return [
        {
            "source": "remoteok",
            "title": clean(job.get("position")),
            "company": clean(job.get("company")),
            "location": clean(job.get("location")),
            "remote": True,
            "schedule": None,
            "posted": job.get("date"),
            "text": strip_html(job.get("description")),
            "url": clean(job.get("url")),
        }
        for job in rows
    ]


def from_himalayas() -> list[dict]:
    out = []
    for offset in range(0, 200, 50):
        payload = get(f"https://himalayas.app/jobs/api?limit=50&offset={offset}")
        jobs = payload.get("jobs", [])
        if not jobs:
            break
        for job in jobs:
            out.append(
                {
                    "source": "himalayas",
                    "title": clean(job.get("title")),
                    "company": clean(job.get("companyName")),
                    "location": "|".join(job.get("locationRestrictions") or []) or None,
                    "remote": True,
                    "schedule": clean(job.get("employmentType")),
                    "posted": job.get("pubDate"),
                    "text": strip_html(job.get("description")),
                    "url": clean(job.get("applicationLink")),
                }
            )
    return out


def collect(pages: int) -> list[dict]:
    postings = []
    for name, loader in [
        ("arbeitnow", lambda: from_arbeitnow(pages)),
        ("jobicy", from_jobicy),
        ("remoteok", from_remoteok),
        ("himalayas", from_himalayas),
    ]:
        try:
            rows = loader()
            postings.extend(rows)
            print(f"  {name:<11} {len(rows):>5} postings")
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as error:
            print(f"  {name:<11} unavailable: {error}")
    return postings


def classify(title: str) -> str:
    """Map a live title onto the job_title_short values used in the 2023 data."""
    lowered = title.lower()
    for needle, short in [
        ("data analyst", "Data Analyst"),
        ("business intelligence", "Business Analyst"),
        ("bi developer", "Business Analyst"),
        ("business analyst", "Business Analyst"),
        ("data scientist", "Data Scientist"),
        ("data engineer", "Data Engineer"),
    ]:
        if needle in lowered:
            return short
    return "Data Analyst" if "analy" in lowered else "Other"


def main(pages: int) -> None:
    if not BASE_DB.exists():
        raise SystemExit("build the 2023 database first: python scripts/build_database.py")

    base = duckdb.connect(str(BASE_DB), read_only=True)
    vocabulary = {
        term: skill_id
        for skill_id, term in base.execute("SELECT skill_id, skills FROM skills_dim").fetchall()
    }
    base.close()

    matchers = {
        term: re.compile(
            r"(?<![A-Za-z0-9+#.])" + re.escape(term) + r"(?![A-Za-z0-9+#])", re.I
        )
        for term in vocabulary
        if term not in AMBIGUOUS and not (len(term) < 3 and term.isalpha())
    }

    print("collecting")
    raw = collect(pages)
    postings = [job for job in raw if job["title"] and ROLE_PATTERN.search(job["title"])]
    print(f"  {'-' * 17}\n  fetched {len(raw):,}, analyst-type {len(postings):,}")

    # Same posting syndicated to several boards: keep one copy per title+company.
    unique, seen = [], set()
    for job in postings:
        key = ((job["company"] or "").lower(), job["title"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    print(f"  after de-duplication {len(unique):,}")

    collected_at = datetime.now(timezone.utc)
    if LIVE_DB.exists():
        LIVE_DB.unlink()
    con = duckdb.connect(str(LIVE_DB))
    con.execute(SCHEMA.read_text())

    companies, rows, pairs = {}, [], []
    for job_id, job in enumerate(unique, start=1):
        name = job["company"] or "Unknown"
        company_id = companies.setdefault(name, len(companies) + 1)
        skills = {
            vocabulary[term] for term, pattern in matchers.items() if pattern.search(job["text"])
        }
        pairs.extend((job_id, skill_id) for skill_id in skills)
        rows.append(
            (
                job_id,
                company_id,
                classify(job["title"]),
                job["title"],
                "Anywhere" if job["remote"] else job["location"],
                job["source"],
                job["schedule"],
                job["remote"],
                job["location"],
                collected_at,
                None,
                None,
                None,
                None,
                # No source publishes salary with usable coverage for these roles.
                None,
                None,
            )
        )

    con.executemany(
        "INSERT INTO company_dim VALUES (?, ?)",
        [(cid, name) for name, cid in companies.items()],
    )
    con.executemany(
        "INSERT INTO skills_dim VALUES (?, ?)",
        [(skill_id, term) for term, skill_id in vocabulary.items()],
    )
    con.executemany(
        "INSERT INTO job_postings_fact VALUES (" + ", ".join(["?"] * 16) + ")", rows
    )
    con.executemany("INSERT INTO skills_job_dim VALUES (?, ?)", sorted(set(pairs)))

    with_skills = con.execute(
        "SELECT COUNT(DISTINCT job_id) FROM skills_job_dim"
    ).fetchone()[0]
    with_salary = con.execute(
        "SELECT COUNT(salary_year_avg) FROM job_postings_fact"
    ).fetchone()[0]
    by_source = con.execute(
        "SELECT job_via AS source, COUNT(*) FROM job_postings_fact GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall()
    con.close()

    print(f"\nlive database: {LIVE_DB.relative_to(ROOT)}")
    print(f"  collected at    {collected_at:%Y-%m-%d %H:%M}Z")
    print(f"  postings        {len(rows):,}")
    for source, count in by_source:
        print(f"    {source:<13} {count:>4}")
    print(f"  with skills     {with_skills:,} ({100 * with_skills / len(rows):.0f}%)")
    print(f"  with salary     {with_salary:,} ({100 * with_salary / len(rows):.0f}%)")
    if with_salary == 0:
        print("  salary queries will return no rows, which is the honest result here")
    print(f"\n{ATTRIBUTION}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=15, help="Arbeitnow pages (default 15)")
    main(parser.parse_args().pages)
