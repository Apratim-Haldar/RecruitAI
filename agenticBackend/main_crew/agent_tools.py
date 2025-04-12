# agent_tools.py
from crewai.tools import BaseTool # Try importing from core crewai.tools module
import json
import os

# Import functions from our utility files
from file_utils import extract_text_from_file
# Assume llm_utils contains structure_resume_text, structure_job_description, rate_resume_against_jd, summarize_text_contextually
from llm_utils import structure_resume_text, structure_job_description, rate_resume_against_jd, summarize_text_contextually
# Assume database_utils contains init_db, get_structured_resume, get_structured_jd, get_top_applicants_for_job, get_resume_path
from database_utils import init_db, get_structured_resume, get_structured_jd, get_top_applicants_for_job, get_resume_path, add_applicant, add_application_rating

# Initialize DB schema when tools are loaded (ensures DB exists)
# Note: Consider if init_db should be called elsewhere in a real app setup
print("Initializing database from agent_tools.py...")
init_db()
print("Database initialization check complete.")


# --- Tool Definitions ---

class ResumeAnalysisTool(BaseTool):
    name: str = "Resume Text Extractor and Structurer"
    description: str = ("Extracts text from a resume file (PDF, DOCX, TXT...) located at the given 'file_path' "
                       "and then structures the extracted text into JSON format using an LLM. "
                       "Input MUST be a single string representing the valid file path to the resume.")

    def _run(self, file_path: str) -> dict:
        print(f"--- ResumeAnalysisTool: Running for file path: {file_path} ---")
        if not file_path or not isinstance(file_path, str):
             return {"error": "Invalid input. Tool expects a single string: the file path."}
             
        # 1. Extract text
        text = extract_text_from_file(file_path)
        if "Error:" in text or "Warning:" in text:
            print(f"Error/Warning during text extraction: {text}")
            # If extraction failed, we can't structure it
            return {"error": f"Failed to extract text: {text}"}

        # 2. Structure text using LLM
        print(f"Text extracted successfully (length: {len(text)}). Now structuring...")
        structured_data = structure_resume_text(text)

        # 3. Optionally: Save structured data back to the applicant profile?
        # This requires applicant_id. We might need separate tools or pass ID here.
        # For now, just return the structured data. It can be saved later if needed.
        print(f"Structuring complete. Result: {structured_data}")
        return structured_data


class JobDescriptionAnalysisTool(BaseTool):
    name: str = "Job Description Structurer"
    description: str = ("Structures raw job description text into JSON format using an LLM. "
                       "Input MUST be a single string containing the full job description text.")

    def _run(self, jd_text: str) -> dict:
        print("--- JobDescriptionAnalysisTool: Running ---")
        if not jd_text or not isinstance(jd_text, str):
             return {"error": "Invalid input. Tool expects a single string: the job description text."}
             
        structured_data = structure_job_description(jd_text)
        print(f"JD Structuring complete. Result: {structured_data}")
        return structured_data


class SuitabilityRatingTool(BaseTool):
    name: str = "Resume-Job Suitability Rater"
    description: str = ("Rates the suitability of a candidate for a job based on their structured resume "
                       "and the structured job description. "
                       "Input must be two arguments: "
                       "1. 'structured_resume_json': A JSON string representing the structured resume. "
                       "2. 'structured_jd_json': A JSON string representing the structured job description.")

    # Defining args_schema for clarity and potential validation by CrewAI
    # from pydantic.v1 import BaseModel, Field
    # class RatingArgsSchema(BaseModel):
    #     structured_resume_json: str = Field(..., description="JSON string of the structured resume")
    #     structured_jd_json: str = Field(..., description="JSON string of the structured job description")
    # args_schema: Type[BaseModel] = RatingArgsSchema

    # Modified _run to accept arguments more reliably
    def _run(self, structured_resume_json: str, structured_jd_json: str) -> dict:
        print("--- SuitabilityRatingTool: Running ---")
        try:
            # Parse JSON strings back into Python dictionaries
            resume_data = json.loads(structured_resume_json)
            jd_data = json.loads(structured_jd_json)
            print("Successfully parsed input JSON for rating.")
            # Call the LLM rating function from llm_utils
            rating_result = rate_resume_against_jd(resume_data, jd_data)
            print(f"Rating complete. Result: {rating_result}")
            return rating_result
        except json.JSONDecodeError as e:
             print(f"Error: Failed to parse input JSON for rating: {e}")
             # Provide a structured error response
             return {"error": f"Input JSON parsing error: {e}", "rating": 0, "summary": "Input Error", "fits": [], "lacks": []}
        except Exception as e:
            print(f"Unexpected error during rating: {e}")
            return {"error": f"Unexpected error: {e}", "rating": 0, "summary": "Processing Error", "fits": [], "lacks": []}

class ApplicantRankerTool(BaseTool):
    name: str = "Top Applicant Ranker"
    description: str = ("Retrieves a ranked list of the top N applicants for a specific job_id from the database, "
                       "based on previously calculated ratings. Input must be two arguments: 'job_id' (string) and 'n' (integer, number of applicants to return, defaults to 5).")

    def _run(self, job_id: str, n: int = 5) -> list:
        print(f"--- ApplicantRankerTool: Running for Job ID: {job_id}, Top N: {n} ---")
        if not job_id or not isinstance(job_id, str):
             return [{"error": "Invalid input. 'job_id' (string) is required."}] # Return list with error dict
        try:
             # Ensure n is an integer
             n = int(n)
             if n <= 0: n = 5 # Default to 5 if invalid number provided
        except ValueError:
             print("Warning: Invalid 'n' provided, defaulting to 5.")
             n = 5
             
        ranked_list = get_top_applicants_for_job(job_id, n)
        print(f"Ranking complete. Found {len(ranked_list)} applicants.")
        # Return the list of tuples: (applicant_id, name, rating)
        # Convert tuples to dicts for potentially easier handling by LLM? Optional.
        # return [{"applicant_id": r[0], "name": r[1], "rating": r[2]} for r in ranked_list]
        return ranked_list # Keep as list of tuples for now

class ApplicantSummarizerTool(BaseTool):
    name: str = "Applicant Contextual Summarizer"
    description: str = ("Generates a concise summary for a specific applicant's resume, tailored to the context "
                       "of a specific job description. Input must be two arguments: 'applicant_id' (string) and 'job_id' (string).")

    def _run(self, applicant_id: str, job_id: str) -> str:
        print(f"--- ApplicantSummarizerTool: Running for Applicant: {applicant_id}, Job: {job_id} ---")
        if not applicant_id or not job_id:
            return "Error: Both 'applicant_id' and 'job_id' are required inputs."

        # 1. Get structured resume and JD from DB
        print("Retrieving structured resume and JD from database...")
        structured_resume = get_structured_resume(applicant_id)
        structured_jd = get_structured_jd(job_id)

        if not structured_resume:
            return f"Error: Could not retrieve structured resume data for Applicant ID: {applicant_id}."
        if not structured_jd:
            return f"Error: Could not retrieve structured job description data for Job ID: {job_id}."
            
        # Option 1: Summarize based on structured data (might be less fluent)
        # resume_summary_input = json.dumps(structured_resume, indent=2)
        # jd_context_input = json.dumps(structured_jd, indent=2)

        # Option 2: Retrieve original text and summarize that (might be better)
        print("Retrieving original resume file path...")
        resume_file_path = get_resume_path(applicant_id)
        if not resume_file_path or not os.path.exists(resume_file_path):
             return f"Error: Could not find resume file path or file does not exist for Applicant ID: {applicant_id}."
        
        print("Extracting text from resume file for summarization...")
        resume_text = extract_text_from_file(resume_file_path)
        if "Error:" in resume_text or "Warning:" in resume_text:
             return f"Error: Failed to extract text from resume file {resume_file_path} for summarization."

        # Use structured JD as context, but original resume text as main text
        jd_context_input = json.dumps(structured_jd, indent=2) # Context is still the structured JD

        print("Generating contextual summary using LLM...")
        summary = summarize_text_contextually(text_to_summarize=resume_text, context_text=jd_context_input)
        print(f"Summarization complete. Result: {summary}")
        return summary
        
# --- Instantiate Tools for use by agents ---
resume_analyzer_tool = ResumeAnalysisTool()
jd_analyzer_tool = JobDescriptionAnalysisTool()
suitability_rater_tool = SuitabilityRatingTool()
applicant_ranker_tool = ApplicantRankerTool()
applicant_summarizer_tool = ApplicantSummarizerTool()

# Note: We might also need tools specifically for ADDING data via CrewAI,
# e.g., saving a structured resume/JD or a calculated rating back to the DB.
# These would call the respective `add_` functions from database_utils.

# Example (Not used in main crew yet, but shows pattern):
# class SaveRatingTool(BaseTool):
#    name: str = "Save Application Rating"
#    description: str = ("Saves the calculated suitability rating result to the database. "
#                       "Input must be three arguments: 'applicant_id', 'job_id', and 'rating_result_json'.")
#
#    def _run(self, applicant_id: str, job_id: str, rating_result_json: str) -> str:
#        print(f"--- SaveRatingTool: Running for A:{applicant_id}, J:{job_id} ---")
#        try:
#            rating_dict = json.loads(rating_result_json)
#            success = add_application_rating(applicant_id, job_id, rating_dict)
#            if success:
#                return f"Rating for Applicant {applicant_id} / Job {job_id} saved successfully."
#            else:
#                return f"Failed to save rating for Applicant {applicant_id} / Job {job_id}."
#        except json.JSONDecodeError as e:
#            return f"Error: Invalid JSON input for rating result: {e}"
#        except Exception as e:
#            return f"Error saving rating: {e}"

##```3.  **Save the file.**
##
##This file defines the `BaseTool` classes that CrewAI agents will use. Each class wraps one or more functions from our `file_utils`, `llm_utils`, and `database_utils` files, providing a clear `name` and `description` so the CrewAI framework and the underlying LLM know when and how to use them. I've added more print statements inside the `_run` methods for better debugging when we run the crew.
##
##**To Test `agent_tools.py` (Optional but recommended):**
##
##You can add a small `if __name__ == "__main__":` block at the end of this file to test individual tools, similar to how we tested the other utility files. For example, to test the `ResumeAnalysisTool`:
##
##```python
# Add this at the VERY END of agent_tools.py
if __name__ == "__main__":
    print("\n--- Testing Agent Tools ---")
    
    # Ensure sample_resume.txt exists from previous tests
    test_resume_path = "sample_resume.txt"
    if not os.path.exists(test_resume_path):
         print(f"ERROR: Cannot run test, {test_resume_path} not found.")
    else:
        print(f"\n--- Testing ResumeAnalysisTool with: {test_resume_path} ---")
        resume_tool_instance = ResumeAnalysisTool()
        structured_result = resume_tool_instance.run(file_path=test_resume_path) # Use .run() for testing
        print("\nResumeAnalysisTool Result:")
        print(json.dumps(structured_result, indent=2))
        
        # Example: Test Summarizer (requires data in DB from database_utils test)
        # print("\n--- Testing ApplicantSummarizerTool ---")
        # test_applicant_id = "APP001"
        # test_job_id = "TESTJOB001"
        # summarizer_instance = ApplicantSummarizerTool()
        # summary = summarizer_instance.run(applicant_id=test_applicant_id, job_id=test_job_id)
        # print("\nApplicantSummarizerTool Result:")
        # print(summary)
