# AI Usage Documentation

## Tools Used
- **Claude (Claude Code in the Claude desktop app)**, used as a reviewer and pair programmer: checking my work against the project rubric, comparing my drafts with its versions, writing the HTML templates, and helping with the UI styling.

### Who did what
- **Database (`schema.sql`):** I created it myself and loaded data from my earlier coursework scripts. I asked the AI to revise it and to help convert my prototype data (old column names and statuses) to the final schema.
- **`database.py`:** I wrote it myself, starting from the connection-test script from class. The AI pointed out that the app needs a reusable `get_db()` function that reads the password from an environment variable, and I fixed my file to do that.
- **`app.py`:** I started the draft and wrote the Companies CRUD routes myself, then compared them with the AI's version. I followed the same structure for Jobs, Applications and Contacts, adding the differences the AI described (dropdowns filled from other tables, JSON skills, extra validation).
- **Templates:** the AI helped the most here. It helped build pages first, then supplied the extra files (form pages, detail pages and the shared icon file), which I added to the project.
- **Job Match:** I built my own draft first, then compared it with the AI's version and refined mine.
- **UI:** the AI's styling suggestions worked well. I chose the direction myself, using reference screenshots for the colors and layout.
- **Project setup:** I created the GitHub repo, `requirements.txt`, `.gitignore` and the environment-variable setup. The AI drafted the first version of `README.md` and of this file, and I reviewed and corrected any mistakes.

## Key Prompts
1. "Go step by step through the project requirements and check the rubric. Provide an outline/workflow" (This produced the build order: database, skeleton, CRUD for each table, dashboard, Job Match, docs.)
2. "Walk me through the Companies CRUD and explain what each part of the code does, so I can compare it with my own draft."
3. Pasted tracebacks and screenshots of errors (`Access denied for user 'root'`, `TemplateNotFound`, `NameError: name 'date' is not defined`) and asked what was wrong.
4. "The default Bootstrap look feels generic. Restyle it with a blue title bar, a light grey background and rounded cards, using my reference screenshots for the colors and layout."
5. "Put the logos in front of the title for each category's section." (Icons on the list pages and the Job Match page.)
6. "Compare my Job Match draft with a better version and tell me what is different."
7. Asked for README and AI_USAGE drafts based on what the project actually contains.

## What Worked Well
- **Project plan:** mapping every requirement and rubric line to a concrete step kept me from missing anything.
- **Compare-and-learn approach:** writing my own draft first (the Companies routes, Job Match), then comparing it with the AI's version, showed me exactly what I had missed.
- **CRUD pattern:** one fully working table, then the same routes (list, detail, add, edit, delete) repeated for Jobs, Applications and Contacts.
- **Parameterized queries:** every query uses `%s` placeholders, which I learned protects against SQL injection.
- **Reading error messages:** the AI found the cause of each error quickly, for example the spec's example `app.py` defining its own `get_db()` with a hardcoded password, which meant my environment variable was being ignored.
- **JSON handling:** turning the comma-separated skills text into a JSON array for `jobs.requirements`, and back again for display and for matching.
- **Templates and UI:** the AI's templates and styling worked well, with only small fixes needed.
- **Moving my prototype data into the final schema:** the AI mapped the old columns and statuses to the new ones (for example `first_name` + `last_name` into `contact_name`, and `Phone Screen` into `Screening`).

## What I Modified
- Replaced the spec's example `app.py`, which has a hardcoded password, so it imports `get_db()` from `database.py`. My MySQL password is never stored in the repository.
- Fixed my own mistakes while following the steps: saving files that were still empty, a misspelled template filename (`comapny_detail.html`) and a missing `from datetime import date`.
- Learned that my password contains `$`, which PowerShell treats specially inside double quotes, so I set it with single quotes.
- Chose the visual design myself: the blue title bar color (sampled from a screenshot I picked), the grey page background, the Geist font, the colored icon tiles, and bold black box titles.
- Ran the SQL in MySQL Workbench to check that the data and constraints worked.
- Tested every page and form in the browser, including bad input (empty required fields, a minimum salary above the maximum, invalid JSON, a skills search with nothing entered).

## What the AI Got Wrong or Needed Checking
- The sample **skill lists for most jobs in `schema.sql` are made up by the AI** so Job Match has something to rank. Only jobs 1 and 3 came from my coursework data. I treat them as demo data, not real job requirements.
- Some AI-written code showed type-checker warnings in VS Code (Pylance) even though it ran correctly, so I had to judge which warnings mattered.
- Some steps assumed things about my setup that weren't true until I checked, such as which Python environment the packages went into.

## Lessons Learned
- Always run and test AI code. It often works but has small gaps, like a missing import or a setup assumption.
- Writing my own draft first and then comparing it with the AI's taught me more than copying would have.
- AI is great for repeated boilerplate such as templates and CRUD routes, but I still needed to understand each piece in order to debug it.
- Give the AI error messages and screenshots. Specific evidence gets much better answers than "it doesn't work".
- Keep secrets such as passwords out of code and out of Git. Use environment variables.
- Ask the AI to explain what the code does. That is how I learned why things like `commit()`, redirect-after-POST and `%s` placeholders matter.
