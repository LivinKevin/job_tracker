import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from database import get_db
from datetime import date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")  # needed later for flash messages

@app.route("/")
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS count FROM applications")
    stats = cursor.fetchone()
    conn.close()
    return render_template("dashboard.html", stats=stats)

# Companies CRUD routes
COMPANY_FIELDS = ("company_name", "industry", "website", "city", "state", "notes")
def read_company_form():
    return {k: request.form.get(k, "").strip() or None for k in COMPANY_FIELDS}

def get_company_or_404(cursor, company_id):
    # Fetches one company, shows a 404 page if the id does not exist
    cursor.execute("SELECT * FROM companies WHERE company_id = %s", (company_id,))
    company = cursor.fetchone()
    if company is None:
        abort(404)
    return company

@app.route("/companies")
def companies():
    # READ (list): all companies, sorted by name
    conn = get_db()
    # dictionary=True lets templates use c.company_name
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM companies ORDER BY company_name")
    rows = cursor.fetchall()
    conn.close()
    return render_template("companies.html", companies=rows)

@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    # READ (detail): one company plus its jobs and contacts
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    company = get_company_or_404(cursor, company_id)
    cursor.execute("SELECT * FROM jobs WHERE company_id = %s", (company_id,))
    jobs = cursor.fetchall()
    cursor.execute("SELECT * FROM contacts WHERE company_id = %s", (company_id,))
    contacts = cursor.fetchall()
    conn.close()
    return render_template("company_detail.html", company=company, jobs=jobs, contacts=contacts)

@app.route("/companies/add", methods=["GET", "POST"])
def add_company():
    # CREATE
    if request.method == "POST":
        data = read_company_form()
        # validation: name required
        if not data["company_name"]:
            flash("Company name is required.", "danger")
            return render_template("company_form.html", company=data, action="Add")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO companies (company_name, industry, website, city, state, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s)", 
tuple(data.values()))
        conn.commit()
        conn.close()
        flash("Company added.", "success")
        return redirect(url_for("companies"))
    return render_template("company_form.html", company={}, action="Add")

@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def edit_company(company_id):
    # UPDATE
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    company = get_company_or_404(cursor, company_id)
    if request.method == "POST":
        data = read_company_form()
        if not data["company_name"]:
            conn.close()
            flash("Company name is required.", "danger")
            return render_template("company_form.html", company=data, action="Edit")
        cursor.execute(
            "UPDATE companies SET company_name=%s, industry=%s, website=%s, "
            "city=%s, state=%s, notes=%s WHERE company_id=%s",
            tuple(data.values()) + (company_id,))
        conn.commit()
        conn.close()
        flash("Company updated.", "success")
        return redirect(url_for("companies"))
    conn.close()
    return render_template("company_form.html", company=company, action="Edit")

@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def delete_company(company_id):
    # DELETE (POST only, so a link can't delete by accident)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
    conn.commit()
    conn.close()
    flash("Company deleted.", "warning")
    return redirect(url_for("companies"))

# Jobs CRUD routes
# ---------- Jobs ----------
JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]

def parse_skills(value):
    # MySQL returns a JSON column as text; turn it into a Python list (or [] if empty)
    if not value:
        return []
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    return json.loads(value) if isinstance(value, str) else list(value)

def read_job_form():
    # Reads the form. Returns (data dict, skills as a comma-separated string for redisplay)
    f = request.form
    def clean(key):
        return f.get(key, "").strip() or None
    skills = [s.strip() for s in f.get("requirements", "").split(",") if s.strip()]
    data = {
        "company_id": clean("company_id"),
        "job_title": clean("job_title"),
        "job_type": clean("job_type"),
        "salary_min": clean("salary_min"),
        "salary_max": clean("salary_max"),
        "job_url": clean("job_url"),
        "date_posted": clean("date_posted"),
        "requirements": json.dumps(skills) if skills else None,
    }
    return data, ", ".join(skills)

def validate_job(data):
    errors = []
    if not data["company_id"]:
        errors.append("Company is required.")
    if not data["job_title"]:
        errors.append("Job title is required.")
    try:
        low = int(data["salary_min"]) if data["salary_min"] else None
        high = int(data["salary_max"]) if data["salary_max"] else None
    except ValueError:
        errors.append("Salaries must be whole numbers.")
    else:
        if low is not None and high is not None and low > high:
            errors.append("Minimum salary cannot be greater than maximum salary.")
    return errors

def render_job_form(action, job, skills_text, errors=()):
    # Shows the add/edit form (with any validation errors) and the company dropdown
    for message in errors:
        flash(message, "danger")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
    company_list = cursor.fetchall()
    conn.close()
    return render_template("job_form.html", action=action, job=job, skills_text=skills_text,
                           companies=company_list, job_types=JOB_TYPES)

def get_job_or_404(cursor, job_id):
    cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
    if job is None:
        abort(404)
    return job

@app.route("/jobs")
def jobs():
    # READ (list): jobs joined with their company name
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT j.*, c.company_name FROM jobs j "
        "JOIN companies c ON j.company_id = c.company_id "
        "ORDER BY j.date_posted DESC, j.job_title")
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        row["skills"] = parse_skills(row["requirements"])
    return render_template("jobs.html", jobs=rows)

@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    # READ (detail): one job, its company, and applications for it
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    job = get_job_or_404(cursor, job_id)
    cursor.execute("SELECT * FROM companies WHERE company_id = %s", (job["company_id"],))
    company = cursor.fetchone()
    cursor.execute("SELECT * FROM applications WHERE job_id = %s ORDER BY application_date DESC", (job_id,))
    apps = cursor.fetchall()
    conn.close()
    return render_template("job_detail.html", job=job, company=company,
                           skills=parse_skills(job["requirements"]), applications=apps)

@app.route("/jobs/add", methods=["GET", "POST"])
def add_job():
    # CREATE
    if request.method == "POST":
        data, skills_text = read_job_form()
        errors = validate_job(data)
        if errors:
            return render_job_form("Add", data, skills_text, errors)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, "
            "job_url, date_posted, requirements) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            tuple(data.values()))
        conn.commit()
        conn.close()
        flash("Job added.", "success")
        return redirect(url_for("jobs"))
    return render_job_form("Add", {}, "")

@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def edit_job(job_id):
    # UPDATE
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    job = get_job_or_404(cursor, job_id)
    if request.method == "POST":
        data, skills_text = read_job_form()
        errors = validate_job(data)
        if errors:
            conn.close()
            return render_job_form("Edit", data, skills_text, errors)
        cursor.execute(
            "UPDATE jobs SET company_id=%s, job_title=%s, job_type=%s, salary_min=%s, "
            "salary_max=%s, job_url=%s, date_posted=%s, requirements=%s WHERE job_id=%s",
            tuple(data.values()) + (job_id,))
        conn.commit()
        conn.close()
        flash("Job updated.", "success")
        return redirect(url_for("jobs"))
    conn.close()
    return render_job_form("Edit", job, ", ".join(parse_skills(job["requirements"])))

@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def delete_job(job_id):
    # DELETE
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    conn.commit()
    conn.close()
    flash("Job deleted.", "warning")
    return redirect(url_for("jobs"))

# Applications CRUD routes
STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]

def pretty_json(value):
    # Turns the JSON column's text into indented text for the edit textarea
    if not value:
        return ""
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    parsed = json.loads(value) if isinstance(value, str) else value
    return json.dumps(parsed, indent=2)

def read_application_form():
    f = request.form
    def clean(key):
        return f.get(key, "").strip() or None
    interview_text = f.get("interview_data", "").strip()
    data = {
        "job_id": clean("job_id"),
        "application_date": clean("application_date"),
        "status": clean("status"),
        "resume_version": clean("resume_version"),
        "cover_letter_sent": 1 if f.get("cover_letter_sent") else 0,      
        # checkbox: present = checked
        "interview_data": interview_text or None,
    }
    return data, interview_text

def validate_application(data):
    errors = []
    if not data["job_id"]:
        errors.append("Job is required.")
    if not data["application_date"]:
        errors.append("Application date is required.")
    else:
        try:
            date.fromisoformat(data["application_date"])
        except ValueError:
            errors.append("Application date must be a valid date.")
    if data["status"] not in STATUSES:
        errors.append("Choose a valid status.")
    if data["interview_data"]:
        try:
            json.loads(data["interview_data"])
        except json.JSONDecodeError:
            errors.append("Interview data must be valid JSON, for example "
                          '{"interview_rounds": 2, "feedback": "Went well"}.')
    return errors

def render_application_form(action, application, interview_text, errors=()):
    for message in errors:
        flash(message, "danger")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT j.job_id, j.job_title, c.company_name FROM jobs j "
        "JOIN companies c ON j.company_id = c.company_id "
        "ORDER BY c.company_name, j.job_title")
    job_list = cursor.fetchall()
    conn.close()
    return render_template("application_form.html", action=action, application=application,
                           interview_text=interview_text, jobs=job_list, statuses=STATUSES)

def get_application_or_404(cursor, application_id):
    cursor.execute("SELECT * FROM applications WHERE application_id = %s", (application_id,))
    application = cursor.fetchone()
    if application is None:
        abort(404)
    return application

@app.route("/applications")
def applications():
    # READ (list): applications joined with job title and company name
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT a.*, j.job_title, c.company_name FROM applications a "
        "JOIN jobs j ON a.job_id = j.job_id "
        "JOIN companies c ON j.company_id = c.company_id "
        "ORDER BY a.application_date DESC, a.application_id DESC")
    rows = cursor.fetchall()
    conn.close()
    return render_template("applications.html", applications=rows)

@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    # READ (detail)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    application = get_application_or_404(cursor, application_id)
    cursor.execute(
        "SELECT j.job_id, j.job_title, c.company_id, c.company_name FROM jobs j "
        "JOIN companies c ON j.company_id = c.company_id WHERE j.job_id = %s",
        (application["job_id"],))
    job = cursor.fetchone()
    conn.close()
    return render_template("application_detail.html", application=application, job=job,
                           interview_text=pretty_json(application["interview_data"]))

@app.route("/applications/add", methods=["GET", "POST"])
def add_application():
    # CREATE
    if request.method == "POST":
        data, interview_text = read_application_form()
        errors = validate_application(data)
        if errors:
            return render_application_form("Add", data, interview_text, errors)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO applications (job_id, application_date, status, resume_version, "
            "cover_letter_sent, interview_data) VALUES (%s, %s, %s, %s, %s, %s)",
            tuple(data.values()))
        conn.commit()
        conn.close()
        flash("Application added.", "success")
        return redirect(url_for("applications"))
    defaults = {"application_date": date.today().isoformat(), "status": "Applied"}
    return render_application_form("Add", defaults, "")

@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def edit_application(application_id):
    # UPDATE
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    application = get_application_or_404(cursor, application_id)
    if request.method == "POST":
        data, interview_text = read_application_form()
        errors = validate_application(data)
        if errors:
            conn.close()
            return render_application_form("Edit", data, interview_text, errors)
        cursor.execute(
            "UPDATE applications SET job_id=%s, application_date=%s, status=%s, "
            "resume_version=%s, cover_letter_sent=%s, interview_data=%s WHERE application_id=%s",
            tuple(data.values()) + (application_id,))
        conn.commit()
        conn.close()
        flash("Application updated.", "success")
        return redirect(url_for("applications"))
    conn.close()
    return render_application_form("Edit", application, pretty_json(application["interview_data"]))

@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def delete_application(application_id):
    # DELETE
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
    conn.commit()
    conn.close()
    flash("Application deleted.", "warning")
    return redirect(url_for("applications"))


if __name__ == "__main__":
    app.run(debug=True)