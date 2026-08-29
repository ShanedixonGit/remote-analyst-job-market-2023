/*
Q2. Which skills do the highest-paying remote Data Analyst postings ask for?

Population : the top 10 postings from Q1
Grain      : one row per skill
Measures   : postings  = how many of those 10 postings list the skill
             coverage  = postings as a share of the top-10 postings that list any
                         skill at all (the correct denominator; some postings have
                         no skills recorded)
Ties       : ordered by postings then skill name so the output is deterministic.
*/

WITH top_paying_jobs AS (
    SELECT
        f.job_id,
        f.salary_year_avg
    FROM job_postings_fact AS f
    WHERE f.job_title_short = 'Data Analyst'
      AND f.job_work_from_home = TRUE
      AND f.salary_year_avg IS NOT NULL
    ORDER BY f.salary_year_avg DESC
    LIMIT 10
),

jobs_with_skills AS (
    SELECT COUNT(DISTINCT sj.job_id) AS n_jobs
    FROM top_paying_jobs AS t
    JOIN skills_job_dim AS sj
        ON sj.job_id = t.job_id
)

SELECT
    s.skills AS skill,
    COUNT(DISTINCT sj.job_id) AS postings,
    ROUND(100.0 * COUNT(DISTINCT sj.job_id) / MAX(w.n_jobs), 1) AS coverage_pct
FROM top_paying_jobs AS t
JOIN skills_job_dim AS sj
    ON sj.job_id = t.job_id
JOIN skills_dim AS s
    ON s.skill_id = sj.skill_id
CROSS JOIN jobs_with_skills AS w
GROUP BY s.skills
ORDER BY postings DESC, skill
LIMIT 15;
