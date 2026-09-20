import os
import json
import tempfile
import traceback
import re
from datetime import datetime, timezone

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber
from google import genai
from google.genai import types
from pymongo import MongoClient
import certifi

# ============================================================
# NEW IMPORTS FOR FEATURE: URL SCRAPER
# ============================================================
import requests
from bs4 import BeautifulSoup


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Resume Reviewer API",
    version="6.1.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CONFIGURATIONS (GEMINI & MONGODB)
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.6-flash"

MONGO_URI = os.getenv("MONGO_URI")

db_client = None
db = None
resume_reports_collection = None

# Initialize MongoDB Connection
if MONGO_URI:
    try:
        db_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        db = db_client["resume_ai_db"]
        resume_reports_collection = db["resume_reports"]
        print("MongoDB Connected Successfully.")
    except Exception as e:
        print(f"MongoDB Connection Error: {e}")


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AI Resume Reviewer API is running",
        "version": "6.1.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": GEMINI_MODEL,
        "gemini_configured": bool(API_KEY),
        "db_connected": bool(resume_reports_collection is not None)
    }


# ============================================================
# FEATURE: JOB URL SCRAPER
# ============================================================

def scrape_job_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted script, style, and nav tags to get clean text
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text[:5000] # Return up to 5000 characters
    except Exception as e:
        print(f"URL Scraping Error: {e}")
        return ""


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
    except Exception as e:
        raise RuntimeError(
            f"Failed to extract text from PDF: {str(e)}"
        )
    return "\n".join(text_parts).strip()


# ============================================================
# SAFE SCORE
# ============================================================

def safe_score(value):
    try:
        score = int(float(value))
        return max(0, min(100, score))
    except Exception:
        return 0


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):
    if value is None:
        return ""
    value = str(value).strip()
    value = re.sub(r"^[\-\*\•\·]\s*", "", value)
    value = re.sub(r"^\d{1,2}[.)]\s*", "", value)
    if re.fullmatch(r"\d{1,2}\.", value):
        return ""
    return value.strip()


# ============================================================
# CLEAN LIST
# ============================================================

def clean_list(items):
    if not isinstance(items, list):
        return []
    cleaned = []
    for item in items:
        text = clean_text(item)
        if text:
            cleaned.append(text)
    return cleaned


# ============================================================
# NORMALIZE GEMINI RESPONSE
# ============================================================

def normalize_analysis(data: dict):
    if not isinstance(data, dict):
        raise RuntimeError("Invalid analysis structure.")

    data["overallScore"] = safe_score(data.get("overallScore", 0))
    data["summary"] = clean_text(data.get("summary", ""))
    data["strengths"] = clean_list(data.get("strengths", []))
    data["weaknesses"] = clean_list(data.get("weaknesses", []))
    data["recommendations"] = clean_list(data.get("recommendations", []))
    data["verdict"] = clean_text(data.get("verdict", ""))

    skills = data.get("skills", {})
    if not isinstance(skills, dict):
        skills = {}
    skills["score"] = safe_score(skills.get("score", 0))
    skills["technical"] = clean_list(skills.get("technical", []))
    skills["soft"] = clean_list(skills.get("soft", []))
    skills["missing"] = clean_list(skills.get("missing", []))
    data["skills"] = skills

    experience = data.get("experience", {})
    if not isinstance(experience, dict):
        experience = {}
    experience["score"] = safe_score(experience.get("score", 0))
    experience["points"] = clean_list(experience.get("points", []))
    data["experience"] = experience

    projects = data.get("projects", {})
    if not isinstance(projects, dict):
        projects = {}
    projects["score"] = safe_score(projects.get("score", 0))
    projects["points"] = clean_list(projects.get("points", []))
    data["projects"] = projects

    education = data.get("education", {})
    if not isinstance(education, dict):
        education = {}
    education["score"] = safe_score(education.get("score", 0))
    education["points"] = clean_list(education.get("points", []))
    data["education"] = education

    ats = data.get("ats", {})
    if not isinstance(ats, dict):
        ats = {}
    ats["score"] = safe_score(ats.get("score", 0))
    ats["keywords"] = clean_list(ats.get("keywords", []))
    ats["formatting"] = clean_list(ats.get("formatting", []))
    ats["issues"] = clean_list(ats.get("issues", []))
    data["ats"] = ats

    job_match = data.get("jobMatch", {})
    if not isinstance(job_match, dict):
        job_match = {}
    job_match["score"] = safe_score(job_match.get("score", 0))
    job_match["matchedKeywords"] = clean_list(job_match.get("matchedKeywords", []))
    job_match["missingKeywords"] = clean_list(job_match.get("missingKeywords", []))
    job_match["recommendations"] = clean_list(job_match.get("recommendations", []))
    job_match["summary"] = clean_text(job_match.get("summary", ""))
    data["jobMatch"] = job_match

    # ============================================================
    # FEATURE 4: MULTI-ROLE TARGETING NORMALIZATION
    # ============================================================
    raw_multi_role = data.get("multiRoleTargeting", [])
    normalized_multi_roles = []

    if isinstance(raw_multi_role, list) and len(raw_multi_role) > 0:
        for item in raw_multi_role:
            if isinstance(item, dict):
                normalized_multi_roles.append({
                    "role": clean_text(item.get("role", "Target Role")),
                    "matchScore": safe_score(item.get("matchScore", 0)),
                    "prioritySkills": clean_list(item.get("prioritySkills", [])),
                    "projectToHighlight": clean_text(item.get("projectToHighlight", "")),
                    "reorderAdvice": clean_text(item.get("reorderAdvice", ""))
                })

    # Default multi-role fallback if empty
    if not normalized_multi_roles:
        normalized_multi_roles = [
            {
                "role": "Frontend Developer",
                "matchScore": safe_score(skills.get("score", 65)),
                "prioritySkills": ["React", "JavaScript", "HTML5", "CSS3 / Tailwind"],
                "projectToHighlight": "Portfolio or responsive web interface projects",
                "reorderAdvice": "Place UI frameworks and interactive web projects right below Summary."
            },
            {
                "role": "Backend Developer",
                "matchScore": safe_score(experience.get("score", 60)),
                "prioritySkills": ["Python", "FastAPI / Spring Boot", "REST APIs", "SQL / MongoDB"],
                "projectToHighlight": "API microservices, database schemas, and server integration projects",
                "reorderAdvice": "Prioritize backend systems, query optimization, and architectural contributions."
            },
            {
                "role": "Full Stack Engineer",
                "matchScore": safe_score(data.get("overallScore", 68)),
                "prioritySkills": ["React", "FastAPI / Node.js", "Database Design", "Git & CI/CD"],
                "projectToHighlight": "End-to-end full-stack applications with active deployment",
                "reorderAdvice": "Showcase complete workflow from frontend state management to backend persistence."
            }
        ]

    data["multiRoleTargeting"] = normalized_multi_roles

    return data


# ============================================================
# FORMAT ANALYSIS FOR OLD FRONTEND
# ============================================================

def format_analysis(data: dict):
    lines = []
    
    lines.append("1. OVERALL SCORE")
    lines.append(f"{data.get('overallScore', 0)}/100\n")

    lines.append("2. RESUME SUMMARY")
    lines.append(data.get("summary", "") + "\n")

    lines.append("3. KEY STRENGTHS")
    for item in data.get("strengths", []): lines.append(f"- {item}")
    lines.append("")

    lines.append("4. WEAKNESSES")
    for item in data.get("weaknesses", []): lines.append(f"- {item}")
    lines.append("")

    skills = data.get("skills", {})
    lines.append("5. SKILLS ANALYSIS")
    lines.append(f"Skills Score: {skills.get('score', 0)}/100")
    if skills.get("technical"):
        lines.append("Technical Skills:")
        for item in skills["technical"]: lines.append(f"- {item}")
    if skills.get("soft"):
        lines.append("Soft Skills:")
        for item in skills["soft"]: lines.append(f"- {item}")
    if skills.get("missing"):
        lines.append("Missing / Recommended Skills:")
        for item in skills["missing"]: lines.append(f"- {item}")
    lines.append("")

    experience = data.get("experience", {})
    lines.append("6. EXPERIENCE ANALYSIS")
    lines.append(f"Experience Score: {experience.get('score', 0)}/100")
    for item in experience.get("points", []): lines.append(f"- {item}")
    lines.append("")

    projects = data.get("projects", {})
    lines.append("7. PROJECT ANALYSIS")
    lines.append(f"Projects Score: {projects.get('score', 0)}/100")
    for item in projects.get("points", []): lines.append(f"- {item}")
    lines.append("")

    education = data.get("education", {})
    lines.append("8. EDUCATION ANALYSIS")
    lines.append(f"Education Score: {education.get('score', 0)}/100")
    for item in education.get("points", []): lines.append(f"- {item}")
    lines.append("")

    ats = data.get("ats", {})
    lines.append("9. ATS ANALYSIS")
    lines.append(f"ATS Score: {ats.get('score', 0)}/100")
    if ats.get("keywords"):
        lines.append("Keywords:")
        for item in ats["keywords"]: lines.append(f"- {item}")
    if ats.get("formatting"):
        lines.append("Formatting:")
        for item in ats["formatting"]: lines.append(f"- {item}")
    if ats.get("issues"):
        lines.append("ATS Issues:")
        for item in ats["issues"]: lines.append(f"- {item}")
    lines.append("")

    job_match = data.get("jobMatch", {})
    lines.append("10. JOB MATCH ANALYSIS")
    lines.append(f"Job Match Score: {job_match.get('score', 0)}/100")
    if job_match.get("summary"): lines.append(job_match["summary"])
    if job_match.get("matchedKeywords"):
        lines.append("Matched Keywords:")
        for item in job_match["matchedKeywords"]: lines.append(f"- {item}")
    if job_match.get("missingKeywords"):
        lines.append("Missing Keywords:")
        for item in job_match["missingKeywords"]: lines.append(f"- {item}")
    if job_match.get("recommendations"):
        lines.append("Job Match Recommendations:")
        for item in job_match["recommendations"]: lines.append(f"- {item}")
    lines.append("")

    multi_roles = data.get("multiRoleTargeting", [])
    if multi_roles:
        lines.append("11. MULTI-ROLE TARGETING ANALYSIS")
        for mr in multi_roles:
            lines.append(f"- Role: {mr.get('role')} (Match: {mr.get('matchScore')}/100)")
            lines.append(f"  Highlight Project: {mr.get('projectToHighlight')}")
            lines.append(f"  Advice: {mr.get('reorderAdvice')}")
        lines.append("")

    lines.append("12. ACTIONABLE RECOMMENDATIONS")
    for item in data.get("recommendations", []): lines.append(f"- {item}")
    lines.append("")

    lines.append("13. FINAL VERDICT")
    lines.append(data.get("verdict", ""))

    return "\n".join(lines)


# ============================================================
# GEMINI AI REVIEW
# ============================================================

def generate_ai_review(resume_text: str, job_description: str = ""):
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on the server."
        )

    try:
        print("\n======================================")
        print("STARTING GEMINI REQUEST")
        print("======================================")
        print(f"Model: {GEMINI_MODEL}")
        print(f"Resume characters: {len(resume_text)}")
        print(f"Job description provided: {bool(job_description.strip())}")

        client = genai.Client(api_key=API_KEY)

        if job_description.strip():
            job_section = f"""
TARGET JOB DESCRIPTION:
==================================================
{job_description}
==================================================
Compare the resume against this job description.
Calculate a realistic job match score.
Identify:
- matched keywords
- missing keywords
- relevant skill gaps
- specific improvements for this target role
"""
        else:
            job_section = """
No target job description was provided.
For jobMatch:
- score should be 0
- matchedKeywords should be []
- missingKeywords should be []
- recommendations should be []
- summary should say that no target job description was provided
"""

        prompt = f"""
You are an expert professional resume reviewer, career advisor and ATS specialist.
Analyze the uploaded resume carefully and objectively.
Your response MUST be valid JSON only.

IMPORTANT RULES:
- Return ONLY JSON.
- Do NOT use Markdown.
- Do NOT use code fences.
- Do NOT write anything before or after the JSON.
- Do NOT add section numbers.
- Do NOT add numbering inside arrays.
- Do NOT add bullet symbols inside array values.
- Never invent information.
- Never assume information that is not present.
- If something is missing, clearly say that it is missing.
- Keep points concise and useful.
- Use simple professional English.

Return EXACTLY this structure:
{{
    "overallScore": 0,
    "summary": "",
    "strengths": ["", "", ""],
    "weaknesses": ["", "", ""],
    "skills": {{
        "score": 0,
        "technical": [],
        "soft": [],
        "missing": []
    }},
    "experience": {{
        "score": 0,
        "points": []
    }},
    "projects": {{
        "score": 0,
        "points": []
    }},
    "education": {{
        "score": 0,
        "points": []
    }},
    "ats": {{
        "score": 0,
        "keywords": [],
        "formatting": [],
        "issues": []
    }},
    "jobMatch": {{
        "score": 0,
        "matchedKeywords": [],
        "missingKeywords": [],
        "recommendations": [],
        "summary": ""
    }},
    "multiRoleTargeting": [
        {{
            "role": "Frontend Developer",
            "matchScore": 0,
            "prioritySkills": ["", ""],
            "projectToHighlight": "",
            "reorderAdvice": ""
        }},
        {{
            "role": "Backend Developer",
            "matchScore": 0,
            "prioritySkills": ["", ""],
            "projectToHighlight": "",
            "reorderAdvice": ""
        }},
        {{
            "role": "Full Stack Developer",
            "matchScore": 0,
            "prioritySkills": ["", ""],
            "projectToHighlight": "",
            "reorderAdvice": ""
        }}
    ],
    "recommendations": ["", "", ""],
    "verdict": ""
}}

SCORING: 0 to 100 for all scores.

{job_section}

RESUME:
==================================================
{resume_text}
==================================================
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                max_output_tokens=4000,
                response_mime_type="application/json"
            )
        )

        if not response or not response.text:
            raise RuntimeError("Gemini returned no response.")

        raw_text = response.text.strip()
        raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"^```\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text).strip()

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print("\nINVALID JSON FROM GEMINI")
            print(raw_text)
            raise RuntimeError(f"Gemini returned invalid JSON: {str(e)}")

        if not isinstance(data, dict):
            raise RuntimeError("Gemini returned an invalid JSON object.")

        data = normalize_analysis(data)

        print("\nGEMINI SUCCESS")
        print(f"Overall Score: {data['overallScore']}")
        return data

    except HTTPException:
        raise
    except Exception as e:
        print("\nGEMINI ERROR\n", traceback.format_exc())
        error_text = str(e).lower()

        if any(err in error_text for err in ["503", "unavailable", "high demand", "overloaded"]):
            raise HTTPException(status_code=503, detail="Gemini is temporarily busy. Please try again in a few seconds.")
        if any(err in error_text for err in ["429", "resource exhausted", "rate limit", "quota"]):
            raise HTTPException(status_code=429, detail="Gemini API rate limit or quota reached. Please try again later.")
        
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")


# ============================================================
# RESUME REVIEW API (POST)
# ============================================================

@app.post("/api/review-resume")
def review_resume(
    file: UploadFile = File(...),
    job_description: str = Form(""),
    user_id: str = Form("")  
):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing on the server.")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    temp_path = None

    try:
        print("\nReceiving resume...")
        file_content = file.file.read()

        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="PDF must be smaller than 10 MB.")
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            temp_file.write(file_content)

        print("Resume saved.\nExtracting resume text...")
        resume_text = extract_text_from_pdf(temp_path)

        if not resume_text:
            raise HTTPException(status_code=400, detail="Could not extract text. Please upload a text-based PDF.")

        resume_text = resume_text[:25000]
        job_description = (job_description or "").strip()
        
        # FEATURE: JOB URL SCRAPER INTEGRATION
        if job_description.startswith("http://") or job_description.startswith("https://"):
            print(f"Detected URL. Scraping job description from: {job_description}")
            scraped_text = scrape_job_url(job_description)
            if scraped_text:
                job_description = scraped_text
                print("URL scraped successfully.")
            else:
                print("Failed to scrape URL, continuing with original input.")
        
        job_description = job_description[:5000]

        print("\nSending resume to Gemini...")
        structured_analysis = generate_ai_review(resume_text, job_description)
        analysis_text = format_analysis(structured_analysis)

        # SAVE TO MONGODB
        if resume_reports_collection is not None and user_id.strip():
            try:
                print("\nSaving report to MongoDB...")
                db_document = {
                    "user_id": user_id.strip(),
                    "file_name": file.filename,
                    "job_description": job_description,
                    "overall_score": structured_analysis.get("overallScore", 0),
                    "structured_data": structured_analysis,
                    "created_at": datetime.now(timezone.utc)
                }
                resume_reports_collection.insert_one(db_document)
                print("Successfully saved to MongoDB database.")
            except Exception as db_err:
                print(f"\nMongoDB Save Error: {str(db_err)}")

        print("\nResume analysis completed successfully.")

        return {
            "success": True,
            "analysis": analysis_text,
            "structured": structured_analysis,
            "meta": {
                "filename": file.filename,
                "jobDescriptionProvided": bool(job_description),
                "model": GEMINI_MODEL,
                "saved_to_db": bool(resume_reports_collection is not None and user_id.strip())
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print("\nRESUME REVIEW ERROR\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print("Could not delete temporary file:", str(e))

# ============================================================
# GET USER REPORTS API
# ============================================================

@app.get("/api/user-reports")
def get_user_reports(user_id: str):
    if resume_reports_collection is None:
        raise HTTPException(status_code=500, detail="Database not connected.")
    
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required.")
        
    try:
        # Fetch reports, sort by created_at descending (newest first)
        cursor = resume_reports_collection.find({"user_id": user_id.strip()}).sort("created_at", -1)
        
        reports = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            reports.append(doc)
            
        return {
            "success": True,
            "reports": reports
        }
    except Exception as e:
        print("\nFETCH REPORTS ERROR\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to fetch reports from database.")


# ============================================================
# GENERATE COVER LETTER & COLD EMAIL API (NEW FEATURE)
# ============================================================

@app.post("/api/generate-communication")
def generate_communication(
    structured_data: str = Form(...),
    job_description: str = Form("")
):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing.")
        
    try:
        jd_text = job_description.strip()
        # Ensure we scrape here too if the user passed a URL initially but it wasn't saved parsed
        if jd_text.startswith("http://") or jd_text.startswith("https://"):
            scraped_text = scrape_job_url(jd_text)
            jd_text = scraped_text if scraped_text else jd_text
        jd_text = jd_text[:5000]
        
        client = genai.Client(api_key=API_KEY)
        
        prompt = f"""
        You are an expert career coach and professional copywriter.
        Using the candidate's parsed resume data and the target job description below, generate a highly personalized, ATS-friendly Cover Letter and a short, punchy Cold Email to the Hiring Manager.
        
        Return ONLY valid JSON in this exact format, with NO markdown and NO extra text:
        {{
            "cover_letter": "Your generated cover letter text here...",
            "cold_email": "Your generated cold email text here..."
        }}
        
        CANDIDATE RESUME ANALYSIS DATA:
        {structured_data}
        
        TARGET JOB DESCRIPTION:
        {jd_text}
        """
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                max_output_tokens=2000,
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text.strip()
        raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"^```\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text).strip()
        
        data = json.loads(raw_text)
        
        return {
            "success": True,
            "cover_letter": data.get("cover_letter", ""),
            "cold_email": data.get("cold_email", "")
        }
        
    except Exception as e:
        print("\nGENERATE COMMUNICATION ERROR\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to generate communication templates.")