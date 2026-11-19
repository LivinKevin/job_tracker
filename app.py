import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from database import get_db
from datetime import date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")  # needed later for flash messages

@app.route("/")
@app.route("/")
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Four totals in one query
    cursor.execute(
        "SELECT (SELECT COUNT(*) FROM companies) AS total_companies, "
        "(SELECT COUNT(*) FROM jobs) AS total_jobs, "
        "(SELECT COUNT(*) FROM applications) AS total_applications, "
        "(SELECT COUNT(*) FROM contacts) AS total_contacts")
    totals = cursor.fetchone()

    # Applications per status
    cursor.execute("SELECT status, COUNT(*) AS count FROM applications "
                   "GROUP BY status ORDER BY count DESC")
    by_status = cursor.fetchall()

    # Companies with the most job postings
    cursor.execute(
        "SELECT c.company_name, COUNT(j.job_id) AS job_count FROM companies c "
        "LEFT JOIN jobs j ON c.company_id = j.company_id "
        "GROUP BY c.company_id, c.company_name "
        "ORDER BY job_count DESC, c.company_name LIMIT 5")
    top_companies = cursor.fetchall()

    # Average salary range by industry
    cursor.execute(
        "SELECT c.industry, ROUND(AVG(j.salary_min)) AS avg_min, ROUND(AVG(j.salary_max)) AS avg_max "
        "FROM companies c JOIN jobs j ON c.company_id = j.company_id "
        "WHERE j.salary_min IS NOT NULL AND c.industry IS NOT NULL "
        "GROUP BY c.industry ORDER BY avg_max DESC")
    salaries = cursor.fetchall()

    # Five most recent applications
    cursor.execute(
        "SELECT a.application_id, a.application_date, a.status, j.job_title, c.company_name "
        "FROM applications a JOIN jobs j ON a.job_id = j.job_id "
        "JOIN companies c ON j.company_id = c.company_id "
        "ORDER BY a.application_date DESC, a.application_id DESC LIMIT 5")
    recent = cursor.fetchall()
    conn.close()

    # Response rate = applications that moved past "Applied"
    total_apps = totals["total_applications"]
    responded = sum(row["count"] for row in by_status if row["status"] != "Applied")
    response_rate = round(responded * 100 / total_apps) if total_apps else 0

    return render_template("dashboard.html", totals=totals, by_status=by_status,
                           top_companies=top_companies, salaries=salaries, recent=recent,
                           responded=responded, response_rate=response_rate)

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

# Contacts CRUD routes
CONTACT_FIELDS = ("company_id", "contact_name", "title", "email", "phone", "linkedin_url", "notes")

def read_contact_form():
    return {k: request.form.get(k, "").strip() or None for k in CONTACT_FIELDS}

def validate_contact(data):
    errors = []
    if not data["company_id"]:
        errors.append("Company is required.")
    if not data["contact_name"]:
        errors.append("Contact name is required.")
    if data["email"] and ("@" not in data["email"] or "." not in data["email"].split("@")[-1]):
        errors.append("Enter a valid email address.")
    if data["phone"] and len(data["phone"]) > 20:
        errors.append("Phone number must be 20 characters or fewer.")
    return errors

def render_contact_form(action, contact, errors=()):
    for message in errors:
        flash(message, "danger")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
    company_list = cursor.fetchall()
    conn.close()
    return render_template("contact_form.html", action=action, contact=contact, companies=company_list)

def get_contact_or_404(cursor, contact_id):
    cursor.execute("SELECT * FROM contacts WHERE contact_id = %s", (contact_id,))
    contact = cursor.fetchone()
    if contact is None:
        abort(404)
    return contact

@app.route("/contacts")
def contacts():
    # READ (list): contacts joined with company name
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT ct.*, c.company_name FROM contacts ct "
        "JOIN companies c ON ct.company_id = c.company_id "
        "ORDER BY ct.contact_name")
    rows = cursor.fetchall()
    conn.close()
    return render_template("contacts.html", contacts=rows)

@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    # READ (detail)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    contact = get_contact_or_404(cursor, contact_id)
    cursor.execute("SELECT * FROM companies WHERE company_id = %s", (contact["company_id"],))
    company = cursor.fetchone()
    conn.close()
    return render_template("contact_detail.html", contact=contact, company=company)

@app.route("/contacts/add", methods=["GET", "POST"])
def add_contact():
    # CREATE
    if request.method == "POST":
        data = read_contact_form()
        errors = validate_contact(data)
        if errors:
            return render_contact_form("Add", data, errors)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)", tuple(data.values()))
        conn.commit()
        conn.close()
        flash("Contact added.", "success")
        return redirect(url_for("contacts"))
    return render_contact_form("Add", {})

@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def edit_contact(contact_id):
    # UPDATE
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    contact = get_contact_or_404(cursor, contact_id)
    if request.method == "POST":
        data = read_contact_form()
        errors = validate_contact(data)
        if errors:
            conn.close()
            return render_contact_form("Edit", data, errors)
        cursor.execute(
            "UPDATE contacts SET company_id=%s, contact_name=%s, title=%s, email=%s, "
            "phone=%s, linkedin_url=%s, notes=%s WHERE contact_id=%s",
            tuple(data.values()) + (contact_id,))
        conn.commit()
        conn.close()
        flash("Contact updated.", "success")
        return redirect(url_for("contacts"))
    conn.close()
    return render_contact_form("Edit", contact)

@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    # DELETE
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))
    conn.commit()
    conn.close()
    flash("Contact deleted.", "warning")
    return redirect(url_for("contacts"))

# Job Match Algorithm
def normalize_skill(skill):
    # "  Python " -> "python", so matching ignores case and extra spaces
    return skill.strip().lower()

def parse_skill_input(text):
    # "Python, SQL\nFlask" -> ["Python", "SQL", "Flask"] (no blanks, no duplicates)
    seen, skills = set(), []
    for part in text.replace("\n", ",").split(","):
        part = part.strip()
        if part and normalize_skill(part) not in seen:
            seen.add(normalize_skill(part))
            skills.append(part)
    return skills

def match_jobs(user_skills):
    # Returns (ranked matches, number of jobs with no skills listed, number with 0% match)
    user_set = {normalize_skill(s) for s in user_skills}
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT j.job_id, j.job_title, j.job_type, j.requirements, c.company_name "
        "FROM jobs j JOIN companies c ON j.company_id = c.company_id")
    all_jobs = cursor.fetchall()
    conn.close()

    results, no_requirements, no_match = [], 0, 0
    for job in all_jobs:
        required = parse_skills(job["requirements"]) # type: ignore
        # Map normalized name -> original spelling, which also removes duplicates
        required_map = {normalize_skill(s): s for s in required}
        if not required_map:
            no_requirements += 1
            continue
        matched = [orig for key, orig in required_map.items() if key in user_set]
        missing = [orig for key, orig in required_map.items() if key not in user_set]
        if not matched:
            no_match += 1
            continue
        results.append({
            "job_id": job["job_id"],                # type: ignore
            "job_title": job["job_title"],          # type: ignore
            "company_name": job["company_name"],    # type: ignore
            "job_type": job["job_type"],            # type: ignore
            "percent": round(len(matched) * 100 / len(required_map)),
            "matched": matched,
            "missing": missing,
            "total": len(required_map),
        })
    # Highest percentage first; ties -> more matched skills, then alphabetical
    results.sort(key=lambda r: (-r["percent"], -len(r["matched"]), r["job_title"]))
    return results, no_requirements, no_match

@app.route("/job-match")
def job_match():
    skills_text = request.args.get("skills", "").strip()
    user_skills = parse_skill_input(skills_text)
    results = no_requirements = no_match = None
    if "skills" in request.args:
        if user_skills:
            results, no_requirements, no_match = match_jobs(user_skills)
        else:
            flash("Enter at least one skill.", "danger")
    return render_template("job_match.html", skills_text=skills_text, user_skills=user_skills,
                           results=results, no_requirements=no_requirements, no_match=no_match)


if __name__ == "__main__":
    app.run(debug=True)