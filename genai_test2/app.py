# app.py (Add Scheduler, Preferences, Re-open Route)
from flask import (
    Flask, request, jsonify, render_template, redirect,
    url_for, flash, session, send_from_directory
)
from flask_mail import Mail, Message
from urllib.parse import unquote
import os
import uuid
import json
import re # Still needed for Markdown
from markupsafe import Markup
import traceback
from werkzeug.utils import secure_filename # For secure file uploads

# --- NEW IMPORTS ---
from flask_apscheduler import APScheduler
import atexit # To shutdown scheduler gracefully
# --- END NEW IMPORTS ---


# Import workflow and utility functions
from main_crew import (
    run_suitability_check_direct,
    run_summarization_direct,
    run_ranking_direct
)
from llm_utils import (
    structure_job_description,
    summarize_text_contextually,
    understand_hr_chat_intent,
    to_5_star,
    generate_ranking_highlights
)
# Ensure database_utils functions are correctly imported
from database_utils import (
    get_all_jobs, get_job, get_structured_jd, add_job,
    add_applicant, add_application, get_applicants_for_job,
    update_application_rating, get_resume_path, get_ranked_applicants,
    update_application_status, get_applications_by_status, update_job_status,
    get_jobs_with_preference, # Import the new function
    init_db, # Ensure init_db is imported
    get_structured_resume # Ensure this is imported if needed by main_crew etc.
)
from file_utils import UPLOAD_FOLDER, extract_text_from_file

# --- App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Initialize Scheduler ---
# Configure APScheduler
app.config['SCHEDULER_API_ENABLED'] = False # Disable the API endpoint for security/simplicity
app.config['SCHEDULER_TIMEZONE'] = 'UTC' # Or your local timezone e.g., 'America/New_York'

scheduler = APScheduler()

# --- Email Configuration ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail_username = app.config['MAIL_USERNAME']
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', f"Job Portal AI <{mail_username}>" if mail_username else "Job Portal AI")

mail = None
if all([app.config['MAIL_SERVER'], app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']]):
    try:
        mail = Mail(app)
        print("Flask-Mail initialized.")
    except Exception as e:
        print(f"ERROR initializing Flask-Mail: {e}. Email sending disabled.")
else:
    print("WARNING: Mail server details not fully configured in .env. Email sending disabled.")


# --- Helper Functions & Filters ---
@app.template_filter('nl2br')
def nl2br(s):
    return Markup(s.replace('\n', '<br>\n')) if s else s

@app.template_filter('to_5_star')
def to_5_star_filter(score):
    return to_5_star(score)

# --- Qualitative Status Assessment Function ---
def assess_job_status_quality(job_id):
    """Provides a qualitative assessment of a job listing's progress based on DB data."""
    try:
        # Use include_rejected=True to get all applications for statistics
        apps = get_applicants_for_job(job_id, include_rejected=True)
        if not apps:
            return "No applications yet."

        total = len(apps)
        # Correctly check for non-None rating
        rated = [a for a in apps if a.get('rating') is not None]
        # Correctly check for status strings
        shortlisted = [a for a in apps if a.get('status') == 'shortlisted']
        rejected = [a for a in apps if a.get('status') == 'rejected']
        pending = total - len(shortlisted) - len(rejected)

        # Correctly calculate average rating, avoiding division by zero
        avg_rating = (sum(a['rating'] for a in rated if a.get('rating') is not None) / len(rated)) if rated else 0

        # --- Assessment Logic ---
        if total == 0: return "No applications received yet."
        if len(shortlisted) > 0:
             if avg_rating >= 70: return f"Excellent progress! ({len(shortlisted)} shortlisted, avg. rating {avg_rating:.0f}/100)."
             else: return f"Good start! ({len(shortlisted)} shortlisted, avg. rating {avg_rating:.0f}/100). Keep reviewing."
        if len(rated) < total / 2 and total > 5: return f"Moderate activity ({total} apps), many pending review ({pending})."
        if len(rated) == total and avg_rating >= 60: return f"Review complete. Avg. rating is solid ({avg_rating:.0f}/100), but no one shortlisted yet."
        if len(rated) > 0 and avg_rating < 45:
            if len(rejected) > total * 0.6: return f"Challenging: high rejection rate ({len(rejected)}/{total}) and low avg. rating ({avg_rating:.0f}/100)."
            else: return f"Low suitability: avg. rating is poor ({avg_rating:.0f}/100). Consider revising JD or sourcing."
        if len(rated) == 0 and total > 0: return f"Receiving applications ({total}), but none rated yet."
        # Default fallback
        return f"Steady progress: {total} apps, {len(rated)} rated (avg: {avg_rating:.0f}/100), {pending} pending."

    except Exception as e:
        print(f"Error assessing job status quality for {job_id}: {e}")
        traceback.print_exc()
        return "Assessment unavailable (error)."


# --- Scheduled Task Definitions ---

def analyze_job_applicants(job_id):
    """Task function to analyze unrated applicants for a specific job."""
    # Wrap in app context as scheduler runs outside request context
    with app.app_context():
        print(f"[Scheduler] Analyzing unrated applicants for job: {job_id}")
        job = get_job(job_id)
        if not job or job.get('job_status') != 'open':
            print(f"[Scheduler] Skipping analysis for {job_id} (not found or not open).")
            return

        all_applicants = get_applicants_for_job(job_id, include_rejected=True)
        unrated_applicants = [app for app in all_applicants if app.get('rating') is None]

        if not unrated_applicants:
            # print(f"[Scheduler] No unrated applicants found for {job_id}.") # Less verbose
            return

        print(f"[Scheduler] Found {len(unrated_applicants)} unrated for {job_id}. Starting rating...")
        rated_count = 0; error_count = 0; skipped_count = 0
        for applicant in unrated_applicants:
            applicant_id = applicant.get('applicant_id')
            if not applicant_id: skipped_count += 1; print(f"[Scheduler] Skipping applicant with missing ID in job {job_id}."); continue

            resume_filename = get_resume_path(applicant_id)
            if not resume_filename: skipped_count += 1; print(f"[Scheduler] Skipping {applicant_id} (job {job_id}): No resume path."); continue

            resume_full_path = os.path.join(UPLOAD_FOLDER, secure_filename(resume_filename))
            if not os.path.exists(resume_full_path): skipped_count += 1; print(f"[Scheduler] Skipping {applicant_id} (job {job_id}): Resume file missing ({resume_filename})."); continue

            print(f"[Scheduler] Rating {applicant_id} for job {job_id}...")
            try:
                 rating_result = run_suitability_check_direct(resume_file_path=resume_full_path, job_id=job_id)
                 if isinstance(rating_result, dict) and 'error' not in rating_result and all(k in rating_result for k in ['rating', 'summary', 'fits', 'lacks']):
                     if update_application_rating(applicant_id, job_id, rating_result):
                          rated_count += 1
                     else: error_count += 1; print(f"[Scheduler] ERROR updating DB for {applicant_id} (job {job_id})")
                 else:
                     error_count += 1
                     error_detail = "Incomplete AI response" if isinstance(rating_result, dict) and 'error' not in rating_result else rating_result.get('details', rating_result.get('error', 'Unknown AI error'))
                     print(f"[Scheduler] ERROR AI rating {applicant_id} (job {job_id}): {error_detail}")
            except Exception as e: error_count += 1; print(f"[Scheduler] ERROR exception rating {applicant_id} for {job_id}: {e}"); traceback.print_exc()

        print(f"[Scheduler] Finished rating for {job_id}. Rated: {rated_count}, Errors: {error_count}, Skipped: {skipped_count}")


def check_jobs_for_batch_analysis():
     """Scheduled task to check jobs configured for batch analysis."""
     # Wrap in app context
     with app.app_context():
        print("[Scheduler] Running check for batch analysis jobs...")
        jobs_for_batch_check = get_jobs_with_preference('batch')
        if not jobs_for_batch_check:
            # print("[Scheduler] No jobs configured for batch analysis.") # Less verbose
            return

        for job in jobs_for_batch_check:
            job_id = job['job_id']
            if job.get('job_status') != 'open':
                continue # Skip non-open jobs

            batch_size = job.get('analysis_batch_size', 5)
            batch_size = max(1, batch_size) # Ensure positive batch size

            all_applicants = get_applicants_for_job(job_id, include_rejected=True)
            unrated_applicants = [app for app in all_applicants if app.get('rating') is None]

            if len(unrated_applicants) >= batch_size:
                print(f"[Scheduler] Job {job_id} meets batch threshold ({len(unrated_applicants)} unrated >= {batch_size}). Triggering analysis.")
                # Trigger analysis immediately
                analyze_job_applicants(job_id)

def update_scheduler_for_job(job_id, preference, schedule_time, batch_size):
    """Adds, modifies, or removes scheduler jobs based on job preferences."""
    if not scheduler.running:
        print("[Scheduler] Warning: Scheduler not running, cannot update job.")
        return

    scheduled_job_id = f'scheduled_analysis_{job_id}'
    existing_job = scheduler.get_job(scheduled_job_id)

    # Remove existing job if preference is no longer 'scheduled' or time is invalid/missing
    if preference != 'scheduled' or not schedule_time or not re.match(r'^\d{1,2}:\d{2}$', schedule_time):
        if existing_job:
            try:
                scheduler.remove_job(scheduled_job_id)
                print(f"[Scheduler] Removed scheduled job for {job_id}")
            except Exception as e:
                print(f"[Scheduler] Error removing job {scheduled_job_id}: {e}")
        return # Stop here if not scheduling

    # Add or Modify the job if preference is 'scheduled' and time is valid
    try:
        hour, minute = map(int, schedule_time.split(':'))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            if existing_job:
                 scheduler.modify_job(scheduled_job_id, trigger='cron', hour=hour, minute=minute)
                 print(f"[Scheduler] Modified CRON job for {job_id} to run at {schedule_time}")
            else:
                scheduler.add_job(
                    id=scheduled_job_id,
                    func=analyze_job_applicants,
                    args=[job_id],
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    replace_existing=True # Replace if somehow still exists
                )
                print(f"[Scheduler] Added CRON job for {job_id} at {schedule_time}")
        else:
             print(f"[Scheduler] Error: Invalid hour/minute in schedule time '{schedule_time}' for job {job_id}.")
             if existing_job: # Remove invalid existing job
                 try: scheduler.remove_job(scheduled_job_id); print(f"[Scheduler] Removed invalid existing job for {job_id}")
                 except: pass

    except ValueError:
        print(f"[Scheduler] Error: Invalid schedule time format '{schedule_time}' for job {job_id}.")
        if existing_job: # Remove invalid existing job
            try: scheduler.remove_job(scheduled_job_id); print(f"[Scheduler] Removed invalid existing job for {job_id}")
            except: pass
    except Exception as e:
        print(f"[Scheduler] Error adding/modifying scheduled job for {job_id}: {e}")


def load_scheduled_jobs_from_db():
    """Loads jobs with 'scheduled' preference from DB and schedules them."""
    # Check if scheduler is available and running before proceeding
    if not scheduler or not scheduler.running:
         print("[Scheduler] Scheduler not initialized or running. Skipping DB job load.")
         return

    with app.app_context(): # Need context for DB access
        print("[Scheduler] Loading scheduled analysis jobs from database...")
        try:
             scheduled_jobs_db = get_jobs_with_preference('scheduled')
             count = 0
             for job in scheduled_jobs_db:
                 if job.get('job_status') == 'open': # Only schedule open jobs
                     update_scheduler_for_job(
                         job['job_id'],
                         job['analysis_preference'],
                         job['analysis_schedule'],
                         job['analysis_batch_size']
                     )
                     count += 1
                 # else: # Less verbose
                     # print(f"[Scheduler] Skipping non-open job {job['job_id']} found in DB scheduled jobs.")
             print(f"[Scheduler] Loaded and scheduled {count} jobs from database.")
        except Exception as e:
             print(f"[Scheduler] ERROR loading jobs from DB: {e}")
             traceback.print_exc()


# === Common Routes ===
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# === Chatbot API Endpoint (Enhanced) ===
@app.route('/hr/chat', methods=['POST'])
# @login_required # Add authentication later
def hr_chat_api():
    """Handles requests from the HR chatbot UI using LLM for NLU and DB for data."""
    # ... (keep existing implementation) ...
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"response": "Invalid request format."}), 400

    user_message = data.get('message', '')
    page_context_job_id = data.get('page_context_job_id') # Get from frontend
    session_job_id = session.get('hr_chat_job_context')

    print(f"Chat API received message: '{user_message}', Page Context: {page_context_job_id}, Session Context: {session_job_id}")

    # 1. Understand Intent and Entities using LLM
    current_context_for_nlu = page_context_job_id or session_job_id
    nlu_result = understand_hr_chat_intent(user_message, current_context_for_nlu)
    print(f"NLU Result: {nlu_result}")

    if 'error' in nlu_result:
        print(f"NLU Error: {nlu_result.get('details', nlu_result['error'])}")
        return jsonify({"response": "Apologies, the AI assistant had trouble understanding your request. Please try rephrasing."}), 500

    intent = nlu_result.get('intent', 'unknown')
    entities = nlu_result.get('entities', {})
    extracted_job_id = entities.get('job_id')
    extracted_job_id = extracted_job_id.upper() if isinstance(extracted_job_id, str) else None
    extracted_email = entities.get('applicant_email')
    extracted_name = entities.get('applicant_name')

    # --- Determine Effective Job ID ---
    effective_job_id = None
    # Check if user is asking about 'this/current' job when on a specific page
    use_page_context = intent in ['get_overview', 'get_ranking', 'get_applicant_details', 'get_report'] and \
                       not extracted_job_id and \
                       re.search(r'\b(this|current|here|the job)\b', user_message.lower()) is not None

    if extracted_job_id:
        effective_job_id = extracted_job_id
    elif use_page_context and page_context_job_id:
        effective_job_id = page_context_job_id
        print(f"Using Page Context Job ID based on implicit reference: {effective_job_id}")
    # NEW: Check if intent suggests general overview (e.g., 'status of listings')
    elif intent == 'get_overview' and re.search(r'\b(listings?|jobs?|all|everything)\b', user_message.lower()):
        effective_job_id = 'ALL_JOBS' # Special marker for multi-job overview
        print("Detected multi-job overview request.")
    else:
        effective_job_id = session_job_id # Fallback to session context if specific job needed

    # --- Simple Fuzzy Job ID Matching (Keep as is) ---
    if not effective_job_id and not extracted_job_id and not extracted_email and not extracted_name and len(user_message.split()) <= 3:
        potential_id_part = user_message.upper()
        all_jobs_list = get_all_jobs() # Renamed local variable
        possible_matches = [j['job_id'] for j in all_jobs_list if potential_id_part in j['job_id']]
        if len(possible_matches) == 1:
             effective_job_id = possible_matches[0]
             intent = 'set_context'; extracted_job_id = effective_job_id
             print(f"Found single partial match: {effective_job_id}")
        elif len(possible_matches) > 1:
             intent = 'clarification'; print(f"Found multiple partial matches: {possible_matches}")

    print(f"Effective Job ID for processing: {effective_job_id}")

    # Update session context if a specific job ID was determined or used
    if extracted_job_id and extracted_job_id != session_job_id:
         session['hr_chat_job_context'] = extracted_job_id; print(f"Session context updated to Job ID: {extracted_job_id}")
    elif effective_job_id and effective_job_id != 'ALL_JOBS' and effective_job_id != session_job_id and intent != 'set_context':
        session['hr_chat_job_context'] = effective_job_id; print(f"Session context updated based on effective ID: {effective_job_id}")

    # --- Default Response ---
    response_text = "I'm sorry, I don't understand that request. Try asking for 'help' to see what I can do."

    # --- Handle Intents ---
    try:
        if intent == 'greeting': response_text = "Hello! How can I assist with your HR tasks today?"
        elif intent == 'get_help':
             response_text = """
Here's what I can help you with:
- **Overview:** Ask 'overview for [job_id]', 'status on this job', or 'status of listings'.
- **Top Candidates:** Ask 'top candidates for [job_id]' or 'who is best here?'.
- **Applicant Details:** Ask 'details about [email]' or 'tell me about [name]' (for the current job).
- **Set Focus:** Say 'focus on job [job_id]'.
You can also just type a potential Job ID fragment.
            """
        elif intent == 'set_context': # (Logic adjusted slightly during ID determination)
            if extracted_job_id:
                job_check = get_job(extracted_job_id)
                if job_check:
                    session['hr_chat_job_context'] = extracted_job_id # Ensure session is set
                    response_text = f"Okay, focusing on Job ID: **{extracted_job_id}**. Ask for 'overview', 'top candidates', etc."
                else: response_text = f"Sorry, I couldn't find Job ID '{extracted_job_id}'."
            else: response_text = "Which Job ID would you like me to focus on?"

        elif intent == 'get_overview':
            # --- Multi-Job Overview ---
            if effective_job_id == 'ALL_JOBS':
                open_jobs = get_all_jobs(status_filter='open') # Focus on open jobs for general status
                if not open_jobs: response_text = "There are currently no open job listings."
                else:
                    overview_lines = ["**Current Open Job Listing Status:**"]
                    for job_data in open_jobs: # Use different variable name
                        job_id_loop = job_data['job_id'] # Use different variable name
                        title = job_data.get('title', job_id_loop)
                        apps = get_applicants_for_job(job_id_loop, include_rejected=True) # Need all for stats
                        quality_assessment = assess_job_status_quality(job_id_loop) # Use new helper
                        overview_lines.append(f"- **{title} ({job_id_loop}):** {len(apps)} Applicants. *Assessment:* {quality_assessment}")
                    response_text = "\n".join(overview_lines)
            # --- Single Job Overview ---
            elif not effective_job_id:
                response_text = "Which Job ID do you need an overview for? Specify the ID or ask about the 'current job'."
            else:
                job_data = get_job(effective_job_id) # Use different variable name
                if not job_data: response_text = f"Sorry, I couldn't find Job ID '{effective_job_id}'."
                else:
                    quality_assessment = assess_job_status_quality(effective_job_id) # Use helper
                    apps = get_applicants_for_job(effective_job_id, include_rejected=True)
                    total = len(apps)
                    rated = [a for a in apps if a.get('rating') is not None]
                    avg_r_str = f"{sum(a['rating'] for a in rated if a.get('rating') is not None) / len(rated):.0f}/100" if rated else "N/A"
                    counts = {}
                    for app in apps: counts[app.get('status', 'pending')] = counts.get(app.get('status', 'pending'), 0) + 1
                    status_counts_str = ", ".join([f"{k.capitalize()}: {v}" for k, v in counts.items()]) if counts else "None"
                    response_text = (
                        f"**Overview for {job_data.get('title', effective_job_id)} ({effective_job_id})**\n"
                        f"- **Assessment:** {quality_assessment}\n" # Added assessment
                        f"- **Job Status:** {job_data.get('job_status', 'Unknown').capitalize()}\n"
                        f"- **Total Apps:** {total}\n"
                        f"- **Rated Apps:** {len(rated)} (Avg Rating: {avg_r_str})\n"
                        f"- **Status Counts:** {status_counts_str}"
                    )

        elif intent == 'get_ranking': # (Keep existing logic)
            if not effective_job_id or effective_job_id == 'ALL_JOBS':
                 response_text = "Which Job ID do you want the ranking for? Specify the ID or ask about the 'current job'."
            else:
                job_data = get_job(effective_job_id) # Use different variable name
                if not job_data: response_text = f"Sorry, I couldn't find Job ID '{effective_job_id}'."
                else:
                    print(f"Fetching top candidates for job: {effective_job_id}")
                    ranking_result_dict = run_ranking_direct(effective_job_id, n=3, include_rejected=False) # Correctly calls ranking
                    if 'error' in ranking_result_dict: response_text = f"Could not retrieve ranking for {effective_job_id}: {ranking_result_dict['error']}"
                    else:
                        ranked_list = ranking_result_dict.get('ranked_applicants', [])
                        if not ranked_list: response_text = f"No rated, non-rejected applicants found yet for Job ID {effective_job_id}."
                        else:
                            candidates_for_highlight = []
                            valid_ranked_tuples = [r for r in ranked_list if isinstance(r, (tuple, list)) and len(r) >= 3]
                            for app_tuple in valid_ranked_tuples:
                                applicant_id, name, rating = app_tuple[0], app_tuple[1], app_tuple[2]
                                summary_data = run_summarization_direct(applicant_id, effective_job_id)
                                candidates_for_highlight.append({"applicant_id": applicant_id, "name": name, "rating": rating, "summary": summary_data.get('summary', 'Summary unavailable.')})
                            highlights = {}
                            if candidates_for_highlight:
                                structured_jd_data = get_structured_jd(effective_job_id) or {} # Renamed
                                highlights = generate_ranking_highlights(candidates_for_highlight, structured_jd_data)
                            response_lines = [f"**Top {len(valid_ranked_tuples)} Rated Applicant(s) for {job_data.get('title', effective_job_id)} ({effective_job_id}):**"]
                            for i, candidate_info in enumerate(candidates_for_highlight):
                                app_id = candidate_info['applicant_id']; name = candidate_info['name']; rating = candidate_info['rating']
                                star_rating = to_5_star(rating); rating_display = f"{star_rating}/5.00 ({rating}/100)" if star_rating is not None else f"{rating}/100"
                                highlight_text = highlights.get(app_id, "Highlight unavailable.") if 'error' not in highlights else "Highlight error."
                                response_lines.append(f"{i+1}. **{name or app_id}** - Rating: {rating_display}"); response_lines.append(f"   - *Highlight:* {highlight_text}")
                            response_text = "\n".join(response_lines); response_text += "\n\nAsk 'details about [email/name]' for more."

        elif intent == 'get_applicant_details': # (Keep existing logic)
            applicant_identifier = extracted_email or extracted_name
            if not applicant_identifier: response_text = "Who is the applicant? Please provide name or email."
            elif not effective_job_id or effective_job_id == 'ALL_JOBS': response_text = f"Which Job ID should I check for applicant '{applicant_identifier}'?"
            else:
                print(f"Getting details for applicant identifier: '{applicant_identifier}' in job '{effective_job_id}'")
                apps = get_applicants_for_job(effective_job_id, include_rejected=True); applicant_data = None; matches = []
                if extracted_email: applicant_data = next((a for a in apps if a.get('applicant_id') == extracted_email), None)
                elif extracted_name:
                     matches = [a for a in apps if extracted_name.lower() in a.get('name', '').lower()]
                     if len(matches) == 1: applicant_data = matches[0]
                     elif len(matches) > 1:
                         match_list = [f"- {a.get('name')} ({a.get('applicant_id')})" for a in matches]
                         response_text = f"Found multiple applicants matching '{extracted_name}' for this job:\n" + "\n".join(match_list) + "\nPlease specify using the email address."
                if applicant_data:
                     found_email = applicant_data.get('applicant_id')
                     summary_result = run_summarization_direct(found_email, effective_job_id); summary_text = "AI summary could not be generated."
                     if isinstance(summary_result, dict) and 'error' in summary_result: summary_text = f"AI summary error: {summary_result.get('details', summary_result['error'])}"
                     elif isinstance(summary_result, dict) and 'summary' in summary_result: summary_text = summary_result['summary']
                     elif isinstance(summary_result, str) and summary_result.startswith("Error:"): summary_text = summary_result
                     rating_score = applicant_data.get('rating'); star_rating_str = f"({to_5_star(rating_score)}/5.00)" if rating_score is not None else ""
                     rating_str = f"{rating_score}/100 {star_rating_str}" if rating_score is not None else "Not Rated"; status_str = applicant_data.get('status', 'pending').capitalize()
                     response_text = (f"**Details for {applicant_data.get('name', found_email)} (Job: {effective_job_id})**\n- **Email:** {found_email}\n- **Status:** {status_str}\n- **AI Rating:** {rating_str}\n\n**AI Summary:**\n{summary_text}")
                elif len(matches) == 0: response_text = f"No applicant found matching '{applicant_identifier}' for Job ID '{effective_job_id}'."

        elif intent == 'get_report': # (Keep existing basic response)
             if not effective_job_id or effective_job_id == 'ALL_JOBS': response_text = "Please specify the Job ID for the report."
             else: response_text = f"Generating a basic report for Job ID {effective_job_id}...\n(This feature is under development)."

        elif intent == 'clarification':
             response_text = "Sorry, I need a bit more information. "
             if not effective_job_id and intent != 'set_context' and effective_job_id != 'ALL_JOBS': response_text += "Which Job ID? "
             if intent == 'get_applicant_details' and not (extracted_email or extracted_name): response_text += "Applicant name or email? "
             response_text += "Could you please rephrase?"

        elif intent == 'unknown': response_text = "I can't help with that. Try asking for 'help'."

    except Exception as e:
        print(f"Error during action execution for intent '{intent}': {e}"); traceback.print_exc()
        response_text = "Sorry, an internal error occurred."

    # --- Format and Return Response ---
    if not isinstance(response_text, str): response_text = "An unexpected error occurred."
    formatted_response = re.sub(r'\*\*(.*?)\*\*', r'<strong>\\1</strong>', response_text)
    formatted_response = Markup(formatted_response.replace('\n', '<br>'))
    return jsonify({"response": formatted_response})


# === Applicant Routes ===
@app.route('/jobs', methods=['GET'])
def list_jobs():
    jobs = get_all_jobs(status_filter='open')
    return render_template('jobs_list.html', jobs=jobs)

@app.route('/job/<job_id>', methods=['GET'])
def job_detail(job_id):
    job_data = get_job(job_id) # Renamed variable
    if not job_data: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('list_jobs'))
    if job_data.get('job_status') != 'open': flash(f"Job '{job_data.get('title', job_id)}' is no longer accepting applications.", "warning"); return redirect(url_for('list_jobs'))
    structured_jd_data = get_structured_jd(job_id) # Renamed variable
    return render_template('job_detail.html', job=job_data, structured_jd=structured_jd_data, rating_result=None, error=None)

@app.route('/check_suitability/<job_id>', methods=['POST'])
def check_suitability(job_id):
    print(f"Received suitability check request for Job ID: {job_id}")
    job_data = get_job(job_id); structured_jd_data = get_structured_jd(job_id) # Renamed variables
    if not job_data: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('list_jobs'))
    if job_data.get('job_status') != 'open': flash(f"Job '{job_data.get('title', job_id)}' is closed.", "warning"); return redirect(url_for('list_jobs'))
    if 'resume' not in request.files: flash("Missing 'resume' file for check.", "error"); return render_template('job_detail.html', job=job_data, structured_jd=structured_jd_data, error="No file provided.")
    resume_file = request.files['resume']
    if resume_file.filename == '': flash("No file selected for check.", "error"); return render_template('job_detail.html', job=job_data, structured_jd=structured_jd_data, error="No file selected.")

    save_path = None; result_dict = None; error_msg = None
    try:
        filename = secure_filename(resume_file.filename) # Secure filename
        file_extension = os.path.splitext(filename)[1].lower()
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        if file_extension not in allowed_extensions: error_msg = f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        else:
            if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
            unique_filename = str(uuid.uuid4()) + "_check" + file_extension
            save_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            resume_file.save(save_path); # print(f"Resume saved for check: {save_path}") # Less verbose
    except Exception as e: print(f"Error saving check file: {e}"); error_msg = "Could not save uploaded file."

    if not error_msg and save_path:
        try:
            print(f"Running suitability check: J:{job_id}, R:{save_path}")
            result_dict = run_suitability_check_direct(resume_file_path=save_path, job_id=job_id)
            # print(f"Suitability check finished. Result: {result_dict}") # Less verbose
            if isinstance(result_dict, dict) and 'error' in result_dict:
                 error_msg = f"Analysis Error: {result_dict.get('details', result_dict['error'])}"; result_dict = None
            elif not isinstance(result_dict, dict) or not all(k in result_dict for k in ['rating', 'summary', 'fits', 'lacks']):
                 error_msg = "Analysis returned incomplete format."; result_dict = None
        except Exception as e: print(f"Error during check workflow: {e}"); error_msg = f"Internal error during analysis: {e}"; result_dict = None
    # elif not error_msg: error_msg = "File processing failed before analysis." # Avoid double message

    if save_path and os.path.exists(save_path):
        try: os.remove(save_path); # print(f"Cleaned up check file: {save_path}") # Less verbose
        except Exception as e: print(f"Warn: Could not delete check file {save_path}: {e}")

    return render_template('job_detail.html', job=job_data, structured_jd=structured_jd_data, rating_result=result_dict, error=error_msg)

@app.route('/apply/<job_id>', methods=['POST'])
def apply_for_job(job_id):
    print(f"Received application submission for Job ID: {job_id}")
    job_data = get_job(job_id) # Renamed variable
    if not job_data: flash(f"Cannot apply: Job ID '{job_id}' not found.", "error"); return redirect(url_for('list_jobs'))
    if job_data.get('job_status') != 'open': flash(f"Sorry, job '{job_data.get('title', job_id)}' is no longer accepting applications.", "warning"); return redirect(url_for('job_detail', job_id=job_id))

    applicant_name = request.form.get('applicant_name'); applicant_email = request.form.get('applicant_email')
    if not applicant_name or not applicant_email: flash("Name and Email required.", "error"); return redirect(url_for('job_detail', job_id=job_id))
    if 'resume_apply' not in request.files: flash("Resume file required.", "error"); return redirect(url_for('job_detail', job_id=job_id))
    resume_file = request.files['resume_apply']
    if resume_file.filename == '': flash("No resume file selected.", "error"); return redirect(url_for('job_detail', job_id=job_id))

    save_path = None; filename_for_db = None
    try:
        filename = secure_filename(resume_file.filename) # Secure filename
        file_extension = os.path.splitext(filename)[1].lower()
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        if file_extension not in allowed_extensions: flash(f"Invalid file type.", "error"); return redirect(url_for('job_detail', job_id=job_id))
        if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
        # Ensure unique filename for application resumes
        unique_filename = f"{applicant_email.split('@')[0]}_{job_id}_{uuid.uuid4().hex[:6]}{file_extension}"
        save_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        resume_file.save(save_path); filename_for_db = unique_filename
        print(f"Application Resume saved to: {save_path}")
    except Exception as e: print(f"Error saving application file: {e}"); flash(f"Could not save application resume.", "error"); return redirect(url_for('job_detail', job_id=job_id))

    applicant_id = applicant_email # Use email as ID
    profile_saved = add_applicant(applicant_id, applicant_name, filename_for_db)
    if not profile_saved:
         flash("Database error saving profile (maybe email already exists with different resume?).", "error")
         if save_path and os.path.exists(save_path):
             try:
                 os.remove(save_path)
                 print(f"Cleaned up file due to DB profile error: {save_path}")
             except Exception as del_e:
                 print(f"Error cleaning file after DB profile error: {del_e}")
         return redirect(url_for('job_detail', job_id=job_id))

    application_recorded = add_application(applicant_id, job_id)
    if application_recorded is True:
         flash(f"Application for '{job_data.get('title', job_id)}' submitted!", "success")
    elif application_recorded is False:
         flash("You have already applied for this job.", "warning")
    else: # None means DB error during application insert
         flash("Issue recording your application (database error).", "error")
         # Clean up profile if application failed? Maybe not, profile might be useful.

    return redirect(url_for('job_detail', job_id=job_id))


# --- Resume Viewing Route ---
@app.route('/resume/<filename>')
# @login_required
def view_resume(filename):
    """Serves a saved resume file from the uploads directory."""
    # Basic security check
    if not filename or '..' in filename or filename.startswith(('/', '\\')):
        flash("Invalid file request.", "error")
        return redirect(request.referrer or url_for('hr_dashboard')), 400
    # Secure the filename just in case, although DB value should be safe
    filename = secure_filename(filename)
    try:
        # print(f"Attempting to serve file: {filename} from {UPLOAD_FOLDER}") # Less verbose
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)
    except FileNotFoundError: print(f"File not found: {filename}"); flash("Resume file not found.", "error"); return redirect(request.referrer or url_for('hr_dashboard')), 404
    except Exception as e: print(f"Error serving file {filename}: {e}"); flash("Error accessing resume file.", "error"); return redirect(request.referrer or url_for('hr_dashboard')), 500


# === HR / Company Routes ===
@app.route('/hr', methods=['GET'])
# @login_required
def hr_dashboard(): return render_template('hr_dashboard.html')

@app.route('/hr/jobs', methods=['GET'])
# @login_required
def hr_list_jobs():
    jobs = get_all_jobs()
    return render_template('hr_jobs_list.html', jobs=jobs)

@app.route('/hr/job/create', methods=['GET'])
# @login_required
def hr_create_job_form(): return render_template('hr_create_job.html')

# --- UPDATED: Handle Job Creation with Analysis Preferences ---
@app.route('/hr/job/create', methods=['POST'])
# @login_required
def hr_create_job():
    job_id = request.form.get('job_id', '').strip().upper()
    title = request.form.get('title', '').strip()
    desc_text = request.form.get('description_text', '').strip()
    jd_file = request.files.get('jd_file') # Use .get for optional file

    # --- Get Analysis Preferences ---
    analysis_pref = request.form.get('analysis_preference', 'manual') # 'manual', 'scheduled', 'batch'
    analysis_schedule_time = request.form.get('analysis_schedule_time') # e.g., "23:00"
    analysis_batch_size_str = request.form.get('analysis_batch_size', '5')
    try: analysis_batch_size = int(analysis_batch_size_str); analysis_batch_size = max(1, analysis_batch_size)
    except (ValueError, TypeError): analysis_batch_size = 5 # Default on error

    # Validate schedule time format if 'scheduled' is chosen
    if analysis_pref == 'scheduled':
        if not analysis_schedule_time or not re.match(r'^\d{1,2}:\d{2}$', analysis_schedule_time):
             flash("Invalid schedule time format. Use HH:MM (e.g., 02:00 or 23:30).", "error")
             return redirect(url_for('hr_create_job_form'))
        # Optional: Pad single digit hour
        parts = analysis_schedule_time.split(':')
        if len(parts[0]) == 1: analysis_schedule_time = f"0{parts[0]}:{parts[1]}"

    # --- Input Validation (Job ID) ---
    if not job_id:
        flash("Job ID is required.", "error")
        return redirect(url_for('hr_create_job_form'))

    job_description_source = None
    extracted_text_for_structuring = None
    temp_file_path = None

    # --- File Processing / Text Area Fallback ---
    if jd_file and jd_file.filename != '':
        try:
            filename = secure_filename(jd_file.filename)
            file_extension = os.path.splitext(filename)[1].lower()
            allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
            if file_extension not in allowed_extensions:
                flash(f"Invalid JD file type. Allowed: {', '.join(allowed_extensions)}", "error")
                return redirect(url_for('hr_create_job_form'))
            if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER) # Ensure upload folder exists
            temp_filename = f"temp_jd_{uuid.uuid4()}{file_extension}"
            temp_file_path = os.path.join(UPLOAD_FOLDER, temp_filename)
            jd_file.save(temp_file_path)

            extracted_text_for_structuring = extract_text_from_file(temp_file_path)
            if "Error:" in extracted_text_for_structuring or "Warning:" in extracted_text_for_structuring:
                flash(f"Could not extract text from uploaded JD file: {extracted_text_for_structuring}", "error")
                if temp_file_path and os.path.exists(temp_file_path): os.remove(temp_file_path) # Clean up temp file
                return redirect(url_for('hr_create_job_form'))
            job_description_source = extracted_text_for_structuring
            print("Using text extracted from uploaded JD file.")
        except Exception as e:
            print(f"Error processing uploaded JD file: {e}"); traceback.print_exc()
            flash(f"Error processing uploaded file: {e}", "error")
            if temp_file_path and os.path.exists(temp_file_path): os.remove(temp_file_path)
            return redirect(url_for('hr_create_job_form'))
        finally:
             if temp_file_path and os.path.exists(temp_file_path):
                 try: os.remove(temp_file_path);
                 except Exception as del_e: print(f"Error deleting temp JD file: {del_e}")
    elif desc_text:
        extracted_text_for_structuring = desc_text
        job_description_source = desc_text
        print("Using text provided in the description field.")
    else:
        flash("Either upload a JD file or provide a description in the text area.", "error")
        return redirect(url_for('hr_create_job_form'))

    # --- Structure the description ---
    structured_jd = structure_job_description(extracted_text_for_structuring)
    error_in_struct = False
    if isinstance(structured_jd, dict) and 'error' in structured_jd:
        error_detail = structured_jd.get('details', structured_jd['error'])
        flash(f"AI Warning structuring JD: {error_detail}", "warning")
        structured_jd = None; error_in_struct = True
    elif not isinstance(structured_jd, dict):
        flash("AI structuring returned unexpected result.", "warning")
        structured_jd = None; error_in_struct = True
    else:
        # Derive title ONLY if it wasn't provided explicitly
        if not title and structured_jd.get('job_title'):
            title = structured_jd['job_title']
            print(f"Using job title derived from structured JD: {title}")

    # Title fallback if still empty
    if not title: title = f"Job {job_id}" # Use Job ID if title still missing

    # --- Save to Database (pass preferences) ---
    if add_job(job_id=job_id, title=title, description_text=job_description_source,
               structured_jd_dict=structured_jd, analysis_preference=analysis_pref,
               analysis_schedule=analysis_schedule_time, analysis_batch_size=analysis_batch_size):
        flash(f"Job '{job_id}' created/updated successfully!{' (Warning: AI structuring failed)' if error_in_struct else ''}", "success")
        # --- Update Scheduler for this specific job ---
        update_scheduler_for_job(job_id, analysis_pref, analysis_schedule_time, analysis_batch_size)
        # --- End Scheduler Update ---
        return redirect(url_for('hr_list_jobs'))
    else:
        flash("Failed to save job (Database error or Job ID conflict?).", "error")
        return redirect(url_for('hr_create_job_form'))


@app.route('/hr/job/<job_id>/applicants', methods=['GET'])
# @login_required
@app.route('/hr/job/<job_id>/applicants', methods=['GET'])
# @login_required
def hr_view_applicants(job_id):
    job_data = get_job(job_id)
    if not job_data: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))

    show_rejected = request.args.get('show_rejected', 'false').lower() == 'true'
    applicants = get_applicants_for_job(job_id, include_rejected=show_rejected)
    if applicants is None: applicants = []

    # Calculate progress stats more comprehensively
    all_apps = get_applicants_for_job(job_id, include_rejected=True) # Need all for stats
    all_apps_count = len(all_apps)
    all_rated_count = len([a for a in all_apps if a.get('rating') is not None])
    shortlisted_count = len([a for a in all_apps if a.get('status') == 'shortlisted'])
    # Add counts for other statuses if needed for progress bar/display
    selected_count = len([a for a in all_apps if a.get('status') == 'selected'])
    hired_count = len([a for a in all_apps if a.get('status') == 'hired'])
    pending_count = len([a for a in all_apps if a.get('status') == 'pending']) # Explicitly count pending

    progress = {
        "total": all_apps_count,
        "rated_percent": int((all_rated_count / all_apps_count * 100)) if all_apps_count > 0 else 0,
        "shortlisted_count": shortlisted_count,
        "selected_count": selected_count, # Pass these for potential future use
        "hired_count": hired_count,       # Pass these for potential future use
        "pending_count": pending_count,   # Pass these for potential future use
        "rated_count": all_rated_count    # Pass rated count
    }

    # Fetch structured JD - it's already part of get_job result now
    structured_jd_data = None
    if job_data.get('structured_jd'):
        try:
            structured_jd_data = json.loads(job_data['structured_jd'])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse structured_jd JSON from DB for job {job_id}")
            # Pass raw string or error indicator? Let's pass None.
            # structured_jd_data = {"error": "Invalid JSON in DB"}
            structured_jd_data = None

    # Enhance applicant data for modal trigger (add more fields if needed later)
    applicants_for_template = []
    for app in applicants:
         app_dict = dict(app) # Convert Row to dict
         # Add rating for data attribute (handle None)
         app_dict['rating_value'] = app_dict.get('rating', '')
         # Add status for data attribute
         app_dict['status_value'] = app_dict.get('status', 'pending')
         # Format date for display/data attribute if needed
         app_dict['application_date_formatted'] = app_dict.get('application_date', '')[:10] if app_dict.get('application_date') else 'N/A'
         applicants_for_template.append(app_dict)


    return render_template('hr_job_applicants.html',
                           job_id=job_id,
                           job_title=job_data.get('title', job_id),
                           job_description=job_data.get('description_text'), # Pass full description
                           structured_jd=structured_jd_data, # Pass parsed structured JD
                           job_date_added=job_data.get('date_added','N/A')[:10], # Example: Pass dates
                           # Add closing date if available in DB/job_data
                           # job_closing_date=job_data.get('closing_date', 'N/A'),
                           applicants=applicants_for_template, # Use enhanced list
                           show_rejected=show_rejected,
                           job_status=job_data.get('job_status'),
                           progress=progress) # Pass progress stats

# --- NEW Route for Applicant Modal Details ---
@app.route('/hr/details/<path:applicant_id>/<job_id>', methods=['GET'])
# @login_required
def hr_get_applicant_details_for_modal(applicant_id, job_id):
    """Fetches detailed info for the applicant modal via AJAX."""
    try: applicant_id = unquote(applicant_id)
    except Exception as e: return jsonify({"error": "Invalid applicant identifier."}), 400

    if not applicant_id or not job_id: return jsonify({"error": "Missing identifiers."}), 400

    # 1. Get basic application data (status, rating etc.)
    all_apps = get_applicants_for_job(job_id, include_rejected=True)
    app_data = next((dict(a) for a in all_apps if a.get('applicant_id') == applicant_id), None)

    if not app_data: return jsonify({"error": "Application not found."}), 404

    # 2. Get structured resume (if available) for more details like experience/skills
    #   (You might need more specific DB queries if performance becomes an issue)
    structured_resume = get_structured_resume(applicant_id)
    experience_years = None
    skills_list = []
    education_list = []
    if structured_resume and isinstance(structured_resume, dict):
        # Example: Try to extract years of experience - this needs robust parsing logic
        exp_list = structured_resume.get('experience', [])
        if exp_list: # Very basic sum - needs proper duration parsing!
            total_exp = 0
            for exp in exp_list:
                 # Placeholder: This requires parsing "duration" strings like "2 years", "6 months"
                 # For now, just count number of roles or assume 1 year per role listed
                 total_exp += 1 # Simple count for demo
            experience_years = total_exp # Assign calculated years

        skills_list = structured_resume.get('skills', [])
        education_list = structured_resume.get('education', [])


    # 3. Get AI Summary
    summary_result = run_summarization_direct(applicant_id, job_id)
    ai_summary = "AI Summary not available."
    if isinstance(summary_result, dict) and 'summary' in summary_result:
        ai_summary = summary_result['summary']
    elif isinstance(summary_result, dict) and 'error' in summary_result:
        ai_summary = f"Error generating summary: {summary_result.get('details', summary_result['error'])}"

    # 4. Combine data for JSON response
    details = {
        "name": app_data.get('name', 'N/A'),
        "applicant_id": applicant_id, # same as email
        "email": applicant_id,
        "status": app_data.get('status', 'pending').capitalize(),
        "application_date": app_data.get('application_date', '')[:10] if app_data.get('application_date') else 'N/A',
        "rating": app_data.get('rating'), # Send raw rating
        "resume_file_path": app_data.get('resume_file_path'),
        "ai_summary": ai_summary,
        "experience_years": experience_years, # Add calculated experience
        "skills": skills_list, # Add extracted skills
        "education": education_list, # Add extracted education
        # Add other fields as needed (e.g., phone from structured_resume if available)
        "phone": structured_resume.get('contact_info', {}).get('phone') if structured_resume else None,
    }

    return jsonify(details)

@app.route('/hr/rate_applicant/<path:applicant_id>/<job_id>', methods=['POST']) # Use path for ID
# @login_required
def hr_rate_applicant(applicant_id, job_id):
    try: applicant_id = unquote(applicant_id)
    except Exception as e: print(f"Error decoding applicant_id '{applicant_id}': {e}"); flash("Invalid applicant identifier.", "error"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    job_data = get_job(job_id); # Renamed
    if not job_data: flash(f"Job '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))
    if job_data.get('job_status') != 'open': flash(f"Job '{job_data.get('title', job_id)}' is not open.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    apps_check = get_applicants_for_job(job_id, include_rejected=True)
    applicant_exists = next((app for app in apps_check if app.get('applicant_id') == applicant_id), None)
    if not applicant_exists: flash(f"Applicant {applicant_id} not found for job {job_id}.", "error"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    resume_filename = get_resume_path(applicant_id)
    if not resume_filename: flash(f"No resume path for {applicant_id}.", "error"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    resume_full_path = os.path.join(UPLOAD_FOLDER, secure_filename(resume_filename))
    if not os.path.exists(resume_full_path): flash(f"Resume file '{resume_filename}' missing.", "error"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    rating_result = {}
    try:
        flash(f"Initiating AI rating for {applicant_id}...", "info")
        print(f"Running suitability check (HR Trigger): J:{job_id}, R:{resume_full_path}")
        rating_result = run_suitability_check_direct(resume_file_path=resume_full_path, job_id=job_id)
        # print(f"Rating check result: {rating_result}") # Less verbose
        if isinstance(rating_result, dict) and 'error' not in rating_result and all(k in rating_result for k in ['rating', 'summary', 'fits', 'lacks']):
            if update_application_rating(applicant_id, job_id, rating_result): flash(f"Successfully rated {applicant_id}.", "success")
            else: flash(f"Failed to update database for {applicant_id}.", "error")
        elif isinstance(rating_result, dict) and 'error' in rating_result: flash(f"AI Error for {applicant_id}: {rating_result.get('details', rating_result['error'])}", "error")
        else: flash(f"Unexpected AI result for {applicant_id}.", "error"); print(f"Unexpected AI result: {rating_result}")
    except Exception as e: print(f"Error during HR rating workflow {applicant_id}: {e}"); flash(f"Internal error during rating: {e}", "error"); traceback.print_exc()

    redirect_url = url_for('hr_view_applicants', job_id=job_id, show_rejected=request.args.get('show_rejected', 'false'))
    return redirect(redirect_url)

@app.route('/hr/rate_all_unrated/<job_id>', methods=['POST'])
# @login_required
def hr_rate_all_unrated(job_id):
    """Rates all applicants for a job whose rating is currently NULL."""
    job_data = get_job(job_id) # Renamed
    if not job_data:
        return jsonify({"success": False, "message": f"Job ID '{job_id}' not found."}), 404
    if job_data.get('job_status') != 'open':
        return jsonify({"success": False, "message": f"Job '{job_data.get('title', job_id)}' is not open."}), 400

    print(f"Processing request to rate all unrated for {job_id}.")
    all_applicants = get_applicants_for_job(job_id, include_rejected=True)
    unrated_applicants = [app for app in all_applicants if app.get('rating') is None]

    if not unrated_applicants:
        return jsonify({"success": True, "message": "No applicants need rating.", "rated_count": 0, "error_count": 0, "skipped_count": 0})

    print(f"Found {len(unrated_applicants)} unrated applicants for job {job_id}. Starting rating process...")
    rated_count = 0; error_count = 0; skipped_count = 0
    for applicant in unrated_applicants:
        applicant_id = applicant.get('applicant_id')
        if not applicant_id: skipped_count += 1; print(f"Warning: Skipping applicant with missing ID in job {job_id}."); continue

        # print(f"Rating applicant {applicant_id}...") # Less verbose
        resume_filename = get_resume_path(applicant_id)
        if not resume_filename: skipped_count += 1; print(f"Skipping {applicant_id} (job {job_id}): No resume path."); continue

        resume_full_path = os.path.join(UPLOAD_FOLDER, secure_filename(resume_filename))
        if not os.path.exists(resume_full_path): skipped_count += 1; print(f"Skipping {applicant_id} (job {job_id}): Resume file missing ({resume_filename})."); continue

        try:
             rating_result = run_suitability_check_direct(resume_file_path=resume_full_path, job_id=job_id)
             if isinstance(rating_result, dict) and 'error' not in rating_result and all(k in rating_result for k in ['rating', 'summary', 'fits', 'lacks']):
                 if update_application_rating(applicant_id, job_id, rating_result):
                      rated_count += 1;
                 else: error_count += 1; print(f"ERROR updating DB for {applicant_id} (job {job_id})")
             else:
                 error_count += 1
                 error_detail = "Incomplete AI response" if isinstance(rating_result, dict) and 'error' not in rating_result else rating_result.get('details', rating_result.get('error', 'Unknown AI error'))
                 print(f"ERROR AI rating {applicant_id} (job {job_id}): {error_detail}")
        except Exception as e: error_count += 1; print(f"ERROR exception rating {applicant_id} for {job_id}: {e}"); traceback.print_exc()

    result_message = f"Rating process finished for {job_id}. Rated: {rated_count}, Errors: {error_count}, Skipped: {skipped_count}."
    print(result_message)
    # Flash is not useful for AJAX request, return in JSON
    return jsonify({
        "success": True,
        "message": result_message,
        "rated_count": rated_count,
        "error_count": error_count,
        "skipped_count": skipped_count
    })


@app.route('/hr/summary/<path:applicant_id>/<job_id>', methods=['GET']) # Use path for ID
# @login_required
def hr_get_summary(applicant_id, job_id):
    try: applicant_id = unquote(applicant_id)
    except Exception as e: print(f"Error decoding applicant_id '{applicant_id}': {e}"); return jsonify({"error": "Invalid applicant identifier."}), 400
    # print(f"\n--- Request received at /hr/summary/{applicant_id}/{job_id} ---") # Less verbose
    if not applicant_id or not job_id: return jsonify({"error": "Applicant ID and Job ID are required."}), 400

    # Check application exists
    apps_check = get_applicants_for_job(job_id, include_rejected=True)
    if not any(app.get('applicant_id') == applicant_id for app in apps_check): return jsonify({"error": f"Applicant {applicant_id} not found for job {job_id}."}), 404

    # Check job exists
    job_data = get_job(job_id); # Renamed
    if not job_data: return jsonify({"error": f"Job ID '{job_id}' not found."}), 404

    summary_result = {}
    try:
        summary_result = run_summarization_direct(applicant_id, job_id)
        if not isinstance(summary_result, dict): print(f"Warning: Summarization non-dict: {summary_result}"); return jsonify({"error": "Unexpected result format."}), 500
    except Exception as e: print(f"Error during summary workflow: {e}"); traceback.print_exc(); return jsonify({"error": f"Internal error: {e}"}), 500

    if 'error' in summary_result:
        error_detail = summary_result.get('details', summary_result['error'])
        print(f"Summarization error A:'{applicant_id}': {error_detail}")
        status_code = 404 if "not found" in str(error_detail).lower() else 500
        return jsonify({"error": error_detail}), status_code
    elif 'summary' in summary_result:
        # print(f"Summarization SUCCESS A:'{applicant_id}'.") # Less verbose
        return jsonify({"summary": summary_result.get("summary", "Summary unavailable.")})
    else: print(f"Summarization result missing keys A:'{applicant_id}'"); return jsonify({"error": "Failed to generate summary."}), 500


@app.route('/hr/job/<job_id>/ranked', methods=['GET'])
# @login_required
def hr_view_ranked_applicants(job_id):
    job_data = get_job(job_id) # Renamed
    if not job_data: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))
    try: top_n = int(request.args.get('n', 10)); top_n = max(1, top_n)
    except ValueError: top_n = 10
    ranked_result = run_ranking_direct(job_id, top_n, include_rejected=False) # Use False for default ranked view
    applicants = []; error_msg = None
    if isinstance(ranked_result, dict) and 'error' in ranked_result: error_msg = ranked_result['error']
    elif isinstance(ranked_result, dict) and 'ranked_applicants' in ranked_result:
        applicants_raw = ranked_result['ranked_applicants']
        if isinstance(applicants_raw, list):
            applicants = [{"applicant_id": r[0], "name": r[1], "rating": r[2]} for r in applicants_raw if isinstance(r, (tuple, list)) and len(r) >= 3 and r[0] is not None and r[2] is not None]
        else: error_msg = "Invalid 'ranked_applicants' format."
    else: error_msg = "Unexpected result format from ranking."
    if error_msg: flash(f"Could not retrieve ranked: {error_msg}", "warning")
    return render_template('hr_job_ranked_applicants.html', job_id=job_id, job_title=job_data.get('title', job_id), applicants=applicants, top_n=top_n, is_filtered_view=False)


@app.route('/hr/job/<job_id>/filter_relevant', methods=['POST'])
# @login_required
def hr_filter_relevant_applicants(job_id):
    job_data = get_job(job_id) # Renamed
    if not job_data: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))
    if job_data.get('job_status') != 'open': flash(f"Job '{job_data.get('title', job_id)}' is not open.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))
    try: m = int(request.form.get('top_m', 5)); m = max(1, m)
    except ValueError: m = 5; flash("Invalid number for 'Top M', defaulting to 5.", "warning")
    print(f"Filter & Rank request: Job {job_id}, Top M = {m}")
    flash(f"Processing request to find top {m} applicants for {job_id}. Rating unrated applicants first...", "info")

    # Get only non-rejected applicants to consider for rating/ranking
    applicants_to_consider = get_applicants_for_job(job_id, include_rejected=False)
    if not applicants_to_consider: flash(f"No non-rejected applicants found for job {job_id}.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    rated_count = 0; error_count = 0; skipped_count = 0; already_rated_count = 0
    # --- Rating Loop (only rate those in the non-rejected list that are unrated) ---
    for applicant in applicants_to_consider:
        if applicant.get('rating') is None:
            applicant_id = applicant.get('applicant_id')
            if not applicant_id: skipped_count += 1; print(f"Skipping rating for applicant with missing ID in job {job_id}."); continue

            resume_filename = get_resume_path(applicant_id)
            if not resume_filename: skipped_count+=1; print(f"Skipping rating for {applicant_id} (job {job_id}): No resume path."); continue

            resume_full_path = os.path.join(UPLOAD_FOLDER, secure_filename(resume_filename))
            if not os.path.exists(resume_full_path): skipped_count+=1; print(f"Skipping rating for {applicant_id} (job {job_id}): Resume file missing."); continue

            print(f"Rating applicant {applicant_id} for job {job_id} (Filter & Rank)...")
            try:
                 rating_result = run_suitability_check_direct(resume_file_path=resume_full_path, job_id=job_id)
                 if isinstance(rating_result, dict) and 'error' not in rating_result and all(k in rating_result for k in ['rating', 'summary', 'fits', 'lacks']):
                     if update_application_rating(applicant_id, job_id, rating_result): rated_count += 1
                     else: error_count += 1; print(f"ERROR updating DB for {applicant_id} (job {job_id})")
                 else:
                      error_count += 1
                      error_detail = "Incomplete AI response" if isinstance(rating_result, dict) and 'error' not in rating_result else rating_result.get('details', rating_result.get('error', 'Unknown AI error'))
                      print(f"ERROR AI rating {applicant_id} (job {job_id}): {error_detail}")
            except Exception as e: error_count += 1; print(f"ERROR exception rating {applicant_id} for {job_id}: {e}"); traceback.print_exc()
        else:
            already_rated_count += 1 # Count those already rated in the considered list

    print(f"Filter&Rank Rating stats: Rated now={rated_count}, Already rated={already_rated_count}, Errors={error_count}, Skipped={skipped_count}")
    flash_msgs = []
    if rated_count > 0: flash_msgs.append(f"AI analysis completed for {rated_count} applicant(s).")
    if error_count > 0: flash(f"Encountered errors during rating for {error_count} applicant(s).", "danger")
    if skipped_count > 0: flash(f"Skipped rating for {skipped_count} applicant(s) due to missing info.", "warning")
    if flash_msgs: flash(" ".join(flash_msgs), "info")

    # --- Ranking after rating ---
    print(f"Fetching top {m} ranked non-rejected applicants...")
    ranked_result = run_ranking_direct(job_id, m, include_rejected=False) # Always exclude rejected here
    top_m_applicants = []; error_msg_ranking = None
    if isinstance(ranked_result, dict) and 'error' in ranked_result: error_msg_ranking = ranked_result['error']
    elif isinstance(ranked_result, dict) and 'ranked_applicants' in ranked_result:
        applicants_raw = ranked_result['ranked_applicants']
        if isinstance(applicants_raw, list): top_m_applicants = [{"applicant_id": r[0], "name": r[1], "rating": r[2]} for r in applicants_raw if isinstance(r, (tuple, list)) and len(r) >= 3 and r[0] is not None and r[2] is not None]
        else: error_msg_ranking = "Invalid list format."
    else: error_msg_ranking = "Unexpected ranking result."
    if error_msg_ranking: flash(f"Error retrieving final ranked list: {error_msg_ranking}", "danger")

    return render_template('hr_job_ranked_applicants.html', job_id=job_id, job_title=job_data.get('title', job_id), applicants=top_m_applicants, top_n=m, is_filtered_view=True)

@app.route('/hr/update_status/<path:applicant_id>/<job_id>', methods=['POST']) # Use path for ID
# @login_required
def update_status(applicant_id, job_id):
    try: applicant_id = unquote(applicant_id)
    except Exception as e: print(f"Error decoding applicant_id '{applicant_id}': {e}"); return jsonify({"success": False, "error": "Invalid applicant identifier."}), 400
    if not request.is_json: return jsonify({"success": False, "error": "Request must be JSON."}), 415
    new_status = request.json.get('status'); # print(f"Status update request: A:{applicant_id}, J:{job_id}, New Status: {new_status}") # Less verbose
    allowed_statuses = ['pending', 'shortlisted', 'rejected', 'selected', 'hired']
    if not new_status or new_status not in allowed_statuses: return jsonify({"success": False, "error": f"Invalid status '{new_status}'."}), 400

    if update_application_status(applicant_id, job_id, new_status):
        # print(f"Status updated successfully for {applicant_id} to {new_status}") # Less verbose
        return jsonify({"success": True, "new_status": new_status})
    else:
        print(f"Failed to update status for {applicant_id}")
        # Check if application actually exists before claiming DB error
        apps_check = get_applicants_for_job(job_id, include_rejected=True)
        applicant_exists = any(app.get('applicant_id') == applicant_id for app in apps_check)
        error_msg = "Applicant/application not found." if not applicant_exists else "Failed to update status (DB error)."
        status_code = 404 if not applicant_exists else 500
        return jsonify({"success": False, "error": error_msg}), status_code

@app.route('/hr/finalize_job/<job_id>', methods=['POST'])
# @login_required
def finalize_job(job_id):
    print(f"Request to finalize job: {job_id}")
    job_data = get_job(job_id) # Renamed
    if not job_data: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))
    if job_data.get('job_status') != 'open': flash(f"Job '{job_data.get('title', job_id)}' is already {job_data.get('job_status', 'not open')}.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    shortlisted_applicants = get_applications_by_status(job_id, 'shortlisted')
    if not shortlisted_applicants: flash("No applicants shortlisted. Please shortlist candidates first.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    print(f"Found {len(shortlisted_applicants)} shortlisted applicants.")
    success_emails = 0; failed_emails = 0; failed_status_updates = 0

    for applicant in shortlisted_applicants:
        applicant_id = applicant.get('applicant_id'); applicant_name = applicant.get('name') or 'Candidate'
        if not applicant_id: failed_status_updates += 1; print("Warning: Skipping shortlisted applicant with missing ID."); continue

        if update_application_status(applicant_id, job_id, 'selected'):
            if mail: # Check if mail is configured
                try:
                    company_name = os.environ.get("COMPANY_NAME", "Our Company")
                    hr_contact_email = os.environ.get("HR_CONTACT_EMAIL", app.config['MAIL_DEFAULT_SENDER']) # Use default sender if specific contact missing
                    job_title_email = job_data.get('title', 'the position') # Use job_data
                    subject = f"Update on your application for {job_title_email} at {company_name}"
                    # --- DEFAULT EMAIL BODY - CONSIDER MAKING CONFIGURABLE ---
                    body = f"""Dear {applicant_name},

Congratulations! We were impressed with your application for the {job_title_email} position at {company_name} and would like to invite you to the next stage of our selection process.

Our HR team will be in touch shortly with details regarding the next steps [Consider adding specifics here manually or via future config: e.g., interview scheduling link, documents required].

Please let us know if you have any immediate questions by replying to this email.

We look forward to speaking with you soon.

Best regards,
The Hiring Team
{company_name}
"""
                    # --- END DEFAULT EMAIL BODY ---
                    msg = Message(subject=subject, recipients=[applicant_id], body=body.strip()) # Ensure recipients is a list
                    mail.send(msg)
                    print(f"Sent selection email to {applicant_id}"); success_emails += 1
                except Exception as e: print(f"ERROR sending email to {applicant_id}: {e}"); failed_emails += 1; traceback.print_exc()
            else: print(f"Skipping email to {applicant_id} (Mail not configured).")
        else: print(f"ERROR: Failed to update status to 'selected' for {applicant_id}"); failed_status_updates += 1

    if not update_job_status(job_id, 'closed'): flash(f"Failed to update job status for {job_id} to 'closed'.", "error")
    else:
        print(f"Job {job_id} status updated to 'closed'.")
        # Remove any scheduled jobs for this job_id as it's closed
        update_scheduler_for_job(job_id, 'manual', None, None) # Setting preference to manual effectively removes schedule

    flash(f"Finalized selection for job '{job_data.get('title', job_id)}'. Processed {len(shortlisted_applicants)} shortlisted.", "success")
    if success_emails > 0: flash(f"Successfully sent selection emails to {success_emails} applicant(s).", "info")
    if failed_emails > 0: flash(f"Failed to send emails to {failed_emails} applicant(s). Check logs/config.", "danger")
    if failed_status_updates > 0: flash(f"Failed to update status for {failed_status_updates} applicant(s). Check logs.", "danger")
    if not mail and success_emails == 0 and len(shortlisted_applicants) > 0: flash("Email sending is disabled (mail server not configured). No notifications sent.", "warning")

    return redirect(url_for('hr_view_applicants', job_id=job_id))

# --- NEW Route: Re-open Job ---
@app.route('/hr/job/<job_id>/reopen', methods=['POST'])
# @login_required
def reopen_job(job_id):
    """Sets a job's status back to 'open'."""
    print(f"Request received to re-open job: {job_id}")
    job_data = get_job(job_id) # Fetch current job details
    if not job_data:
        flash(f"Job ID '{job_id}' not found.", "error")
        return redirect(url_for('hr_list_jobs'))

    # Only allow re-opening if it's 'closed' or 'filled'
    if job_data.get('job_status') == 'open':
        flash(f"Job '{job_data.get('title', job_id)}' is already open.", "info")
    elif job_data.get('job_status') in ['closed', 'filled']:
        if update_job_status(job_id, 'open'):
            flash(f"Job '{job_data.get('title', job_id)}' has been re-opened.", "success")
             # Re-evaluate scheduler for this job using stored preferences
            update_scheduler_for_job(
                job_data['job_id'],
                job_data['analysis_preference'],
                job_data['analysis_schedule'],
                job_data['analysis_batch_size']
            )
        else:
            flash(f"Failed to re-open job '{job_data.get('title', job_id)}'. Database error.", "error")
    else:
         flash(f"Cannot re-open job with status '{job_data.get('job_status')}'.", "warning")

    # Redirect back to the applicants page for that job
    return redirect(url_for('hr_view_applicants', job_id=job_id))

# --- Run the Flask App ---
if __name__ == '__main__':
    # Initialize DB first
    init_db()

    # Configure and start Scheduler *after* app initialization but *before* run
    try:
        scheduler.init_app(app)
        scheduler.start(paused=False) # Start immediately
        print("[Scheduler] Initialized and started.")

        # Schedule the periodic check for batch jobs (e.g., every 30 minutes)
        scheduler.add_job(id='batch_analysis_check', func=check_jobs_for_batch_analysis, trigger='interval', minutes=30)
        print("[Scheduler] Added batch check job.")

        # Load scheduled jobs from DB on startup
        # Needs to run *after* scheduler.start() potentially? Let's try here.
        # Or maybe load them within the app context manually before starting run?
        # For simplicity, let's assume loading here works or run load_scheduled_jobs_from_db() manually after start if needed.
        # It's safer to load them after start within the app context.
        # Let's add a simple startup hook or do it just before app.run
        with app.app_context():
             load_scheduled_jobs_from_db()


        # Register shutdown hook
        atexit.register(lambda: scheduler.shutdown())
        print("[Scheduler] Registered shutdown hook.")

    except Exception as scheduler_e:
         print(f"!!! SCHEDULER INITIALIZATION FAILED: {scheduler_e} !!!")
         traceback.print_exc()
         # Consider exiting if scheduler is critical?
         # import sys; sys.exit(1)

    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    # Disable Flask Debugger when using APScheduler reloader if issues arise
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    use_reloader = debug # Match reloader to debug status
    if use_reloader and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
         print("WARNING: Flask Debugger + APScheduler might cause duplicate jobs. Consider running with FLASK_DEBUG=0 if issues occur.")

    if not os.path.exists(UPLOAD_FOLDER):
        try: os.makedirs(UPLOAD_FOLDER); print(f"Created upload folder: {UPLOAD_FOLDER}")
        except OSError as e: print(f"ERROR creating upload folder {UPLOAD_FOLDER}: {e}"); import sys; sys.exit(1)
    print(f"Starting Flask app on http://{host}:{port} (Debug: {debug}, Reloader: {use_reloader})")
    # Ensure Mail config check happens before run
    if not mail: print("Reminder: Email sending is disabled.")
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)