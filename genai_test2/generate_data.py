import random
import os
import zipfile
import time
from faker import Faker
from fpdf import FPDF
import datetime # For DOB generation

# --- Configuration & Data Lists (EXPAND THESE SIGNIFICANTLY) ---
NUM_CVS = 100
NUM_JEDIS = 15
OUTPUT_CV_DIR = "fake_cvs_pdf_std_fonts" # New output folder name
OUTPUT_JEDI_DIR = "fake_jedis_txt"

# Initialize Faker
fake = Faker(['en_IN', 'en_US', 'en_GB', 'zh_CN', 'de_DE', 'fr_FR', 'es_ES'])

# --- Data Lists (Expand these for better variety) ---
# (Keeping the previous lists, you should still expand them)
indian_names = ["Priya Sharma", "Rohan Kumar", "Ananya Reddy", "Vikram Singh", "Meera Iyer", "Arjun Gupta", "Sneha Patel", "Aditya Nair", "Fatima Begum", "Manpreet Kaur", "Siddharth Joshi", "Deepika Rao", "Amit Banerjee", "Kavita Desai", "Rahul Verma", "Pooja Agarwal", "Suresh Menon", "Lakshmi Iyer"]
foreign_names = ["Li Wei", "Kenji Tanaka", "Maria Garcia", "Ahmed Hassan", "Sophie Muller", "John Smith", "Emily White", "Alex Ivanov", "Fatima Rossi", "Chen Yu", "Hans Gruber", "Chloe Dubois", "David Lee", "Olga Petrova", "Yuki Sato", "Mohammed Al Fayed"] # Removed umlaut from Muller
all_names = indian_names * 5 + foreign_names

companies = ["Alpha AI Solutions", "Beta Analytics", "Gamma Innovations", "DataWeave Solutions", "OmniCorp AI", "Spectra Dynamics", "QuantumLeap AI", "Horizon Robotics", "CogniLink Systems", "Innovatech Labs", "Nexus Data Co.", "Vertex ML Group", "Aether Systems", "Synergy AI", "InfraData Corp", "LogicFlow Tech"]

job_titles = ["Machine Learning Engineer", "Data Scientist", "AI Researcher", "Computer Vision Engineer", "NLP Engineer", "MLOps Engineer", "AI Product Manager", "Data Analyst", "Research Scientist", "Deep Learning Engineer", "AI Consultant", "Analytics Engineer", "Robotics Engineer (AI)", "Software Engineer - AI/ML"]
seniority = ["Junior", "Mid-Level", "", "Senior", "Lead", "Principal", "Staff", "Intern"]

locations = ["Bangalore, India", "Hyderabad, India", "Pune, India", "Gurgaon, India", "Chennai, India", "Mumbai, India", "Remote (India)", "Berlin, Germany", "London, UK", "Singapore", "Shanghai, China", "San Francisco Bay Area, USA", "New York, USA", "Paris, France", "Toronto, Canada", "Austin, USA", "Dublin, Ireland"]

prog_languages = ["Python", "R", "Java", "C++", "SQL", "Scala", "Go", "JavaScript", "Bash", "MATLAB", "Embedded C"]
ml_libs = ["PyTorch", "TensorFlow", "Keras", "Scikit-learn", "Pandas", "NumPy", "XGBoost", "LightGBM", "CatBoost", "spaCy", "NLTK", "Hugging Face Transformers", "OpenCV", "LangChain", "Statsmodels", "SciPy", "Polars", "Dask"]
tools_platforms = ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Kubeflow", "MLflow", "Airflow", "Git", "GitHub Actions", "Jenkins", "Apache Spark", "Databricks", "Snowflake", "Tableau", "Power BI", "Looker", "Kafka", "Redis", "Linux", "STM32 CubeMX", "Arduino IDE", "VS Code"]
concepts = ["Deep Learning", "NLP", "Computer Vision", "Recommender Systems", "MLOps", "Reinforcement Learning", "Statistical Modeling", "Time Series Analysis", "Causal Inference", "XAI", "Generative AI", "LLMs", "A/B Testing", "Data Warehousing", "Feature Engineering", "AI Ethics", "IoT", "Embedded Systems", "Signal Processing", "Automation"]

degrees = ["B.Tech", "B.Eng", "B.Sc", "B.E.", "M.Tech", "M.S.", "M.Sc", "M.Eng", "Ph.D."]
majors = ["Computer Science", "AI", "Machine Learning", "Data Science", "Statistics", "Computer Eng", "Electrical Eng", "Mathematics", "Physics", "Computational Linguistics", "Robotics", "Electronics & Comm"]
universities_india = ["IIT Bombay", "IIT Delhi", "IISc Bangalore", "IIT Madras", "IIT Kanpur", "IIT Kharagpur", "NIT Warangal", "IIIT Hyderabad", "BITS Pilani", "University of Hyderabad", "Anna University", "Jadavpur University", "VIT Vellore", "Manipal Inst. of Tech."]
universities_foreign = ["Stanford", "MIT", "Carnegie Mellon", "UC Berkeley", "ETH Zurich", "Cambridge", "Oxford", "NUS", "Tsinghua University", "University of Toronto", "EPFL", "Max Planck", "Georgia Tech", "Imperial College London"]

project_areas = ["Demand Forecasting", "Image Classification", "Sentiment Analysis", "Autonomous Drone Navigation", "Smart Home Automation", "Predictive Maintenance", "Chatbot Development", "Anomaly Detection", "Stock Price Prediction", "Personalized Recommendation Engine", "Medical Image Segmentation", "Object Detection in Videos"]
award_types = ["Best Paper Award", "Hackathon Winner", "Innovation Challenge Winner", "Top Project Award", "Dean's List", "Scholarship Recipient", "Coding Competition Top 3", "Poster Presentation Award"]
conference_names = ["NeurIPS", "ICML", "CVPR", "ACL", "EMNLP", "AI Dev Summit", "Data Science Con", "Robotics Intl.", "Local Tech Meetup"]
certification_providers = ["Coursera", "Udacity", "edX", "AWS", "Google Cloud", "Azure", "DeepLearning.AI", "NPTEL", "DataCamp"]
certification_topics = ["Machine Learning", "Deep Learning Specialization", "NLP Specialization", "Data Science Professional Certificate", "Cloud Practitioner", "AI Engineer Associate", "TensorFlow Developer", "Python for Everybody"]
spoken_languages = ["English", "Hindi", "Bengali", "Tamil", "Telugu", "Marathi", "German", "French", "Spanish", "Mandarin", "Japanese"]
language_levels = ["Native", "Fluent", "Proficient", "Intermediate", "Basic", "Working Knowledge"]

# --- Helper Function for Encoding ---
def safe_encode(text):
    """Encodes text to latin-1, replacing unsupported characters."""
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- PDF Helper Class (using Standard Fonts) ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No font loading needed, defaults to standard fonts like Arial/Helvetica
        self.set_font('Arial', '', 10) # Set default

    def header(self):
        pass

    def footer(self):
        pass

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, safe_encode(title.upper()), 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, body_text):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, safe_encode(body_text))
        self.ln(1)

    def contact_info(self, text):
        self.set_font('Arial', '', 9)
        self.cell(0, 4, safe_encode(text), 0, 1, 'C')
        self.ln(1)

    def main_title(self, text):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 8, safe_encode(text), 0, 1, 'C')
        self.ln(2)

    def section_item_title(self, text):
        self.set_font('Arial', 'B', 10)
        self.multi_cell(0, 5, safe_encode(text))
        self.ln(1)

    def list_item(self, item_text, indent=0):
        self.set_font('Arial', '', 10)
        bullet = '-' # Use hyphen instead of bullet
        text_to_write = f'{bullet}  {item_text}'
        if indent > 0:
            self.cell(indent * 5)
        self.multi_cell(0, 5, safe_encode(text_to_write))
        self.ln(1)

    def skill_list(self, category, skills):
        self.set_font('Arial', 'B', 10)
        self.cell(35, 5, safe_encode(f'{category}:'), 0, 0)
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, safe_encode(", ".join(skills)))
        self.ln(1)

# --- Generation Helper Functions ---
# (These functions remain the same as the previous version, generating the data)
# generate_phone, generate_email, generate_linkedin, generate_github,
# generate_experience_details, generate_education_details, generate_skills_dict,
# generate_summary_or_objective, generate_projects, generate_accomplishments,
# generate_certifications, generate_languages_spoken
# ... (Include all the helper functions from the previous good version here) ...
# --- Generation Helper Functions (Copied from previous version) ---
def generate_phone():
    if random.random() < 0.75:
        return f"+91 {random.randint(6, 9)}{random.randint(100, 999)} {random.randint(10000, 99999)}"
    else:
         return f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}"

def generate_email(name):
    parts = name.lower().split()
    safe_parts = [p.replace('.', '') for p in parts]
    if len(safe_parts) > 1:
        return f"{safe_parts[0]}.{safe_parts[-1]}{random.choice(['', str(random.randint(1,99))])}@email.com"
    elif safe_parts:
        return f"{safe_parts[0]}{random.randint(1,99)}@email.com"
    else:
        return f"user{random.randint(1000,9999)}@email.com"

def generate_linkedin(name):
     parts = name.lower().replace(' ', '-').replace('.', '')
     return f"linkedin.com/in/{parts}-fake{random.randint(100,999)}"

def generate_github(name):
     parts = name.lower().replace(' ', '-').replace('.', '')
     return f"github.com/{parts}{random.randint(10,99)}"

def generate_experience_details(years_total):
    experiences = []
    remaining_years = years_total
    current_year = datetime.datetime.now().year
    if years_total == 0: return experiences

    num_jobs = random.randint(1, min(4, (years_total // 2) + 1))

    for i in range(num_jobs):
        if remaining_years <= 0: break
        min_duration = 1 if years_total > 1 else remaining_years
        max_duration = max(min_duration, remaining_years - (num_jobs - 1 - i) * min_duration) if i < num_jobs - 1 else remaining_years
        job_duration = random.randint(min_duration, max_duration) if i < num_jobs - 1 else remaining_years

        job_end_year = current_year - (years_total - remaining_years)
        job_start_year = job_end_year - job_duration
        job_end_str = "Present" if i == 0 else f"{random.choice(['Jan','Mar','Jun','Sep'])} {job_end_year}"
        job_start_str = f"{random.choice(['Jan','Mar','Jun','Sep'])} {job_start_year}"

        role_seniority = random.choice(seniority) if i == 0 or remaining_years > 2 else "Intern"
        job_title = f"{role_seniority} {random.choice(job_titles)}".strip()
        company = random.choice(companies)
        location = random.choice(locations)

        details = {
            "title_line": f"{job_title} | {company}",
            "date_location_line": f"{job_start_str} - {job_end_str} | {location}",
            "bullets": []
        }
        num_bullets = random.randint(2, 4)
        for _ in range(num_bullets):
            action = random.choice(["Led", "Developed", "Implemented", "Analyzed", "Designed", "Managed", "Collaborated on", "Optimized", "Built", "Researched", "Deployed", "Maintained"])
            task_area = random.choice(concepts + ml_libs)
            tech_used = random.choice(ml_libs + tools_platforms + prog_languages)
            impact_val = random.randint(5, 50)
            impact_metric = random.choice(["efficiency", "accuracy", "performance", "user engagement", "revenue", "cost reduction", "latency"])
            outcome = random.choice([
                f"resulting in {impact_val}% improvement in {impact_metric}",
                f"enhancing {impact_metric} by {impact_val}%",
                f"contributing to project success",
                f"deployed successfully to production environment",
                f"used by X users/teams"
            ])
            bullet = f"{action} {task_area} using {tech_used}, {outcome}."
            details["bullets"].append(bullet)

        experiences.append(details)
        remaining_years -= job_duration

    return experiences

def generate_education_details(max_level):
    education_list = []
    grad_year_phd, grad_year_ms, grad_year_bs = None, None, None
    current_year = datetime.datetime.now().year

    has_phd = max_level >= 2 and random.random() < 0.6
    has_masters = max_level >= 1 and (has_phd or random.random() < 0.8)
    has_bachelors = True

    if has_phd:
        grad_year_phd = random.randint(current_year - 5, current_year + 1)
        duration_phd = random.randint(3, 6)
        degree = "Ph.D."
        major = random.choice([m for m in majors if "AI" in m or "Machine Learning" in m or "Computer Science" in m or "Stats" in m])
        uni = random.choice(universities_india + universities_foreign)
        location = fake.city() + ", " + fake.country()
        grade = f"Thesis: '{fake.bs().title()}'"
        education_list.append({"degree_major": f"{degree}, {major}", "uni_location": f"{uni} | {location}", "grad_year": f"{grad_year_phd - duration_phd} - {grad_year_phd if grad_year_phd <= current_year else 'Present'}", "grade": grade})

    if has_masters:
        if grad_year_phd: grad_year_ms = grad_year_phd - duration_phd + random.randint(-1, 1)
        else: grad_year_ms = random.randint(current_year - 7, current_year)
        duration_ms = random.randint(1, 2)
        degree = random.choice(["M.Tech", "M.S.", "M.Sc", "M.Eng"])
        major = random.choice(majors)
        uni = random.choice(universities_india + universities_foreign)
        location = fake.city() + ", " + fake.country()
        grade_val = round(random.uniform(7.5, 10.0) if "India" in location else random.uniform(3.5, 4.0), 2)
        grade_suffix = "CGPA" if "India" in location else "GPA"
        grade = f"{grade_val}/{10.0 if 'India' in location else 4.0} {grade_suffix}"
        education_list.append({"degree_major": f"{degree}, {major}", "uni_location": f"{uni} | {location}", "grad_year": f"{grad_year_ms - duration_ms} - {grad_year_ms if grad_year_ms <= current_year else 'Present'}", "grade": grade})

    if has_bachelors:
        if grad_year_ms: grad_year_bs = grad_year_ms - duration_ms + random.randint(-1, 0)
        elif grad_year_phd: grad_year_bs = grad_year_phd - duration_phd - random.randint(1, 2)
        else: grad_year_bs = random.randint(current_year - 10, current_year - 3)
        duration_bs = 4
        degree = random.choice(["B.Tech", "B.Eng", "B.Sc", "B.E."])
        major = random.choice(majors)
        uni = random.choice(universities_india + universities_foreign)
        location = fake.city() + ", " + fake.country()
        grade_val = round(random.uniform(7.0, 9.8) if "India" in location else random.uniform(3.0, 3.9), 2)
        grade_suffix = "CGPA" if "India" in location else "GPA"
        grade = f"{grade_val}/{10.0 if 'India' in location else 4.0} {grade_suffix}"
        education_list.append({"degree_major": f"{degree}, {major}", "uni_location": f"{uni} | {location}", "grad_year": f"{grad_year_bs - duration_bs} - {grad_year_bs if grad_year_bs <= current_year else 'Present'}", "grade": grade})

    return education_list


def generate_skills_dict():
    num_prog = random.randint(3, 5)
    num_libs = random.randint(6, 10)
    num_tools = random.randint(5, 8)
    num_concepts = random.randint(6, 9)

    skills = {
        "Languages": random.sample(prog_languages, num_prog),
        "Technologies/Frameworks": random.sample(ml_libs, num_libs),
        "Tools/Platforms": random.sample(tools_platforms, num_tools),
        "Concepts/Domains": random.sample(concepts, num_concepts)
    }
    return skills

def generate_summary_or_objective(exp_years, main_skills):
    if exp_years < 1 and random.random() > 0.5:
        objective = f"Highly motivated and enthusiastic {random.choice(majors)} graduate seeking an entry-level {random.choice(job_titles)} position. Eager to apply strong foundation in {random.choice(main_skills)} and {random.choice(main_skills)} to contribute to innovative projects."
        return objective
    else:
        level_desc = "Recent graduate"
        title_choice = random.choice(job_titles)
        if 1 <= exp_years <= 2: level_desc = f"Junior {title_choice} ({exp_years} year{'s' if exp_years > 1 else ''})"
        elif 3 <= exp_years <= 7: level_desc = f"Mid-Level {title_choice} ({exp_years}+ years)"
        elif exp_years > 7: level_desc = f"Senior {title_choice} ({exp_years}+ years)"

        summary = f"{level_desc} with expertise in {', '.join(random.sample(main_skills, min(len(main_skills), 2)))}. "
        summary += f"Proven ability to {random.choice(['develop', 'implement', 'analyze', 'manage', 'deploy'])} complex {random.choice(['AI/ML models', 'data pipelines', 'software systems'])}. "
        summary += f"Seeking a challenging role leveraging skills in {random.choice(main_skills)}."
        return summary.replace("  ", " ")

def generate_projects(num_projects=random.randint(1, 3)):
    projects = []
    for _ in range(num_projects):
        area = random.choice(project_areas)
        tech = random.sample(ml_libs + tools_platforms + prog_languages, random.randint(2, 4))
        proj = {
            "title": f"{area} System" if "System" not in area else area,
            "tech": ", ".join(tech),
            "bullets": []
        }
        num_bullets = random.randint(1, 3)
        for _ in range(num_bullets):
            action = random.choice(["Developed", "Implemented", "Designed", "Built", "Achieved"])
            feature = fake.bs()
            outcome = random.choice(["improving X by Y%", "handling Z data points", "reducing processing time", "demonstrating feasibility", "published/presented results"])
            proj["bullets"].append(f"{action} {feature} {outcome}.")
        projects.append(proj)
    return projects

def generate_accomplishments(num_accomp=random.randint(0, 4)):
    accomplishments = []
    for _ in range(num_accomp):
        year = random.randint(datetime.datetime.now().year - 5, datetime.datetime.now().year)
        award = random.choice(award_types)
        event = random.choice(conference_names) if "Award" in award or "Presentation" in award else fake.company() + " Challenge"
        accomplishments.append(f"{award} at {event}, {year}")
    return accomplishments

def generate_certifications(num_certs=random.randint(0, 3)):
    certs = []
    for _ in range(num_certs):
        year = random.randint(datetime.datetime.now().year - 3, datetime.datetime.now().year)
        provider = random.choice(certification_providers)
        topic = random.choice(certification_topics)
        certs.append(f"{provider} - {topic} ({year})")
    return certs

def generate_languages_spoken(num_langs=random.randint(1, 3)):
    langs = {}
    picked_langs = random.sample(spoken_languages, num_langs)
    for lang in picked_langs:
        level = "Native" if lang in ["English", "Hindi", "Bengali"] and random.random() > 0.3 else random.choice(language_levels)
        if lang == "English" and language_levels.index(level) < language_levels.index("Proficient"):
            level = random.choice(["Proficient", "Fluent", "Native"])
        langs[lang] = level
    if "English" not in langs and random.random() > 0.1:
        langs["English"] = random.choice(["Fluent", "Proficient", "Native"])
    return langs
# --- End of Helper Functions ---


# --- Generation Loop: CVs (PDF) ---
os.makedirs(OUTPUT_CV_DIR, exist_ok=True)
print(f"Generating {NUM_CVS} CVs in PDF format (using Standard fonts)...")

for i in range(NUM_CVS):
    pdf_creation_success = False
    name = "Unknown Candidate" # Default name in case of error
    try:
        name = random.choice(all_names)
        email = generate_email(name)
        phone = generate_phone()
        linkedin = generate_linkedin(name)
        github = generate_github(name) if random.random() > 0.3 else None
        location = random.choice(locations)

        experience_years = random.randint(0, 15)
        max_education_level = 0
        if experience_years >= 1 or random.random() > 0.3: max_education_level = 1
        if experience_years >= 4 and random.random() > 0.5: max_education_level = 2

        skills_dict = generate_skills_dict()
        primary_skills = random.sample(skills_dict["Concepts/Domains"] + skills_dict["Technologies/Frameworks"], random.randint(3, 5))
        summary_text = generate_summary_or_objective(experience_years, primary_skills)

        education_details = generate_education_details(max_education_level)
        experience_details = generate_experience_details(experience_years)
        project_details = generate_projects()
        accomplishments = generate_accomplishments()
        certifications = generate_certifications()
        languages_spoken = generate_languages_spoken()

        # --- PDF Generation ---
        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(15, 15, 15)

        # Header
        pdf.main_title(name)
        contact_line1 = f"{phone} | {email}"
        contact_line2 = f"{location}"
        if linkedin: contact_line2 += f" | {linkedin}"
        if github: contact_line2 += f" | {github}"
        pdf.contact_info(contact_line1)
        pdf.contact_info(contact_line2)
        pdf.ln(5)

        # Summary / Objective
        pdf.chapter_title('Summary' if experience_years >= 1 or random.random() < 0.5 else 'Objective')
        pdf.chapter_body(summary_text)
        pdf.ln(3)

        # Experience
        if experience_details:
            pdf.chapter_title('Work Experience')
            for exp in experience_details:
                pdf.section_item_title(exp["title_line"])
                pdf.set_font('Arial', '', 9) # Smaller font for date/location
                pdf.cell(0, 4, safe_encode(exp["date_location_line"]), 0, 1)
                pdf.ln(1)
                for bullet in exp["bullets"]:
                    pdf.list_item(bullet) # list_item handles encoding
                pdf.ln(2)
            pdf.ln(1)

        # Projects
        if project_details:
            pdf.chapter_title('Projects')
            for proj in project_details:
                 pdf.section_item_title(f"{proj['title']} | Tech: {proj['tech']}")
                 for bullet in proj["bullets"]:
                     pdf.list_item(bullet) # list_item handles encoding
                 pdf.ln(2)
            pdf.ln(1)

        # Education
        if education_details:
            pdf.chapter_title('Education')
            for edu in education_details:
                 pdf.section_item_title(edu["degree_major"])
                 pdf.set_font('Arial', '', 10)
                 pdf.cell(0, 5, safe_encode(edu["uni_location"]), 0, 1)
                 pdf.cell(0, 5, safe_encode(f"Graduation: {edu['grad_year']} | {edu['grade']}"), 0, 1)
                 pdf.ln(2)
            pdf.ln(1)

        # Technical Skills
        if skills_dict:
            pdf.chapter_title('Technical Skills')
            for category, skill_list in skills_dict.items():
                pdf.skill_list(category, skill_list) # skill_list handles encoding
            pdf.ln(3)

        # Certifications
        if certifications:
            pdf.chapter_title('Certifications')
            for cert in certifications:
                 pdf.list_item(cert) # list_item handles encoding
            pdf.ln(3)

        # Accomplishments
        if accomplishments:
             pdf.chapter_title('Accomplishments / Awards')
             for accomp in accomplishments:
                  pdf.list_item(accomp) # list_item handles encoding
             pdf.ln(3)

        # Languages Spoken
        if languages_spoken:
            pdf.chapter_title('Languages')
            lang_str = ", ".join([f"{lang} ({level})" for lang, level in languages_spoken.items()])
            pdf.chapter_body(lang_str) # chapter_body handles encoding
            pdf.ln(3)


        # Save PDF
        safe_lastname = name.split()[-1].replace('.', '').replace('/', '') if name.split() else 'Unknown'
        filename = os.path.join(OUTPUT_CV_DIR, f"cv_{i+1:03d}_{safe_lastname}.pdf")
        # Output with fallback encoding for the entire file content if needed,
        # although individual elements are already encoded.
        # This is less critical now but kept as a safety net.
        pdf.output(filename, "F") # 'F' mode might be slightly more robust for standard fonts
        pdf_creation_success = True

    except Exception as e:
        print(f"ERROR generating or saving PDF for candidate {i+1} ({name}): {e}")
        if not pdf_creation_success and 'filename' in locals() and os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"  Removed potentially corrupt file: {filename}")
            except OSError as oe:
                print(f"  Warning: Could not remove partial file {filename}: {oe}")


print(f"Finished generating CVs.")

# --- Generation Loop: JEDIs (TXT) ---
# (This part remains the same as the previous version - TXT files don't have font issues)
# ... (Include the JEDI generation loop and zipping logic from the previous good version here) ...
# --- Generation Loop: JEDIs (TXT) ---
os.makedirs(OUTPUT_JEDI_DIR, exist_ok=True)
print(f"Generating {NUM_JEDIS} JEDIs in TXT format...")

for i in range(NUM_JEDIS):
    try:
        title = f"{random.choice(seniority)} {random.choice(job_titles)}".strip()
        company = random.choice(companies)
        location = random.choice(locations)
        job_type = random.choice(["Full-time", "Contract", "Full-time, Hybrid", "Internship"])

        core_concept = random.choice(concepts)
        related_skills = random.sample(ml_libs + tools_platforms + prog_languages + concepts, random.randint(8, 15))
        req_skills = random.sample(related_skills, random.randint(4, 6))
        pref_skills = random.sample([s for s in related_skills if s not in req_skills], random.randint(3, 5))

        min_exp = random.choice([0, 1, 2, 3, 5, 7, 10])
        req_edu_level_idx = random.choices([0, 1, 2], weights=[0.4, 0.5, 0.1], k=1)[0]
        req_edu_levels = ["B.S./B.Tech", "M.S./M.Tech", "Ph.D."]
        req_edu_level = req_edu_levels[req_edu_level_idx]
        req_edu_field = random.choice(majors)

        jedi_content = f"**Job Title:** {title}\n"
        jedi_content += f"**Company:** {company}\n"
        jedi_content += f"**Location:** {location}\n"
        jedi_content += f"**Job Type:** {job_type}\n\n"

        jedi_content += f"**About {company}:**\n{company} is a {random.choice(['dynamic startup', 'leading tech firm', 'global innovator'])} focused on leveraging AI to {random.choice(['solve complex challenges', 'drive business value', 'transform industries'])} in the {random.choice(['finance', 'healthcare', 'e-commerce', 'logistics', 'SaaS', 'robotics'])} sector. We offer a collaborative and fast-paced environment where you can make a real impact.\n\n"
        jedi_content += f"**Role Summary:**\nWe are seeking a talented and motivated {title} to join our growing team. In this role, you will be responsible for {random.choice(['designing, developing, and deploying', 'researching and implementing', 'building and scaling'])} state-of-the-art AI/ML solutions, with a potential focus on {core_concept}.\n\n"

        jedi_content += "**Key Responsibilities:**\n"
        for _ in range(random.randint(4, 6)):
            resp = random.choice([
                f"Design, implement, and evaluate machine learning models for {random.choice(concepts)}.",
                f"Process, clean, and analyze large-scale datasets using tools like {random.choice(tools_platforms)} and {random.choice(prog_languages)}.",
                f"Collaborate effectively with product managers, software engineers, and other data scientists/researchers.",
                f"Develop and maintain robust data pipelines and MLOps infrastructure.",
                f"Stay current with the latest research papers and technological advancements in AI/ML.",
                f"Conduct experiments and A/B tests to validate hypotheses and improve model performance.",
                f"Communicate findings, results, and technical details clearly to both technical and non-technical audiences."
            ])
            jedi_content += f"*   {resp}\n"
        jedi_content += "\n"

        jedi_content += "**Required Qualifications:**\n"
        jedi_content += f"*   {req_edu_level} in {req_edu_field} or a closely related quantitative field (e.g., Physics, Operations Research).\n"
        if min_exp > 0:
            jedi_content += f"*   {min_exp}+ years of relevant industry experience in {random.choice(['Machine Learning', 'Data Science', 'AI Research', 'Software Engineering (ML)'])}.\n"
        else:
            jedi_content += f"*   Strong portfolio showcasing relevant projects (academic, personal, internships) in AI/ML.\n"

        core_lang = random.choice([s for s in req_skills if s in prog_languages] or ['Python'])
        jedi_content += f"*   Proficiency in at least one programming language such as {core_lang}.\n"

        req_skill_subset = random.sample([s for s in req_skills if s not in prog_languages], min(len(req_skills)-1, random.randint(3,5)))
        # Ensure list is not empty before sampling
        ml_libs_in_subset = [s for s in req_skill_subset if s in ml_libs]
        if ml_libs_in_subset:
            libs_to_mention = random.sample(ml_libs_in_subset, min(len(ml_libs_in_subset), random.randint(1,3)))
            jedi_content += f"*   Hands-on experience with core ML libraries/frameworks (e.g., {', '.join(libs_to_mention)}).\n"
        else:
            jedi_content += f"*   Hands-on experience with core ML libraries/frameworks.\n" # Generic fallback

        jedi_content += f"*   Solid understanding of fundamental machine learning algorithms and statistical concepts.\n"
        jedi_content += f"*   Strong analytical and problem-solving skills.\n"
        jedi_content += f"*   Excellent communication and teamwork abilities.\n\n"

        jedi_content += "**Preferred Qualifications:**\n"
        if req_edu_level_idx < 2:
            jedi_content += f"*   {req_edu_levels[req_edu_level_idx+1]} or {req_edu_levels[2]} preferred.\n"
        if min_exp < 10 :
             jedi_content += f"*   {min_exp + random.randint(2,5)}+ years of experience.\n"
        for skill in pref_skills:
            jedi_content += f"*   Experience or familiarity with {skill}.\n"
        if random.random() > 0.5: jedi_content += f"*   Experience with cloud platforms (AWS, Azure, or GCP).\n"
        if random.random() > 0.5: jedi_content += f"*   Experience with big data technologies (e.g., Spark, Hadoop).\n"
        if random.random() > 0.4: jedi_content += f"*   Publications in top-tier AI/ML conferences or journals.\n"
        if random.random() > 0.4: jedi_content += f"*   Contributions to relevant open-source projects.\n"
        if random.random() > 0.5: jedi_content += f"*   Experience working in an Agile development environment.\n"


        safe_title = title.replace(' ', '_').replace('/', '_').replace('.', '').replace('(','').replace(')','')
        filename = os.path.join(OUTPUT_JEDI_DIR, f"jedi_{i+1:02d}_{safe_title[:30]}.txt")
        with open(filename, "w", encoding="utf-8") as f: # UTF-8 is fine for TXT
            f.write(jedi_content)

    except Exception as e:
         print(f"ERROR generating or writing JEDI {i+1}: {e}")


print(f"Finished generating JEDIs.")

# --- Zipping ---
timestamp = time.strftime("%Y%m%d-%H%M%S")

def zip_directory(folder_path, zip_path):
    print(f"Creating zip file: {zip_path} from folder: {folder_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            if root == folder_path: arc_dir = ''
            else: arc_dir = os.path.relpath(root, folder_path)

            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.join(arc_dir, file)
                zipf.write(file_path, arcname=arc_name)

# Check directories and zip
if os.path.exists(OUTPUT_CV_DIR):
    if any(f.endswith('.pdf') for f in os.listdir(OUTPUT_CV_DIR)):
        cv_zip_filename = f"{OUTPUT_CV_DIR}_{timestamp}.zip" # Changed zip filename
        zip_directory(OUTPUT_CV_DIR, cv_zip_filename)
        print(f"Created CV PDF zip file: {cv_zip_filename}")
    else:
        print(f"Skipping CV zip creation, directory '{OUTPUT_CV_DIR}' contains no PDF files.")
else:
    print(f"Skipping CV zip creation, directory '{OUTPUT_CV_DIR}' not found.")

if os.path.exists(OUTPUT_JEDI_DIR):
    if any(f.endswith('.txt') for f in os.listdir(OUTPUT_JEDI_DIR)):
        jedi_zip_filename = f"{OUTPUT_JEDI_DIR}_{timestamp}.zip" # Changed zip filename
        zip_directory(OUTPUT_JEDI_DIR, jedi_zip_filename)
        print(f"Created JEDI TXT zip file: {jedi_zip_filename}")
    else:
        print(f"Skipping JEDI zip creation, directory '{OUTPUT_JEDI_DIR}' contains no TXT files.")
else:
     print(f"Skipping JEDI zip creation, directory '{OUTPUT_JEDI_DIR}' not found.")

print("Script finished.")
