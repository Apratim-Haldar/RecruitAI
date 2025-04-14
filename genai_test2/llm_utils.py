# llm_utils.py (Refined structure_resume_text)
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
            model="gemini-1.5-flash-latest", # Using Flash for speed/cost
            temperature=0.1, # Low temp for structured output
            google_api_key=google_api_key,
            convert_system_message_to_human=True
            )
        # Analyzer LLM for summaries, ratings, highlights (more creative)
        analyzer_llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest", # Can use the same model
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
    # Remove markdown code blocks (json, etc.)
    cleaned = re.sub(r"```[a-zA-Z]*\n?", "", response_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"```", "", cleaned)
    # Find the first '{' and the last '}'
    start_index = cleaned.find('{')
    end_index = cleaned.rfind('}')
    if start_index != -1 and end_index != -1 and end_index > start_index:
        json_str = cleaned[start_index : end_index + 1]
        return json_str.strip()
    else:
        # Fallback: Check if the entire stripped string is a valid JSON object
        cleaned_strip = cleaned.strip()
        if cleaned_strip.startswith('{') and cleaned_strip.endswith('}'):
            try:
                json.loads(cleaned_strip) # Validate if it's parsable JSON
                print("Warning: clean_json_response returning stripped response as potential JSON.")
                return cleaned_strip
            except json.JSONDecodeError:
                print(f"Warning: Stripped response looked like JSON but failed parsing:\n{cleaned_strip}")
                return None
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
    # Scale to 0-20, round to nearest integer, then divide by 4
    scaled_score = round((score / 100.0) * 20.0)
    star_rating = scaled_score / 4.0
    return f"{star_rating:.2f}"


# --- Core LLM Interaction Functions ---

def structure_resume_text(resume_text):
    """Extracts key info from resume text and returns structured JSON."""
    if not llm: return {"error": "Gemini LLM not available."}

    # --- Refined Prompt ---
    prompt_template = """
    Analyze the following resume text provided between the '---' markers. Your goal is to extract key information and format it STRICTLY as a single JSON object.

    Instructions:
    1.  Respond ONLY with the JSON object. Do NOT include any explanations, introductions, summaries, apologies, or markdown formatting like ```json before or after the JSON.
    2.  Identify standard resume sections like "SUMMARY", "WORK EXPERIENCE", "PROJECTS", "EDUCATION", "SKILLS", "TECHNICAL SKILLS", "CONTACT INFORMATION".
    3.  Extract the following fields and structure them as specified:
        *   `name`: The candidate's full name (string, null if not found).
        *   `contact_info`: An object containing:
            *   `email`: Candidate's email address (string, null if not found). Look for patterns with '@'.
            *   `phone`: Candidate's phone number (string, null if not found). Look for typical phone number patterns.
        *   `summary`: The text from the "SUMMARY" or "OBJECTIVE" section (string, null if not found).
        *   `skills`: A list of key technical skills (strings). Prioritize extracting from a dedicated "SKILLS" or "TECHNICAL SKILLS" section. Also include relevant technical skills mentioned in experience or projects if clearly identifiable. Exclude soft skills unless explicitly listed as technical.
        *   `experience`: A list of objects, where each object represents a job/role and has:
            *   `title`: Job title (string, null if not found).
            *   `company`: Company name (string, null if not found).
            *   `duration`: Dates or duration worked (string, e.g., "Jan 2024 - Present", "Mar 2021 - Jan 2024", null if not found). Capture the text as presented.
            *   `description`: Key responsibilities or achievements, often bullet points (string, ideally newline-separated if possible, null if not found). Capture the bullet points or paragraph text associated with the role.
        *   `education`: A list of objects, where each object represents a degree/qualification and has:
            *   `degree`: Name of the degree or qualification (e.g., "M.S., Computer Science", "B.Tech, Statistics") (string, null if not found).
            *   `institution`: Name of the school/university (string, null if not found).
            *   `year`: Graduation year or duration (string, e.g., "2022", "2020 - 2022", null if not found). Capture the text as presented.
    4.  If information for a field is not found or cannot be reliably extracted, use `null` for strings/objects or an empty list `[]` for lists like 'skills', 'experience', 'education'.
    5.  Ensure the final output is valid JSON. Pay close attention to quotes (use double quotes for keys and string values), commas between elements, and brackets/braces. Escape any double quotes within string values using a backslash (\\").

    Example Structure (Do NOT copy data, just structure):
    ```json
    {{
      "name": "Jane Doe",
      "contact_info": {{ "email": "jane@example.com", "phone": "123-456-7890" }},
      "summary": "Experienced software engineer...",
      "skills": ["Python", "AWS", "SQL", "Docker"],
      "experience": [
        {{ "title": "Software Engineer", "company": "Tech Corp", "duration": "2020 - Present", "description": "- Developed new features using Python.\n- Managed AWS infrastructure." }},
        {{ "title": "Junior Developer", "company": "Startup Inc", "duration": "2018 - 2020", "description": "Assisted senior developers." }}
      ],
      "education": [
        {{ "degree": "BSc Computer Science", "institution": "State University", "year": "2018" }}
      ]
    }}
    ```

    Resume Text:
    ---
    {resume_text}
    ---

    JSON Output:
    """

    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    print("\n--- Sending text to Gemini LLM for structuring resume (using refined prompt) ---")
    raw_response = ""
    try:
        response = chain.invoke({"resume_text": resume_text})
        raw_response = response
        print("--- Gemini raw response (resume structure): ---")
        # Limit printing very long responses in console
        print(raw_response[:1000] + "..." if len(raw_response) > 1000 else raw_response)

        json_str = clean_json_response(response)

        if json_str:
            try:
                # Attempt to parse the cleaned JSON
                parsed_json = json.loads(json_str)
                # Basic validation: Check if it's a dictionary
                if not isinstance(parsed_json, dict):
                    print(f"Error: Parsed result is not a dictionary. Type: {type(parsed_json)}")
                    print(f"Cleaned JSON string was: {json_str}")
                    return {"error": "LLM did not return a valid JSON dictionary structure", "raw_response": raw_response}

                # Ensure expected top-level keys exist, using .get for safety
                result_dict = {
                    "name": parsed_json.get("name"),
                    "contact_info": parsed_json.get("contact_info", {}), # Default to empty dict
                    "summary": parsed_json.get("summary"),
                    "skills": parsed_json.get("skills", []), # Default to empty list
                    "experience": parsed_json.get("experience", []), # Default to empty list
                    "education": parsed_json.get("education", []) # Default to empty list
                }
                # Further validation/cleaning can be added here if needed (e.g., ensure lists contain objects)
                print("--- Successfully parsed structured resume JSON ---")
                return result_dict

            except json.JSONDecodeError as json_e:
                print(f"Error: Failed to parse cleaned JSON for resume. Error: {json_e}")
                print(f"Cleaned JSON string was: {json_str}") # Log the problematic string
                return {"error": "Failed to parse structured resume JSON from Gemini", "details": str(json_e), "raw_response": raw_response}
        else:
             print("Error: Cleaned JSON string was empty or invalid after cleaning.")
             return {"error": "Failed to parse structured resume JSON from Gemini (empty/invalid after cleaning)", "raw_response": raw_response}

    except Exception as e:
        print(f"Error structuring resume via Gemini: {e}")
        traceback.print_exc() # Log full traceback
        return {"error": "Failed to structure resume with Gemini", "details": str(e), "raw_response": raw_response}


# --- Keep other functions (structure_job_description, rate_resume_against_jd, etc.) as is ---

def structure_job_description(jd_text):
    if not llm: return {"error": "Gemini LLM not available."}
    prompt_template = """
    Analyze the following job description text. Respond ONLY with a valid JSON object representing the extracted requirements.
    DO NOT include any introductory text, explanations, markdown markers (like ```json), or concluding remarks outside the JSON structure itself.
    The JSON object must include keys: 'job_title', 'required_skills' (list of strings), 'preferred_skills' (list of strings), 'required_experience_years' (integer or null), 'required_education' (string or null), 'key_responsibilities' (list of strings).
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
        # print("--- Gemini raw response (JD structure): ---") # Less verbose
        # print(response)
        json_str = clean_json_response(response)
        if json_str:
            try:
                parsed_json = json.loads(json_str)
                # Add basic validation
                if not isinstance(parsed_json, dict):
                     raise ValueError("Parsed result is not a dictionary.")
                # Ensure required keys are at least present (can be null/empty)
                required_keys = ['job_title', 'required_skills', 'preferred_skills', 'required_experience_years', 'required_education', 'key_responsibilities']
                for key in required_keys:
                    if key not in parsed_json:
                         print(f"Warning: Missing key '{key}' in structured JD response. Setting default.")
                         if 'skills' in key or 'responsibilities' in key:
                              parsed_json[key] = []
                         else:
                              parsed_json[key] = None
                return parsed_json
            except (json.JSONDecodeError, ValueError) as json_e:
                print(f"Error: Failed to parse or validate cleaned JD JSON. Error: {json_e}")
                print(f"Cleaned JSON string was: {json_str}")
                return {"error": "Failed to parse structured JD JSON from Gemini", "details": str(json_e), "raw_response": response}
        else:
            print("Error: Cleaned JSON string was empty for JD.")
            return {"error": "Failed to parse structured JD JSON from Gemini (empty after cleaning)", "raw_response": response}
    except Exception as e:
        print(f"Error structuring JD via Gemini: {e}")
        traceback.print_exc()
        return {"error": "Failed to structure job description with Gemini", "details": str(e), "raw_response": raw_response}

def rate_resume_against_jd(structured_resume, structured_jd):
    if not analyzer_llm: return {"error": "Gemini LLM (analyzer) not available."}
    prompt_template = """
    Act as an expert HR analyst. Analyze the structured resume data and structured job description data provided below.
    Respond ONLY with a valid JSON object containing your evaluation.
    DO NOT include any introductory text, explanations, markdown markers (like ```json), or concluding remarks outside the JSON structure itself.
    The JSON object MUST have these exact keys:
    - "rating": An integer score from 0 to 100 representing suitability. Be realistic based on REQUIREMENTS vs candidate profile.
    - "summary": A concise (1-2 sentence) justification for the rating, highlighting key strengths/weaknesses against requirements.
    - "fits": A list of strings detailing specific aspects where the resume MATCHES the JD requirements (e.g., "Has required skill: Python", "Meets 3+ years experience requirement"). Be specific. Maximum 5 items.
    - "lacks": A list of strings detailing specific aspects where the resume DOES NOT meet critical JD requirements (e.g., "Missing required skill: AWS", "Lacks required PhD degree", "Experience duration less than required"). Be specific. Maximum 5 items.

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
        # print("--- Gemini raw response (Rating): ---") # Less verbose
        # print(response)
        json_str = clean_json_response(response)
        if json_str:
             try:
                 parsed_json = json.loads(json_str)
                 required_keys = ["rating", "summary", "fits", "lacks"]
                 if not isinstance(parsed_json, dict): raise ValueError("Parsed response is not a dictionary.")
                 if not all(key in parsed_json for key in required_keys): raise ValueError(f"Missing required keys. Found: {list(parsed_json.keys())}")
                 # Validate types more carefully
                 try: parsed_json["rating"] = int(parsed_json.get("rating", 0))
                 except (ValueError, TypeError): parsed_json["rating"] = 0; print("Warning: Invalid rating type, set to 0")
                 if not isinstance(parsed_json.get("summary"), str): parsed_json["summary"] = str(parsed_json.get("summary", "")); print("Warning: Invalid summary type, converted to str")
                 if not isinstance(parsed_json.get("fits"), list): parsed_json["fits"] = []; print("Warning: Invalid fits type, set to []")
                 if not isinstance(parsed_json.get("lacks"), list): parsed_json["lacks"] = []; print("Warning: Invalid lacks type, set to []")
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
        traceback.print_exc()
        return {**default_error_response, "error": "Failed to rate resume with Gemini", "details": str(e), "raw_response": raw_response}

def summarize_text_contextually(text_to_summarize, context_text):
    if not analyzer_llm: return "Error: Gemini LLM (analyzer) not available."
    prompt_template = """
    Based solely on the provided job context and resume text, write a concise summary (3-4 sentences max) of the resume focusing ONLY on its direct relevance to the key requirements mentioned in the job context.
    Highlight matches and significant gaps regarding skills and experience required by the job context.
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
        # print("--- Gemini raw response (Summary): ---") # Less verbose
        # print(summary)
        return summary.strip() if isinstance(summary, str) else "Error: Summary generation returned non-string result."
    except Exception as e:
        print(f"Error generating summary via Gemini: {e}")
        traceback.print_exc()
        return f"Error: Could not generate summary with Gemini. Details: {e}"

# --- NLU and Highlight Generation ---

def understand_hr_chat_intent(user_message: str, current_job_context: str = None):
    """Uses Gemini LLM to understand intent and extract entities from HR chat."""
    if not llm: return {"error": "Gemini LLM not available."}

    context_hint = f"The user might be asking about Job ID '{current_job_context}' if they use terms like 'this job', 'current job', 'here', or don't specify another Job ID." if current_job_context else "No specific job context is currently set."

    prompt_template = f"""
    Analyze the HR user's chat message below. Identify the primary intent and extract relevant entities (job_id, applicant_email, applicant_name).
    {context_hint}

    Possible Intents:
    - get_overview: User wants a status summary of a job listing or all listings. Needs a job_id (explicitly mentioned or from context) or general term like 'listings'.
    - get_applicant_details: User wants details about a specific applicant. Needs applicant_email OR applicant_name, and job_id (explicitly mentioned or from context).
    - get_ranking: User wants a list of top-rated/best candidates for a job. Needs a job_id (explicitly mentioned or from context).
    - get_report: User wants a report. Needs a job_id. (Currently basic)
    - set_context: User is trying to specify which job ID to focus on. Needs a job_id.
    - get_help: User is asking for help or instructions.
    - greeting: User is saying hello or similar.
    - clarification: User message is too ambiguous or missing essential info (e.g., needs job_id but none provided/in context).
    - unknown: The intent is unrelated or completely unclear.

    Extracted Entities:
    - job_id: Specific job identifier (e.g., "DEV001", "MKTG-02"). Return null if not clearly mentioned.
    - applicant_email: Applicant's email address. Return null if not mentioned.
    - applicant_name: Applicant's name (e.g., "Adrija Ghosh", "John Doe"). Return null if not mentioned.

    Instructions:
    1. If the user refers to "this job", "current job", "here", etc., and a context Job ID is available, assume intent relates to that context ID, but DO NOT extract it as `job_id` unless they also state the ID explicitly.
    2. If the user asks for a general overview ('status of listings', 'how are jobs going?'), the intent is 'get_overview' but job_id should be null.
    3. If essential info is missing (e.g., needs job_id but none provided/in context, needs name/email but none provided), set intent to `clarification`.

    Respond ONLY with a valid JSON object containing 'intent' (string) and 'entities' (object containing 'job_id', 'applicant_email', 'applicant_name', using null for missing values). No explanations or markdown.

    User Message:
    ---
    {{user_message}}
    ---

    JSON Output:
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    print("\n--- Sending HR chat message to Gemini LLM for NLU ---")
    raw_response = ""
    default_nlu_error = {"error": "Failed to understand message", "intent": "unknown", "entities": {"job_id": None, "applicant_email": None, "applicant_name": None}}
    try:
        response = chain.invoke({"user_message": user_message})
        raw_response = response
        # print(f"--- Gemini raw response (NLU): ---\n{response}") # Less verbose
        json_str = clean_json_response(response)
        if json_str:
            try:
                parsed_json = json.loads(json_str)
                if not isinstance(parsed_json, dict) or 'intent' not in parsed_json or 'entities' not in parsed_json:
                    raise ValueError("Missing required keys 'intent' or 'entities'.")
                if not isinstance(parsed_json.get('entities'), dict):
                     raise ValueError("'entities' key is not a dictionary.")
                entities_dict = parsed_json.get('entities', {})
                parsed_json['entities'] = {
                    'job_id': entities_dict.get('job_id'),
                    'applicant_email': entities_dict.get('applicant_email'),
                    'applicant_name': entities_dict.get('applicant_name')
                }
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
        traceback.print_exc()
        return {**default_nlu_error, "error": "Failed to understand message with Gemini", "details": str(e), "raw_response": raw_response}

def generate_ranking_highlights(top_candidates_data, job_context):
    """Uses Gemini LLM to generate a 1-sentence highlight for each top candidate."""
    if not analyzer_llm: return {"error": "Gemini LLM (analyzer) not available."}
    if not top_candidates_data: return {}

    candidates_input_str = ""
    for i, candidate in enumerate(top_candidates_data):
        summary = candidate.get('summary', 'No summary available.')
        candidates_input_str += f"\nCandidate {i+1}:\n"
        candidates_input_str += f"  Name: {candidate.get('name', candidate.get('applicant_id'))}\n"
        candidates_input_str += f"  ID: {candidate.get('applicant_id')}\n" # Use ID as key
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
        # print("--- Gemini raw response (Highlights): ---") # Less verbose
        # print(response)
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
        print("\n=== Testing Gemini: Resume Structuring (Refined) ===")
        # Use Suresh Menon example text
        test_resume_text = """
Suresh Menon
+51 517 6389 | suresh.menon@email.com
Austin, USA | linkedin.com/in/suresh-menon-fake229 | github.com/suresh-menon90
SUMMARY
Mid-Level Computer Vision Engineer (4+ years) with expertise in Generative AI, Automation. Proven ability to
implement complex AI/ML models. Seeking a challenging role leveraging skills in spaCy.
WORK EXPERIENCE
Mid-Level AI Product Manager | Alpha AI Solutions
Jan 2024 - Present | Paris, France
- Implemented Keras using VS Code, used by X users/teams.
- Analyzed PyTorch using Apache Spark, deployed successfully to production environment.
- Analyzed Hugging Face Transformers using Python, contributing to project success.
- Optimized PyTorch using Go, resulting in 15% improvement in latency.
AI Product Manager | Aether Systems
Mar 2021 - Jan 2024 | Chennai, India
- Built NumPy using Java, deployed successfully to production environment.
- Designed NLTK using Scala, contributing to project success.
- Researched Causal Inference using Apache Spark, enhancing latency by 45%.
- Implemented Feature Engineering using Looker, deployed successfully to production environment.
PROJECTS
Demand Forecasting System | Tech: Snowflake, Tableau, GitHub Actions
- Implemented incubate leading-edge supply-chains reducing processing time.
Medical Image Segmentation System | Tech: spaCy, Apache Spark, Dask, Hugging Face Transformers
- Implemented utilize web-enabled architectures handling Z data points.
- Achieved utilize vertical deliverables reducing processing time.
Predictive Maintenance System | Tech: Dask, Polars, Keras
- Designed reinvent viral e-business improving X by Y%.
- Achieved expedite 24/365 markets published/presented results.
EDUCATION
M.S., Computer Science
IIT Kanpur | Vizcaya, Belgium
Graduation: 2020 - 2022 | 3.58/4.0 GPA
B.Tech, Statistics
University of Hyderabad | ???, Faroe Islands
Graduation: 2016 - 2020 | 3.53/4.0 GPA
TECHNICAL SKILLS
Languages: MATLAB, R, JavaScript
Technologies/Frameworks:Dask, Statsmodels, NumPy, spaCy, LightGBM, Keras, Pandas, Hugging Face
Transformers
Tools/Platforms: Git, VS Code, Redis, Kafka, Airflow
Concepts/Domains: Recommender Systems, IoT, Automation, Signal Processing, A/B Testing, Generative AI
CERTIFICATIONS
- DataCamp - Python for Everybody (2024)
- DeepLearning.AI - AI Engineer Associate (2023)
- NPTEL - Cloud Practitioner (2025)
ACCOMPLISHMENTS / AWARDS
- Best Paper Award at Robotics Intl., 2022
- Poster Presentation Award at Data Science Con, 2025
- Poster Presentation Award at Robotics Intl., 2023
- Hackathon Winner at Clark, Richard and Tran Challenge, 2020
LANGUAGES
German (Basic), Telugu (Native)
        """
        structured_result = structure_resume_text(test_resume_text)
        print("\nStructured Resume Result (Suresh Menon):")
        print(json.dumps(structured_result, indent=2))
        # Basic Assertions
        if 'error' not in structured_result:
            assert structured_result.get('name') == "Suresh Menon", "Name extraction failed"
            assert structured_result.get('contact_info', {}).get('email') == "suresh.menon@email.com", "Email extraction failed"
            assert len(structured_result.get('experience', [])) > 0, "Experience extraction failed"
            assert len(structured_result.get('education', [])) > 0, "Education extraction failed"
            assert len(structured_result.get('skills', [])) > 0, "Skills extraction failed"
            print("Basic structure assertions passed.")
        else:
            print(f"Structuring failed: {structured_result.get('error')}")


        # ... (Keep existing tests for structure_job_description, rate_resume_against_jd, summarize_text_contextually, understand_hr_chat_intent, generate_ranking_highlights, to_5_star) ...