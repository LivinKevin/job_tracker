# Kev's Job Tracker

A web app for tracking job applications. It keeps companies, job postings, applications and recruiter contacts in a MySQL database, and includes a **Job Match** page that ranks jobs by how well they fit your skills.

## Features

- **Dashboard**: totals, applications by status, response rate, companies with the most jobs, average salary by industry, and recent applications.
- **Companies, Jobs, Applications, Contacts**: list, detail view, add, edit and delete for each, with form validation and a confirmation before deleting.
- **Job Match**: enter your skills (for example `Python, SQL, Flask`) and see jobs ranked by match percentage, with the skills you matched and the ones you're missing.
- **JSON columns**: `jobs.requirements` stores a JSON array of required skills, and `applications.interview_data` stores interview notes as a JSON object.

## Tech stack

| Layer | Tool |
|---|---|
| Database | MySQL |
| Backend | Python 3 + Flask |
| Frontend | HTML, CSS, Bootstrap 5 (loaded from a CDN) |
| Database driver | mysql-connector-python |

## Setup

### 1. Prerequisites
- Python 3.10 or newer
- MySQL Server (and optionally MySQL Workbench)

### 2. Get the code
```bash
git clone https://github.com/LivinKevin/job_tracker
cd job_tracker
```

### 3. Create a virtual environment and install dependencies
Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Create the database
`schema.sql` drops and recreates the `job_tracker` database, creates the four tables, and loads sample data. Run it with either:

- **MySQL Workbench:** open `schema.sql` and run the whole script, or
- **Command line:**
  ```bash
  mysql -u root -p < schema.sql
  ```

> Running it again resets the database to the sample data.

### 5. Set your database password
The app reads its connection settings from environment variables, so no password is stored in the code.

| Variable | Default | Meaning |
|---|---|---|
| `DB_PASSWORD` | *(empty)* | MySQL password |
| `DB_USER` | `root` | MySQL user |
| `DB_HOST` | `localhost` | MySQL host |

Windows (PowerShell). Use **single quotes**, which keeps characters like `$` in a password intact:
```powershell
$env:DB_PASSWORD = 'your password here'
```
macOS / Linux:
```bash
export DB_PASSWORD='your password here'
```

### 6. Run the app
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

## Project structure

```
job_tracker/
├── app.py              # Flask app: all routes (dashboard, CRUD, job match)
├── database.py         # get_db(): MySQL connection from environment variables
├── schema.sql          # Creates the database, tables and sample data
├── requirements.txt    # Python dependencies
├── AI_USAGE.md         # How GenAI tools were used
├── README.md
├── static/
│   └── style.css       # Theme layered over Bootstrap
└── templates/
    ├── base.html                # Layout, title bar and navigation
    ├── _icons.html              # Shared inline SVG icons
    ├── dashboard.html
    ├── companies.html           company_form.html       company_detail.html
    ├── jobs.html                job_form.html           job_detail.html
    ├── applications.html        application_form.html   application_detail.html
    ├── contacts.html            contact_form.html       contact_detail.html
    └── job_match.html
```

## Database

Four tables with foreign keys. Deleting a parent row removes its children (`ON DELETE CASCADE`).

```
companies ──< jobs ──< applications
    └──────< contacts
```

| Table | Key columns |
|---|---|
| `companies` | `company_id`, `company_name`, `industry`, `website`, `city`, `state`, `notes` |
| `jobs` | `job_id`, `company_id` → companies, `job_title`, `job_type` (ENUM), `salary_min`, `salary_max`, `job_url`, `date_posted`, `requirements` (JSON array) |
| `applications` | `application_id`, `job_id` → jobs, `application_date`, `status` (ENUM), `resume_version`, `cover_letter_sent`, `interview_data` (JSON) |
| `contacts` | `contact_id`, `company_id` → companies, `contact_name`, `title`, `email`, `phone`, `linkedin_url`, `notes` |

`schema.sql` also creates indexes on `jobs(job_title)`, `jobs(company_id, job_type)`, `applications(status)` and `companies(industry)`.

## How Job Match works

1. Skills you enter are split on commas and compared case-insensitively (`python` matches `Python`).
2. For every job with listed requirements, the match is `matched skills ÷ required skills × 100`.
3. Jobs are sorted by percentage, then by number of matched skills, then by title. Jobs matching none of your skills are hidden.

Example: with `Python, SQL, Flask`, a job requiring `Python, Flask, SQL` is 100% (3/3), and one requiring `Python, Flask, SQL, Docker` is 75% (3/4, missing Docker).

## Notes

- This is a development server (`debug=True`). It is not meant for production use.
- Some sample `requirements` skills in `schema.sql` are made-up demo data so Job Match has something to rank.
- GenAI usage is documented in [AI_USAGE.md](AI_USAGE.md).
