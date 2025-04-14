import os
import time
import re
import pymongo
import collections
from dotenv import load_dotenv
import google.generativeai as genai
from bson import ObjectId
# Load environment variables
load_dotenv()
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not MONGO_DB_URI or not GOOGLE_API_KEY:
    raise EnvironmentError("MONGO_DB_URI and GOOGLE_API_KEY must be set in the environment.")

# Configure the Google Generative AI (Gemini) library
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# Setup MongoDB client and collections
mongo_client = pymongo.MongoClient(MONGO_DB_URI)
db = mongo_client.get_default_database()
applications_collection = db["applications"]
jobposts_collection = db["jobposts"]

def tokenize(text: str) -> list:
    """Tokenizes text into lowercase words."""
    return re.findall(r'\w+', text.lower())

def generate_ai_analysis(resume_text: str, job_text: str) -> dict:
    """
    Generates an in-depth AI analysis for the candidate.
    The prompt asks for detailed evaluation across several aspects.
    Returns a dictionary with keys:
      - technical_match (percentage)
      - missing_skills (list)
      - soft_skills (rating with explanation)
      - seniority (assessment)
      - suggestions (list of actionable improvement suggestions)
      - detailed_strengths (in-depth analysis of candidate strengths)
      - detailed_weaknesses (in-depth analysis of candidate weaknesses)
      - overall_analysis (overall candidate evaluation summary)
    """
    prompt = f"""Analyze candidate suitability for the job in depth. Evaluate technical skill overlap as a percentage. Provide a detailed analysis of the candidate's strengths including specifics about relevant project experience, certifications, and technical nuances that match the job requirements. Identify missing qualifications as a comma-separated list. Evaluate the candidate's soft skills and rate them (excellent, good, moderate, poor) with a brief explanation. Assess the seniority level (junior, mid, senior, executive) based on the resume details and job requirements. Give improvement suggestions as a numbered list with detailed actionable advice.
    
    Also, provide:
    - Detailed Strengths Analysis: a descriptive qualitative analysis of the candidate's notable strengths.
    - Detailed Weaknesses Analysis: a descriptive qualitative analysis of the candidate's shortcomings.
    - Overall Candidate Analysis: a comprehensive summary of how well the candidate fits the role, listing pros and cons.

    Resume Excerpt:
    {resume_text[:3000]}

    Job Description Excerpt:
    {job_text[:3000]}

    Provide your answer strictly in this structured format (without any extra text):

    Technical Skills Match: [percentage]%
    Missing Qualifications: [item1, item2, ...]
    Soft Skill Alignment: [rating with explanation]
    Seniority Assessment: [level]
    Improvement Suggestions:
    1. [detailed suggestion]
    2. [detailed suggestion]
    Detailed Strengths Analysis: [detailed text]
    Detailed Weaknesses Analysis: [detailed text]
    Overall Candidate Analysis: [detailed text]"""

    try:
        response = gemini_model.generate_content(prompt)
        if not response.text:
            return {}
            
        # Initialize analysis dictionary with defaults
        analysis = {
            "technical_match": 0,
            "missing_skills": [],
            "soft_skills": "N/A",
            "seniority": "N/A",
            "suggestions": [],
            "detailed_strengths": "",
            "detailed_weaknesses": "",
            "overall_analysis": ""
        }

        # Extract values using regex
        if match := re.search(r"Technical Skills Match:\s*(\d+)%", response.text):
            analysis["technical_match"] = int(match.group(1))
        if missing := re.search(r"Missing Qualifications:\s*\[(.*?)\]", response.text):
            analysis["missing_skills"] = [s.strip() for s in missing.group(1).split(",") if s.strip()]
        if soft := re.search(r"Soft Skill Alignment:\s*(.*)", response.text):
            analysis["soft_skills"] = soft.group(1).strip()
        if senior := re.search(r"Seniority Assessment:\s*(\w+)", response.text):
            analysis["seniority"] = senior.group(1).strip()
        if sugg := re.findall(r"\d+\.\s(.*)", response.text):
            analysis["suggestions"] = [s.strip() for s in sugg if s.strip()]
        if ds := re.search(r"Detailed Strengths Analysis:\s*(.*?)(?:Detailed Weaknesses Analysis:|$)", response.text, re.DOTALL):
            analysis["detailed_strengths"] = ds.group(1).strip()
        if dw := re.search(r"Detailed Weaknesses Analysis:\s*(.*?)(?:Overall Candidate Analysis:|$)", response.text, re.DOTALL):
            analysis["detailed_weaknesses"] = dw.group(1).strip()
        if oa := re.search(r"Overall Candidate Analysis:\s*(.*)", response.text, re.DOTALL):
            analysis["overall_analysis"] = oa.group(1).strip()

        return analysis
        
    except Exception as e:
        print(f"Gemini API error: {str(e)[:200]}")
        return {}

def comprehensive_analyze_candidate(resume_text: str, job_text: str) -> dict:
    """
    Computes a basic keyword match analysis and then refines it with in-depth AI analysis.
    Returns a dictionary including overall match percentage, basic strengths and weaknesses,
    recommendations, combined explanation, and the detailed AI analysis.
    """
    resume_tokens = tokenize(resume_text)
    job_tokens = tokenize(job_text)
    
    if not job_tokens:
        return {
            "matchPercentage": 0.0,
            "score": 0.0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "explanation": "Job posting text is empty; cannot perform evaluation.",
            "aiAnalysis": {}
        }
    
    job_counter = collections.Counter(job_tokens)
    resume_set = set(resume_tokens)
    job_set = set(job_tokens)
    
    common_words = resume_set.intersection(job_set)
    strengths = sorted(common_words, key=lambda w: job_counter[w], reverse=True)[:5]
    missing_words = job_set.difference(resume_set)
    weaknesses = sorted(missing_words, key=lambda w: job_counter[w], reverse=True)[:5]
    basic_match = (len(common_words) / len(job_set)) * 100
    
    # Get in-depth analysis using Gemini
    ai_analysis = generate_ai_analysis(resume_text, job_text)
    
    # Combine basic match with in-depth technical match if available
    combined_match = basic_match
    if ai_analysis.get("technical_match"):
        combined_match = (basic_match + ai_analysis["technical_match"]) / 2
        
    # Merge weaknesses from basic and AI analysis (limit to 5)
    if ai_analysis.get("missing_skills"):
        weaknesses = list(set(weaknesses + ai_analysis["missing_skills"]))[:5]
    
    recommendations = []
    for word in weaknesses:
        recommendations.append(f"Consider highlighting experience with '{word}'.")
    if ai_analysis.get("suggestions"):
        recommendations += ai_analysis["suggestions"][:3]
    
    explanation = (
        f"Basic keyword match: {basic_match:.1f}%\n"
        f"Key strengths: {', '.join(strengths)}\n"
        f"Missing skills: {', '.join(weaknesses)}\n\n"
        "In-depth AI Analysis:\n"
        f"- Technical Match: {ai_analysis.get('technical_match', 0)}%\n"
        f"- Soft Skills: {ai_analysis.get('soft_skills', 'N/A')}\n"
        f"- Seniority Assessment: {ai_analysis.get('seniority', 'N/A')}\n"
        f"- Detailed Strengths Analysis: {ai_analysis.get('detailed_strengths', '')}\n"
        f"- Detailed Weaknesses Analysis: {ai_analysis.get('detailed_weaknesses', '')}\n"
        f"- Overall Candidate Analysis: {ai_analysis.get('overall_analysis', '')}\n"
        f"- Suggestions: {' | '.join(ai_analysis.get('suggestions', []))}"
    )
    
    return {
        "matchPercentage": round(combined_match, 2),
        "score": round(combined_match, 2),
        "aiAnalysis": ai_analysis
    }

def process_application_for_ai_evaluation(application_doc: dict):
    """
    Processes an application document: extracts resume and job text,
    generates comprehensive AI evaluation, and updates the database record.
    """
    app_id = application_doc.get("_id")
    job_post_id = application_doc.get("jobPost")
    if not job_post_id:
        print(f"Application {app_id} is missing a jobPost reference. Skipping evaluation.")
        return

    if not application_doc.get("resume_details"):
        print(f"Application {app_id} does not have resume_details. Skipping evaluation.")
        return

    job_doc = jobposts_collection.find_one({"_id": job_post_id})
    if not job_doc:
        print(f"Job Post {job_post_id} not found for Application {app_id}. Skipping evaluation.")
        return

    job_text = f"{job_doc.get('title', '')}\n{job_doc.get('description', '')}".strip()
    resume_text = application_doc.get("resume_details", "").strip()

    if not job_text or not resume_text:
        print(f"Insufficient text for evaluation in Application {app_id}.")
        return

    print(f"Performing comprehensive analysis for Application {app_id} against Job Post {job_post_id}...")
    evaluation_result = comprehensive_analyze_candidate(resume_text, job_text)
    
    #************************************* MONGO DB PUSH *******************************************************
    update_result = applications_collection.update_one(
        {"_id": app_id},
        {"$set": {"aiEvaluation": evaluation_result}}
    )
    
    if update_result.modified_count:
        print(f"Application {app_id} successfully updated with comprehensive aiEvaluation.")
    else:
        print(f"Failed to update Application {app_id} with AI evaluation.")

if __name__ == "__main__":
    print("Starting the Comprehensive AI Evaluation Background Worker (Polling mode)...")
    while True:
        try:
            pending_apps = list(applications_collection.find({
                "resume_details": {"$exists": True, "$ne": None},
                "$or": [{"aiEvaluation": {"$exists": False}}, {"aiEvaluation": None}]
            }))

            if pending_apps:
                print(f"\nFound {len(pending_apps)} candidate(s) pending comprehensive AI evaluation.")
                for app in pending_apps:
                    process_application_for_ai_evaluation(app)
            else:
                print("No candidates pending comprehensive AI evaluation.")
        except Exception as e:
            print(f"Error in evaluation loop: {e}")
        
        time.sleep(1)
