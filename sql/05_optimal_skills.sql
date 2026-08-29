/*
Q5. Which skills combine high demand with high pay?

Population : job_title_short = 'Data Analyst', fully remote, annual salary stated
Grain      : one row per skill
Measures   : postings   = salaried remote postings listing the skill (demand)
             avg_salary = mean advertised annual salary
             med_salary = median advertised annual salary
             demand_pct = postings as a share of all salaried remote postings

Reading it
    A skill is "optimal" when it sits high on both measures. The output is ordered
    by demand so the volume leaders come first; the accompanying scatter chart
    plots demand against pay, which is where the trade-off is actually visible.
    Same minimum sample of 10 postings as Q4.
*/

WITH salaried_remote_postings AS (
    SELECT f.job_id, f.salary_year_avg
    FROM job_postings_fact AS f
    WHERE f.job_title_short = 'Data Analyst'
      AND f.job_work_from_home = TRUE
      AND f.salary_year_avg IS NOT NULL
),

population AS (
    SELECT COUNT(*) AS n_postings FROM salaried_remote_postings
)

SELECT
    s.skills AS skill,
    COUNT(*) AS postings,
    ROUND(100.0 * COUNT(*) / MAX(p.n_postings), 1) AS demand_pct,
    ROUND(AVG(r.salary_year_avg), 0) AS avg_salary,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY r.salary_year_avg), 0) AS med_salary
FROM salaried_remote_postings AS r
JOIN skills_job_dim AS sj
    ON sj.job_id = r.job_id
JOIN skills_dim AS s
    ON s.skill_id = sj.skill_id
CROSS JOIN population AS p
GROUP BY s.skills
HAVING COUNT(*) >= 10
ORDER BY postings DESC, avg_salary DESC
LIMIT 20;
