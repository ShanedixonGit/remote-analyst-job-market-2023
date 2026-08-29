/*
Data quality checks.

These run against the loaded database and back the caveats stated in the README.
Each block is a standalone SELECT; the runner writes one CSV per block.
*/

-- CHECK: population sizes at each filter step, so every denominator is traceable.
SELECT
    'all postings' AS step,
    COUNT(*) AS postings
FROM job_postings_fact
UNION ALL
SELECT 'data analyst', COUNT(*)
FROM job_postings_fact WHERE job_title_short = 'Data Analyst'
UNION ALL
SELECT 'data analyst, remote', COUNT(*)
FROM job_postings_fact WHERE job_title_short = 'Data Analyst' AND job_work_from_home = TRUE
UNION ALL
SELECT 'data analyst, remote, salaried', COUNT(*)
FROM job_postings_fact
WHERE job_title_short = 'Data Analyst' AND job_work_from_home = TRUE AND salary_year_avg IS NOT NULL
UNION ALL
-- Skill questions can only count postings that actually record a skill, so the
-- denominator for those is smaller than the population above.
SELECT 'data analyst, remote, with skills', COUNT(DISTINCT sj.job_id)
FROM job_postings_fact AS f
JOIN skills_job_dim AS sj ON sj.job_id = f.job_id
WHERE f.job_title_short = 'Data Analyst' AND f.job_work_from_home = TRUE
UNION ALL
SELECT 'data analyst, remote, salaried, with skills', COUNT(DISTINCT sj.job_id)
FROM job_postings_fact AS f
JOIN skills_job_dim AS sj ON sj.job_id = f.job_id
WHERE f.job_title_short = 'Data Analyst' AND f.job_work_from_home = TRUE
  AND f.salary_year_avg IS NOT NULL;

-- CHECK: is job_work_from_home interchangeable with job_location = 'Anywhere'?
-- Any row returned here is a disagreement between the two definitions.
SELECT
    job_work_from_home,
    job_location = 'Anywhere' AS location_is_anywhere,
    COUNT(*) AS postings
FROM job_postings_fact
GROUP BY 1, 2
ORDER BY 1, 2;

-- CHECK: salary outliers in the analysis population, by distance from the median.
-- The single highest posting is an order of magnitude above the rest.
WITH salaried_remote AS (
    SELECT f.job_id, f.job_title, c.name AS company_name, f.job_via, f.salary_year_avg
    FROM job_postings_fact AS f
    JOIN company_dim AS c ON c.company_id = f.company_id
    WHERE f.job_title_short = 'Data Analyst'
      AND f.job_work_from_home = TRUE
      AND f.salary_year_avg IS NOT NULL
),
stats AS (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_year_avg) AS med
    FROM salaried_remote
)
SELECT
    job_title,
    company_name,
    job_via,
    salary_year_avg,
    ROUND(salary_year_avg / MAX(stats.med), 1) AS multiple_of_median
FROM salaried_remote
CROSS JOIN stats
GROUP BY job_title, company_name, job_via, salary_year_avg
ORDER BY salary_year_avg DESC
LIMIT 5;

-- CHECK: effect of that outlier on the headline averages. If a single posting
-- moves a summary statistic materially, the statistic needs a caveat.
WITH salaried_remote AS (
    SELECT salary_year_avg
    FROM job_postings_fact
    WHERE job_title_short = 'Data Analyst'
      AND job_work_from_home = TRUE
      AND salary_year_avg IS NOT NULL
)
SELECT
    COUNT(*) AS postings,
    ROUND(AVG(salary_year_avg), 0) AS avg_all,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_year_avg), 0) AS median_all,
    ROUND(AVG(salary_year_avg) FILTER (WHERE salary_year_avg < 650000), 0) AS avg_excl_top,
    ROUND(MAX(salary_year_avg), 0) AS max_salary
FROM salaried_remote;

-- CHECK: why Q4 needs a minimum sample. This is the unguarded "highest paying
-- skills" ranking - the top of it rests on one or two postings each.
SELECT
    s.skills AS skill,
    COUNT(*) AS postings,
    ROUND(AVG(f.salary_year_avg), 0) AS avg_salary
FROM job_postings_fact AS f
JOIN skills_job_dim AS sj ON sj.job_id = f.job_id
JOIN skills_dim AS s ON s.skill_id = sj.skill_id
WHERE f.job_title_short = 'Data Analyst'
  AND f.job_work_from_home = TRUE
  AND f.salary_year_avg IS NOT NULL
GROUP BY s.skills
ORDER BY avg_salary DESC, skill
LIMIT 10;

-- CHECK: postings in the top 10 of Q1 that carry no skills at all. These are the
-- reason Q2's denominator is smaller than 10.
WITH top_paying_jobs AS (
    SELECT f.job_id, f.job_title, f.salary_year_avg
    FROM job_postings_fact AS f
    WHERE f.job_title_short = 'Data Analyst'
      AND f.job_work_from_home = TRUE
      AND f.salary_year_avg IS NOT NULL
    ORDER BY f.salary_year_avg DESC
    LIMIT 10
)
SELECT
    t.job_title,
    t.salary_year_avg,
    COUNT(sj.skill_id) AS skills_listed
FROM top_paying_jobs AS t
LEFT JOIN skills_job_dim AS sj ON sj.job_id = t.job_id
GROUP BY t.job_id, t.job_title, t.salary_year_avg
ORDER BY t.salary_year_avg DESC;
