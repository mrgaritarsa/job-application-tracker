"""Job Application Tracker - Flask application.

Pages:
    /               Dashboard (statistics)
    /companies      Companies CRUD
    /jobs           Jobs CRUD
    /applications   Applications CRUD
    /contacts       Contacts CRUD
    /job-match      Rank jobs by how well they match your skills
"""
import json
import os
import re
from datetime import date

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from mysql.connector import Error as MySQLError

from database import execute, query_all, query_one

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
PHONE_RE = re.compile(r"^[0-9+()\-.\s]{7,20}$")


# =============================================================
# Helpers
# =============================================================
def clean(value):
    """Strip whitespace; turn empty strings into None so MySQL stores NULL."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_int(value, field, errors, minimum=0):
    """Convert an optional form value to int, recording an error if invalid."""
    value = clean(value)
    if value is None:
        return None
    try:
        number = int(value.replace(",", ""))
    except ValueError:
        errors.append(f"{field} must be a whole number.")
        return None
    if number < minimum:
        errors.append(f"{field} cannot be less than {minimum}.")
    return number


def parse_date(value, field, errors, required=False):
    """Validate a YYYY-MM-DD date string."""
    value = clean(value)
    if value is None:
        if required:
            errors.append(f"{field} is required.")
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        errors.append(f"{field} must be a valid date (YYYY-MM-DD).")
        return None


def check_length(value, field, max_len, errors):
    if value and len(value) > max_len:
        errors.append(f"{field} must be {max_len} characters or fewer.")


def check_url(value, field, errors):
    if value and not URL_RE.match(value):
        errors.append(f"{field} must start with http:// or https://")


def load_json(value, default):
    """MySQL returns JSON columns as strings (or bytes); decode safely."""
    if value is None:
        return default
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return default
    return value


def parse_skills(text):
    """'Python, SQL,  flask' -> ['Python', 'SQL', 'flask'] (deduplicated)."""
    skills, seen = [], set()
    for part in re.split(r"[,\n;]", text or ""):
        skill = part.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def parse_interviews(text, errors):
    """Turn lines of 'YYYY-MM-DD | Round | Notes' into a list of dicts."""
    rounds = []
    for line_no, line in enumerate((text or "").splitlines(), start=1):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        interview_date = parts[0]
        try:
            date.fromisoformat(interview_date)
        except ValueError:
            errors.append(f"Interview line {line_no}: '{interview_date}' is not a valid date (YYYY-MM-DD).")
            continue
        rounds.append({
            "date": interview_date,
            "round": parts[1] if len(parts) > 1 else "",
            "notes": " | ".join(parts[2:]) if len(parts) > 2 else "",
        })
    return rounds


def interviews_to_text(rounds):
    return "\n".join(f"{r.get('date', '')} | {r.get('round', '')} | {r.get('notes', '')}".rstrip(" |")
                     for r in rounds)


def get_or_404(sql, record_id):
    row = query_one(sql, (record_id,))
    if row is None:
        abort(404)
    return row


def company_choices():
    return query_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


def job_choices():
    return query_all(
        """SELECT j.job_id, j.job_title, c.company_name
           FROM jobs j JOIN companies c ON c.company_id = j.company_id
           ORDER BY c.company_name, j.job_title""")


@app.template_filter("money")
def money_filter(value):
    return f"${value:,.0f}" if value is not None else "—"


@app.context_processor
def inject_constants():
    return {"JOB_TYPES": JOB_TYPES, "STATUSES": STATUSES}


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", message="That record was not found."), 404


@app.errorhandler(MySQLError)
def database_error(err):
    app.logger.error("Database error: %s", err)
    return render_template(
        "error.html",
        message="Could not talk to the database. Check that MySQL is running and that your "
                "DB_USER / DB_PASSWORD settings are correct.",
        detail=str(err)), 500


# =============================================================
# Dashboard
# =============================================================
@app.route("/")
def dashboard():
    counts = query_one(
        """SELECT
             (SELECT COUNT(*) FROM companies)    AS companies,
             (SELECT COUNT(*) FROM jobs)         AS jobs,
             (SELECT COUNT(*) FROM applications) AS applications,
             (SELECT COUNT(*) FROM contacts)     AS contacts""")

    status_rows = query_all("SELECT status, COUNT(*) AS total FROM applications GROUP BY status")
    by_status = {s: 0 for s in STATUSES}
    for row in status_rows:
        by_status[row["status"]] = row["total"]

    total_apps = counts["applications"] or 0
    responded = sum(by_status[s] for s in ("Screening", "Interview", "Offer", "Rejected"))
    response_rate = round(responded / total_apps * 100) if total_apps else 0
    active = sum(by_status[s] for s in ("Applied", "Screening", "Interview"))

    salary = query_one(
        "SELECT AVG(salary_min) AS avg_min, AVG(salary_max) AS avg_max FROM jobs")

    recent = query_all(
        """SELECT a.application_id, a.application_date, a.status, j.job_title, c.company_name
           FROM applications a
           JOIN jobs j ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           ORDER BY a.application_date DESC, a.application_id DESC
           LIMIT 5""")

    not_applied = query_all(
        """SELECT j.job_id, j.job_title, c.company_name, j.date_posted
           FROM jobs j
           JOIN companies c ON c.company_id = j.company_id
           LEFT JOIN applications a ON a.job_id = j.job_id
           WHERE a.application_id IS NULL
           ORDER BY j.date_posted DESC""")

    return render_template(
        "dashboard.html", counts=counts, by_status=by_status, total_apps=total_apps,
        response_rate=response_rate, active=active, salary=salary,
        recent=recent, not_applied=not_applied)


# =============================================================
# Companies
# =============================================================
def validate_company(form):
    errors = []
    data = {
        "company_name": clean(form.get("company_name")),
        "industry": clean(form.get("industry")),
        "website": clean(form.get("website")),
        "city": clean(form.get("city")),
        "state": clean(form.get("state")),
        "notes": clean(form.get("notes")),
    }
    if not data["company_name"]:
        errors.append("Company name is required.")
    check_length(data["company_name"], "Company name", 100, errors)
    check_length(data["industry"], "Industry", 50, errors)
    check_length(data["website"], "Website", 200, errors)
    check_length(data["city"], "City", 50, errors)
    check_length(data["state"], "State", 50, errors)
    check_url(data["website"], "Website", errors)
    return data, errors


def company_name_taken(name, exclude_id=None):
    row = query_one(
        "SELECT company_id FROM companies WHERE LOWER(company_name) = LOWER(%s) AND company_id <> %s",
        (name, exclude_id or 0))
    return row is not None


@app.route("/companies")
def companies():
    search = (request.args.get("q") or "").strip()
    sql = """SELECT c.*,
                    (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id) AS job_count,
                    (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.company_id) AS contact_count
             FROM companies c"""
    params = ()
    if search:
        sql += " WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s"
        like = f"%{search}%"
        params = (like, like, like)
    sql += " ORDER BY c.company_name"
    return render_template("companies.html", companies=query_all(sql, params), search=search)


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", company_id)
    jobs = query_all("SELECT * FROM jobs WHERE company_id = %s ORDER BY date_posted DESC", (company_id,))
    contacts = query_all("SELECT * FROM contacts WHERE company_id = %s ORDER BY contact_name", (company_id,))
    return render_template("company_detail.html", company=company, jobs=jobs, contacts=contacts)


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    if request.method == "POST":
        data, errors = validate_company(request.form)
        if data["company_name"] and company_name_taken(data["company_name"]):
            errors.append(f"A company named '{data['company_name']}' already exists.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("company_form.html", company=request.form, action="Add"), 400
        new_id = execute(
            """INSERT INTO companies (company_name, industry, website, city, state, notes)
               VALUES (%(company_name)s, %(industry)s, %(website)s, %(city)s, %(state)s, %(notes)s)""",
            data)
        flash(f"Company '{data['company_name']}' added.", "success")
        return redirect(url_for("company_detail", company_id=new_id))
    return render_template("company_form.html", company={}, action="Add")


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = get_or_404("SELECT * FROM companies WHERE company_id = %s", company_id)
    if request.method == "POST":
        data, errors = validate_company(request.form)
        if data["company_name"] and company_name_taken(data["company_name"], company_id):
            errors.append(f"A company named '{data['company_name']}' already exists.")
        if errors:
            for e in errors:
                flash(e, "danger")
            form = dict(request.form, company_id=company_id)
            return render_template("company_form.html", company=form, action="Edit"), 400
        data["company_id"] = company_id
        execute(
            """UPDATE companies SET company_name=%(company_name)s, industry=%(industry)s,
                   website=%(website)s, city=%(city)s, state=%(state)s, notes=%(notes)s
               WHERE company_id=%(company_id)s""", data)
        flash("Company updated.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("company_form.html", company=company, action="Edit")


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    company = get_or_404("SELECT company_name FROM companies WHERE company_id = %s", company_id)
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
    flash(f"Deleted '{company['company_name']}' and its jobs, applications and contacts.", "success")
    return redirect(url_for("companies"))


# =============================================================
# Jobs
# =============================================================
def validate_job(form):
    errors = []
    data = {
        "company_id": parse_int(form.get("company_id"), "Company", errors, minimum=1),
        "job_title": clean(form.get("job_title")),
        "job_type": clean(form.get("job_type")),
        "salary_min": parse_int(form.get("salary_min"), "Minimum salary", errors),
        "salary_max": parse_int(form.get("salary_max"), "Maximum salary", errors),
        "job_url": clean(form.get("job_url")),
        "date_posted": parse_date(form.get("date_posted"), "Date posted", errors),
    }
    skills = parse_skills(form.get("requirements"))
    data["requirements"] = json.dumps(skills)

    if data["company_id"] is None:
        errors.append("Please choose a company.")
    elif not query_one("SELECT 1 FROM companies WHERE company_id = %s", (data["company_id"],)):
        errors.append("Selected company does not exist.")
    if not data["job_title"]:
        errors.append("Job title is required.")
    check_length(data["job_title"], "Job title", 100, errors)
    if data["job_type"] not in JOB_TYPES:
        errors.append("Please choose a valid job type.")
    if (data["salary_min"] is not None and data["salary_max"] is not None
            and data["salary_min"] > data["salary_max"]):
        errors.append("Minimum salary cannot be greater than maximum salary.")
    check_length(data["job_url"], "Job URL", 300, errors)
    check_url(data["job_url"], "Job URL", errors)
    for s in skills:
        check_length(s, f"Skill '{s[:20]}…'", 50, errors)
    return data, errors


def job_with_skills(job):
    job["skills"] = load_json(job.get("requirements"), [])
    return job


@app.route("/jobs")
def jobs():
    job_type = request.args.get("type", "")
    sql = """SELECT j.*, c.company_name,
                    (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS app_count
             FROM jobs j JOIN companies c ON c.company_id = j.company_id"""
    params = ()
    if job_type in JOB_TYPES:
        sql += " WHERE j.job_type = %s"
        params = (job_type,)
    sql += " ORDER BY j.date_posted DESC, j.job_id DESC"
    rows = [job_with_skills(j) for j in query_all(sql, params)]
    return render_template("jobs.html", jobs=rows, job_type=job_type)


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = job_with_skills(get_or_404(
        """SELECT j.*, c.company_name FROM jobs j
           JOIN companies c ON c.company_id = j.company_id WHERE j.job_id = %s""", job_id))
    applications = query_all(
        "SELECT * FROM applications WHERE job_id = %s ORDER BY application_date DESC", (job_id,))
    return render_template("job_detail.html", job=job, applications=applications)


def job_form_values(source):
    """Prepare values for the job form (skills shown as comma-separated text)."""
    values = dict(source)
    if "skills" in values:
        values["requirements"] = ", ".join(values["skills"])
    return values


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    if request.method == "POST":
        data, errors = validate_job(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("job_form.html", job=request.form, companies=company_choices(),
                                   action="Add"), 400
        new_id = execute(
            """INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                                 job_url, date_posted, requirements)
               VALUES (%(company_id)s, %(job_title)s, %(job_type)s, %(salary_min)s, %(salary_max)s,
                       %(job_url)s, %(date_posted)s, %(requirements)s)""", data)
        flash(f"Job '{data['job_title']}' added.", "success")
        return redirect(url_for("job_detail", job_id=new_id))
    preset = {"company_id": request.args.get("company_id", ""), "job_type": "Full-time"}
    return render_template("job_form.html", job=preset, companies=company_choices(), action="Add")


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = job_with_skills(get_or_404("SELECT * FROM jobs WHERE job_id = %s", job_id))
    if request.method == "POST":
        data, errors = validate_job(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            form = dict(request.form, job_id=job_id)
            return render_template("job_form.html", job=form, companies=company_choices(),
                                   action="Edit"), 400
        data["job_id"] = job_id
        execute(
            """UPDATE jobs SET company_id=%(company_id)s, job_title=%(job_title)s,
                   job_type=%(job_type)s, salary_min=%(salary_min)s, salary_max=%(salary_max)s,
                   job_url=%(job_url)s, date_posted=%(date_posted)s, requirements=%(requirements)s
               WHERE job_id=%(job_id)s""", data)
        flash("Job updated.", "success")
        return redirect(url_for("job_detail", job_id=job_id))
    return render_template("job_form.html", job=job_form_values(job), companies=company_choices(),
                           action="Edit")


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    job = get_or_404("SELECT job_title FROM jobs WHERE job_id = %s", job_id)
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    flash(f"Deleted job '{job['job_title']}' and its applications.", "success")
    return redirect(url_for("jobs"))


# =============================================================
# Applications
# =============================================================
def validate_application(form):
    errors = []
    data = {
        "job_id": parse_int(form.get("job_id"), "Job", errors, minimum=1),
        "application_date": parse_date(form.get("application_date"), "Application date", errors,
                                       required=True),
        "status": clean(form.get("status")),
        "resume_version": clean(form.get("resume_version")),
        "cover_letter_sent": 1 if form.get("cover_letter_sent") else 0,
    }
    data["interview_data"] = json.dumps(parse_interviews(form.get("interview_data"), errors))

    if data["job_id"] is None:
        errors.append("Please choose a job.")
    elif not query_one("SELECT 1 FROM jobs WHERE job_id = %s", (data["job_id"],)):
        errors.append("Selected job does not exist.")
    if data["status"] not in STATUSES:
        errors.append("Please choose a valid status.")
    if data["application_date"] and data["application_date"] > date.today().isoformat():
        errors.append("Application date cannot be in the future.")
    check_length(data["resume_version"], "Resume version", 50, errors)
    return data, errors


@app.route("/applications")
def applications():
    status = request.args.get("status", "")
    sql = """SELECT a.*, j.job_title, c.company_name, c.company_id
             FROM applications a
             JOIN jobs j ON j.job_id = a.job_id
             JOIN companies c ON c.company_id = j.company_id"""
    params = ()
    if status in STATUSES:
        sql += " WHERE a.status = %s"
        params = (status,)
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    rows = query_all(sql, params)
    for r in rows:
        r["interviews"] = load_json(r.get("interview_data"), [])
    return render_template("applications.html", applications=rows, status=status)


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    app_row = get_or_404(
        """SELECT a.*, j.job_title, j.job_id, c.company_name, c.company_id
           FROM applications a
           JOIN jobs j ON j.job_id = a.job_id
           JOIN companies c ON c.company_id = j.company_id
           WHERE a.application_id = %s""", application_id)
    app_row["interviews"] = load_json(app_row.get("interview_data"), [])
    contacts = query_all("SELECT * FROM contacts WHERE company_id = %s ORDER BY contact_name",
                         (app_row["company_id"],))
    return render_template("application_detail.html", a=app_row, contacts=contacts)


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    if request.method == "POST":
        data, errors = validate_application(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("application_form.html", a=request.form, jobs=job_choices(),
                                   action="Add"), 400
        new_id = execute(
            """INSERT INTO applications (job_id, application_date, status, resume_version,
                                         cover_letter_sent, interview_data)
               VALUES (%(job_id)s, %(application_date)s, %(status)s, %(resume_version)s,
                       %(cover_letter_sent)s, %(interview_data)s)""", data)
        flash("Application added.", "success")
        return redirect(url_for("application_detail", application_id=new_id))
    preset = {"job_id": request.args.get("job_id", ""), "status": "Applied",
              "application_date": date.today().isoformat()}
    return render_template("application_form.html", a=preset, jobs=job_choices(), action="Add")


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    a = get_or_404("SELECT * FROM applications WHERE application_id = %s", application_id)
    if request.method == "POST":
        data, errors = validate_application(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            form = dict(request.form, application_id=application_id)
            return render_template("application_form.html", a=form, jobs=job_choices(),
                                   action="Edit"), 400
        data["application_id"] = application_id
        execute(
            """UPDATE applications SET job_id=%(job_id)s, application_date=%(application_date)s,
                   status=%(status)s, resume_version=%(resume_version)s,
                   cover_letter_sent=%(cover_letter_sent)s, interview_data=%(interview_data)s
               WHERE application_id=%(application_id)s""", data)
        flash("Application updated.", "success")
        return redirect(url_for("application_detail", application_id=application_id))
    a["interview_data"] = interviews_to_text(load_json(a.get("interview_data"), []))
    return render_template("application_form.html", a=a, jobs=job_choices(), action="Edit")


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def application_delete(application_id):
    get_or_404("SELECT 1 FROM applications WHERE application_id = %s", application_id)
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
    flash("Application deleted.", "success")
    return redirect(url_for("applications"))


# =============================================================
# Contacts
# =============================================================
def validate_contact(form):
    errors = []
    data = {
        "company_id": parse_int(form.get("company_id"), "Company", errors, minimum=1),
        "contact_name": clean(form.get("contact_name")),
        "title": clean(form.get("title")),
        "email": clean(form.get("email")),
        "phone": clean(form.get("phone")),
        "linkedin_url": clean(form.get("linkedin_url")),
        "notes": clean(form.get("notes")),
    }
    if data["company_id"] is None:
        errors.append("Please choose a company.")
    elif not query_one("SELECT 1 FROM companies WHERE company_id = %s", (data["company_id"],)):
        errors.append("Selected company does not exist.")
    if not data["contact_name"]:
        errors.append("Contact name is required.")
    check_length(data["contact_name"], "Contact name", 100, errors)
    check_length(data["title"], "Title", 100, errors)
    check_length(data["email"], "Email", 100, errors)
    check_length(data["linkedin_url"], "LinkedIn URL", 200, errors)
    if data["email"] and not EMAIL_RE.match(data["email"]):
        errors.append("Email address is not valid.")
    if data["phone"] and not PHONE_RE.match(data["phone"]):
        errors.append("Phone number may only contain digits, spaces and + ( ) - . (7-20 characters).")
    check_url(data["linkedin_url"], "LinkedIn URL", errors)
    return data, errors


@app.route("/contacts")
def contacts():
    rows = query_all(
        """SELECT ct.*, c.company_name FROM contacts ct
           JOIN companies c ON c.company_id = ct.company_id
           ORDER BY c.company_name, ct.contact_name""")
    return render_template("contacts.html", contacts=rows)


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    contact = get_or_404(
        """SELECT ct.*, c.company_name FROM contacts ct
           JOIN companies c ON c.company_id = ct.company_id WHERE ct.contact_id = %s""", contact_id)
    return render_template("contact_detail.html", contact=contact)


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    if request.method == "POST":
        data, errors = validate_contact(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("contact_form.html", contact=request.form,
                                   companies=company_choices(), action="Add"), 400
        new_id = execute(
            """INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
               VALUES (%(company_id)s, %(contact_name)s, %(title)s, %(email)s, %(phone)s,
                       %(linkedin_url)s, %(notes)s)""", data)
        flash(f"Contact '{data['contact_name']}' added.", "success")
        return redirect(url_for("contact_detail", contact_id=new_id))
    preset = {"company_id": request.args.get("company_id", "")}
    return render_template("contact_form.html", contact=preset, companies=company_choices(),
                           action="Add")


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = get_or_404("SELECT * FROM contacts WHERE contact_id = %s", contact_id)
    if request.method == "POST":
        data, errors = validate_contact(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            form = dict(request.form, contact_id=contact_id)
            return render_template("contact_form.html", contact=form,
                                   companies=company_choices(), action="Edit"), 400
        data["contact_id"] = contact_id
        execute(
            """UPDATE contacts SET company_id=%(company_id)s, contact_name=%(contact_name)s,
                   title=%(title)s, email=%(email)s, phone=%(phone)s,
                   linkedin_url=%(linkedin_url)s, notes=%(notes)s
               WHERE contact_id=%(contact_id)s""", data)
        flash("Contact updated.", "success")
        return redirect(url_for("contact_detail", contact_id=contact_id))
    return render_template("contact_form.html", contact=contact, companies=company_choices(),
                           action="Edit")


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    contact = get_or_404("SELECT contact_name FROM contacts WHERE contact_id = %s", contact_id)
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
    flash(f"Deleted contact '{contact['contact_name']}'.", "success")
    return redirect(url_for("contacts"))


# =============================================================
# Job Match
# =============================================================
def match_jobs(user_skills, jobs_list):
    """Rank jobs by the share of each job's required skills the user has.

    Matching is case-insensitive. A job requiring Python, SQL and Tableau
    matched against a user with Python, SQL and Flask scores 2/3 = 67%,
    and Tableau is reported as missing. Jobs with no listed requirements
    are skipped because a percentage would be meaningless.
    """
    have = {s.lower() for s in user_skills}
    results = []
    for job in jobs_list:
        required = load_json(job.get("requirements"), [])
        if not required:
            continue
        matched = [s for s in required if s.lower() in have]
        missing = [s for s in required if s.lower() not in have]
        results.append({
            **job,
            "matched": matched,
            "missing": missing,
            "required_count": len(required),
            "percent": round(len(matched) / len(required) * 100),
        })
    # Highest percentage first; break ties by number of matched skills, then title.
    results.sort(key=lambda r: (-r["percent"], -len(r["matched"]), r["job_title"].lower()))
    return results


@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    skills_text = request.values.get("skills", "")
    min_percent = request.values.get("min_percent", "0")
    try:
        min_percent = max(0, min(100, int(min_percent)))
    except ValueError:
        min_percent = 0

    user_skills = parse_skills(skills_text)
    results = None
    if request.method == "POST" or skills_text:
        if not user_skills:
            flash("Enter at least one skill (separate skills with commas).", "warning")
        else:
            all_jobs = query_all(
                """SELECT j.job_id, j.job_title, j.job_type, j.salary_min, j.salary_max,
                          j.requirements, c.company_name
                   FROM jobs j JOIN companies c ON c.company_id = j.company_id""")
            results = [r for r in match_jobs(user_skills, all_jobs) if r["percent"] >= min_percent]

    # All distinct skills across jobs, used for the clickable suggestions.
    known = set()
    for row in query_all("SELECT requirements FROM jobs"):
        known.update(load_json(row["requirements"], []))
    return render_template("job_match.html", skills_text=skills_text, user_skills=user_skills,
                           results=results, min_percent=min_percent,
                           known_skills=sorted(known, key=str.lower))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
