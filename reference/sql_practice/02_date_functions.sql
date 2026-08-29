-- Inspect the raw timestamp column

SELECT 
    job_posted_date 
FROM 
job_postings_fact 
LIMIT 10;

-- By selecting followed by a date we can create a string

SELECT '2023-02-19';

-- We can also determine the data type with ::

SELECT '2023-02-19'::DATE;

/* We can modify dates/hours in multiple ways:
1. ::DATE will return just the date
2. AT TIME ZONE 'UTC' AT TIME ZONE 'EST' as date_time (Changing from UTC to EST)
3. EXTRACT(MONTH FROM column_name) AS column_month -- To extract month/day/week
*/

SELECT 
    job_title_short AS title,
    job_location AS location,
    job_posted_date AT TIME ZONE 'UTC' AT TIME ZONE 'EST' AS date_time,
    EXTRACT(WEEK FROM job_posted_date) AS date_week,
    EXTRACT(MONTH FROM job_posted_date) AS date_month,
    EXTRACT(YEAR FROM job_posted_date) AS date_year
FROM 
    job_postings_fact
LIMIT 5;

/* Practice problems
   1. Average yearly salary and average hourly pay by schedule type
   2. Count job postings by month
   3. Companies posting jobs with health insurance, second quarter only
*/

-- 1. Average yearly and hourly pay by schedule type.
SELECT
    job_schedule_type,
    AVG(salary_year_avg),
    AVG(salary_hour_avg)
FROM 
    job_postings_fact
WHERE job_posted_date > '2023-06-01'
GROUP BY job_schedule_type;

-- 2. Postings per month.
SELECT 
    EXTRACT(MONTH FROM job_posted_date AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York') AS job_posted_month,
    COUNT(job_id) AS job_count
FROM 
    job_postings_fact
GROUP BY 
    job_posted_month
ORDER BY 
    job_posted_month;

-- 3. Companies posting health-insurance roles in Q2, one row per posting.
SELECT 
    B.name,
    A.job_health_insurance,
    EXTRACT(QUARTER FROM A.job_posted_date) AS job_posted_quarter
FROM 
    job_postings_fact A
INNER JOIN company_dim B
ON A.company_id = B.company_id
WHERE job_health_insurance = TRUE
AND EXTRACT(QUARTER FROM A.job_posted_date) = 2
ORDER BY B.name ASC;

-- 3b. Same question aggregated to one row per company.
SELECT 
    B.name,
    COUNT(A.job_id) AS job_count,
    EXTRACT(QUARTER FROM A.job_posted_date) AS job_posted_quarter
FROM 
    job_postings_fact A
INNER JOIN company_dim B
    ON A.company_id = B.company_id
WHERE 
    A.job_health_insurance = TRUE
    AND EXTRACT(QUARTER FROM A.job_posted_date) = 2
GROUP BY 
    B.name, job_posted_quarter  -- Group by to remove duplicates
ORDER BY 
    B.name ASC;