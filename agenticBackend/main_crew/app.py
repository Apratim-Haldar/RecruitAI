# app.py (Corrected + Enhanced Chatbot Logic)
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
    generate_ranking_highlights # Import new function
)
from database_utils import (
    get_all_jobs, get_job, get_structured_jd, add_job,
    add_applicant, add_application, get_applicants_for_job,
    update_application_rating, get_resume_path, get_ranked_applicants,
    update_application_status, get_applications_by_status, update_job_status
)
from file_utils import UPLOAD_FOLDER, extract_text_from_file

# --- App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

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
    print("WARNING: Mail server details not fully configured. Email sending disabled.")


# --- Helper Functions & Filters ---
@app.template_filter('nl2br')
def nl2br(s):
    return Markup(s.replace('\n', '<br>\n')) if s else s

@app.template_filter('to_5_star')
def to_5_star_filter(score):
    return to_5_star(score)

# --- Qualitative Status Assessment ---
def assess_job_status_quality(job_id):
    """Provides a qualitative assessment of a job listing's progress."""
    try:
        apps = get_applicants_for_job(job_id, include_rejected=True)
        if not apps:
            return "It's early days - no applications received yet."

        total = len(apps)
        rated = [a for a in apps if a.get('rating') is not None]
        shortlisted = [a for a in apps if a.get('status') == 'shortlisted']
        rejected = [a for a in apps if a.get('status') == 'rejected']
        pending = total - len(shortlisted) - len(rejected) # Approx pending/other

        avg_rating = (sum(a['rating'] for a in rated) / len(rated)) if rated else 0

        if avg_rating >= 70 and len(shortlisted) > 0:
            return f"Looking good! Average rating is strong ({avg_rating:.0f}/100) and {len(shortlisted)} candidate(s) are shortlisted."
        elif avg_rating >= 50:
            if len(shortlisted) > 0:
                return f"Making decent progress. Average rating is {avg_rating:.0f}/100 with {len(shortlisted)} shortlisted. Still {pending} pending review."
            else:
                return f"Getting applications ({total} total), average rating is okay ({avg_rating:.0f}/100), but no one shortlisted yet. Keep reviewing!"
        elif total > 5 and avg_rating < 40:
             if len(rejected) > total / 2:
                  return f"Seems challenging. Receiving applications ({total}), but the average rating is low ({avg_rating:.0f}/100) and many ({len(rejected)}) have been marked unsuitable."
             else:
                  return f"Progress is slow. Average rating is quite low ({avg_rating:.0f}/100). Consider reviewing the job description or sourcing channels."
        else: # Low avg rating, few applications, or mostly pending
             return f"It's still developing. {total} application(s) received, average rating is {avg_rating:.0f}/100. {pending} are pending review."

    except Exception as e:
        print(f"Error assessing job status quality for {job_id}: {e}")
        return "Sorry, I couldn't assess the status quality due to an error."


# === Common Routes ===
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# === Chatbot API Endpoint (Smarter Version) ===

@app.route('/hr/chat', methods=['POST'])
# @login_required # Add authentication later
def hr_chat_api():
    """Handles requests from the HR chatbot UI using LLM for NLU."""
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"response": "Invalid request format."}), 400

    user_message = data.get('message', '')
    page_context_job_id = data.get('page_context_job_id') # Get from frontend
    session_job_id = session.get('hr_chat_job_context')

    print(f"Chat API received message: '{user_message}', Page Context: {page_context_job_id}, Session Context: {session_job_id}")

    # 1. Understand Intent and Entities using LLM (Pass combined context info)
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
    # Priority: Explicit ID > Page Context (if intent implies 'this job') > Session Context > None
    effective_job_id = None
    use_page_context = intent in ['get_overview', 'get_ranking', 'get_applicant_details', 'get_report'] and \
                       not extracted_job_id and \
                       re.search(r'\b(this|current|here|latest)\b', user_message.lower()) is not None

    if extracted_job_id:
        effective_job_id = extracted_job_id
    elif use_page_context and page_context_job_id:
        effective_job_id = page_context_job_id
        print(f"Using Page Context Job ID based on implicit reference: {effective_job_id}")
    else:
        effective_job_id = session_job_id # Fallback to session

    # --- Simple Fuzzy Job ID Matching (Example) ---
    # If no effective_job_id yet, and user provided *something* that might be part of an ID
    if not effective_job_id and not extracted_job_id and not extracted_email and not extracted_name and len(user_message.split()) <= 3:
        potential_id_part = user_message.upper() # Assume it might be a partial ID
        print(f"Attempting basic partial match for: {potential_id_part}")
        all_jobs = get_all_jobs() # Fetch all job IDs
        possible_matches = [j['job_id'] for j in all_jobs if potential_id_part in j['job_id']]
        if len(possible_matches) == 1:
             effective_job_id = possible_matches[0]
             print(f"Found single partial match: {effective_job_id}")
             intent = 'set_context' # Treat as setting context
             extracted_job_id = effective_job_id # Set it as if extracted
        elif len(possible_matches) > 1:
             print(f"Found multiple partial matches: {possible_matches}")
             intent = 'clarification' # Ambiguous

    print(f"Effective Job ID for processing: {effective_job_id}")

    # Update session if a new explicit job ID was determined
    if extracted_job_id and extracted_job_id != session_job_id:
         session['hr_chat_job_context'] = extracted_job_id
         print(f"Session context updated to Job ID: {extracted_job_id}")
    elif effective_job_id and effective_job_id != session_job_id and intent != 'set_context': # Update session if page context was used
        session['hr_chat_job_context'] = effective_job_id
        print(f"Session context updated based on effective ID: {effective_job_id}")

    # --- Default Response ---
    response_text = "I'm sorry, I don't understand that request. Try asking for 'help' to see what I can do."

    # --- Handle Intents ---
    try:
        if intent == 'greeting':
            response_text = "Hello! How can I assist with your HR tasks today?"

        elif intent == 'get_help':
             response_text = """
Here's what I can help you with:
- **Overview:** Ask 'overview for [job_id]' or 'status on this job' (if you're viewing it).
- **Top Candidates:** Ask 'top candidates for [job_id]' or 'who is best here?'.
- **Applicant Details:** Ask 'details about [email]' or 'tell me about [name]' (for the current job).
- **Set Focus:** Say 'focus on job [job_id]' to talk about a specific listing.
You can also just type a potential Job ID fragment like 'IOT 2' and I'll try to find it.
            """

        elif intent == 'set_context':
            # This is now handled slightly differently due to fuzzy matching potentially setting the intent
            if extracted_job_id: # Check if an ID was successfully determined (explicitly or via fuzzy)
                job_check = get_job(extracted_job_id)
                if job_check:
                    session['hr_chat_job_context'] = extracted_job_id # Ensure session is set
                    response_text = f"Okay, focusing on Job ID: **{extracted_job_id}**. Ask for 'overview', 'top candidates', etc."
                else:
                    # This case should be less likely if fuzzy match worked, but handle explicit wrong IDs
                    response_text = f"Sorry, I couldn't find Job ID '{extracted_job_id}'. Please provide a valid ID."
            else:
                # This happens if the intent was 'set_context' but no ID was extracted (should be rare)
                 response_text = "Which Job ID would you like me to focus on? Please mention the ID."


        elif intent == 'get_overview':
            if not effective_job_id:
                response_text = "Which Job ID do you need an overview for? Please specify the ID or ask about the 'current job' if you're viewing one."
            else:
                job = get_job(effective_job_id)
                if not job:
                    response_text = f"Sorry, I couldn't find Job ID '{effective_job_id}'."
                else:
                    # Get qualitative assessment
                    quality_assessment = assess_job_status_quality(effective_job_id)
                    # Get quantitative data
                    apps = get_applicants_for_job(effective_job_id, include_rejected=True)
                    total = len(apps)
                    rated = [a for a in apps if a.get('rating') is not None]
                    avg_r_str = f"{sum(a['rating'] for a in rated) / len(rated):.0f}/100" if rated else "N/A"
                    counts = {}
                    for app in apps: counts[app.get('status', 'pending')] = counts.get(app.get('status', 'pending'), 0) + 1
                    status_counts_str = ", ".join([f"{k.capitalize()}: {v}" for k, v in counts.items()]) if counts else "None"
                    response_text = (
                        f"**Overview for {job.get('title', effective_job_id)} ({effective_job_id})**\n"
                        f"- **Assessment:** {quality_assessment}\n"
                        f"- **Job Status:** {job.get('job_status', 'Unknown').capitalize()}\n"
                        f"- **Total Apps:** {total}\n"
                        f"- **Rated Apps:** {len(rated)} (Avg Rating: {avg_r_str})\n"
                        f"- **Status Counts:** {status_counts_str}"
                    )

        elif intent == 'get_ranking':
            if not effective_job_id:
                 response_text = "Which Job ID do you want the ranking for? Specify the ID or ask about the 'current job'."
            else:
                job = get_job(effective_job_id)
                if not job:
                    response_text = f"Sorry, I couldn't find Job ID '{effective_job_id}'."
                else:
                    print(f"Fetching top candidates for job: {effective_job_id}")
                    # Fetch top 3 non-rejected candidates
                    ranking_result_dict = run_ranking_direct(effective_job_id, n=3, include_rejected=False)

                    if 'error' in ranking_result_dict:
                        response_text = f"Could not retrieve ranking for {effective_job_id}: {ranking_result_dict['error']}"
                    else:
                        ranked_list = ranking_result_dict.get('ranked_applicants', [])
                        if not ranked_list:
                            response_text = f"No rated, non-rejected applicants found yet for Job ID {effective_job_id}. You might need to rate some candidates."
                        else:
                            # Prepare data for highlight generation
                            candidates_for_highlight = []
                            valid_ranked_tuples = [r for r in ranked_list if isinstance(r, (tuple, list)) and len(r) >= 3]

                            for app_tuple in valid_ranked_tuples:
                                applicant_id, name, rating = app_tuple[0], app_tuple[1], app_tuple[2]
                                # Fetch summary for context (could be slow - optimize later if needed)
                                summary_data = run_summarization_direct(applicant_id, effective_job_id)
                                candidates_for_highlight.append({
                                    "applicant_id": applicant_id,
                                    "name": name,
                                    "rating": rating,
                                    "summary": summary_data.get('summary', 'Summary unavailable.') # Use summary for highlight context
                                })

                            # Get highlights from LLM
                            highlights = {}
                            if candidates_for_highlight:
                                structured_jd = get_structured_jd(effective_job_id) or {}
                                highlights = generate_ranking_highlights(candidates_for_highlight, structured_jd)

                            # Format the response
                            response_lines = [f"**Top {len(valid_ranked_tuples)} Rated Applicant(s) for {job.get('title', effective_job_id)} ({effective_job_id}):**"]
                            for i, candidate_info in enumerate(candidates_for_highlight):
                                app_id = candidate_info['applicant_id']
                                name = candidate_info['name']
                                rating = candidate_info['rating']
                                star_rating = to_5_star(rating)
                                rating_display = f"{star_rating}/5.00 ({rating}/100)" if star_rating is not None else f"{rating}/100"
                                # Get the generated highlight, default if error or missing
                                highlight_text = highlights.get(app_id, "Highlight unavailable.") if 'error' not in highlights else "Highlight error."

                                response_lines.append(f"{i+1}. **{name or app_id}** - Rating: {rating_display}")
                                response_lines.append(f"   - *Highlight:* {highlight_text}") # Add highlight

                            response_text = "\n".join(response_lines)
                            response_text += "\n\nAsk 'details about [email/name]' for more."

        elif intent == 'get_applicant_details':
            applicant_identifier = extracted_email or extracted_name # Prioritize email if both somehow extracted
            if not applicant_identifier:
                 response_text = "Who is the applicant you want details for? Please provide their name or email address."
            elif not effective_job_id:
                 response_text = f"Which Job ID should I check for applicant '{applicant_identifier}'? Please specify the ID or ask about the 'current job'."
            else:
                 print(f"Getting details for applicant identifier: '{applicant_identifier}' in job '{effective_job_id}'")
                 apps = get_applicants_for_job(effective_job_id, include_rejected=True)
                 applicant_data = None

                 if extracted_email: # Exact match on email
                     applicant_data = next((a for a in apps if a.get('applicant_id') == extracted_email), None)
                 elif extracted_name: # Name matching (case-insensitive substring)
                     matches = [
                         a for a in apps
                         if extracted_name.lower() in a.get('name', '').lower()
                     ]
                     if len(matches) == 1:
                         applicant_data = matches[0]
                         print(f"Found single match for name '{extracted_name}': {applicant_data.get('applicant_id')}")
                     elif len(matches) > 1:
                         print(f"Found multiple matches for name '{extracted_name}'")
                         match_list = [f"- {a.get('name')} ({a.get('applicant_id')})" for a in matches]
                         response_text = f"Found multiple applicants matching '{extracted_name}' for this job:\n" + "\n".join(match_list) + "\nPlease specify using the email address."
                     # If len == 0, applicant_data remains None

                 # --- Process if a unique applicant was found ---
                 if applicant_data:
                     found_email = applicant_data.get('applicant_id')
                     # Fetch summary and format
                     summary_result = run_summarization_direct(found_email, effective_job_id)
                     summary_text = "AI summary could not be generated."
                     if isinstance(summary_result, dict) and 'error' in summary_result: summary_text = f"AI summary error: {summary_result.get('details', summary_result['error'])}"
                     elif isinstance(summary_result, dict) and 'summary' in summary_result: summary_text = summary_result['summary']
                     elif isinstance(summary_result, str) and summary_result.startswith("Error:"): summary_text = summary_result

                     rating_score = applicant_data.get('rating')
                     star_rating_str = f"({to_5_star(rating_score)}/5.00)" if rating_score is not None else ""
                     rating_str = f"{rating_score}/100 {star_rating_str}" if rating_score is not None else "Not Rated"
                     status_str = applicant_data.get('status', 'pending').capitalize()
                     response_text = (
                         f"**Details for {applicant_data.get('name', found_email)} (Job: {effective_job_id})**\n"
                         f"- **Email:** {found_email}\n" # Include email for clarity
                         f"- **Status:** {status_str}\n"
                         f"- **AI Rating:** {rating_str}\n\n"
                         f"**AI Summary:**\n{summary_text}"
                     )
                 elif len(matches) == 0: # Only set response if no matches found *and* not handled above
                     response_text = f"No applicant found matching '{applicant_identifier}' for Job ID '{effective_job_id}'."
                 # If multiple matches, response_text was already set

        elif intent == 'get_report':
             if not effective_job_id: response_text = "Please specify the Job ID for the report."
             else:
                 if extracted_job_id and extracted_job_id != session_job_id: session['hr_chat_job_context'] = extracted_job_id; print(f"Chat context updated to Job ID: {extracted_job_id}")
                 response_text = f"Generating a basic report for Job ID {effective_job_id}...\n(This feature is under development)."

        elif intent == 'clarification':
             # Handle cases where NLU decided essential info was missing
             response_text = "Sorry, I need a bit more information. "
             if not effective_job_id and intent != 'set_context':
                 response_text += "Which Job ID are you asking about? "
             if intent == 'get_applicant_details' and not (extracted_email or extracted_name):
                  response_text += "Please provide the applicant's name or email address. "
             response_text += "Could you please rephrase your request?"

        elif intent == 'unknown':
             response_text = "I'm sorry, I can't help with that specific request. Try asking for 'help' to see my capabilities."


    except Exception as e:
        print(f"Error during action execution for intent '{intent}': {e}")
        traceback.print_exc()
        response_text = "Sorry, an internal error occurred while processing your request."

    # --- Format and Return Response ---
    if not isinstance(response_text, str):
        response_text = "An unexpected error occurred generating the response."

    formatted_response = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_text)
    formatted_response = Markup(formatted_response.replace('\n', '<br>'))
    return jsonify({"response": formatted_response})


# === Applicant Routes ===
# ... (Keep list_jobs, job_detail, check_suitability, apply_for_job as is) ...
@app.route('/jobs', methods=['GET'])
def list_jobs():
    """Applicant view: Lists all available jobs (only 'open' jobs)."""
    jobs = get_all_jobs(status_filter='open')
    return render_template('jobs_list.html', jobs=jobs)

@app.route('/job/<job_id>', methods=['GET'])
def job_detail(job_id):
    """Applicant view: Shows details for a specific job."""
    job = get_job(job_id)
    if not job:
        flash(f"Job ID '{job_id}' not found.", "error")
        return redirect(url_for('list_jobs'))
    if job.get('job_status') != 'open': # Use .get for safety
         flash(f"Job '{job.get('title', job_id)}' is no longer accepting applications.", "warning")
         return redirect(url_for('list_jobs'))

    structured_jd = get_structured_jd(job_id)
    return render_template('job_detail.html', job=job, structured_jd=structured_jd, rating_result=None, error=None)


@app.route('/check_suitability/<job_id>', methods=['POST'])
def check_suitability(job_id):
    """Handles resume upload for suitability check (doesn't submit application)."""
    print(f"Received suitability check request for Job ID: {job_id}")
    job = get_job(job_id)
    if not job: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('list_jobs'))
    if job.get('job_status') != 'open': flash(f"Job '{job.get('title', job_id)}' is closed.", "warning"); return redirect(url_for('list_jobs'))

    if 'resume' not in request.files: flash("Missing 'resume' file for check.", "error"); return redirect(url_for('job_detail', job_id=job_id))
    resume_file = request.files['resume']
    if resume_file.filename == '': flash("No file selected for check.", "error"); return redirect(url_for('job_detail', job_id=job_id))

    save_path = None; result_dict = None; error_msg = None
    try:
        file_extension = os.path.splitext(resume_file.filename)[1].lower()
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        if file_extension not in allowed_extensions:
            error_msg = f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        else:
            if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
            unique_filename = str(uuid.uuid4()) + "_check" + file_extension
            save_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            resume_file.save(save_path); print(f"Resume saved for check: {save_path}")
    except Exception as e:
        print(f"Error saving check file: {e}"); traceback.print_exc(); error_msg = "Could not save uploaded file."

    if not error_msg and save_path:
        try:
            print(f"Running suitability check: J:{job_id}, R:{save_path}")
            result_dict = run_suitability_check_direct(resume_file_path=save_path, job_id=job_id)
            print(f"Suitability check finished. Result: {result_dict}")
            if isinstance(result_dict, dict) and 'error' in result_dict:
                 error_detail = result_dict.get('details', result_dict['error'])
                 error_msg = f"Analysis Error: {error_detail}"
                 result_dict = None
            elif not isinstance(result_dict, dict) or not all(k in result_dict for k in ['rating', 'summary', 'fits', 'lacks']):
                 error_msg = "Analysis returned incomplete or unexpected result format."
                 result_dict = None
        except Exception as e:
            print(f"Error during check workflow: {e}"); traceback.print_exc()
            error_msg = f"Internal error during analysis: {e}"; result_dict = None
    elif not error_msg:
        error_msg = "File processing failed before analysis."

    if save_path and os.path.exists(save_path):
        try: os.remove(save_path); print(f"Cleaned up check file: {save_path}")
        except Exception as e: print(f"Warn: Could not delete check file {save_path}: {e}")

    structured_jd = get_structured_jd(job_id)
    return render_template('job_detail.html', job=job, structured_jd=structured_jd,
                           rating_result=result_dict,
                           error=error_msg)


@app.route('/apply/<job_id>', methods=['POST'])
def apply_for_job(job_id):
    """Handles the actual application submission."""
    print(f"Received application submission for Job ID: {job_id}")

    job = get_job(job_id)
    if not job: flash(f"Cannot apply: Job ID '{job_id}' not found.", "error"); return redirect(url_for('list_jobs'))
    if job.get('job_status') != 'open':
        flash(f"Sorry, job '{job.get('title', job_id)}' is no longer accepting applications.", "warning")
        return redirect(url_for('job_detail', job_id=job_id))

    applicant_name = request.form.get('applicant_name')
    applicant_email = request.form.get('applicant_email')

    if not applicant_name or not applicant_email: flash("Name and Email are required to apply.", "error"); return redirect(url_for('job_detail', job_id=job_id))

    if 'resume_apply' not in request.files: flash("Resume file is required to apply.", "error"); return redirect(url_for('job_detail', job_id=job_id))
    resume_file = request.files['resume_apply']
    if resume_file.filename == '': flash("No resume file selected for application.", "error"); return redirect(url_for('job_detail', job_id=job_id))

    save_path = None; filename_for_db = None
    try:
        file_extension = os.path.splitext(resume_file.filename)[1].lower()
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
        if file_extension not in allowed_extensions: flash(f"Invalid file type. Allowed: {', '.join(allowed_extensions)}", "error"); return redirect(url_for('job_detail', job_id=job_id))

        if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
        unique_filename = str(uuid.uuid4()) + file_extension
        save_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        resume_file.save(save_path)
        filename_for_db = unique_filename
        print(f"Application Resume saved to: {save_path}")
    except Exception as e: print(f"Error saving application file: {e}"); traceback.print_exc(); flash(f"Could not save application resume: {e}", "error"); return redirect(url_for('job_detail', job_id=job_id))

    applicant_id = applicant_email
    profile_saved_or_updated = add_applicant(applicant_id, applicant_name, filename_for_db)

    if not profile_saved_or_updated:
         flash("Database error saving applicant profile. Please try again or contact support.", "error")
         if save_path and os.path.exists(save_path):
            try: os.remove(save_path); print(f"Cleaned up file due to DB error: {save_path}")
            except Exception as del_e: print(f"Error cleaning file after DB error: {del_e}")
         return redirect(url_for('job_detail', job_id=job_id))

    application_recorded = add_application(applicant_id, job_id)
    if application_recorded is True:
         flash(f"Application for '{job.get('title', job_id)}' submitted successfully! HR will review it.", "success")
    elif application_recorded is False:
         flash("You have already applied for this job.", "warning")
    else:
         flash("An unexpected issue occurred recording your application.", "error")

    return redirect(url_for('job_detail', job_id=job_id))


# --- Resume Viewing Route ---
# ... (Keep view_resume as is) ...
@app.route('/resume/<filename>')
# @login_required # Add authentication!
def view_resume(filename):
    """Serves a saved resume file from the uploads directory."""
    if not filename or '..' in filename or filename.startswith(('/', '\\')):
        flash("Invalid file request.", "error")
        return redirect(request.referrer or url_for('hr_dashboard')), 400
    try:
        print(f"Attempting to serve file: {filename} from {UPLOAD_FOLDER}")
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)
    except FileNotFoundError:
        print(f"File not found: {filename}"); flash("Resume file not found.", "error")
        return redirect(request.referrer or url_for('hr_dashboard')), 404
    except Exception as e:
        print(f"Error serving file {filename}: {e}"); traceback.print_exc(); flash("Error accessing resume file.", "error")
        return redirect(request.referrer or url_for('hr_dashboard')), 500


# === HR / Company Routes ===
# ... (Keep hr_dashboard, hr_list_jobs, hr_create_job_form, hr_create_job as is) ...
@app.route('/hr', methods=['GET'])
# @login_required
def hr_dashboard(): return render_template('hr_dashboard.html')

@app.route('/hr/jobs', methods=['GET'])
# @login_required
def hr_list_jobs():
    """Lists all jobs for HR, regardless of status."""
    jobs = get_all_jobs() # Get all jobs for HR view
    return render_template('hr_jobs_list.html', jobs=jobs)

@app.route('/hr/job/create', methods=['GET'])
# @login_required
def hr_create_job_form(): return render_template('hr_create_job.html')

@app.route('/hr/job/create', methods=['POST'])
# @login_required
def hr_create_job():
    job_id = request.form.get('job_id', '').strip().upper() # Normalize ID
    title = request.form.get('title', '').strip()
    desc = request.form.get('description_text', '').strip()
    if not job_id or not title or not desc: flash("All fields (Job ID, Title, Description) are required.", "error"); return redirect(url_for('hr_create_job_form'))

    print(f"Structuring JD for new job: {job_id}"); struct_jd = structure_job_description(desc)
    error_in_struct = False
    if isinstance(struct_jd, dict) and 'error' in struct_jd:
        error_detail = struct_jd.get('details', struct_jd['error'])
        flash(f"AI Warning structuring JD: {error_detail}", "warning");
        struct_jd = None; error_in_struct = True
    elif not isinstance(struct_jd, dict):
        flash("AI structuring returned unexpected result.", "warning"); struct_jd = None; error_in_struct = True
    else: print("JD structured successfully.")

    if add_job(job_id, title, desc, struct_jd):
        flash(f"Job '{job_id}' created/updated successfully!{' (Warning: AI structuring failed)' if error_in_struct else ''}", "success")
        return redirect(url_for('hr_list_jobs'))
    else: flash("Failed to save job (Database error or issue with Job ID?).", "error"); return redirect(url_for('hr_create_job_form'))


# ... (Keep hr_view_applicants as is) ...
@app.route('/hr/job/<job_id>/applicants', methods=['GET'])
# @login_required
def hr_view_applicants(job_id):
    """HR view: Shows applicants for a job, status included, optionally hides rejected."""
    job = get_job(job_id)
    if not job: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))

    show_rejected = request.args.get('show_rejected', 'false').lower() == 'true'
    applicants = get_applicants_for_job(job_id, include_rejected=show_rejected)
    print(f"Found {len(applicants)} applicant(s) for job {job_id} (rejected hidden: {not show_rejected})")

    if applicants is None: applicants = []

    return render_template('hr_job_applicants.html',
                           job_id=job_id,
                           job_title=job.get('title', job_id),
                           applicants=applicants,
                           show_rejected=show_rejected,
                           job_status=job.get('job_status'))

# ... (Keep hr_rate_applicant as is) ...
@app.route('/hr/rate_applicant/<path:applicant_id>/<job_id>', methods=['POST']) # Use path for ID
# @login_required
def hr_rate_applicant(applicant_id, job_id):
    """Triggers the AI suitability check and updates the rating in the DB."""
    try:
        applicant_id = unquote(applicant_id)
    except Exception as e:
         print(f"Error decoding applicant_id '{applicant_id}': {e}")
         flash("Invalid applicant identifier.", "error")
         return redirect(url_for('hr_view_applicants', job_id=job_id))

    print(f"HR triggered rating for Applicant: {applicant_id}, Job: {job_id}")

    job = get_job(job_id)
    if not job: flash(f"Job '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))

    apps_check = get_applicants_for_job(job_id, include_rejected=True)
    applicant_exists = next((app for app in apps_check if app.get('applicant_id') == applicant_id), None)

    if not applicant_exists:
         flash(f"Applicant {applicant_id} has not applied for job {job_id}.", "error")
         return redirect(url_for('hr_view_applicants', job_id=job_id))

    resume_filename = get_resume_path(applicant_id)
    if not resume_filename: flash(f"Could not find resume path for applicant {applicant_id}.", "error"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    resume_full_path = os.path.join(UPLOAD_FOLDER, resume_filename)
    if not os.path.exists(resume_full_path): flash(f"Resume file '{resume_filename}' not found in uploads folder.", "error"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    rating_result = {}
    try:
        flash(f"Initiating AI rating for {applicant_id}...", "info")
        print(f"Running suitability check (HR Trigger): J:{job_id}, R:{resume_full_path}")
        rating_result = run_suitability_check_direct(resume_file_path=resume_full_path, job_id=job_id)
        print(f"Rating check result: {rating_result}")

        if isinstance(rating_result, dict) and 'error' not in rating_result:
            if all(k in rating_result for k in ['rating', 'summary', 'fits', 'lacks']):
                if update_application_rating(applicant_id, job_id, rating_result):
                    flash(f"Successfully rated applicant {applicant_id}.", "success")
                else:
                    flash(f"Rating generated, but failed to update database for {applicant_id}.", "error")
            else:
                 flash(f"AI analysis returned incomplete data for {applicant_id}. Rating not saved.", "error")
                 print(f"Incomplete data received: {rating_result}")
        elif isinstance(rating_result, dict) and 'error' in rating_result:
             error_detail = rating_result.get('details', rating_result['error'])
             flash(f"AI Analysis Error for {applicant_id}: {error_detail}", "error")
        else:
            flash(f"Unexpected result from AI analysis for {applicant_id}. Rating not saved.", "error")
            print(f"Unexpected AI result: {rating_result}")

    except Exception as e:
        print(f"Error during HR rating workflow execution for {applicant_id}: {e}"); traceback.print_exc()
        flash(f"An internal error occurred during rating process: {e}", "error")

    redirect_url = url_for('hr_view_applicants', job_id=job_id, show_rejected=request.args.get('show_rejected', 'false'))
    return redirect(redirect_url)


# ... (Keep hr_get_summary as is) ...
@app.route('/hr/summary/<path:applicant_id>/<job_id>', methods=['GET']) # Use path for ID
# @login_required
def hr_get_summary(applicant_id, job_id):
    """Provides an AI-generated summary for an applicant in relation to a job (AJAX)."""
    try:
        applicant_id = unquote(applicant_id)
    except Exception as e:
         print(f"Error decoding applicant_id '{applicant_id}': {e}")
         return jsonify({"error": "Invalid applicant identifier."}), 400

    print(f"\n--- Request received at /hr/summary Route ---")
    print(f"Decoded applicant_id: '{applicant_id}'")
    print(f"Raw job_id: '{job_id}'")

    if not applicant_id or not job_id:
        return jsonify({"error": "Applicant ID and Job ID are required."}), 400

    apps_check = get_applicants_for_job(job_id, include_rejected=True)
    applicant_exists = next((app for app in apps_check if app.get('applicant_id') == applicant_id), None)
    if not applicant_exists:
         return jsonify({"error": f"Applicant {applicant_id} not found for job {job_id}."}), 404

    job = get_job(job_id)
    if not job: return jsonify({"error": f"Job ID '{job_id}' not found."}), 404

    summary_result = {}
    try:
        summary_result = run_summarization_direct(applicant_id, job_id)
        if not isinstance(summary_result, dict):
             print(f"Warning: Summarization workflow returned non-dict: {summary_result}")
             return jsonify({"error": "Unexpected result format from summarizer."}), 500

    except Exception as e:
        print(f"Error during summary workflow execution for A:'{applicant_id}', J:'{job_id}': {e}"); traceback.print_exc()
        return jsonify({"error": f"Internal error during summary generation: {e}"}), 500

    if 'error' in summary_result:
        error_detail = summary_result.get('details', summary_result['error'])
        print(f"Summarization workflow error for A:'{applicant_id}': {error_detail}")
        status_code = 404 if "not found" in str(error_detail).lower() else 500
        return jsonify({"error": error_detail}), status_code
    elif 'summary' in summary_result:
        print(f"Summarization workflow SUCCESS for A:'{applicant_id}'.")
        return jsonify({"summary": summary_result.get("summary", "Summary not available.")})
    else:
        print(f"Summarization workflow result missing 'summary' and 'error' keys for A:'{applicant_id}'")
        return jsonify({"error": "Failed to generate summary, unknown reason."}), 500

# ... (Keep hr_view_ranked_applicants as is) ...
@app.route('/hr/job/<job_id>/ranked', methods=['GET'])
# @login_required
def hr_view_ranked_applicants(job_id):
    """HR view: Shows Top N pre-rated, non-rejected applicants for a specific job."""
    job = get_job(job_id)
    if not job: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))

    try: top_n = int(request.args.get('n', 10)); top_n = max(1, top_n) # Default 10, min 1
    except ValueError: top_n = 10

    ranked_result = run_ranking_direct(job_id, top_n, include_rejected=False)
    applicants = []
    error_msg = None

    if isinstance(ranked_result, dict) and 'error' in ranked_result:
        error_msg = ranked_result['error']; print(f"Error getting ranked applicants for {job_id}: {error_msg}")
    elif isinstance(ranked_result, dict) and 'ranked_applicants' in ranked_result:
        applicants_raw = ranked_result['ranked_applicants']
        if isinstance(applicants_raw, list):
            applicants = [
                {"applicant_id": r[0], "name": r[1], "rating": r[2]}
                for r in applicants_raw if isinstance(r, (tuple, list)) and len(r) >= 3 and r[0] is not None and r[2] is not None
            ]
            print(f"Found {len(applicants)} valid ranked, non-rejected applicant(s) for job {job_id}")
        else:
             error_msg = "Ranking function returned invalid 'ranked_applicants' format (expected list)."
             print(f"Invalid ranked_applicants format: {applicants_raw}")
    else:
        error_msg = "Unexpected result format from ranking function."; print(f"Error getting ranked applicants for {job_id}: {ranked_result}")

    if error_msg: flash(f"Could not retrieve ranked applicants: {error_msg}", "warning")

    return render_template('hr_job_ranked_applicants.html',
                           job_id=job_id,
                           job_title=job.get('title', job_id),
                           applicants=applicants,
                           top_n=top_n,
                           is_filtered_view=False) # Flag this as the pre-rated view


# ... (Keep hr_filter_relevant_applicants as is) ...
@app.route('/hr/job/<job_id>/filter_relevant', methods=['POST'])
# @login_required
def hr_filter_relevant_applicants(job_id):
    """HR action: Rates all unrated (pending/shortlisted), then shows top M ranked."""
    job = get_job(job_id)
    if not job: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))
    if job.get('job_status') != 'open': flash(f"Job '{job.get('title', job_id)}' is not open, cannot filter.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    try: m = int(request.form.get('top_m', 5)); m = max(1, m)
    except ValueError: m = 5; flash("Invalid number for 'Top M', defaulting to 5.", "warning")

    print(f"Filtering request: Job {job_id}, Top M = {m}")
    flash(f"Processing request to find top {m} applicants for {job_id}. This may take a moment if many applicants need rating...", "info")

    applicants_to_consider = get_applicants_for_job(job_id, include_rejected=False)
    if not applicants_to_consider: flash(f"No non-rejected applicants found for job {job_id}.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    print(f"Found {len(applicants_to_consider)} total non-rejected applicants. Checking ratings...")
    rated_count = 0; error_count = 0; skipped_count = 0; already_rated_count = 0

    # --- Rate unrated applicants (Consider moving to background task later) ---
    for applicant in applicants_to_consider:
        if applicant.get('rating') is None:
            applicant_id = applicant.get('applicant_id')
            if not applicant_id:
                 print("Warning: Skipping applicant with missing ID in list.")
                 skipped_count += 1
                 continue

            print(f"Rating applicant {applicant_id} for job {job_id}...")
            resume_filename = get_resume_path(applicant_id)
            if not resume_filename: print(f"Skipping {applicant_id}: No resume path."); skipped_count+=1; continue

            resume_full_path = os.path.join(UPLOAD_FOLDER, resume_filename)
            if not os.path.exists(resume_full_path): print(f"Skipping {applicant_id}: Resume file missing ({resume_filename})."); skipped_count+=1; continue

            try:
                 rating_result = run_suitability_check_direct(resume_file_path=resume_full_path, job_id=job_id)
                 if isinstance(rating_result, dict) and 'error' not in rating_result and all(k in rating_result for k in ['rating', 'summary', 'fits', 'lacks']):
                     if update_application_rating(applicant_id, job_id, rating_result):
                          rated_count += 1; print(f"Rated {applicant_id}")
                     else: error_count += 1; print(f"ERROR updating DB for {applicant_id}")
                 else:
                     error_count += 1;
                     error_detail = "Incomplete AI response" if isinstance(rating_result, dict) and 'error' not in rating_result else rating_result.get('details', rating_result.get('error', 'Unknown AI error'))
                     print(f"ERROR AI rating {applicant_id}: {error_detail}")
            except Exception as e: error_count += 1; print(f"ERROR exception rating {applicant_id}: {e}"); traceback.print_exc()
        else:
            already_rated_count += 1
    # --- End Rating Loop ---

    print(f"Rating stats: Rated now={rated_count}, Already rated={already_rated_count}, Errors={error_count}, Skipped={skipped_count}")
    flash_msgs = []
    if rated_count > 0: flash_msgs.append(f"AI analysis completed for {rated_count} applicant(s).")
    if already_rated_count > 0 and rated_count == 0 and error_count == 0 and skipped_count == 0:
         flash_msgs.append(f"All {already_rated_count} non-rejected applicants were already rated.")
    if error_count > 0: flash(f"Encountered errors during rating for {error_count} applicant(s). Check server logs.", "danger")
    if skipped_count > 0: flash(f"Skipped rating for {skipped_count} applicant(s) due to missing resume info or other issues.", "warning")
    if flash_msgs: flash(" ".join(flash_msgs), "info")

    print(f"Fetching top {m} ranked non-rejected applicants...")
    ranked_result = run_ranking_direct(job_id, m, include_rejected=False)
    top_m_applicants = []
    error_msg_ranking = None

    if isinstance(ranked_result, dict) and 'error' in ranked_result:
        error_msg_ranking = ranked_result['error']
    elif isinstance(ranked_result, dict) and 'ranked_applicants' in ranked_result:
        applicants_raw = ranked_result['ranked_applicants']
        if isinstance(applicants_raw, list):
             top_m_applicants = [
                 {"applicant_id": r[0], "name": r[1], "rating": r[2]}
                 for r in applicants_raw if isinstance(r, (tuple, list)) and len(r) >= 3 and r[0] is not None and r[2] is not None
             ]
             print(f"Selected top {len(top_m_applicants)} applicants after rating.")
        else: error_msg_ranking = "Ranking function returned invalid list format."
    else: error_msg_ranking = "Unexpected ranking result."

    if error_msg_ranking: flash(f"Error retrieving final ranked list: {error_msg_ranking}", "danger")

    return render_template('hr_job_ranked_applicants.html',
                           job_id=job_id,
                           job_title=job.get('title', job_id),
                           applicants=top_m_applicants,
                           top_n=m,
                           is_filtered_view=True) # Flag this view


# ... (Keep update_status as is) ...
@app.route('/hr/update_status/<path:applicant_id>/<job_id>', methods=['POST']) # Use path for ID
# @login_required
def update_status(applicant_id, job_id):
    """Handles AJAX requests to update an applicant's status."""
    try:
        applicant_id = unquote(applicant_id)
    except Exception as e:
         print(f"Error decoding applicant_id '{applicant_id}': {e}")
         return jsonify({"success": False, "error": "Invalid applicant identifier."}), 400

    if not request.is_json:
         return jsonify({"success": False, "error": "Request must be JSON."}), 415

    new_status = request.json.get('status')
    print(f"Received status update request: A:{applicant_id}, J:{job_id}, New Status: {new_status}")

    allowed_statuses = ['pending', 'shortlisted', 'rejected', 'selected', 'hired']
    if not new_status or new_status not in allowed_statuses:
        return jsonify({"success": False, "error": f"Invalid status '{new_status}' provided."}), 400

    if update_application_status(applicant_id, job_id, new_status):
        print(f"Status updated successfully for {applicant_id} to {new_status}")
        return jsonify({"success": True, "new_status": new_status})
    else:
        print(f"Failed to update status for {applicant_id} (DB issue or record not found?)")
        apps_check = get_applicants_for_job(job_id, include_rejected=True)
        applicant_exists = next((app for app in apps_check if app.get('applicant_id') == applicant_id), None)
        error_msg = "Applicant or application not found." if not applicant_exists else "Failed to update status (database error)."
        status_code = 404 if not applicant_exists else 500
        return jsonify({"success": False, "error": error_msg}), status_code

# ... (Keep finalize_job as is) ...
@app.route('/hr/finalize_job/<job_id>', methods=['POST'])
# @login_required
def finalize_job(job_id):
    """Marks shortlisted as 'selected', closes job, sends emails (if configured)."""
    print(f"Received request to finalize job: {job_id}")
    job = get_job(job_id)
    if not job: flash(f"Job ID '{job_id}' not found.", "error"); return redirect(url_for('hr_list_jobs'))
    if job.get('job_status') != 'open': flash(f"Job '{job.get('title', job_id)}' is already {job.get('job_status', 'not open')}, cannot finalize again.", "warning"); return redirect(url_for('hr_view_applicants', job_id=job_id))

    shortlisted_applicants = get_applications_by_status(job_id, 'shortlisted')
    if not shortlisted_applicants:
        flash("No applicants were shortlisted for this job. Please shortlist candidates before finalizing.", "warning")
        return redirect(url_for('hr_view_applicants', job_id=job_id))

    print(f"Found {len(shortlisted_applicants)} shortlisted applicants to process.")
    success_emails = 0; failed_emails = 0; failed_status_updates = 0

    for applicant in shortlisted_applicants:
        applicant_id = applicant.get('applicant_id')
        applicant_name = applicant.get('name') or 'Candidate'
        if not applicant_id:
            print("Warning: Skipping shortlisted applicant with missing ID.")
            failed_status_updates += 1
            continue

        if update_application_status(applicant_id, job_id, 'selected'):
            if mail:
                try:
                    company_name = os.environ.get("COMPANY_NAME", "Our Company")
                    hr_contact_email = os.environ.get("HR_CONTACT_EMAIL", "hr@example.com")
                    job_title_email = job.get('title', 'the position')
                    subject = f"Update on your application for {job_title_email} at {company_name}"
                    body = f"""Dear {applicant_name},

Congratulations! We were impressed with your application for the {job_title_email} position at {company_name} and would like to invite you to the next stage of our selection process.

[Insert details about the next steps here, e.g., interview scheduling link, documents required, contact person, expected timeline].

Please let us know if you have any questions by replying to this email or contacting {hr_contact_email}.

We look forward to speaking with you soon.

Best regards,
The Hiring Team at {company_name}
{hr_contact_email if hr_contact_email != 'hr@example.com' else ''}
"""
                    msg = Message(subject=subject, recipients=[applicant_id], body=body.strip())
                    mail.send(msg)
                    print(f"Sent selection email to {applicant_id}")
                    success_emails += 1
                except Exception as e:
                    print(f"ERROR sending email to {applicant_id}: {e}"); traceback.print_exc(); failed_emails += 1
            else:
                print(f"Skipping email to {applicant_id} (Mail not configured).")
        else:
            print(f"ERROR: Failed to update status to 'selected' for {applicant_id}")
            failed_status_updates += 1

    if not update_job_status(job_id, 'closed'):
        flash(f"Failed to update job status for {job_id} to 'closed'. Please check manually.", "error")
    else:
        print(f"Job {job_id} status updated to 'closed'.")

    flash(f"Finalized selection for job '{job.get('title', job_id)}'. Processed {len(shortlisted_applicants)} shortlisted applicant(s).", "success")
    if success_emails > 0: flash(f"Successfully sent selection emails to {success_emails} applicant(s).", "info")
    if failed_emails > 0: flash(f"Failed to send emails to {failed_emails} applicant(s). Check server logs and mail configuration.", "danger")
    if failed_status_updates > 0: flash(f"Failed to update status for {failed_status_updates} applicant(s). Check server logs.", "danger")
    if not mail and success_emails == 0 and len(shortlisted_applicants) > 0: flash("Email sending is disabled (mail server not configured). No notifications sent.", "warning")

    return redirect(url_for('hr_view_applicants', job_id=job_id))


# --- Run the Flask App ---
if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    if not os.path.exists(UPLOAD_FOLDER):
        try:
            os.makedirs(UPLOAD_FOLDER)
            print(f"Created upload folder: {UPLOAD_FOLDER}")
        except OSError as e:
            print(f"ERROR creating upload folder {UPLOAD_FOLDER}: {e}")
            import sys
            print("Exiting application.")
            sys.exit(1)

    print(f"Starting Flask app on http://{host}:{port} (Debug: {debug})")
    app.run(host=host, port=port, debug=debug, use_reloader=debug)
