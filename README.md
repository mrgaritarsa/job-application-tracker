# Job Application Tracker

A full-stack web app for tracking a job search: the companies you're interested in, the jobs they've posted, your applications and interview rounds, and the people you know there. A **Job Match** page ranks saved jobs by how many of their required skills you already have.

**Stack:** MySQL · Python 3 / Flask · HTML / CSS (Bootstrap 5, bundled locally)

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Record counts, active applications, response rate, average salary range, applications by status, recent applications, and saved jobs you haven't applied to yet |
| **Companies** | List (with search) / detail / add / edit / delete. The detail page shows the company's jobs and contacts |
| **Jobs** | List (filter by job type) / detail / add / edit / delete. Required skills are stored in a `JSON` column |
| **Applications** | List (filter by status) / detail / add / edit / delete. Interview rounds are stored in a `JSON` column and shown as a timeline |
| **Contacts** | List / detail / add / edit / delete |
| **Job Match** | Enter your skills and see jobs ranked by match percentage, with matched and missing skills for each |

Every delete asks for confirmation, and deletes only run through POST requests. All forms are validated on the server (required fields, lengths, URL/email/phone formats, dates, salary min ≤ max, valid foreign keys, duplicate company names), and the form keeps your input when there's an error.

## Database design

Four tables, all related through foreign keys with `ON DELETE CASCADE`:

```
companies 1───* jobs 1───* applications
    │
    └──────* contacts
```

- `jobs.requirements` – JSON array of skills, e.g. `["Python", "SQL", "Flask"]`
- `applications.interview_data` – JSON array of rounds, e.g. `[{"date": "2026-10-15", "round": "Phone Screen", "notes": "…"}]`
- `jobs.chk_salary` – CHECK constraint so `salary_min <= salary_max`
- `companies.company_name` – UNIQUE

`schema.sql` creates the database and loads sample data (5 companies, 6 jobs, 5 applications, 4 contacts).

## Setup

### 1. Prerequisites
- Python 3.9+
- MySQL 8 (MariaDB 10.5+ also works)

### 2. Get the code and install dependencies
```bash
git clone https://github.com/mrgaritarsa/job-application-tracker.git
cd job-application-tracker
python -m venv venv
```

Activate the virtual environment:

| Terminal | Command |
|---|---|
| Windows PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then `.\venv\Scripts\Activate.ps1` |
| Windows Command Prompt | `venv\Scripts\activate` |
| macOS / Linux | `source venv/bin/activate` |

Then install the packages:
```bash
pip install -r requirements.txt
```

### 3. Create the database
If `mysql` is "not recognized" on Windows, add it to the PATH first (change `8.0` to match the folder name in `C:\Program Files\MySQL`):
```powershell
$env:Path += ";C:\Program Files\MySQL\MySQL Server 8.0\bin"
```

| Terminal | Command |
|---|---|
| Windows PowerShell | `cmd /c "mysql -u root -p < schema.sql"` |
| Windows Command Prompt / macOS / Linux | `mysql -u root -p < schema.sql` |

⚠️ This **drops and recreates** the `job_tracker` database, so it resets any data you've entered.

### 4. Set your database password
The app reads its connection settings from environment variables so no password goes into Git. Use your real MySQL root password:

| Terminal | Command |
|---|---|
| Windows PowerShell | `$env:DB_PASSWORD="your_mysql_password"` |
| Windows Command Prompt | `set DB_PASSWORD=your_mysql_password` |
| macOS / Linux | `export DB_PASSWORD="your_mysql_password"` |

Optional variables: `DB_HOST` (default `localhost`), `DB_PORT` (`3306`), `DB_USER` (`root`), `DB_NAME` (`job_tracker`), `SECRET_KEY`.

### 5. Run
```bash
python app.py
```
Open **http://127.0.0.1:5000**. Press Ctrl+C to stop.

### Troubleshooting
- **"Access denied for user 'root'@'localhost'"**: `DB_PASSWORD` is wrong or not set in this terminal. Set it again, then rerun `python app.py`.
- **"Unknown database 'job_tracker'"**: step 3 hasn't been run yet.
- **"'mysql' is not recognized"**: add MySQL to the PATH (see step 3).
- **"The '<' operator is reserved for future use"**: you're in PowerShell, so use the `cmd /c` version in step 3.
- Environment variables only last for the current terminal window, so set `DB_PASSWORD` again each time you open a new one.

## Job Match algorithm

For each job with listed requirements:

```
match % = (required skills you have) / (total required skills) × 100
```

Matching ignores capitalization (`python` = `Python`). Jobs are sorted by percentage, then by number of matched skills. Example with skills **Python, SQL, Flask**:

```
1. Software Developer at TechCorp – 100% (3/3 skills)
2. Data Analyst at DataCo       –  67% (2/3 skills)   Missing: Tableau
```

You can filter by a minimum match percentage, and click the suggested skills to add them to your search.

## Project structure

```
job-application-tracker/
├── app.py                 # Flask routes, validation, Job Match algorithm
├── database.py            # MySQL connection + query helpers
├── schema.sql             # Creates tables and sample data
├── requirements.txt
├── templates/
│   ├── base.html          # Layout, navbar, flash messages
│   ├── _macros.html       # Reusable pieces (delete button, badges, pills)
│   ├── dashboard.html
│   ├── companies.html     company_form.html     company_detail.html
│   ├── jobs.html          job_form.html         job_detail.html
│   ├── applications.html  application_form.html application_detail.html
│   ├── contacts.html      contact_form.html     contact_detail.html
│   ├── job_match.html
│   └── error.html
├── static/
│   ├── style.css
│   └── vendor/            # Bootstrap 5.3.3 (bundled so it works offline)
├── AI_USAGE.md
└── README.md
```