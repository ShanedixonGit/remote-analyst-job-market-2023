/*
Loading the normalised tables into PostgreSQL.

The reproducible pipeline uses DuckDB, which needs no server. Use this only if you
want the analysis in PostgreSQL instead. The analysis queries in sql/ are standard
SQL and run unchanged on either engine.

    1. python scripts/build_database.py --export-csv
    2. createdb job_market
    3. psql -d job_market -f sql/00_schema.sql
    4. psql -d job_market -f sql/00_postgres_load.sql

Paths below are relative to the repository root, so run psql from there. \copy is a
client-side command, which avoids the server-side permission errors that COPY hits
when the server cannot read your local files.
*/

\copy company_dim       FROM 'data/normalised/company_dim.csv'       WITH (FORMAT csv, HEADER true);
\copy skills_dim        FROM 'data/normalised/skills_dim.csv'        WITH (FORMAT csv, HEADER true);
\copy job_postings_fact FROM 'data/normalised/job_postings_fact.csv' WITH (FORMAT csv, HEADER true);
\copy skills_job_dim    FROM 'data/normalised/skills_job_dim.csv'    WITH (FORMAT csv, HEADER true);

ANALYZE company_dim;
ANALYZE skills_dim;
ANALYZE job_postings_fact;
ANALYZE skills_job_dim;
