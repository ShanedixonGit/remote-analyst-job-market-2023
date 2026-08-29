/*
Supporting query: demand share for every skill, unranked and unlimited.

Question 3 returns only the top 10, which is right for a ranking but wrong as a
lookup: a skill outside the 2023 top 10 is not a skill with zero demand. The
live-versus-2023 comparison chart joins this table on both sides so that every
skill it plots carries its true share in each dataset.

Population and measure are identical to 03_most_in_demand_skills.sql.
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
ORDER BY postings DESC, skill;
