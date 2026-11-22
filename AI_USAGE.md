# AI Usage Documentation — Job Application Tracker
---

## 1. Tools Used
- **Claude (Anthropic, Claude Opus 5.5)**: generated the WebApp wireframe. Aided with, Flask routes, templates, CSS, the Job Match algorithm.

---

## 2. Where I Used AI vs. Where I Worked Alone

This table shows how I split the work. It's here so the reader knows which parts are my own and which were AI-assisted.

| Project Part | Points | Who did it | Notes |
|---|---|---|---|
| Database design: the 4 tables, keys, relationships | 25 | Me | I designed the schema from the spec myself, then asked AI to check it for mistakes |
| `schema.sql` script + sample data | (DB) | AI Assisted | AI generated sample INSERT rows and JSON examples; I checked them against my schema |
| JSON columns (`requirements`, `interview_data`) | (DB) | Me, AI for syntax | I chose what keys go inside the JSON |
| `database.py` connection functions | (CRUD) | AI Assisted | Boilerplate |
| CRUD routes in `app.py` | 25 |AI assisted for the firs table, me the rest | I used AI for one table, understood the pattern, then wrote the other three myself |
| Form validation | (CRUD) | Me, AI for edge cases | I decided which fields are required and what values are allowed |
| Delete with confirmation | (CRUD) | AI assisted | JavaScript confirm / confirmation page |
| HTML templates / `base.html` | 15 | AI assisted | Bootstrap layout and nav bar |
| UI design choices: colors, layout, flow | 15 | Me | My own decisions about what the user sees |
| Dashboard statistics queries | (UI) | Me for which stats to show, AI for SQL help | |
| Job Match algorithm | 15 | AI Assisted (the spec suggests this) | I must be able to explain every line of it |
| Testing the app end-to-end | — | Me | AI can't run my app or confirm it works |
| Git commits & GitHub | 10 | Me | Commit messages written by me, committed regularly |
| `README.md` setup instructions | — | Me, AI for formatting | I tested every setup step on a clean run |
| Demo video (3–7 min) | — | Me | |
| This AI_USAGE.md | 10 | Me (template structure from AI) | All reflections are my own |

---

## 3. Key Prompts 🤖 AI-OK (but log your real ones)

> Copy in the prompts you **actually used**. Below are good example prompts for this project. If you use one, keep it and add the result. Delete the ones you didn't use. The grader wants to see **specific** prompts, not vague ones.

### Database
1. **Prompt:** "Here is my MySQL schema for a job tracker with 4 tables:

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

 Review it for missing foreign keys, ON DELETE behavior, and data type problems. Don't rewrite it, just list issues."
   - **Result:** No missing foreign keys: `jobs → companies`, `applications → jobs` and `contacts → companies` are all defined. Issues it raised:
     - Every foreign key uses `ON DELETE CASCADE`. Deleting one company silently deletes all of its jobs, applications and contacts, so you lose your application history. `RESTRICT`, or a "soft delete" flag, would be safer for real use.
     - The JSON columns accept any valid JSON. Nothing stops `requirements` from being an object instead of an array, so the app has to enforce the structure.
     - Adding a new status or job type to an `ENUM` requires an `ALTER TABLE`. A lookup table is more flexible.
     - There are no `created_at`/`updated_at` timestamps, so you can't tell when a status changed.
     - Contacts are linked to companies, not to specific applications.
     - Not a problem: `BOOLEAN` is stored as `TINYINT(1)`, the `salary_min <= salary_max` CHECK constraint works in MySQL 8.0.16+, and InnoDB automatically indexes foreign key columns.
   - **What I did with it:** kept CASCADE because the app warns before deleting and it keeps the database clean; noted timestamps as a future improvement.

2. **Prompt:** "Generate 5 realistic sample INSERT statements for each of these tables, including valid JSON for the `requirements` column (a list of skills) and the `interview_data` column."
   - **Result:** It generated companies across different industries (software, analytics, cloud, healthcare, energy), jobs covering all four job types with realistic salary ranges, and applications in different statuses. `requirements` uses JSON arrays like `["Python", "SQL", "Flask"]`. `interview_data` uses arrays of objects like `[{"date": "2026-10-15", "round": "Phone Screen", "notes": "Talked with recruiter"}]`, with `'[]'` for applications that have no interviews yet. It pointed out that the inserts must run in order (companies → jobs → applications/contacts) so the foreign key IDs exist.
   - **What I did with it:**  kept it as sample data / replaced some companies with ones I'm actually applying to. Note: schema.sql has 6 jobs but only 4 contacts. Say so, or add a 5th contact.

### Backend / CRUD
3. **Prompt:** "Write Flask routes for full CRUD on a `companies` table using mysql-connector-python with parameterized queries. Use these columns: [list]. Explain each route."
   - **Result:** Six routes:
     - `GET /companies`: lists companies, with an optional `?q=` search on name, industry or city, plus job and contact counts.
     - `GET /companies/<id>`: shows the detail page with that company's jobs and contacts, or a 404.
     - `GET/POST /companies/new`: GET shows the form. POST validates the input and runs an `INSERT`, then redirects to the new record.
     - `GET/POST /companies/<id>/edit`: the same pattern with an `UPDATE`.
     - `POST /companies/<id>/delete`: deletes and redirects. It's POST-only so a link or a web crawler can't delete data.
     
     All queries use `%s` / `%(name)s` placeholders. Validation checks that the name is present, field lengths, the URL format, and duplicate names (case-insensitive). On an error the form is re-shown with the user's input kept.
   - **What I did with it:** implemented it

4. **Prompt:** "Write a Flask route that lists all jobs with their company name using a JOIN between `jobs` and `companies`."
   - **Result:**
     `SELECT j.*, c.company_name, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS app_count FROM jobs j JOIN companies c ON c.company_id = j.company_id ORDER BY j.date_posted DESC`.
     It uses an INNER JOIN because every job must have a company. The subquery counts applications per job. An optional `?type=` filter adds `WHERE j.job_type = %s`, but only after checking the value against the allowed job types.
   - **What I did with it:** implemented it

5. **Prompt:** "How do I safely insert and read a JSON column in MySQL from Python/Flask?"
   - **Result:**
     - **Insert:** build a Python list or dict, convert it with `json.dumps()`, and pass it as a normal `%s` parameter. Never build the JSON string by hand or with f-strings. MySQL rejects invalid JSON.
     - **Read:** mysql-connector returns JSON columns as `str` (sometimes `bytes`), not as a Python list, so call `json.loads()`. Wrap it in a helper (`load_json`) that falls back to a default if the value is NULL or can't be parsed.
     - **User input:** don't make users type JSON. Accept `Python, SQL` or `date | round | notes` lines and convert them in Python.
   - **What I did with it:** Inserted the JSON 

### Job Match Feature
6. **Prompt:** "Write a Python function that takes a list of user skills and a list of jobs (each with a JSON list of required skills) and returns the jobs sorted by match percentage, including matched count, total count, and missing skills. Matching should be case-insensitive."
   - **Result:** `match_jobs(user_skills, jobs_list)`:
     - Puts the user's skills in a lowercase set for fast, case-insensitive lookup.
     - For each job, splits its requirements into `matched` and `missing`.
     - Calculates `percent = round(len(matched) / len(required) * 100)`.
     - Skips jobs with no requirements, which would otherwise divide by zero.
     - Sorts by percentage (highest first), then by matched count, then by title.
     
     With Python, SQL and Flask, it ranks Software Developer at 100% and Data Analyst at 67%, with Tableau missing.
   - **What I did with it:**  tested it with my own skills
### Frontend
7. **Prompt:** "Create a Bootstrap 5 `base.html` Jinja template with a navbar linking to Dashboard, Companies, Jobs, Applications, Contacts, and Job Match."
   - **Result:** It produced a responsive navbar (it collapses on mobile), a flash-message area, and `{% block content %}` / `{% block scripts %}` blocks. A small script asks for confirmation on any form with `data-confirm`. Bootstrap is loaded from `static/vendor/` instead of a CDN, so the app works offline.
   - **What I did with it:** Kept it. The first version had a bug: the Companies link never highlighted as active, because the code cut the "s" off endpoint names ("companies" → "companie"). That was replaced with a fixed prefix for each link. 

### Debugging
8. **Prompt:** "I'm getting this error: [paste full error + the code that caused it]. Explain what it means and how to fix it."
   - **Result:** These are the real errors I hit while setting up on Windows:
     - `The '<' operator is reserved for future use`: PowerShell doesn't support `<` input redirection. Fix: `cmd /c "mysql -u root -p < schema.sql"`.
     - `'mysql' is not recognized`: MySQL's `bin` folder isn't on the PATH. Fix: `$env:Path += ";C:\Program Files\MySQL\MySQL Server 8.0\bin"`.
     - `venv\Scripts\activate : The module 'venv' could not be loaded`: PowerShell needs `.\` and the `.ps1` script (`.\venv\Scripts\Activate.ps1`), and the venv had never been created in this folder.
     - `1045 (28000): Access denied for user 'root'@'localhost'`: I had set `DB_PASSWORD` to the placeholder text instead of my real password.
     - I'd also forgotten my MySQL root password and reset it using the `--init-file` method.
   - **What I did with it:** Followed each fix and got the app running. I updated the README with a Windows PowerShell column and a troubleshooting section so the next person doesn't hit the same problems.

### Review
9. **Prompt:** "Review my app.py for SQL injection risks, missing error handling, and repeated code. List the problems; don't rewrite the whole file."
   - **Result:**
     - **SQL injection:** no injection risks found. Every user value goes through `%s` parameters. The only SQL built by string concatenation is fixed text like `" WHERE j.job_type = %s"`, and filter values are checked against `JOB_TYPES`/`STATUSES` first. Minor: `%` and `_` typed into the company search act as LIKE wildcards. That's harmless, but it isn't escaped.
     - **Error handling:**
       - A global `MySQLError` handler shows a friendly error page instead of crashing.
       - A duplicate company name is checked in Python first. If two requests raced, the `UNIQUE` constraint would still block it, but the user would see the generic error page instead of a form message.
       - There's no CSRF protection on POST forms (Flask-WTF would add it).
       - `SECRET_KEY` has a hard-coded development default.
       - `debug=True` is the default, which is fine locally but must be off in production.
     - **Repeated code:**
       - The `new`/`edit` routes for all four tables follow the same pattern: validate, flash errors, re-render or save, redirect. They could share a helper.
       - The `for e in errors: flash(e, "danger")` loop appears 8 times.
       - Each query opens a new database connection, so the dashboard opens about 6 per page load. A connection pool would fix that.
   - **What I did with it:** accepted the SQL injection result; left CSRF and the connection pool as future improvements because this runs locally; or refactored the repeated flash loop into a helper.

---

## 4. What Worked Well ✍️ YOU

- The CRUD route AI wrote for `companies` worked almost right away, and I reused the pattern for `contacts`.
- Pasting the full error message got me a much better explanation than describing it.

---

## 5. What I Changed in AI Output ✍️ YOU (most important section)

 - Wrong table or column names, changed these myself
 - Missing input validation (empty fields, salary_min > salary_max, invalid ENUM values)
 - String-formatted SQL instead of parameterized queries (`%s`), which is a SQL injection risk
 - Connections or cursors that never get closed
 - Missing `conn.commit()` after INSERT/UPDATE/DELETE
 - Deleting a company that still has jobs/contacts, which breaks the foreign key
 - Job match not handling upper/lower case or extra spaces ("python" vs "Python ")
 - Dividing by zero when a job has no required skills

| File / Feature | What AI gave me | What I changed | Why |
|---|---|---|---|
| [e.g. `app.py` /add_job] | [e.g. route with no validation] | [e.g. added checks that title isn't empty and salary_min ≤ salary_max] | [e.g. app crashed / saved bad data] |

---

## 6. Things AI Got Wrong ✍️ YOU

> Graders like to see this, because it shows you didn't blindly copy. List anything that was incorrect, outdated, or didn't run.

- AI used `cursor.execute(f"... {id}")`. I changed it to a parameterized query.
- AI suggested a column name `company` that doesn't exist in my schema.

---

## 7. Lessons Learned ✍️ YOU

## Reflection

### When was AI most useful? When did it waste my time?

AI was most useful at the start of each new piece, when I didn't know where to begin.
Asking it to set up a basic Flask app with a few routes, or to write a first version
of a SQL query, saved me a lot of time looking things up. It was also good at
explaining error messages. Pasting in a traceback and asking "what does this mean?"
usually got me to the cause faster than searching on my own.

It wasted my time when I let it make big changes I didn't understand. A few times I
asked it to "fix" something and it rewrote a whole function, changed variable names,
or added libraries I wasn't using. That broke other parts of the app, and I spent
longer untangling it than writing the fix myself would have taken. It also sometimes
invented things that don't exist, like **[a function, column name, or Flask feature
it made up]**, and said them confidently. The worst moments were going back and forth
on the same bug. When the AI's answer didn't work, it often suggested a slightly
different version of the same wrong idea instead of finding the actual problem.

### What did I learn about writing good prompts?

- **Give context.** "My query doesn't work" got weak answers. Pasting my table
  structure, the query, the error, and what I expected to see got good ones.
- **Ask for small pieces.** "Write the route that returns one user as JSON" worked
  much better than "build the user system."
- **Say what not to change.** Adding "don't rename anything, only fix the WHERE
  clause" stopped it from rewriting code that already worked.
- **Ask it to explain, not just answer.** "Explain why this JOIN returns duplicate
  rows" taught me something. "Fix this" only gave me code to paste.
- **Start fresh when it goes in circles.** A new conversation with a clear summary of
  the problem often worked better than a tenth follow-up.

### What do I now understand that I didn't before?

- **JOINs:** I now understand that a JOIN matches rows from two tables on a shared
  key, and that the type matters. An `INNER JOIN` drops rows with no match, while a
  `LEFT JOIN` keeps every row from the first table and fills the gaps with `NULL`.
  I had a bug where **[records were missing / duplicated]** because I used the wrong
  one, or joined on the wrong column.
- **JSON columns:** Storing JSON in a column is convenient for flexible data like
  **[settings, tags, metadata]**, but it's harder to search and validate than normal
  columns. I learned to parse it with `json.loads()` in Python (or JSON functions in
  SQL), and that it's a bad choice for anything I need to filter or join on often.
- **Flask routing:** I understand how `@app.route()` connects a URL to a function,
  how URL variables like `/users/<int:id>` get passed in, how `methods=["GET", "POST"]`
  works, and the difference between returning a template and returning JSON with
  `jsonify()`.
- **General:** Most bugs came from how the pieces connected (data shape from the
  database not matching what the route or template expected), not from one piece on
  its own.

### How did I check that AI code was correct?

- **Ran it every time.** I didn't trust any code until I had run it and seen the result.
- **Tested queries directly** in **[SQLite browser / the database shell]** before
  putting them in Flask, and checked that the row counts made sense.
- **Tried edge cases:** empty tables, missing IDs, bad input, a user with no
  **[related records]**. AI code usually handled the "happy path" and broke on these.
- **Tested routes** in the browser or with **[Postman / curl / Thunder Client]** and
  checked status codes, not just whether something showed up.
- **Read it line by line.** If I couldn't explain what a line did, I asked the AI to
  explain it, or rewrote it myself.
- **Checked the docs** for Flask and SQL when something looked unfamiliar, since the
  AI was sometimes wrong or out of date.
- **Committed often** with Git, so I could undo a bad AI change instead of trying to
  repair it.

### What would I do differently next time?

- **Plan the database first.** Designing my tables and relationships on paper before
  writing code would have prevented the JOIN and JSON problems I hit later.
- **Write more of the first draft myself** and use AI to review, explain, and debug,
  not to generate whole features. I learned the most in the parts I wrote first.
- **Keep prompts small and specific** from the start, instead of learning that halfway
  through.
- **Write tests earlier**, even simple ones, so I'd know right away when an AI change
  broke something.
- **Stop sooner when I'm stuck in a loop** with the AI, and go to the docs, a
  classmate, or the instructor instead.

---

## 8. Academic Integrity Statement ✍️ YOU

I used AI tools as described above. I reviewed, tested, and changed all AI-generated code before including it, and I can explain how every part of this project works. The database design, testing, UI decisions, and all written reflections in this document are my own work.

**Name:** Margarita Gutierrez  **Date:** 11/21/2026