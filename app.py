import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from database import get_db

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

if __name__ == "__main__":
    app.run(debug=True)