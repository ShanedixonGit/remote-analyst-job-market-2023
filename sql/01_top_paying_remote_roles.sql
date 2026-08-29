/*
Q1. Which remote Data Analyst postings advertised the highest salaries in 2023?

Population : job_title_short = 'Data Analyst', fully remote, annual salary stated
Grain      : one row per job posting
Note       : job_work_from_home = TRUE is equivalent to job_location = 'Anywhere'
             in this dataset (verified in 06_data_quality_checks.sql), so only the
             boolean flag is used.
*/

SELECT
    f.job_id,
    f.job_title,
    c.name AS company_name,
    f.job_schedule_type,
    f.salary_year_avg,
    f.job_posted_date::DATE AS job_posted_date
FROM job_postings_fact AS f
JOIN company_dim AS c
    ON c.company_id = f.company_id
WHERE f.job_title_short = 'Data Analyst'
  AND f.job_work_from_home = TRUE
  AND f.salary_year_avg IS NOT NULL
ORDER BY f.salary_year_avg DESC
LIMIT 10;
