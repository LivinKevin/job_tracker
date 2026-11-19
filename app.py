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

#Companies
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

if __name__ == "__main__":
    app.run(debug=True)