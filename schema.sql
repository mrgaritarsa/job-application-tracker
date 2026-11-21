-- =============================================================
-- Job Application Tracker - database schema + sample data
-- Run with:  mysql -u root -p < schema.sql
-- =============================================================

DROP DATABASE IF EXISTS job_tracker;
CREATE DATABASE job_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE job_tracker;

-- -------------------------------------------------------------
-- companies
-- -------------------------------------------------------------
CREATE TABLE companies (
    company_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry     VARCHAR(50),
    website      VARCHAR(200),
    city         VARCHAR(50),
    state        VARCHAR(50),
    notes        TEXT,
    UNIQUE KEY uq_company_name (company_name)
);

-- -------------------------------------------------------------
-- jobs  (requirements = JSON array of skills, e.g. ["Python","SQL"])
-- -------------------------------------------------------------
CREATE TABLE jobs (
    job_id       INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE CASCADE,
    CONSTRAINT chk_salary CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max)
);

-- -------------------------------------------------------------
-- applications  (interview_data = JSON array of interview rounds)
-- -------------------------------------------------------------
CREATE TABLE applications (
    application_id    INT PRIMARY KEY AUTO_INCREMENT,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    interview_data    JSON,
    CONSTRAINT fk_app_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- contacts
-- -------------------------------------------------------------
CREATE TABLE contacts (
    contact_id   INT PRIMARY KEY AUTO_INCREMENT,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    CONSTRAINT fk_contact_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE CASCADE
);

-- =============================================================
-- Sample data
-- =============================================================
INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp',      'Software',   'https://techcorp.example.com',  'Austin',   'TX', 'Fast-growing SaaS company.'),
('DataCo',        'Analytics',  'https://dataco.example.com',    'Chicago',  'IL', 'Strong data culture.'),
('CloudNine',     'Cloud',      'https://cloudnine.example.com', 'Seattle',  'WA', NULL),
('HealthPlus',    'Healthcare', 'https://healthplus.example.com','Boston',   'MA', 'Referral from a classmate.'),
('GreenEnergy',   'Energy',     'https://greenenergy.example.com','Denver',  'CO', NULL);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer',      'Full-time',  75000,  95000, 'https://techcorp.example.com/jobs/1',   '2026-10-01', '["Python", "SQL", "Flask"]'),
(2, 'Data Analyst',            'Full-time',  65000,  80000, 'https://dataco.example.com/jobs/7',     '2026-10-05', '["Python", "SQL", "Tableau"]'),
(3, 'Cloud Engineer Intern',   'Internship', 40000,  50000, 'https://cloudnine.example.com/jobs/3',  '2026-10-10', '["AWS", "Linux", "Python", "Docker"]'),
(4, 'Junior Web Developer',    'Contract',   55000,  70000, 'https://healthplus.example.com/jobs/2', '2026-10-12', '["HTML", "CSS", "JavaScript", "Flask"]'),
(5, 'Database Administrator',  'Full-time',  70000,  90000, 'https://greenenergy.example.com/jobs/5','2026-10-15', '["SQL", "MySQL", "Linux"]'),
(1, 'QA Tester',               'Part-time',  30000,  40000, NULL,                                    '2026-10-20', '["Testing", "Python", "Selenium"]');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-10-03', 'Interview', 'v2-software', TRUE,
    '[{"date": "2026-10-15", "round": "Phone Screen", "notes": "Talked with recruiter"}, {"date": "2026-10-22", "round": "Technical", "notes": "Live coding in Python"}]'),
(2, '2026-10-07', 'Screening', 'v1-data',     TRUE,  '[]'),
(3, '2026-10-11', 'Applied',   'v2-software', FALSE, '[]'),
(4, '2026-10-14', 'Rejected',  'v1-web',      TRUE,
    '[{"date": "2026-10-25", "round": "Phone Screen", "notes": "Not a fit for contract role"}]'),
(5, '2026-10-16', 'Offer',     'v1-data',     TRUE,
    '[{"date": "2026-10-20", "round": "Phone Screen", "notes": ""}, {"date": "2026-10-28", "round": "Onsite", "notes": "Met the team"}]');

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Jane Smith',    'Technical Recruiter',  'jane.smith@techcorp.example.com', '512-555-0101', 'https://linkedin.com/in/janesmith', 'Very responsive.'),
(2, 'Mark Lee',      'Hiring Manager',       'mark.lee@dataco.example.com',     '312-555-0144', NULL,                                 NULL),
(4, 'Priya Patel',   'Software Engineer',    'priya@healthplus.example.com',    NULL,           'https://linkedin.com/in/priyapatel', 'Gave me the referral.'),
(5, 'Carlos Rivera', 'HR Coordinator',       'carlos@greenenergy.example.com',  '303-555-0199', NULL,                                 'Sent offer letter.');
