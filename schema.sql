DROP DATABASE IF EXISTS job_tracker;

CREATE DATABASE job_tracker;
USE job_tracker;

-- Drop children first, parents last (foreign keys)
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

-- companies
CREATE TABLE companies(
company_id INT AUTO_INCREMENT PRIMARY KEY,
company_name VARCHAR(100) NOT NULL,
industry VARCHAR(50),
website VARCHAR(200),
city VARCHAR(50),
state VARCHAR(50),
notes TEXT
);

-- jobs ((requirements is a JSON array)
CREATE TABLE jobs (
    job_id       INT AUTO_INCREMENT PRIMARY KEY,
    company_id   INT NOT NULL,
    job_title    VARCHAR(100) NOT NULL,
    job_type     ENUM('Full-time','Part-time','Contract','Internship'),
    salary_min   INT,
    salary_max   INT,
    job_url      VARCHAR(300),
    date_posted  DATE,
    requirements JSON,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);


-- applications  (interview_data is JSON)
CREATE TABLE applications (
    application_id    INT AUTO_INCREMENT PRIMARY KEY,
    job_id            INT NOT NULL,
    application_date  DATE NOT NULL,
    status            ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn')
                      DEFAULT 'Applied',
    resume_version    VARCHAR(50),
    cover_letter_sent BOOLEAN DEFAULT FALSE,
    interview_data    JSON,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- contacts
CREATE TABLE contacts (
    contact_id   INT AUTO_INCREMENT PRIMARY KEY,
    company_id   INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title        VARCHAR(100),
    email        VARCHAR(100),
    phone        VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes        TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

USE job_tracker;

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('Tech Solutions Inc',  'Technology',      'www.techsolutions.com',      'Miami',         'Florida',       NULL),
('Data Analytics Corp', 'Data Science',    'www.dataanalytics.com',      'Austin',        'Texas',         NULL),
('Cloud Systems LLC',   'Cloud Computing', 'www.cloudsystems.com',       'Seattle',       'Washington',    NULL),
('Digital Innovations', 'Software',        'www.digitalinnovations.com', 'San Francisco', 'California',    CONCAT('Applied to Senior Developer position on ', CURDATE())),
('Smart Tech Group',    'AI/ML',           'www.smarttech.com',          'Boston',        'Massachusetts', NULL),
('New Tech Corp',       'Technology',      NULL,                         'Denver',        'Colorado',      NULL);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, date_posted) VALUES
(1, 'Software Developer',     'Full-time',  70000,  90000, '2025-01-15'),
(1, 'Database Administrator', 'Full-time',  75000,  95000, '2025-01-10'),
(2, 'Data Analyst',           'Full-time',  65000,  85000, '2025-01-12'),
(3, 'Cloud Engineer',         'Full-time',  80000, 100000, '2025-01-08'),
(4, 'Junior Developer',       'Full-time',  55000,  70000, '2025-01-14'),
(4, 'Senior Developer',       'Full-time',  95000, 120000, '2025-01-14'),
(5, 'ML Engineer',            'Full-time',  90000, 115000, '2025-01-11'),
(1, 'QA Engineer',            'Full-time',  60000,  80000, '2025-01-05'),
(2, 'Business Analyst',       'Full-time',  65000,  85000, '2025-01-06'),
(2, 'Data Scientist',         'Full-time',  85000, 110000, '2025-01-07'),
(3, 'DevOps Engineer',        'Full-time',  80000, 105000, '2025-01-08'),
(3, 'Security Analyst',       'Full-time',  75000,  95000, '2025-01-09'),
(4, 'UI/UX Designer',         'Full-time',  60000,  80000, '2025-01-10'),
(5, 'Product Manager',        'Full-time',  90000, 120000, '2025-01-11'),
(1, 'Technical Writer',       'Contract',   55000,  75000, '2025-01-12'),
(2, 'Intern - Data',          'Internship', 30000,  40000, '2025-01-13'),
(4, 'Intern - Development',   'Internship', 32000,  42000, '2025-01-14'),
(6, 'Software Architect',     'Full-time', 120000, 150000, NULL);

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent) VALUES
(1, '2025-01-16', 'Applied',   'v2.1', TRUE),
(3, '2025-01-13', 'Interview', 'v2.1', TRUE),
(4, '2025-01-09', 'Interview', 'v2.0', FALSE),
(5, '2025-01-15', 'Applied',   'v2.1', TRUE),
(7, '2025-01-12', 'Screening', 'v2.1', TRUE),
(6, CURDATE(),    'Applied',   'v3.0', TRUE);

-- interview_data JSON
UPDATE applications
SET interview_data = JSON_OBJECT(
    'interview_rounds',    2,
    'interviewers',        JSON_ARRAY('Sarah Johnson', 'Mike Chen', 'David Brown'),
    'technical_questions', JSON_ARRAY('SQL joins', 'Python basics', 'API design'),
    'feedback',            'Strong technical skills, good communication',
    'next_steps',          'Offer extended!',
    'offer_amount',        85000
)
WHERE application_id = 2;

UPDATE applications
SET interview_data = JSON_OBJECT(
    'interview_rounds',    1,
    'interviewers',        JSON_ARRAY('Emily Williams'),
    'technical_questions', JSON_ARRAY('Database normalization', 'Transaction isolation'),
    'feedback',            'Needs more experience with cloud platforms'
)
WHERE application_id = 5;

INSERT INTO contacts (company_id, contact_name, title, email) VALUES
(1, 'Sarah Johnson',  'HR Manager',          'sjohnson@techsolutions.com'),
(2, 'Michael Chen',   'Technical Recruiter', 'mchen@dataanalytics.com'),
(3, 'Emily Williams', 'Hiring Manager',      'ewilliams@cloudsystems.com'),
(4, 'David Brown',    'Senior Developer',    NULL),
(5, 'Lisa Garcia',    'Talent Acquisition',  'lgarcia@smarttech.com'),
(4, 'Robert Kim',     'Engineering Manager', 'rkim@digitalinnovations.com');

UPDATE jobs SET requirements = JSON_ARRAY('Python', 'SQL', 'Git')                  WHERE job_id = 1;
UPDATE jobs SET requirements = JSON_ARRAY('SQL', 'Excel', 'Tableau')               WHERE job_id = 3;
UPDATE jobs SET requirements = JSON_ARRAY('SQL', 'MySQL', 'Backup & Recovery')     WHERE job_id = 2;
UPDATE jobs SET requirements = JSON_ARRAY('AWS', 'Linux', 'Docker')                WHERE job_id = 4;
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Flask', 'SQL')                WHERE job_id = 5;
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Flask', 'SQL', 'Docker')      WHERE job_id = 6;
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'TensorFlow', 'SQL')           WHERE job_id = 7;
UPDATE jobs SET requirements = JSON_ARRAY('Selenium', 'Python', 'Git')             WHERE job_id = 8;
UPDATE jobs SET requirements = JSON_ARRAY('SQL', 'Excel', 'Tableau')               WHERE job_id = 9;
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'SQL', 'Machine Learning')     WHERE job_id = 10;
UPDATE jobs SET requirements = JSON_ARRAY('Docker', 'Kubernetes', 'AWS', 'Linux')  WHERE job_id = 11;
UPDATE jobs SET requirements = JSON_ARRAY('Networking', 'Linux', 'Python')         WHERE job_id = 12;
UPDATE jobs SET requirements = JSON_ARRAY('Figma', 'HTML', 'CSS')                  WHERE job_id = 13;
UPDATE jobs SET requirements = JSON_ARRAY('SQL', 'Agile', 'Communication')         WHERE job_id = 14;
UPDATE jobs SET requirements = JSON_ARRAY('Technical Writing', 'Git', 'Markdown')  WHERE job_id = 15;
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'SQL', 'Excel')                WHERE job_id = 16;
UPDATE jobs SET requirements = JSON_ARRAY('Python', 'Flask', 'HTML', 'CSS')        WHERE job_id = 17;
UPDATE jobs SET requirements = JSON_ARRAY('Java', 'System Design', 'AWS', 'SQL')   WHERE job_id = 18;

-- Indexes
CREATE INDEX idx_job_title        ON jobs(job_title);
CREATE INDEX idx_company_type     ON jobs(company_id, job_type);
CREATE INDEX idx_app_status       ON applications(status);
CREATE INDEX idx_company_industry ON companies(industry);
