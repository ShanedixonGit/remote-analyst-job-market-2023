/*
Q4. Which skills command the highest salaries for remote Data Analyst roles?

Population : job_title_short = 'Data Analyst', fully remote, annual salary stated
Grain      : one row per skill
Measures   : postings   = salaried remote postings listing the skill
             avg_salary = mean advertised annual salary
             med_salary = median advertised annual salary, reported because the
                          means are sensitive to single extreme postings

Minimum sample
    Only skills appearing in at least 10 salaried postings are returned. Without
    this guard the ranking is dominated by skills seen in one or two postings,
    where a single figure sets the "average" - see 06_data_quality_checks.sql for
    the unguarded ranking and the evidence behind the threshold.
*/

SELECT
    s.skills AS skill,
    COUNT(*) AS postings,
    ROUND(AVG(f.salary_year_avg), 0) AS avg_salary,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_year_avg), 0) AS med_salary
FROM job_postings_fact AS f
JOIN skills_job_dim AS sj
    ON sj.job_id = f.job_id
JOIN skills_dim AS s
    ON s.skill_id = sj.skill_id
WHERE f.job_title_short = 'Data Analyst'
  AND f.job_work_from_home = TRUE
  AND f.salary_year_avg IS NOT NULL
GROUP BY s.skills
HAVING COUNT(*) >= 10
ORDER BY avg_salary DESC, skill
LIMIT 10;
