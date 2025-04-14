# database_utils.py (Incorporating Application Status and Job Status)
import sqlite3
import json
import os
from datetime import datetime
import traceback # For more detailed error printing

# Define the database file name
DB_FILE = 'job_portal.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = None
    try:
        # Increased timeout slightly, kept check_same_thread=False for Flask
        conn = sqlite3.connect(DB_FILE, timeout=15, check_same_thread=False)
        # Return rows as dictionary-like objects for easier access
        conn.row_factory = sqlite3.Row
        # Explicitly enable Write-Ahead Logging (WAL) for better concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        # Set busy_timeout to handle potential locking issues better with WAL
        conn.execute("PRAGMA busy_timeout = 5000;") # 5000 ms = 5 seconds
        print("DB Connection established with WAL mode and busy_timeout.")
    except sqlite3.Error as e:
        print(f"DATABASE CONNECTION ERROR: {e}")
        traceback.print_exc() # Print full traceback for connection errors
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    print(f"Checking/Initializing database at: {os.path.abspath(DB_FILE)}")
    conn = None # Initialize conn outside try
    try:
        conn = get_db_connection()
        if conn is None: raise sqlite3.Error("Failed to get DB connection for init.") # Check if connection failed
        cursor = conn.cursor()

        # Job Postings Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description_text TEXT,
            structured_jd TEXT,   -- Store structured JD as JSON string
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            job_status TEXT DEFAULT 'open' NOT NULL -- Added job status (open, closed, filled)
        )''')
        print("Table 'jobs' checked/created.")

        # Applicants Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS applicants (
            applicant_id TEXT PRIMARY KEY, -- Using email from form
            name TEXT,
            resume_file_path TEXT UNIQUE NOT NULL, -- Store filename only, ensure uniqueness
            structured_resume TEXT,  -- Store structured resume as JSON string (can be generated later)
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )''')
        print("Table 'applicants' checked/created.")

        # Applications Table (Tracks who applied to what, when, rating, and status)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_id TEXT NOT NULL, -- References applicants.applicant_id (email)
            job_id TEXT NOT NULL,       -- References jobs.job_id
            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            rating INTEGER,             -- AI Rating (0-100, initially NULL)
            rating_details TEXT,        -- JSON details of rating (initially NULL)
            status TEXT DEFAULT 'pending' NOT NULL, -- Added status column (pending, shortlisted, rejected, selected, hired)
            FOREIGN KEY (applicant_id) REFERENCES applicants (applicant_id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE,
            UNIQUE (applicant_id, job_id) -- An applicant applies only once per job
        )''')
        # Add indices for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_job_id ON applications (job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_applicant_id ON applications (applicant_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_status ON applications (status)") # Index on status
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_job_status ON applications (job_id, status)") # Composite index
        print("Table 'applications' checked/created.")

        conn.commit() # Commit schema changes explicitly
        print("Database schema initialized/verified successfully.")
    except (sqlite3.Error, AssertionError) as e:
        print(f"Database Error during initialization: {e}")
        traceback.print_exc() # Print stack trace for init errors
    finally:
        if conn:
            conn.close()

# === Job Functions ===

def add_job(job_id, title, description_text, structured_jd_dict):
    """Adds or updates a job posting. Sets status to 'open'."""
    if not job_id or not title:
        print("Error: Job ID and Title required.")
        return False
    conn = None
    success = False
    try:
        conn = get_db_connection(); assert conn # Ensure connection is valid
        structured_jd_json = json.dumps(structured_jd_dict) if structured_jd_dict else None
        with conn: # Use context manager for transaction
             # Insert or Replace logic ensures job is always 'open' when added/updated via this function
            conn.execute("""
                INSERT INTO jobs (job_id, title, description_text, structured_jd, job_status)
                VALUES (?, ?, ?, ?, 'open')
                ON CONFLICT(job_id) DO UPDATE SET
                    title = excluded.title,
                    description_text = excluded.description_text,
                    structured_jd = excluded.structured_jd,
                    job_status = 'open', -- Reset status to 'open' on update too
                    date_added = CURRENT_TIMESTAMP
                """, (job_id, title, description_text, structured_jd_json))
        success = True; print(f"Job '{job_id}' transaction committed (Status: open).")
    except (sqlite3.Error, AssertionError) as e: # Catch assertion errors too
        print(f"DB Error adding/updating job {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return success

def get_job(job_id):
    """Retrieves details for a single job, including its status."""
    conn = None
    job_data = None
    try:
        conn = get_db_connection(); assert conn
        # Select job_status as well
        job = conn.execute("SELECT job_id, title, description_text, date_added, job_status FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        job_data = dict(job) if job else None
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error retrieving job {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return job_data

def get_all_jobs(status_filter=None):
    """Retrieves all jobs, optionally filtering by status ('open', 'closed', etc.)."""
    conn = None
    jobs_list = []
    try:
        conn = get_db_connection(); assert conn
        sql = "SELECT job_id, title, description_text, job_status FROM jobs"
        params = []
        if status_filter:
            sql += " WHERE job_status = ?"
            params.append(status_filter)
        sql += " ORDER BY date_added DESC"

        jobs = conn.execute(sql, tuple(params)).fetchall()
        jobs_list = [dict(job) for job in jobs]
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error retrieving jobs (filter: {status_filter}): {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return jobs_list

def get_structured_jd(job_id):
    """Retrieves the structured JD JSON."""
    conn = None
    jd_data = None
    try:
        conn = get_db_connection(); assert conn
        result = conn.execute("SELECT structured_jd FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if result and result['structured_jd']:
            jd_data = json.loads(result['structured_jd'])
    except json.JSONDecodeError as e: print(f"Error decoding JSON JD for {job_id}: {e}"); traceback.print_exc()
    except (sqlite3.Error, AssertionError) as e: print(f"DB Error retrieving structured JD for {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return jd_data

def update_job_status(job_id, new_status):
    """Updates the status of a job posting (e.g., 'open', 'closed', 'filled')."""
    allowed_statuses = ['open', 'closed', 'filled'] # Define valid job statuses
    if new_status not in allowed_statuses:
        print(f"Error: Invalid job status '{new_status}' provided.")
        return False
    conn = None
    success = False
    try:
        conn = get_db_connection(); assert conn
        cursor = None
        with conn:
            cursor = conn.execute("UPDATE jobs SET job_status = ? WHERE job_id = ?", (new_status, job_id))
        if cursor and cursor.rowcount > 0:
            success = True
            print(f"Job status UPDATE committed for J:{job_id} to '{new_status}'.")
        else:
            print(f"WARN: Job not found or status unchanged for J:{job_id}.")
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error updating job status for J:{job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return success

# === Applicant Functions ===

def add_applicant(applicant_id, name, resume_filename):
    """Adds or updates applicant profile. Uses email as applicant_id. Stores resume filename."""
    if not applicant_id or not resume_filename:
        print("Error: Applicant ID (Email) and Resume Filename required.")
        return False
    conn = None
    success = False
    try:
        conn = get_db_connection(); assert conn
        with conn:
            conn.execute("""
                INSERT INTO applicants (applicant_id, name, resume_file_path, structured_resume)
                VALUES (?, ?, ?, NULL)
                ON CONFLICT(applicant_id) DO UPDATE SET
                    name = excluded.name,
                    resume_file_path = excluded.resume_file_path,
                    date_added = CURRENT_TIMESTAMP
                """, (applicant_id, name, resume_filename))
        success = True; print(f"Applicant '{applicant_id}' transaction committed. Resume file: {resume_filename}")
    except sqlite3.IntegrityError as e:
         # Could be applicant_id PK conflict (expected) or resume_file_path UNIQUE conflict (less likely but possible)
         print(f"DB Integrity Error (applicant) {applicant_id}: {e}. Record likely exists, or resume filename conflict.");
         # If the goal is to add or update, ON CONFLICT handles the update, so maybe return True here?
         # Let's assume the update case is still a "success" in terms of the profile being present/updated.
         # However, if it's a resume_file_path conflict, that's different. Hard to distinguish easily.
         # Let's return False specifically on IntegrityError to signal a potential issue.
         success = False
         traceback.print_exc()
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error adding/updating applicant {applicant_id}: {e}"); traceback.print_exc()
        success = False
    finally:
        if conn: conn.close()
    return success

def get_structured_resume(applicant_id):
    """Retrieves the structured resume JSON."""
    conn = None
    resume_data = None
    try:
        conn = get_db_connection(); assert conn
        result = conn.execute("SELECT structured_resume FROM applicants WHERE applicant_id = ?", (applicant_id,)).fetchone()
        if result and result['structured_resume']:
            resume_data = json.loads(result['structured_resume'])
    except json.JSONDecodeError as e: print(f"Error decoding JSON resume for {applicant_id}: {e}"); traceback.print_exc()
    except (sqlite3.Error, AssertionError) as e: print(f"DB Error retrieving structured resume for {applicant_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return resume_data

def get_resume_path(applicant_id):
    """Retrieves the resume filename."""
    conn = None
    file_path = None
    try:
        conn = get_db_connection(); assert conn
        result = conn.execute("SELECT resume_file_path FROM applicants WHERE applicant_id = ?", (applicant_id,)).fetchone()
        file_path = result['resume_file_path'] if result else None
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error retrieving resume path for {applicant_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return file_path


# === Application Functions ===

def add_application(applicant_id, job_id):
    """Records an application link. Default status 'pending'. Returns True if newly inserted."""
    if not applicant_id or not job_id:
        print("Error: Applicant ID and Job ID required.")
        return False
    conn = None
    inserted_new = False
    try:
        conn = get_db_connection(); assert conn
        cursor = None # Initialize cursor
        with conn: # Use context manager for transaction
            cursor = conn.execute("""
                INSERT INTO applications (applicant_id, job_id, rating, rating_details, status)
                VALUES (?, ?, NULL, NULL, 'pending') -- Ensure default status
                ON CONFLICT(applicant_id, job_id) DO NOTHING
                """, (applicant_id, job_id))
        if cursor and cursor.rowcount > 0:
             inserted_new = True
             print(f"Application transaction committed for A:{applicant_id}, J:{job_id}. New record inserted (status: pending).")
        else:
             # This means the (applicant_id, job_id) pair already exists
             print(f"Application transaction finished for A:{applicant_id}, J:{job_id}. Record already existed.")
    except (sqlite3.Error, AssertionError) as e:
        print(f"Database Error adding application for A:{applicant_id}, J:{job_id}: {e}"); traceback.print_exc()
        inserted_new = False # Ensure False on error
    finally:
        if conn: conn.close()
    return inserted_new # Return True only if a new application was recorded

def update_application_rating(applicant_id, job_id, rating_result_dict):
    """Updates an existing application record with AI rating details."""
    if not applicant_id or not job_id or not isinstance(rating_result_dict, dict):
         print("Error: Applicant ID, Job ID, and Rating dict required for update.")
         return False
    conn = None
    success = False
    try:
        conn = get_db_connection(); assert conn
        rating_score = rating_result_dict.get('rating')
        if rating_score is not None:
            try: rating_score = int(rating_score)
            except (ValueError, TypeError): rating_score = None # Set to NULL if conversion fails
        else: rating_score = None # Explicitly NULL if key missing

        rating_details_json = json.dumps(rating_result_dict)
        cursor = None
        with conn:
            # Update timestamp when rating is added/updated
            cursor = conn.execute("""
                UPDATE applications
                SET rating = ?,
                    rating_details = ?,
                    application_date = CURRENT_TIMESTAMP
                WHERE applicant_id = ? AND job_id = ?
                """, (rating_score, rating_details_json, applicant_id, job_id))
        if cursor and cursor.rowcount > 0:
             success = True
             print(f"Rating UPDATE transaction committed for A:{applicant_id}, J:{job_id}.")
        else:
             print(f"WARN: No application found or no change needed to update rating for A:{applicant_id}, J:{job_id}.")
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error updating rating for A:{applicant_id}, J:{job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return success

def update_application_status(applicant_id, job_id, new_status):
    """Updates the status of a specific application."""
    allowed_statuses = ['pending', 'shortlisted', 'rejected', 'selected', 'hired']
    if new_status not in allowed_statuses:
        print(f"Error: Invalid status '{new_status}' provided.")
        return False
    if not applicant_id or not job_id:
        print("Error: Applicant ID and Job ID required for status update.")
        return False

    conn = None
    success = False
    try:
        conn = get_db_connection(); assert conn
        cursor = None
        with conn:
            # Update application_date as well when status changes? Optional.
            # If yes, add ", application_date = CURRENT_TIMESTAMP" to SET clause
            cursor = conn.execute("""
                UPDATE applications
                SET status = ?
                WHERE applicant_id = ? AND job_id = ?
                """, (new_status, applicant_id, job_id))
        if cursor and cursor.rowcount > 0:
             success = True
             print(f"Status UPDATE transaction committed for A:{applicant_id}, J:{job_id} to '{new_status}'.")
        else:
             print(f"WARN: No application found or status unchanged for A:{applicant_id}, J:{job_id}.")
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error updating status for A:{applicant_id}, J:{job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return success

def get_applicants_for_job(job_id, include_rejected=True):
    """Retrieves all applicants+details who applied for a specific job, optionally filtering status."""
    if not job_id: return []
    conn = None
    results_list = []
    print(f"DEBUG: Getting applicants for Job ID: {job_id}, Include Rejected: {include_rejected}")
    try:
        conn = get_db_connection(); assert conn
        sql = '''
            SELECT
                app.applicant_id,
                apl.name,
                apl.resume_file_path,
                app.rating,
                app.application_date,
                app.status -- Fetch the status
            FROM applications app
            JOIN applicants apl ON app.applicant_id = apl.applicant_id
            WHERE app.job_id = ?
        '''
        params = [job_id]
        # --- Corrected Logic: Filter OUT 'rejected' if include_rejected is False ---
        if not include_rejected:
            sql += " AND (app.status IS NULL OR app.status != ?)" # Exclude rows where status IS 'rejected'
            params.append('rejected')

        sql += " ORDER BY app.application_date DESC" # Keep default order by date

        cursor = conn.execute(sql, tuple(params))
        raw_results = cursor.fetchall()
        print(f"DEBUG: Raw fetchall result for job {job_id} (rejected hidden: {not include_rejected}): {raw_results}")
        if raw_results:
             results_list = [dict(row) for row in raw_results]
        else:
            print(f"DEBUG: No rows found by fetchall for job {job_id} (rejected hidden: {not include_rejected}).")

    except (sqlite3.Error, AssertionError, Exception) as e:
        print(f"DB Error retrieving/processing applicants for job {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    print(f"DEBUG: Returning {len(results_list)} applicants for job {job_id}.")
    return results_list

def get_applications_by_status(job_id, status):
    """Retrieves applications matching a specific status for a job."""
    if not job_id or not status: return []
    conn = None
    results_list = []
    try:
        conn = get_db_connection(); assert conn
        cursor = conn.execute('''
            SELECT app.applicant_id, apl.name, apl.resume_file_path, app.rating, app.status
            FROM applications app
            JOIN applicants apl ON app.applicant_id = apl.applicant_id
            WHERE app.job_id = ? AND app.status = ?
            ORDER BY app.rating DESC -- Order by rating for shortlisted/selected
        ''', (job_id, status))
        raw_results = cursor.fetchall()
        if raw_results:
             results_list = [dict(row) for row in raw_results]
    except (sqlite3.Error, AssertionError, Exception) as e:
        print(f"DB Error retrieving applicants for job {job_id} by status {status}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return results_list

def get_ranked_applicants(job_id, n=10, include_rejected=False):
    """Retrieves top N RATED applicants, optionally excluding rejected ones."""
    if not job_id: return []
    conn = None
    ranked_list = []
    try:
        conn = get_db_connection(); assert conn
        sql = '''
            SELECT app.applicant_id, apl.name, app.rating
            FROM applications app
            JOIN applicants apl ON app.applicant_id = apl.applicant_id
            WHERE app.job_id = ? AND app.rating IS NOT NULL
        '''
        params = [job_id]
        if not include_rejected:
            sql += " AND (app.status IS NULL OR app.status != ?)" # Exclude rejected
            params.append('rejected')

        sql += " ORDER BY app.rating DESC LIMIT ?"
        params.append(n) # Add limit parameter

        cursor = conn.execute(sql, tuple(params))
        results = cursor.fetchall()
        ranked_list = [(row['applicant_id'], row['name'], row['rating']) for row in results]
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error retrieving ranked applicants for job {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return ranked_list

# === Test Block ===
if __name__ == "__main__":
    print("\n" + "="*10 + " Running Database Utility Tests " + "="*10)
    DB_FILE = 'test_job_portal.db'
    # Clean up old test DB files if they exist
    for f in [DB_FILE, DB_FILE + "-wal", DB_FILE + "-shm"]:
        if os.path.exists(f):
            try: os.remove(f); print(f"Removed old test file: {f}")
            except Exception as e: print(f"Error removing {f}: {e}")

    print(f"Using temporary database: {DB_FILE}")
    init_db() # Initialize test DB with status columns

    print("\n1. Adding Job...") # Job status defaults to 'open'
    sample_jd = {"title": "DB Test Engineer", "skills": ["SQL"], "experience": 1}
    job_added = add_job("DBTEST001", "Database QA", "Testing DBs.", sample_jd)
    print(f"Job add success: {job_added}")

    print("\n2. Adding Applicants...")
    app1_id="alice@dbtest.com"; app1_res="res1.pdf"
    app2_id="bob@dbtest.com";   app2_res="res2.docx"
    app3_id="charlie@dbtest.com"; app3_res="res3.txt" # Third applicant
    app1_added = add_applicant(app1_id, "Alice DB", app1_res)
    print(f"Applicant 1 add success: {app1_added}")
    app2_added = add_applicant(app2_id, "Bob DB", app2_res)
    print(f"Applicant 2 add success: {app2_added}")
    app3_added = add_applicant(app3_id, "Charlie DB", app3_res)
    print(f"Applicant 3 add success: {app3_added}")


    print("\n3. Adding Applications...") # Status defaults to 'pending'
    app1_applied = add_application(app1_id, "DBTEST001")
    print(f"App1 apply success (first time): {app1_applied}")
    app2_applied = add_application(app2_id, "DBTEST001")
    print(f"App2 apply success (first time): {app2_applied}")
    app3_applied = add_application(app3_id, "DBTEST001")
    print(f"App3 apply success (first time): {app3_applied}")
    app1_reapply = add_application(app1_id, "DBTEST001") # Apply again
    print(f"App1 apply success (second time): {app1_reapply}") # Should be False

    print("\n4. Getting Applicants (All)...")
    applicants_all = get_applicants_for_job("DBTEST001", include_rejected=True)
    print(f"Retrieved Applicants ({len(applicants_all)}):")
    if applicants_all: print(json.dumps(applicants_all, indent=2))
    else: print("No applicants retrieved.")
    assert len(applicants_all) == 3, f"TEST FAILED: Expected 3 applicants, got {len(applicants_all)}"
    print("Applicant retrieval count looks correct.")

    print("\n5. Updating Ratings...")
    rating1 = {"rating": 70, "summary":"ok"}; rating2 = {"rating": 95, "summary":"great"}; rating3 = {"rating": 55, "summary":"maybe"}
    update1_ok = update_application_rating(app1_id, "DBTEST001", rating1)
    print(f"Update rating 1 success: {update1_ok}")
    update2_ok = update_application_rating(app2_id, "DBTEST001", rating2)
    print(f"Update rating 2 success: {update2_ok}")
    update3_ok = update_application_rating(app3_id, "DBTEST001", rating3)
    print(f"Update rating 3 success: {update3_ok}")

    print("\n6. Updating Statuses...")
    status1_ok = update_application_status(app1_id, "DBTEST001", "shortlisted")
    print(f"Update status 1 success: {status1_ok}")
    status2_ok = update_application_status(app2_id, "DBTEST001", "rejected")
    print(f"Update status 2 success: {status2_ok}")
    # Applicant 3 remains 'pending'

    print("\n7. Getting Applicants (Rejected Hidden)...")
    applicants_pending_shortlisted = get_applicants_for_job("DBTEST001", include_rejected=False)
    print(f"Retrieved Pending/Shortlisted ({len(applicants_pending_shortlisted)}):")
    if applicants_pending_shortlisted: print(json.dumps(applicants_pending_shortlisted, indent=2))
    else: print("No applicants retrieved.")
    assert len(applicants_pending_shortlisted) == 2, f"TEST FAILED: Expected 2 non-rejected applicants, got {len(applicants_pending_shortlisted)}"
    app_ids_retrieved = {a['applicant_id'] for a in applicants_pending_shortlisted}
    assert app1_id in app_ids_retrieved and app3_id in app_ids_retrieved, "TEST FAILED: Incorrect applicants retrieved after hiding rejected."
    print("Non-rejected applicant retrieval looks correct.")

    print("\n8. Getting Applicants By Status ('shortlisted')...")
    shortlisted_apps = get_applications_by_status("DBTEST001", "shortlisted")
    print(f"Retrieved Shortlisted ({len(shortlisted_apps)}):")
    if shortlisted_apps: print(json.dumps(shortlisted_apps, indent=2))
    else: print("No shortlisted applicants retrieved.")
    assert len(shortlisted_apps) == 1 and shortlisted_apps[0]['applicant_id'] == app1_id, "TEST FAILED: Incorrect shortlisted retrieval."
    print("Shortlisted retrieval looks correct.")

    print("\n9. Getting Ranked Applicants (All Rated)...")
    ranked_apps_all = get_ranked_applicants("DBTEST001", n=5, include_rejected=True)
    print(f"Retrieved Ranked (incl. rejected) ({len(ranked_apps_all)}): {ranked_apps_all}")
    assert len(ranked_apps_all) == 3, "TEST FAILED: Expected 3 ranked apps."
    assert ranked_apps_all[0][0] == app2_id, "TEST FAILED: Ranking order (incl. rejected) incorrect."
    print("Ranking (incl. rejected) looks correct.")

    print("\n10. Getting Ranked Applicants (Rejected Hidden)...")
    ranked_apps_active = get_ranked_applicants("DBTEST001", n=5, include_rejected=False)
    print(f"Retrieved Ranked (excl. rejected) ({len(ranked_apps_active)}): {ranked_apps_active}")
    assert len(ranked_apps_active) == 2, "TEST FAILED: Expected 2 active ranked apps."
    assert ranked_apps_active[0][0] == app1_id, "TEST FAILED: Ranking order (excl. rejected) incorrect."
    print("Ranking (excl. rejected) looks correct.")

    print("\n11. Updating Job Status...")
    job_status_ok = update_job_status("DBTEST001", "closed")
    print(f"Job status update success: {job_status_ok}")
    updated_job = get_job("DBTEST001")
    assert updated_job and updated_job['job_status'] == 'closed', "TEST FAILED: Job status not updated correctly."
    print("Job status update verified.")


    print("\n12. Cleaning up test database...")
    # Cleanup logic moved to start of test block

    print("\n" + "="*10 + " Database Tests Finished " + "="*10)
