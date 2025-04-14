# main_crew.py (Corrected run_ranking_direct signature and call)
import json
import os

# Import utility functions directly
from file_utils import extract_text_from_file, UPLOAD_FOLDER # Import UPLOAD_FOLDER
from llm_utils import ( # These now point to the Gemini implementations
    structure_resume_text,
    structure_job_description,
    rate_resume_against_jd,
    summarize_text_contextually
)
from database_utils import (
    add_job,
    add_applicant,
    get_structured_jd,
    get_structured_resume,
    get_resume_path,
    get_ranked_applicants, # This function DOES accept include_rejected
    get_applicants_for_job,
    add_application,
    update_application_rating,
    init_db,
    update_application_status, # Added previously
    get_applications_by_status,# Added previously
    update_job_status # Added previously
)

# --- Configuration & Initialization ---
print("Initializing database from main_crew.py...")
init_db()
print(f"LLM Utils is configured to use Google Gemini (check llm_utils.py logs).")


# --- Workflow Functions (Direct Implementation) ---

def run_suitability_check_direct(resume_file_path: str, job_id: str):
    # ... (Keep implementation as is from previous version) ...
    print(f"\n--- Running Direct Suitability Check ---")
    print(f"Resume Path: {resume_file_path}")
    print(f"Job ID: {job_id}")

    if not os.path.exists(resume_file_path):
        return {"error": f"Resume file not found at path: {resume_file_path}"}

    print("Step 1: Extracting resume text...")
    resume_text = extract_text_from_file(resume_file_path)
    if isinstance(resume_text, str) and ("Error:" in resume_text or "Warning:" in resume_text): return {"error": f"Failed to extract text: {resume_text}"}
    if not resume_text: return {"error": "Failed to extract text (empty result)."}
    print("Resume text extracted.")

    print("Step 2: Structuring resume text...")
    structured_resume = structure_resume_text(resume_text)
    if isinstance(structured_resume, dict) and 'error' in structured_resume:
        print(f"Error structuring resume: {structured_resume['error']}")
        structured_resume['details'] = structured_resume.get('details', structured_resume['error'])
        return structured_resume
    print("Resume structured successfully.")

    print("Step 3: Fetching structured job description...")
    structured_jd = get_structured_jd(job_id)
    if not structured_jd: return {"error": f"Job ID '{job_id}' not found or has no structured data."}
    if isinstance(structured_jd, dict) and 'error' in structured_jd:
        print(f"Error in stored JD data: {structured_jd['error']}")
        return {"error": f"Stored JD for {job_id} contains error.", "details": structured_jd.get('details', structured_jd['error'])}
    print("Structured JD fetched successfully.")

    print("Step 4: Rating resume against job description...")
    rating_result = rate_resume_against_jd(structured_resume, structured_jd)
    if isinstance(rating_result, dict) and 'error' in rating_result:
        print(f"Error during rating: {rating_result['error']}")
        rating_result['details'] = rating_result.get('details', rating_result['error'])
    else: print("Rating successful.")
    return rating_result


# --- CORRECTED run_ranking_direct ---
def run_ranking_direct(job_id: str, n: int, include_rejected: bool = False): # Added include_rejected param
    """Retrieves top N RATED applicants directly from database function."""
    print(f"\n--- Running Direct Ranking for Job ID: {job_id}, Top N: {n}, Include Rejected: {include_rejected} ---") # Log new param
    if not job_id: return {"error": "Job ID is required."}
    try: n_int = int(n); n_int = 5 if n_int <= 0 else n_int
    except ValueError: n_int = 5

    # Pass include_rejected down to the database function call
    results = get_ranked_applicants(job_id, n_int, include_rejected=include_rejected)
    print(f"Ranking complete. Found {len(results)} rated applicants (filter applied: rejected hidden={not include_rejected}).")
    return {"ranked_applicants": results}


def run_summarization_direct(applicant_id: str, job_id: str):
    # ... (Keep implementation as is from previous version) ...
    print(f"\n--- Running Direct Summarization for Applicant: {applicant_id}, Job: {job_id} ---")
    if not applicant_id or not job_id: return {"error": "Applicant ID and Job ID required."}

    print("Step 1: Fetching structured job description (context)...")
    structured_jd = get_structured_jd(job_id)
    if not structured_jd: return {"error": f"Job ID '{job_id}' not found or has no structured data."}
    if isinstance(structured_jd, dict) and 'error' in structured_jd:
        return {"error": f"Stored JD for {job_id} contains error.", "details": structured_jd.get('details', structured_jd['error'])}
    jd_context_input = json.dumps(structured_jd, indent=2); print("JD context prepared.")

    print("Step 2: Fetching resume path and text...")
    resume_filename = get_resume_path(applicant_id)
    if not resume_filename: return {"error": f"Resume path not found in DB for applicant {applicant_id}."}
    resume_full_path = os.path.join(UPLOAD_FOLDER, resume_filename)
    if not os.path.exists(resume_full_path): return {"error": f"Resume file not found in uploads folder: {resume_filename}"}
    resume_text = extract_text_from_file(resume_full_path)
    if isinstance(resume_text, str) and ("Error:" in resume_text or "Warning:" in resume_text):
        return {"error": f"Failed to extract resume text: {resume_text}"}
    if not resume_text: return {"error": "Failed to extract resume text (empty)."}
    print("Resume text extracted for summary.")

    print("Step 3: Generating contextual summary using LLM...");
    summary = summarize_text_contextually(text_to_summarize=resume_text, context_text=jd_context_input)

    if isinstance(summary, str) and summary.startswith("Error:"):
        print(f"Error during summarization: {summary}")
        detail = summary.split("Error:", 1)[-1].strip()
        return {"error": "Failed to generate summary with LLM.", "details": detail}
    elif isinstance(summary, str):
        print("Summarization successful.")
        return {"summary": summary.strip()}
    else:
        print(f"Unexpected summary result type: {type(summary)}")
        return {"error": "Summarization returned unexpected result format."}


# --- Example Usage (Test Block) ---
if __name__ == "__main__":
    # --- (Keep the existing test block as is) ---
    # It doesn't directly test include_rejected in run_ranking_direct,
    # but the underlying get_ranked_applicants is tested in database_utils.py tests.
    print("\n" + "="*30 + " STARTING DIRECT WORKFLOW TESTS (using Gemini) " + "="*30)

    if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

    print("\n--- Setting up Test Data ---")
    test_job_id = "DEV001"; test_job_added = False
    jd_text_sample = "Software Engineer needed. Skills: Python, API Design, SQL. Preferred: Docker, AWS. 3+ years exp. BSc required."
    print("Structuring sample JD...")
    structured_jd_for_db = structure_job_description(jd_text_sample)
    if isinstance(structured_jd_for_db, dict) and 'error' not in structured_jd_for_db:
        if add_job(test_job_id, "Software Engineer", jd_text_sample, structured_jd_for_db):
            print(f"Job {test_job_id} added/updated."); test_job_added = True
        else: print(f"ERROR adding Job {test_job_id}.")
    else: print(f"ERROR structuring JD: {structured_jd_for_db.get('error', 'Unknown')}.")

    test_applicant_id_1 = "direct_alice@test.com"; test_resume_filename_1 = "direct_test_resume_1.txt"; applicant_1_added = False
    full_resume_path_1 = os.path.join(UPLOAD_FOLDER, test_resume_filename_1)
    try:
        with open(full_resume_path_1, 'w') as f: f.write("Alice Developer\ndirect_alice@test.com\nPython, API Design, SQL, 4 years exp. BSc CompSci.\n")
        print(f"Created: {full_resume_path_1}")
        if add_applicant(test_applicant_id_1, "Alice Developer", test_resume_filename_1):
             print(f"Added: {test_applicant_id_1}"); applicant_1_added = True; add_application(test_applicant_id_1, test_job_id)
        else: print(f"ERROR adding {test_applicant_id_1}.")
    except Exception as e: print(f"Error setup applicant 1: {e}")

    test_applicant_id_2 = "direct_bob@test.com"; test_resume_filename_2 = "direct_test_resume_2.txt"; applicant_2_added = False
    full_resume_path_2 = os.path.join(UPLOAD_FOLDER, test_resume_filename_2)
    try:
        with open(full_resume_path_2, 'w') as f: f.write("Bob Coder\ndirect_bob@test.com\nPython, SQL. 1 year exp. Associate Degree.\n")
        print(f"Created: {full_resume_path_2}")
        if add_applicant(test_applicant_id_2, "Bob Coder", test_resume_filename_2):
            print(f"Added: {test_applicant_id_2}"); applicant_2_added = True; add_application(test_applicant_id_2, test_job_id)
        else: print(f"ERROR adding {test_applicant_id_2}.")
    except Exception as e: print(f"Error setup applicant 2: {e}")

    print("\n" + "-"*10 + " Test Case 1a: Direct Suitability (Alice) " + "-"*10)
    if test_job_added and applicant_1_added:
        rating_alice = run_suitability_check_direct(full_resume_path_1, test_job_id)
        print(f"Alice Rating: {json.dumps(rating_alice, indent=2)}")
        if isinstance(rating_alice, dict) and 'error' not in rating_alice:
            if update_application_rating(test_applicant_id_1, test_job_id, rating_alice): print("Saved Alice rating.")
            else: print("ERROR saving Alice rating.")
        else: print("Skipped saving Alice rating.")
    else: print("Skipping Alice check.")

    print("\n" + "-"*10 + " Test Case 1b: Direct Suitability (Bob) " + "-"*10)
    if test_job_added and applicant_2_added:
        rating_bob = run_suitability_check_direct(full_resume_path_2, test_job_id)
        print(f"Bob Rating: {json.dumps(rating_bob, indent=2)}")
        if isinstance(rating_bob, dict) and 'error' not in rating_bob:
            if update_application_rating(test_applicant_id_2, test_job_id, rating_bob): print("Saved Bob rating.")
            else: print("ERROR saving Bob rating.")
        else: print("Skipped saving Bob rating.")
    else: print("Skipping Bob check.")

    print("\n" + "-"*10 + " Test Case 2: Direct Ranking " + "-"*10)
    if test_job_added:
        # Test default (exclude rejected - though none are rejected yet)
        ranking_output = run_ranking_direct(test_job_id, 3)
        print(f"Ranking Output (default - excl rejected): {json.dumps(ranking_output, indent=2)}")
        # Test including rejected explicitly (should be same result here)
        ranking_output_incl = run_ranking_direct(test_job_id, 3, include_rejected=True)
        print(f"Ranking Output (incl rejected): {json.dumps(ranking_output_incl, indent=2)}")
    else: print("Skipping ranking check.")

    print("\n" + "-"*10 + " Test Case 3: Direct Summarization (Alice) " + "-"*10)
    if test_job_added and applicant_1_added:
        summary_output = run_summarization_direct(test_applicant_id_1, test_job_id)
        print(f"Summary Output for {test_applicant_id_1}: {json.dumps(summary_output, indent=2)}")
    else: print("Skipping Alice summarization check.")

    print("\n" + "="*30 + " FINISHED DIRECT WORKFLOW TESTS (using Gemini) " + "="*30)
