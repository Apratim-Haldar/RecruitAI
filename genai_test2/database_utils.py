# database_utils.py (Corrected version with get_structured_resume and preferences)
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
        # print("DB Connection established with WAL mode and busy_timeout.") # Less verbose
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

        # --- Modify Job Postings Table ---
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description_text TEXT,
            structured_jd TEXT,   -- Store structured JD as JSON string
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            job_status TEXT DEFAULT 'open' NOT NULL, -- Existing status
            analysis_preference TEXT DEFAULT 'manual' NOT NULL, -- NEW: 'manual', 'scheduled', 'batch'
            analysis_schedule TEXT,                         -- NEW: e.g., '23:00' for scheduled
            analysis_batch_size INTEGER                     -- NEW: e.g., 5 for batch
        )''')
        # Add new columns if table already exists (idempotent add)
        try: cursor.execute("ALTER TABLE jobs ADD COLUMN analysis_preference TEXT DEFAULT 'manual' NOT NULL;")
        except sqlite3.OperationalError: pass # Ignore error if column already exists
        try: cursor.execute("ALTER TABLE jobs ADD COLUMN analysis_schedule TEXT;")
        except sqlite3.OperationalError: pass
        try: cursor.execute("ALTER TABLE jobs ADD COLUMN analysis_batch_size INTEGER;")
        except sqlite3.OperationalError: pass
        print("Table 'jobs' checked/created/updated.")
        # --- End Modification ---

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

        # Applications Table
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

def add_job(job_id, title, description_text, structured_jd_dict,
            analysis_preference='manual', analysis_schedule=None, analysis_batch_size=None):
    """Adds or updates a job posting including analysis preferences. Sets status to 'open'."""
    if not job_id or not title:
        print("Error: Job ID and Title required.")
        return False
    conn = None
    success = False
    try:
        conn = get_db_connection(); assert conn # Ensure connection is valid
        structured_jd_json = json.dumps(structured_jd_dict) if structured_jd_dict else None

        # Clean up preference data based on type
        if analysis_preference != 'scheduled': analysis_schedule = None
        if analysis_preference != 'batch': analysis_batch_size = None
        if analysis_preference == 'batch' and not isinstance(analysis_batch_size, int): analysis_batch_size = 5 # Default

        with conn: # Use context manager for transaction
            conn.execute("""
                INSERT INTO jobs (
                    job_id, title, description_text, structured_jd, job_status,
                    analysis_preference, analysis_schedule, analysis_batch_size
                )
                VALUES (?, ?, ?, ?, 'open', ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    title = excluded.title,
                    description_text = excluded.description_text,
                    structured_jd = excluded.structured_jd,
                    job_status = 'open', -- Reset status to 'open' on update too
                    analysis_preference = excluded.analysis_preference,
                    analysis_schedule = excluded.analysis_schedule,
                    analysis_batch_size = excluded.analysis_batch_size,
                    date_added = CURRENT_TIMESTAMP
                """, (job_id, title, description_text, structured_jd_json,
                      analysis_preference, analysis_schedule, analysis_batch_size))
        success = True; print(f"Job '{job_id}' transaction committed (Prefs: {analysis_preference}).")
    except (sqlite3.Error, AssertionError) as e: # Catch assertion errors too
        print(f"DB Error adding/updating job {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return success

def get_job(job_id):
    """Retrieves details for a single job, including its status and preferences."""
    conn = None
    job_data = None
    try:
        conn = get_db_connection(); assert conn
        # Select all relevant columns
        job = conn.execute("""
            SELECT job_id, title, description_text, date_added, job_status,
                   analysis_preference, analysis_schedule, analysis_batch_size, structured_jd
            FROM jobs WHERE job_id = ?
            """, (job_id,)).fetchone() # Added structured_jd here for hr_view_applicants context
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
        # Include new preference columns
        sql = """SELECT job_id, title, description_text, job_status,
                        analysis_preference, analysis_schedule, analysis_batch_size
                 FROM jobs"""
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
            # Check if the job exists but already has the target status
            existing_job = get_job(job_id) # Need to call get_job correctly
            if existing_job and existing_job['job_status'] == new_status:
                print(f"WARN: Job {job_id} already has status '{new_status}'. No change made.")
                success = True # Consider it success if status is already correct
            else:
                print(f"WARN: Job not found or status unchanged for J:{job_id}.") # Job might not exist
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error updating job status for J:{job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return success

def get_jobs_with_preference(preference_type):
    """Retrieves all jobs matching a specific analysis_preference."""
    conn = None
    jobs_list = []
    try:
        conn = get_db_connection(); assert conn
        sql = """SELECT job_id, title, analysis_preference, analysis_schedule, analysis_batch_size, job_status
                 FROM jobs WHERE analysis_preference = ?"""
        jobs = conn.execute(sql, (preference_type,)).fetchall()
        jobs_list = [dict(job) for job in jobs]
    except (sqlite3.Error, AssertionError) as e:
        print(f"DB Error retrieving jobs by preference '{preference_type}': {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    return jobs_list

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
                    resume_file_path = excluded.resume_file_path, -- Update resume path on conflict too
                    date_added = CURRENT_TIMESTAMP
                """, (applicant_id, name, resume_filename))
        success = True; # print(f"Applicant '{applicant_id}' transaction committed. Resume file: {resume_filename}") # Less verbose
    except sqlite3.IntegrityError as e:
         # Check if it's a unique constraint violation on resume_file_path
         if 'UNIQUE constraint failed: applicants.resume_file_path' in str(e):
              print(f"DB Integrity Error (applicant): Resume filename '{resume_filename}' already exists for another applicant.")
         else:
             # Assume it's the primary key conflict (applicant_id) which is handled by ON CONFLICT
             print(f"DB Integrity Info (applicant): Applicant ID '{applicant_id}' already exists, updating record.")
             success = True # ON CONFLICT update means it's still a 'successful' operation
             # If we get here despite ON CONFLICT, something else is wrong
             if not success: traceback.print_exc()
         # If it wasn't the PK conflict or handled by ON CONFLICT, treat as failure
         if not success:
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
    print(f"--- [DB Util] Attempting to get structured_resume for: {applicant_id} ---") # LOG
    try:
        conn = get_db_connection(); assert conn
        result = conn.execute("SELECT structured_resume FROM applicants WHERE applicant_id = ?", (applicant_id,)).fetchone()
        if result and result['structured_resume']:
            db_json_string = result['structured_resume'] # LOG
            print(f"--- [DB Util] Found raw JSON string in DB for {applicant_id}: {db_json_string[:200]}...") # LOG (truncated)
            try:
                resume_data = json.loads(db_json_string)
                print(f"--- [DB Util] Successfully parsed JSON from DB for {applicant_id} ---") # LOG
            except json.JSONDecodeError as json_e:
                 print(f"Error: [DB Util] Failed decoding JSON resume from DB for {applicant_id}: {json_e}") # LOG ERROR
                 resume_data = {"error": "Invalid JSON stored in database."} # Return error dict
        elif result:
             print(f"--- [DB Util] Found applicant {applicant_id} but structured_resume column is NULL ---") # LOG NULL case
        else:
             print(f"--- [DB Util] Applicant {applicant_id} not found in applicants table ---") # LOG Not Found case

    except (sqlite3.Error, AssertionError) as e:
        print(f"Error: [DB Util] DB Error retrieving structured resume for {applicant_id}: {e}"); traceback.print_exc() # LOG ERROR
        resume_data = {"error": "Database error retrieving structured resume."} # Return error dict
    finally:
        if conn: conn.close()
    # Return None only if record not found or column is NULL, otherwise return dict (or error dict)
    return resume_data if resume_data is not None else None


def update_structured_resume(applicant_id, structured_data_dict):
    """Updates the structured_resume column for a given applicant."""
    if not applicant_id or not isinstance(structured_data_dict, dict):
        print("Error: [DB Util] Applicant ID and structured data dictionary required for update.")
        return False
    conn = None
    success = False
    print(f"--- [DB Util] Attempting to update structured_resume for: {applicant_id} ---") # LOG
    try:
        conn = get_db_connection(); assert conn
        # Log the data being saved (partially, be careful with PII)
        log_data = {k: v for k, v in structured_data_dict.items() if k in ['name', 'skills', 'validation_warnings', 'error']} # Log subset + errors
        print(f"--- [DB Util] Data to save (subset): {log_data}") # LOG
        structured_resume_json = json.dumps(structured_data_dict)
        cursor = None
        with conn:
            cursor = conn.execute(
                "UPDATE applicants SET structured_resume = ? WHERE applicant_id = ?",
                (structured_resume_json, applicant_id)
            )
        if cursor and cursor.rowcount > 0:
            success = True
            print(f"--- [DB Util] Successfully updated structured_resume for applicant {applicant_id}. ---") # LOG SUCCESS
        else:
            print(f"Warning: [DB Util] Applicant {applicant_id} not found or structured_resume not updated (rowcount 0).") # LOG WARN
    except json.JSONDecodeError as json_e:
        print(f"Error: [DB Util] Error encoding structured resume to JSON for {applicant_id}: {json_e}") # LOG ERROR
    except (sqlite3.Error, AssertionError) as e:
        print(f"Error: [DB Util] DB Error updating structured resume for {applicant_id}: {e}"); traceback.print_exc() # LOG ERROR
    finally:
        if conn: conn.close()
    return success

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
    """Records an application link. Default status 'pending'. Returns True if newly inserted, False if exists, None if error."""
    if not applicant_id or not job_id:
        print("Error: Applicant ID and Job ID required.")
        return None # Indicate error
    conn = None
    inserted_new = False
    error_occurred = False
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
             # print(f"Application transaction committed for A:{applicant_id}, J:{job_id}. New record inserted (status: pending).") # Less verbose
        else:
             # This means the (applicant_id, job_id) pair already exists
             pass
    except (sqlite3.Error, AssertionError) as e:
        print(f"Database Error adding application for A:{applicant_id}, J:{job_id}: {e}"); traceback.print_exc()
        error_occurred = True
    finally:
        if conn: conn.close()

    # Return status: True = newly added, False = already exists, None = error
    if error_occurred:
        return None
    elif inserted_new:
        return True
    else:
        return False

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
                    rating_details = ?
                WHERE applicant_id = ? AND job_id = ?
                """, (rating_score, rating_details_json, applicant_id, job_id)) # Removed date update here
        if cursor and cursor.rowcount > 0:
             success = True
             # print(f"Rating UPDATE transaction committed for A:{applicant_id}, J:{job_id}.") # Less verbose
        else:
             # print(f"WARN: No application found or no change needed to update rating for A:{applicant_id}, J:{job_id}.") # Less verbose
             pass
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
            cursor = conn.execute("""
                UPDATE applications
                SET status = ?
                WHERE applicant_id = ? AND job_id = ?
                """, (new_status, applicant_id, job_id))
        if cursor and cursor.rowcount > 0:
             success = True
             # print(f"Status UPDATE transaction committed for A:{applicant_id}, J:{job_id} to '{new_status}'.") # Less verbose
        else:
             # print(f"WARN: No application found or status unchanged for A:{applicant_id}, J:{job_id}.") # Less verbose
             pass
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
    # print(f"DEBUG: Getting applicants for Job ID: {job_id}, Include Rejected: {include_rejected}") # Less verbose
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
        if not include_rejected:
            sql += " AND (app.status IS NULL OR app.status != ?)" # Exclude rows where status IS 'rejected'
            params.append('rejected')

        sql += " ORDER BY app.application_date DESC" # Keep default order by date

        cursor = conn.execute(sql, tuple(params))
        raw_results = cursor.fetchall()
        # print(f"DEBUG: Raw fetchall result for job {job_id} (rejected hidden: {not include_rejected}): {raw_results}") # Less verbose
        if raw_results:
             results_list = [dict(row) for row in raw_results]
        # else: # Less verbose
            # print(f"DEBUG: No rows found by fetchall for job {job_id} (rejected hidden: {not include_rejected}).")

    except (sqlite3.Error, AssertionError, Exception) as e:
        print(f"DB Error retrieving/processing applicants for job {job_id}: {e}"); traceback.print_exc()
    finally:
        if conn: conn.close()
    # print(f"DEBUG: Returning {len(results_list)} applicants for job {job_id}.") # Less verbose
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
    print("\n" + "="*10 + " Running Database Utility Tests (with Preferences) " + "="*10)
    DB_FILE = 'test_job_portal.db'
    # Clean up old test DB files if they exist
    for f in [DB_FILE, DB_FILE + "-wal", DB_FILE + "-shm"]:
        if os.path.exists(f):
            try: os.remove(f); print(f"Removed old test file: {f}")
            except Exception as e: print(f"Error removing {f}: {e}")

    print(f"Using temporary database: {DB_FILE}")
    init_db() # Initialize test DB with status columns

    print("\n1. Adding Jobs with Preferences...")
    sample_jd = {"title": "DB Test Engineer", "skills": ["SQL"], "experience": 1}
    job1_added = add_job("DBTEST001", "Database QA", "Testing DBs.", sample_jd,
                         analysis_preference='scheduled', analysis_schedule='22:00')
    print(f"Job 1 add success (scheduled): {job1_added}")
    job2_added = add_job("DBTEST002", "Batch Tester", "Testing batches.", sample_jd,
                         analysis_preference='batch', analysis_batch_size=10)
    print(f"Job 2 add success (batch): {job2_added}")
    job3_added = add_job("DBTEST003", "Manual Tester", "Manual tests.", sample_jd,
                         analysis_preference='manual') # Default
    print(f"Job 3 add success (manual): {job3_added}")

    print("\n2. Getting Job Details...")
    job1_details = get_job("DBTEST001")
    print(f"Job 1 Details: {json.dumps(dict(job1_details), indent=2) if job1_details else 'Not Found'}") # Convert Row to dict for JSON dump
    assert job1_details and job1_details['analysis_preference'] == 'scheduled' and job1_details['analysis_schedule'] == '22:00', "Test Failed: Job 1 preference incorrect."
    job2_details = get_job("DBTEST002")
    print(f"Job 2 Details: {json.dumps(dict(job2_details), indent=2) if job2_details else 'Not Found'}") # Convert Row to dict
    assert job2_details and job2_details['analysis_preference'] == 'batch' and job2_details['analysis_batch_size'] == 10, "Test Failed: Job 2 preference incorrect."
    job3_details = get_job("DBTEST003")
    print(f"Job 3 Details: {json.dumps(dict(job3_details), indent=2) if job3_details else 'Not Found'}") # Convert Row to dict
    assert job3_details and job3_details['analysis_preference'] == 'manual', "Test Failed: Job 3 preference incorrect."
    print("Job detail retrieval looks correct.")

    print("\n3. Getting Jobs by Preference...")
    scheduled_jobs = get_jobs_with_preference('scheduled')
    print(f"Scheduled Jobs: {[dict(j) for j in scheduled_jobs]}") # Convert list of Rows
    assert len(scheduled_jobs) == 1 and scheduled_jobs[0]['job_id'] == 'DBTEST001', "Test Failed: Scheduled job fetch incorrect."
    batch_jobs = get_jobs_with_preference('batch')
    print(f"Batch Jobs: {[dict(j) for j in batch_jobs]}") # Convert list of Rows
    assert len(batch_jobs) == 1 and batch_jobs[0]['job_id'] == 'DBTEST002', "Test Failed: Batch job fetch incorrect."
    manual_jobs = get_jobs_with_preference('manual')
    print(f"Manual Jobs: {[dict(j) for j in manual_jobs]}") # Convert list of Rows
    assert len(manual_jobs) == 1 and manual_jobs[0]['job_id'] == 'DBTEST003', "Test Failed: Manual job fetch incorrect."
    print("Job retrieval by preference looks correct.")

    print("\n4. Adding Applicants and Applications for Ranking/Status Tests...")
    app1_id="alice@dbtest.com"; app1_res="res1.pdf"
    app2_id="bob@dbtest.com";   app2_res="res2.docx"
    app3_id="charlie@dbtest.com"; app3_res="res3.txt"
    add_applicant(app1_id, "Alice DB", app1_res)
    add_applicant(app2_id, "Bob DB", app2_res)
    add_applicant(app3_id, "Charlie DB", app3_res)
    add_application(app1_id, "DBTEST001")
    add_application(app2_id, "DBTEST001")
    add_application(app3_id, "DBTEST001")
    rating1 = {"rating": 70, "summary":"ok"}; rating2 = {"rating": 95, "summary":"great"}; rating3 = {"rating": 55, "summary":"maybe"}
    update_application_rating(app1_id, "DBTEST001", rating1)
    update_application_rating(app2_id, "DBTEST001", rating2)
    update_application_rating(app3_id, "DBTEST001", rating3)
    update_application_status(app1_id, "DBTEST001", "shortlisted")
    update_application_status(app2_id, "DBTEST001", "rejected")
    print("Added applicants, applications, ratings, and statuses.")

    print("\n5. Testing get_structured_resume (basic check)...")
    # Add a structured resume manually for testing
    structured_resume_sample = {"name": "Alice DB", "skills": ["SQL"]}
    conn_test = get_db_connection()
    try:
        with conn_test:
             conn_test.execute("UPDATE applicants SET structured_resume = ? WHERE applicant_id = ?", (json.dumps(structured_resume_sample), app1_id))
        print(f"Manually added structured resume for {app1_id}")
    except Exception as e:
        print(f"Error adding test structured resume: {e}")
    finally:
        if conn_test: conn_test.close()

    retrieved_struct_resume = get_structured_resume(app1_id)
    print(f"Retrieved structured resume for {app1_id}: {retrieved_struct_resume}")
    assert retrieved_struct_resume == structured_resume_sample, "Test Failed: get_structured_resume failed."
    print("get_structured_resume looks correct.")

    print("\n6. Testing update_structured_resume...")
    test_struct_data = {"name": "Test User", "skills": ["testing"]}
    update_success_nonexist = update_structured_resume("new_test@email.com", test_struct_data) # Test non-existent user
    print(f"Update non-existent user success: {update_success_nonexist}")
    assert not update_success_nonexist, "Test Failed: Should not succeed updating non-existent user."

    # Use existing user from step 4
    update_success_real = update_structured_resume(app2_id, test_struct_data)
    print(f"Update existing user ({app2_id}) success: {update_success_real}")
    assert update_success_real, f"Test Failed: Failed to update existing user {app2_id}."
    retrieved = get_structured_resume(app2_id)
    print(f"Retrieved after update for {app2_id}: {retrieved}")
    assert retrieved == test_struct_data, "Test Failed: Retrieved data doesn't match updated data."
    print("update_structured_resume looks correct.")


    print("\n7. Testing Re-opening Job...")
    update_job_status("DBTEST001", "closed")
    job1_closed = get_job("DBTEST001")
    assert job1_closed and job1_closed['job_status'] == 'closed', "Test Failed: Job closure failed."
    update_job_status("DBTEST001", "open") # Re-open
    job1_reopened = get_job("DBTEST001")
    assert job1_reopened and job1_reopened['job_status'] == 'open', "Test Failed: Job re-opening failed."
    print("Job re-opening verified.")

    print("\n" + "="*10 + " Database Tests (with Preferences) Finished " + "="*10)