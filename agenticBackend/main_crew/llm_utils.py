# llm_utils.py (Using Google Gemini - Smarter Chatbot Version)
import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from dotenv import load_dotenv
import json
import re
import traceback # For detailed error logging

# Load environment variables from .env file
load_dotenv()

# Configure the Google API key
google_api_key = os.getenv("GOOGLE_API_KEY")
OLLAMA_BASE_URL = "N/A" # Placeholder, not used for Gemini

if not google_api_key:
    print("ERROR: GOOGLE_API_KEY not found in environment variables.")
    print("Please create a .env file and add your key: GOOGLE_API_KEY='YOUR_KEY'")
    llm = None
    analyzer_llm = None
else:
    try:
        # Main LLM for structured output and NLU
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            temperature=0.1,
            google_api_key=google_api_key,
            convert_system_message_to_human=True
            )
        # Analyzer LLM for summaries, ratings, highlights (more creative)
        analyzer_llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            temperature=0.5, # Slightly higher temp for summarization/highlights
            google_api_key=google_api_key,
            convert_system_message_to_human=True
            )
        print("Successfully configured Google Gemini LLM (gemini-1.5-flash-latest).")
    except Exception as e:
        print(f"ERROR: Failed to initialize Google Gemini.")
        print(f"Error details: {e}")
        llm = None
        analyzer_llm = None

# --- Helper Functions ---
def clean_json_response(response_text):
    """Cleans common LLM JSON output issues (markdown, extra text)."""
    if not isinstance(response_text, str):
         return None
    cleaned = re.sub(r"```json\n?", "", response_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"```", "", cleaned)
    start_index = cleaned.find('{')
    end_index = cleaned.rfind('}')
    if start_index != -1 and end_index != -1 and end_index > start_index:
        json_str = cleaned[start_index : end_index + 1]
        return json_str.strip()
    else:
        # If no brackets found, maybe the LLM just output the JSON string directly?
        # Basic check: does it look like JSON? (Starts with { ends with })
        cleaned_strip = cleaned.strip()
        if cleaned_strip.startswith('{') and cleaned_strip.endswith('}'):
            print("Warning: clean_json_response returning stripped response as potential JSON.")
            return cleaned_strip
        print(f"Warning: Could not extract valid JSON object from response:\n{response_text}")
        return None # Return None if extraction failed

def to_5_star(score):
    """Converts a 0-100 score to a 0.00-5.00 score with 0.25 increments."""
    if score is None or not isinstance(score, (int, float)):
        return None
    try:
        score = float(score)
    except (ValueError, TypeError):
        return None
    score = max(0.0, min(100.0, score))
    scaled_score = round((score / 100.0) * 20.0)
    star_rating = scaled_score / 4.0
    return f"{star_rating:.2f}"


# --- Core LLM Interaction Functions ---

def structure_resume_text(resume_text):
    # ... (Keep this function as in previous version) ...
    if not llm: return {"error": "Gemini LLM not available."}
    prompt_template = """
    Analyze the following resume text. Respond ONLY with a valid JSON object representing the extracted information.
    DO NOT include any introductory text, explanations, markdown markers (like ```json), or concluding remarks outside the JSON structure itself.
    The JSON object must include keys: 'name', 'contact_info' (object with 'email', 'phone'), 'summary', 'skills' (list), 'experience' (list of objects: 'title', 'company', 'duration', 'description'), 'education' (list of objects: 'degree', 'institution', 'year').
    Use null or empty lists/objects for missing information. Ensure all string values within the JSON are properly escaped.

    Resume Text:
    ---
    {resume_text}
    ---

    JSON Output:
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    print("\n--- Sending text to Gemini LLM for structuring resume ---")
    raw_response = ""
    try:
        response = chain.invoke({"resume_text": resume_text})
        raw_response = response
        print("--- Gemini raw response (resume structure): ---")
        print(response)
        json_str = clean_json_response(response)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as json_e:
                print(f"Error: Failed to parse cleaned JSON for resume. Error: {json_e}")
                print(f"Cleaned JSON string was: {json_str}")
                return {"error": "Failed to parse structured resume JSON from Gemini", "raw_response": response}
        else:
             print("Error: Cleaned JSON string was empty for resume.")
             return {"error": "Failed to parse structured resume JSON from Gemini (empty after cleaning)", "raw_response": response}
    except Exception as e:
        print(f"Error structuring resume via Gemini: {e}")
        return {"error": "Failed to structure resume with Gemini", "details": str(e), "raw_response": raw_response}


def structure_job_description(jd_text):
    # ... (Keep this function as in previous version) ...
    if not llm: return {"error": "Gemini LLM not available."}
    prompt_template = """
    Analyze the following job description text. Respond ONLY with a valid JSON object representing the extracted requirements.
    DO NOT include any introductory text, explanations, markdown markers (like ```json), or concluding remarks outside the JSON structure itself.
    The JSON object must include keys: 'job_title', 'required_skills' (list), 'preferred_skills' (list), 'required_experience_years' (integer or null), 'required_education' (string or null), 'key_responsibilities' (list).
    Use null or empty lists/objects for missing information. Ensure all string values within the JSON are properly escaped.

    Job Description Text:
    ---
    {jd_text}
    ---

    JSON Output:
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    print("\n--- Sending text to Gemini LLM for structuring JD ---")
    raw_response = ""
    try:
        response = chain.invoke({"jd_text": jd_text})
        raw_response = response
        print("--- Gemini raw response (JD structure): ---")
        print(response)
        json_str = clean_json_response(response)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as json_e:
                print(f"Error: Failed to parse cleaned JSON for JD. Error: {json_e}")
                print(f"Cleaned JSON string was: {json_str}")
                return {"error": "Failed to parse structured JD JSON from Gemini", "raw_response": response}
        else:
            print("Error: Cleaned JSON string was empty for JD.")
            return {"error": "Failed to parse structured JD JSON from Gemini (empty after cleaning)", "raw_response": response}
    except Exception as e:
        print(f"Error structuring JD via Gemini: {e}")
        return {"error": "Failed to structure job description with Gemini", "details": str(e), "raw_response": raw_response}


def rate_resume_against_jd(structured_resume, structured_jd):
    # ... (Keep this function as in previous version) ...
    if not analyzer_llm: return {"error": "Gemini LLM (analyzer) not available."}
    prompt_template = """
    Act as an expert HR analyst. Analyze the structured resume data and structured job description data provided below.
    Respond ONLY with a valid JSON object containing your evaluation.
    DO NOT include any introductory text, explanations, markdown markers (like ```json), or concluding remarks outside the JSON structure itself.
    The JSON object MUST have these exact keys:
    - "rating": An integer score from 0 to 100 representing suitability. Be realistic.
    - "summary": A concise (1-2 sentence) justification for the rating.
    - "fits": A list of strings detailing specific aspects where the resume MATCHES the JD (e.g., "Has required skill: Python", "Meets experience requirement"). Be specific. Maximum 5 items.
    - "lacks": A list of strings detailing specific aspects where the resume DOES NOT meet JD requirements (e.g., "Missing preferred skill: AWS", "Lacks required degree"). Be specific. Maximum 5 items.

    Structured Resume Data:
    ```json
    {resume_data}
    ```

    Structured Job Description Data:
    ```json
    {jd_data}
    ```

    JSON Output:
    """
    # Default error response
    default_error_response = {"error": "Failed to get rating", "rating": 0, "summary": "Error", "fits": [], "lacks": []}

    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | analyzer_llm | StrOutputParser()
    print("\n--- Sending structured data to Gemini LLM for rating ---")
    raw_response = ""
    try:
        try:
             resume_json_str = json.dumps(structured_resume, indent=2)
             jd_json_str = json.dumps(structured_jd, indent=2)
        except TypeError as json_dump_e:
             print(f"Error: Input data is not JSON serializable: {json_dump_e}")
             return {**default_error_response, "error": "Invalid input data format."}

        response = chain.invoke({"resume_data": resume_json_str, "jd_data": jd_json_str})
        raw_response = response
        print("--- Gemini raw response (Rating): ---")
        print(response)
        json_str = clean_json_response(response)
        if json_str:
             try:
                 parsed_json = json.loads(json_str)
                 required_keys = ["rating", "summary", "fits", "lacks"]
                 if not isinstance(parsed_json, dict): raise ValueError("Parsed response is not a dictionary.")
                 if not all(key in parsed_json for key in required_keys): raise ValueError(f"Missing required keys. Found: {list(parsed_json.keys())}")
                 if not isinstance(parsed_json.get("rating"), int): parsed_json["rating"] = int(parsed_json.get("rating", 0))
                 if not isinstance(parsed_json.get("summary"), str): raise ValueError("Summary is not a string.")
                 if not isinstance(parsed_json.get("fits"), list): raise ValueError("Fits is not a list.")
                 if not isinstance(parsed_json.get("lacks"), list): raise ValueError("Lacks is not a list.")
                 parsed_json["rating"] = max(0, min(100, parsed_json["rating"]))
                 return parsed_json
             except (json.JSONDecodeError, ValueError, TypeError) as json_e:
                 print(f"Error: Failed to parse or validate rating JSON. Error: {json_e}")
                 print(f"Cleaned JSON string was: {json_str}")
                 return {**default_error_response, "error": f"Failed to parse/validate rating JSON from Gemini: {json_e}", "raw_response": response}
        else:
             print("Error: Cleaned JSON string was empty for rating.")
             return {**default_error_response, "error": "Failed to parse rating JSON from Gemini (empty after cleaning)", "raw_response": response}
    except Exception as e:
        print(f"Error rating resume via Gemini: {e}")
        return {**default_error_response, "error": "Failed to rate resume with Gemini", "details": str(e), "raw_response": raw_response}


def summarize_text_contextually(text_to_summarize, context_text):
    # ... (Keep this function as in previous version) ...
    if not analyzer_llm: return "Error: Gemini LLM (analyzer) not available."
    prompt_template = """
    Based solely on the provided job context and resume text, write a concise summary (3-4 sentences max) of the resume focusing ONLY on its direct relevance to the key requirements mentioned in the job context.
    Highlight matches and significant gaps regarding skills and experience.
    Start the summary directly, without any introductory phrases like "This resume shows..." or "The candidate...". Output only the summary text.

    Job Context:
    ---
    {context}
    ---

    Resume Text to Summarize:
    ---
    {main_text}
    ---

    Concise, Context-Aware Summary (3-4 sentences maximum):
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | analyzer_llm | StrOutputParser()
    print("\n--- Sending text to Gemini LLM for contextual summary ---")
    raw_response = ""
    try:
        summary = chain.invoke({"context": context_text, "main_text": text_to_summarize})
        raw_response = summary
        print("--- Gemini raw response (Summary): ---")
        print(summary)
        return summary.strip() if isinstance(summary, str) else "Error: Summary generation returned non-string result."
    except Exception as e:
        print(f"Error generating summary via Gemini: {e}")
        return f"Error: Could not generate summary with Gemini. Details: {e}"

# --- NLU and Highlight Generation ---

def understand_hr_chat_intent(user_message: str, current_job_context: str = None):
    """Uses Gemini LLM to understand intent and extract entities from HR chat."""
    if not llm: return {"error": "Gemini LLM not available."}

    context_hint = f"The user might be asking about Job ID '{current_job_context}' if they use terms like 'this job', 'current job', 'here', or don't specify another Job ID." if current_job_context else "No specific job context is currently set."

    # --- Updated Prompt ---
    prompt_template = f"""
    Analyze the HR user's chat message below. Identify the primary intent and extract relevant entities (job_id, applicant_email, applicant_name).
    {context_hint}

    Possible Intents:
    - get_overview: User wants a status summary of a job listing. Needs a job_id (explicitly mentioned or from context). (e.g., "status?", "overview?", "how's it going for JOB001?", "status on this one?")
    - get_applicant_details: User wants details about a specific applicant. Needs applicant_email OR applicant_name, and job_id (explicitly mentioned or from context). (e.g., "tell me about applicant@test.com", "details for John Doe", "what about Candidate Name?")
    - get_ranking: User wants a list of top-rated/best candidates for a job. Needs a job_id (explicitly mentioned or from context). (e.g., "who is best?", "recommend top candidates", "show ranking for JOB001", "who is the topper here?", "find good candidates", "top 5?")
    - get_report: User wants a report. Needs a job_id. (Currently basic)
    - set_context: User is trying to specify which job ID to focus on. Needs a job_id. (e.g., "focus on job JOB001", "let's talk about MKTG-02", "switch to DEV003")
    - get_help: User is asking for help or instructions on how to use the chatbot. (e.g., "help", "what can you do?", "list commands")
    - greeting: User is just saying hello or similar pleasantry.
    - clarification: User message is too ambiguous to determine a clear intent or required entity (e.g. "tell me about the candidate" without name/email).
    - unknown: The intent is unrelated to job portal tasks or completely unclear.

    Extracted Entities:
    - job_id: The specific job identifier mentioned (e.g., "DEV001", "MKTG-02", "EMB_IOT_DEV_KOL_02"). Return null if not clearly mentioned.
    - applicant_email: The email address of an applicant mentioned. Return null if not clearly mentioned.
    - applicant_name: The name (first, last, or full) of an applicant mentioned (e.g., "Adrija Ghosh", "John", "Desai"). Return null if not clearly mentioned.

    Instructions:
    1. If the user refers to "this job", "current job", "here", etc., and a context Job ID is available, the intent is likely related to that context ID, but DO NOT extract it as `job_id` unless they also state the ID explicitly. The backend will use the page/session context.
    2. If the user asks for details about a person using only a name, extract the name into `applicant_name`. Do not guess the email.
    3. Prioritize specific intents (`get_ranking`, `get_applicant_details`, `set_context`) over general ones (`get_overview`) if keywords overlap.
    4. If essential information is missing (e.g., needs job_id but none provided/in context, needs name/email but none provided), set intent to `clarification`.

    Respond ONLY with a valid JSON object containing 'intent' (string from "Possible Intents" list) and 'entities' (an object containing 'job_id', 'applicant_email', 'applicant_name', using null for values not found).
    Do not include any explanations or markdown formatting outside the JSON structure.

    User Message:
    ---
    {{user_message}}
    ---

    JSON Output:
    """
    # --- End Updated Prompt ---

    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    print("\n--- Sending HR chat message to Gemini LLM for NLU ---")
    raw_response = ""
    default_nlu_error = {"error": "Failed to understand message", "intent": "unknown", "entities": {"job_id": None, "applicant_email": None, "applicant_name": None}}
    try:
        response = chain.invoke({"user_message": user_message})
        raw_response = response
        print(f"--- Gemini raw response (NLU): ---\n{response}")
        json_str = clean_json_response(response)
        if json_str:
            try:
                parsed_json = json.loads(json_str)
                # Basic validation
                if not isinstance(parsed_json, dict) or 'intent' not in parsed_json or 'entities' not in parsed_json:
                    raise ValueError("Missing required keys 'intent' or 'entities'.")
                if not isinstance(parsed_json.get('entities'), dict):
                     raise ValueError("'entities' key is not a dictionary.")

                # Ensure entities sub-keys exist, default to null if missing
                entities_dict = parsed_json.get('entities', {})
                parsed_json['entities'] = {
                    'job_id': entities_dict.get('job_id'),
                    'applicant_email': entities_dict.get('applicant_email'),
                    'applicant_name': entities_dict.get('applicant_name') # Add name
                }
                # Validate intent value against known intents
                known_intents = ['get_overview', 'get_applicant_details', 'get_ranking', 'get_report', 'set_context', 'get_help', 'greeting', 'clarification', 'unknown']
                if parsed_json.get('intent') not in known_intents:
                    print(f"Warning: LLM returned unknown intent '{parsed_json.get('intent')}'. Mapping to 'unknown'.")
                    parsed_json['intent'] = 'unknown'

                return parsed_json
            except (json.JSONDecodeError, ValueError) as json_e:
                print(f"Error: Failed to parse or validate NLU JSON. Error: {json_e}")
                print(f"Cleaned JSON string was: {json_str}")
                return {**default_nlu_error, "error": f"Failed to parse/validate NLU JSON from Gemini: {json_e}", "raw_response": response}
        else:
            print("Error: Cleaned JSON string was empty for NLU.")
            return {**default_nlu_error, "error": "Failed to parse NLU JSON from Gemini (empty after cleaning)", "raw_response": response}
    except Exception as e:
        print(f"Error understanding HR chat via Gemini: {e}")
        traceback.print_exc() # Log full traceback for unexpected errors
        return {**default_nlu_error, "error": "Failed to understand message with Gemini", "details": str(e), "raw_response": raw_response}


def generate_ranking_highlights(top_candidates_data, job_context):
    """
    Uses Gemini LLM to generate a 1-sentence highlight for each top candidate.

    Args:
        top_candidates_data (list): A list of dictionaries, each containing
                                    at least 'name', 'applicant_id', and 'summary' (or 'fits'/'lacks').
        job_context (dict): The structured job description for context.

    Returns:
        dict: A dictionary mapping applicant_id to highlight sentence, or {"error": ...}
    """
    if not analyzer_llm: return {"error": "Gemini LLM (analyzer) not available."}
    if not top_candidates_data: return {} # Return empty dict if no candidates

    # Prepare the input for the LLM
    candidates_input_str = ""
    for i, candidate in enumerate(top_candidates_data):
        # Use summary if available, otherwise maybe fits/lacks? Adapt as needed.
        summary = candidate.get('summary', 'No summary available.')
        candidates_input_str += f"\nCandidate {i+1}:\n"
        candidates_input_str += f"  Name: {candidate.get('name', candidate.get('applicant_id'))}\n"
        # Include applicant_id to map results back
        candidates_input_str += f"  ID: {candidate.get('applicant_id')}\n"
        candidates_input_str += f"  AI Summary/Notes: {summary}\n"

    job_context_str = json.dumps(job_context, indent=2)

    prompt_template = """
    Act as an expert HR analyst reviewing top candidates. You are given information about the job and summaries/notes for the top {num_candidates} candidates.
    For EACH candidate provided below, write exactly ONE concise highlight sentence explaining their strongest qualification or main reason for being a top candidate *specifically for this job*.
    Focus on key skills, experience, or education mentioned in the job context.

    Job Context:
    ```json
    {job_context}
    ```

    Top Candidate Information:
    ---
    {candidates_info}
    ---

    Required Output Format:
    Respond ONLY with a single valid JSON object. The keys should be the candidate 'ID's provided above, and the values should be the single highlight sentence (string) for that candidate.
    Example:
    {{
      "email1@example.com": "Strong match with 5 years Python experience and required AWS skills.",
      "email2@example.com": "Excellent fit due to direct experience in API design mentioned in the job requirements.",
      "email3@example.com": "Possesses the required Computer Science degree and demonstrates relevant project experience."
    }}
    """

    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | analyzer_llm | StrOutputParser() # Use analyzer LLM

    print("\n--- Sending top candidate data to Gemini LLM for highlights ---")
    raw_response = ""
    try:
        response = chain.invoke({
            "num_candidates": len(top_candidates_data),
            "job_context": job_context_str,
            "candidates_info": candidates_input_str.strip()
        })
        raw_response = response
        print("--- Gemini raw response (Highlights): ---")
        print(response)
        json_str = clean_json_response(response)
        if json_str:
            try:
                highlights = json.loads(json_str)
                if isinstance(highlights, dict):
                    return highlights
                else:
                    raise ValueError("Parsed highlight response is not a dictionary.")
            except (json.JSONDecodeError, ValueError) as json_e:
                print(f"Error: Failed to parse or validate highlight JSON. Error: {json_e}")
                print(f"Cleaned JSON string was: {json_str}")
                return {"error": f"Failed to parse/validate highlight JSON from Gemini: {json_e}", "raw_response": response}
        else:
            print("Error: Cleaned JSON string was empty for highlights.")
            return {"error": "Failed to parse highlight JSON from Gemini (empty after cleaning)", "raw_response": response}
    except Exception as e:
        print(f"Error generating highlights via Gemini: {e}")
        traceback.print_exc()
        return {"error": "Failed to generate highlights with Gemini", "details": str(e), "raw_response": raw_response}


# --- Test Block ---
if __name__ == "__main__":
    if not llm:
        print("\nCannot run tests: Gemini LLM initialization failed (check API key / .env file).")
    else:
        # ... (Keep existing tests for structuring, rating, summarize, to_5_star) ...

        print("\n=== Testing Gemini: HR Chat NLU (Enhanced) ===")
        nlu_tests = [
            ("Can you give me an overview of job DEV001?", None, "get_overview"),
            ("Tell me about applicant alice@example.com", "DEV001", "get_applicant_details"),
            ("What's the status?", "MKTG-02", "get_overview"), # Should use context
            ("Let's focus on SALESJOB", None, "set_context"),
            ("who is the topper for DEV001?", None, "get_ranking"),
            ("recommend the best candidates", "MKTG-02", "get_ranking"), # Should use context
            ("show top 5 for job EMBEDDED-SYS", None, "get_ranking"),
            ("what about John Doe here?", "JOB007", "get_applicant_details"), # Name, uses context
            ("status on this job", "JOB008", "get_overview"), # Implicit job, uses context
            ("help", None, "get_help"),
            ("list commands", None, "get_help"),
            ("tell me about the candidate", "JOB009", "clarification"), # Needs name/email
            ("show ranking", None, "clarification"), # Needs job ID
        ]
        for msg, ctx, expected_intent in nlu_tests:
            nlu_result = understand_hr_chat_intent(msg, current_job_context=ctx)
            print(f"\nNLU for '{msg}' (ctx: {ctx}):")
            print(json.dumps(nlu_result, indent=2))
            # Simple assertion check
            if 'intent' in nlu_result and nlu_result['intent'] != expected_intent:
                 print(f"ASSERTION FAILED: Expected intent '{expected_intent}', got '{nlu_result['intent']}'")


        print("\n=== Testing Highlight Generation ===")
        # Dummy data for testing highlight generation
        test_job_ctx = {"job_title": "Python Dev", "required_skills": ["Python", "API", "SQL"], "required_experience_years": 3}
        test_candidates = [
            {"applicant_id": "a@a.com", "name": "Alice", "summary": "Good Python, 4 years exp, SQL ok. Lacks API design."},
            {"applicant_id": "b@b.com", "name": "Bob", "summary": "Strong API design, 2 years exp. Limited Python."},
            {"applicant_id": "c@c.com", "name": "Charlie", "summary": "Junior dev, 1 year exp, knows basic Python."},
        ]
        highlights = generate_ranking_highlights(test_candidates, test_job_ctx)
        print("\nGenerated Highlights:")
        print(json.dumps(highlights, indent=2))
