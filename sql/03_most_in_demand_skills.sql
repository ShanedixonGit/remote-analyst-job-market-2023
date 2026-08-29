/*
Q3. Which skills are most in demand for remote Data Analyst roles?

Population : job_title_short = 'Data Analyst', fully remote. No salary filter -
             demand is measured across every posting, not only salaried ones.
Grain      : one row per skill
Measures   : postings     = remote Data Analyst postings listing the skill
             share_of_pct = postings as a share of remote Data Analyst postings
                            that list at least one skill
*/

WITH remote_analyst_postings AS (
    SELECT f.job_id
    FROM job_postings_fact AS f
    WHERE f.job_title_short = 'Data Analyst'
      AND f.job_work_from_home = TRUE
),

postings_with_skills AS (
    SELECT COUNT(DISTINCT sj.job_id) AS n_postings
    FROM remote_analyst_postings AS r
    JOIN skills_job_dim AS sj
        ON sj.job_id = r.job_id
)

SELECT
    s.skills AS skill,
    COUNT(DISTINCT sj.job_id) AS postings,
    ROUND(100.0 * COUNT(DISTINCT sj.job_id) / MAX(p.n_postings), 1) AS share_of_pct
FROM remote_analyst_postings AS r
JOIN skills_job_dim AS sj
    ON sj.job_id = r.job_id
JOIN skills_dim AS s
    ON s.skill_id = sj.skill_id
CROSS JOIN postings_with_skills AS p
GROUP BY s.skills
ORDER BY postings DESC, skill
LIMIT 10;
