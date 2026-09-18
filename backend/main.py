import os
import json
import tempfile
import traceback
import re

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber
from google import genai
from google.genai import types


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Resume Reviewer API",
    version="5.0.0"
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
# GEMINI CONFIGURATION
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

# Use a currently supported Gemini Flash model.
GEMINI_MODEL = "gemini-3.6-flash"


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AI Resume Reviewer API is running",
        "version": "5.0.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": GEMINI_MODEL,
        "gemini_configured": bool(API_KEY)
    }


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

        return max(
            0,
            min(
                100,
                score
            )
        )

    except Exception:

        return 0


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value).strip()

    # Remove markdown bullets
    value = re.sub(
        r"^[\-\*\•\·]\s*",
        "",
        value
    )

    # Remove numbering such as:
    # 1. text
    # 2) text
    # 01. text

    value = re.sub(
        r"^\d{1,2}[.)]\s*",
        "",
        value
    )

    # Remove standalone number
    if re.fullmatch(
        r"\d{1,2}\.",
        value
    ):
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

        raise RuntimeError(
            "Invalid analysis structure."
        )

    # ========================================================
    # TOP LEVEL
    # ========================================================

    data["overallScore"] = safe_score(
        data.get("overallScore", 0)
    )

    data["summary"] = clean_text(
        data.get("summary", "")
    )

    data["strengths"] = clean_list(
        data.get("strengths", [])
    )

    data["weaknesses"] = clean_list(
        data.get("weaknesses", [])
    )

    data["recommendations"] = clean_list(
        data.get("recommendations", [])
    )

    data["verdict"] = clean_text(
        data.get("verdict", "")
    )


    # ========================================================
    # SKILLS
    # ========================================================

    skills = data.get(
        "skills",
        {}
    )

    if not isinstance(skills, dict):
        skills = {}

    skills["score"] = safe_score(
        skills.get("score", 0)
    )

    skills["technical"] = clean_list(
        skills.get("technical", [])
    )

    skills["soft"] = clean_list(
        skills.get("soft", [])
    )

    skills["missing"] = clean_list(
        skills.get("missing", [])
    )

    data["skills"] = skills


    # ========================================================
    # EXPERIENCE
    # ========================================================

    experience = data.get(
        "experience",
        {}
    )

    if not isinstance(experience, dict):
        experience = {}

    experience["score"] = safe_score(
        experience.get("score", 0)
    )

    experience["points"] = clean_list(
        experience.get("points", [])
    )

    data["experience"] = experience


    # ========================================================
    # PROJECTS
    # ========================================================

    projects = data.get(
        "projects",
        {}
    )

    if not isinstance(projects, dict):
        projects = {}

    projects["score"] = safe_score(
        projects.get("score", 0)
    )

    projects["points"] = clean_list(
        projects.get("points", [])
    )

    data["projects"] = projects


    # ========================================================
    # EDUCATION
    # ========================================================

    education = data.get(
        "education",
        {}
    )

    if not isinstance(education, dict):
        education = {}

    education["score"] = safe_score(
        education.get("score", 0)
    )

    education["points"] = clean_list(
        education.get("points", [])
    )

    data["education"] = education


    # ========================================================
    # ATS
    # ========================================================

    ats = data.get(
        "ats",
        {}
    )

    if not isinstance(ats, dict):
        ats = {}

    ats["score"] = safe_score(
        ats.get("score", 0)
    )

    ats["keywords"] = clean_list(
        ats.get("keywords", [])
    )

    ats["formatting"] = clean_list(
        ats.get("formatting", [])
    )

    ats["issues"] = clean_list(
        ats.get("issues", [])
    )

    data["ats"] = ats


    # ========================================================
    # JOB MATCH
    # ========================================================

    job_match = data.get(
        "jobMatch",
        {}
    )

    if not isinstance(job_match, dict):
        job_match = {}

    job_match["score"] = safe_score(
        job_match.get("score", 0)
    )

    job_match["matchedKeywords"] = clean_list(
        job_match.get(
            "matchedKeywords",
            []
        )
    )

    job_match["missingKeywords"] = clean_list(
        job_match.get(
            "missingKeywords",
            []
        )
    )

    job_match["recommendations"] = clean_list(
        job_match.get(
            "recommendations",
            []
        )
    )

    job_match["summary"] = clean_text(
        job_match.get(
            "summary",
            ""
        )
    )

    data["jobMatch"] = job_match


    return data


# ============================================================
# FORMAT ANALYSIS FOR OLD FRONTEND
# ============================================================

def format_analysis(data: dict):

    lines = []


    # ========================================================
    # 1. OVERALL
    # ========================================================

    lines.append("1. OVERALL SCORE")

    lines.append(
        f"{data.get('overallScore', 0)}/100"
    )

    lines.append("")


    # ========================================================
    # 2. SUMMARY
    # ========================================================

    lines.append(
        "2. RESUME SUMMARY"
    )

    lines.append(
        data.get(
            "summary",
            ""
        )
    )

    lines.append("")


    # ========================================================
    # 3. STRENGTHS
    # ========================================================

    lines.append(
        "3. KEY STRENGTHS"
    )

    for item in data.get(
        "strengths",
        []
    ):

        lines.append(
            f"- {item}"
        )

    lines.append("")


    # ========================================================
    # 4. WEAKNESSES
    # ========================================================

    lines.append(
        "4. WEAKNESSES"
    )

    for item in data.get(
        "weaknesses",
        []
    ):

        lines.append(
            f"- {item}"
        )

    lines.append("")


    # ========================================================
    # 5. SKILLS
    # ========================================================

    skills = data.get(
        "skills",
        {}
    )

    lines.append(
        "5. SKILLS ANALYSIS"
    )

    lines.append(
        f"Skills Score: {skills.get('score', 0)}/100"
    )

    if skills.get("technical"):

        lines.append(
            "Technical Skills:"
        )

        for item in skills["technical"]:
            lines.append(
                f"- {item}"
            )

    if skills.get("soft"):

        lines.append(
            "Soft Skills:"
        )

        for item in skills["soft"]:
            lines.append(
                f"- {item}"
            )

    if skills.get("missing"):

        lines.append(
            "Missing / Recommended Skills:"
        )

        for item in skills["missing"]:
            lines.append(
                f"- {item}"
            )

    lines.append("")


    # ========================================================
    # 6. EXPERIENCE
    # ========================================================

    experience = data.get(
        "experience",
        {}
    )

    lines.append(
        "6. EXPERIENCE ANALYSIS"
    )

    lines.append(
        f"Experience Score: {experience.get('score', 0)}/100"
    )

    for item in experience.get(
        "points",
        []
    ):

        lines.append(
            f"- {item}"
        )

    lines.append("")


    # ========================================================
    # 7. PROJECTS
    # ========================================================

    projects = data.get(
        "projects",
        {}
    )

    lines.append(
        "7. PROJECT ANALYSIS"
    )

    lines.append(
        f"Projects Score: {projects.get('score', 0)}/100"
    )

    for item in projects.get(
        "points",
        []
    ):

        lines.append(
            f"- {item}"
        )

    lines.append("")


    # ========================================================
    # 8. EDUCATION
    # ========================================================

    education = data.get(
        "education",
        {}
    )

    lines.append(
        "8. EDUCATION ANALYSIS"
    )

    lines.append(
        f"Education Score: {education.get('score', 0)}/100"
    )

    for item in education.get(
        "points",
        []
    ):

        lines.append(
            f"- {item}"
        )

    lines.append("")


    # ========================================================
    # 9. ATS
    # ========================================================

    ats = data.get(
        "ats",
        {}
    )

    lines.append(
        "9. ATS ANALYSIS"
    )

    lines.append(
        f"ATS Score: {ats.get('score', 0)}/100"
    )

    if ats.get("keywords"):

        lines.append(
            "Keywords:"
        )

        for item in ats["keywords"]:
            lines.append(
                f"- {item}"
            )

    if ats.get("formatting"):

        lines.append(
            "Formatting:"
        )

        for item in ats["formatting"]:
            lines.append(
                f"- {item}"
            )

    if ats.get("issues"):

        lines.append(
            "ATS Issues:"
        )

        for item in ats["issues"]:
            lines.append(
                f"- {item}"
            )

    lines.append("")


    # ========================================================
    # 10. JOB MATCH
    # ========================================================

    job_match = data.get(
        "jobMatch",
        {}
    )

    lines.append(
        "10. JOB MATCH ANALYSIS"
    )

    lines.append(
        f"Job Match Score: {job_match.get('score', 0)}/100"
    )

    if job_match.get("summary"):

        lines.append(
            job_match["summary"]
        )

    if job_match.get("matchedKeywords"):

        lines.append(
            "Matched Keywords:"
        )

        for item in job_match["matchedKeywords"]:
            lines.append(
                f"- {item}"
            )

    if job_match.get("missingKeywords"):

        lines.append(
            "Missing Keywords:"
        )

        for item in job_match["missingKeywords"]:
            lines.append(
                f"- {item}"
            )

    if job_match.get("recommendations"):

        lines.append(
            "Job Match Recommendations:"
        )

        for item in job_match["recommendations"]:
            lines.append(
                f"- {item}"
            )

    lines.append("")


    # ========================================================
    # 11. RECOMMENDATIONS
    # ========================================================

    lines.append(
        "11. ACTIONABLE RECOMMENDATIONS"
    )

    for item in data.get(
        "recommendations",
        []
    ):

        lines.append(
            f"- {item}"
        )

    lines.append("")


    # ========================================================
    # 12. VERDICT
    # ========================================================

    lines.append(
        "12. FINAL VERDICT"
    )

    lines.append(
        data.get(
            "verdict",
            ""
        )
    )

    return "\n".join(lines)


# ============================================================
# GEMINI AI REVIEW
# ============================================================

def generate_ai_review(
    resume_text: str,
    job_description: str = ""
):

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is not configured on the server."
            )
        )


    try:

        print("\n======================================")
        print("STARTING GEMINI REQUEST")
        print("======================================")

        print(
            f"Model: {GEMINI_MODEL}"
        )

        print(
            f"Resume characters: {len(resume_text)}"
        )

        print(
            f"Job description provided: {bool(job_description.strip())}"
        )


        # ====================================================
        # GEMINI CLIENT
        # ====================================================

        client = genai.Client(
            api_key=API_KEY
        )


        # ====================================================
        # JOB MATCH INSTRUCTIONS
        # ====================================================

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


        # ====================================================
        # PROMPT
        # ====================================================

        prompt = f"""
You are an expert professional resume reviewer,
career advisor and ATS specialist.

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

    "strengths": [
        "",
        "",
        ""
    ],

    "weaknesses": [
        "",
        "",
        ""
    ],

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

    "recommendations": [
        "",
        "",
        ""
    ],

    "verdict": ""
}}

SCORING:

- overallScore: 0 to 100
- skills.score: 0 to 100
- experience.score: 0 to 100
- projects.score: 0 to 100
- education.score: 0 to 100
- ats.score: 0 to 100
- jobMatch.score: 0 to 100

ANALYSIS RULES:

1. Evaluate the resume based only on the uploaded content.

2. Never invent:
   - internships
   - jobs
   - projects
   - certifications
   - skills
   - achievements
   - technologies
   - experience

3. If the candidate is a student and has no professional experience,
   do not treat being a student itself as a major weakness.

4. For projects evaluate:
   - clarity
   - technologies
   - problem solved
   - candidate contribution
   - measurable results

5. For skills evaluate:
   - technical skills
   - soft skills
   - relevant missing skills

6. For ATS evaluate:
   - relevant keywords
   - formatting
   - section headings
   - readability
   - ATS compatibility
   - potential parsing issues

7. For recommendations:
   give specific actions that the candidate can actually take.

8. Avoid generic advice whenever possible.

9. Keep final verdict short.

10. Never put "1.", "2.", "3." etc. inside arrays.

11. Never put "-" or "•" at the beginning of array values.

12. Keep array values as plain text.

13. Scores must be integers between 0 and 100.

{job_section}

RESUME:

==================================================

{resume_text}

==================================================
"""


        # ====================================================
        # GEMINI REQUEST
        # ====================================================

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal"
                ),

                max_output_tokens=4000,

                response_mime_type="application/json"
            )
        )


        # ====================================================
        # RESPONSE VALIDATION
        # ====================================================

        if not response:

            raise RuntimeError(
                "Gemini returned no response."
            )


        if not response.text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )


        raw_text = response.text.strip()


        # ====================================================
        # REMOVE CODE FENCES IF ANY
        # ====================================================

        raw_text = re.sub(
            r"^```json\s*",
            "",
            raw_text,
            flags=re.IGNORECASE
        )

        raw_text = re.sub(
            r"^```\s*",
            "",
            raw_text
        )

        raw_text = re.sub(
            r"\s*```$",
            "",
            raw_text
        )

        raw_text = raw_text.strip()


        # ====================================================
        # JSON PARSE
        # ====================================================

        try:

            data = json.loads(
                raw_text
            )

        except json.JSONDecodeError as e:

            print("\n======================================")
            print("INVALID JSON FROM GEMINI")
            print("======================================")

            print(raw_text)

            raise RuntimeError(
                f"Gemini returned invalid JSON: {str(e)}"
            )


        # ====================================================
        # OBJECT VALIDATION
        # ====================================================

        if not isinstance(
            data,
            dict
        ):

            raise RuntimeError(
                "Gemini returned an invalid JSON object."
            )


        # ====================================================
        # NORMALIZE
        # ====================================================

        data = normalize_analysis(
            data
        )


        print("\n======================================")
        print("GEMINI SUCCESS")
        print("======================================")

        print(
            f"Overall Score: {data['overallScore']}"
        )

        print(
            f"ATS Score: {data['ats']['score']}"
        )

        print(
            f"Job Match Score: {data['jobMatch']['score']}"
        )


        return data


    except HTTPException:

        raise


    except Exception as e:

        print("\n======================================")
        print("GEMINI ERROR")
        print("======================================")

        print(
            str(e)
        )

        print(
            traceback.format_exc()
        )


        error_text = str(e).lower()


        # ====================================================
        # 503
        # ====================================================

        if (
            "503" in error_text
            or "unavailable" in error_text
            or "high demand" in error_text
            or "overloaded" in error_text
        ):

            raise HTTPException(
                status_code=503,
                detail=(
                    "Gemini is temporarily busy. "
                    "Please try again in a few seconds."
                )
            )


        # ====================================================
        # 429
        # ====================================================

        if (
            "429" in error_text
            or "resource exhausted" in error_text
            or "rate limit" in error_text
            or "quota" in error_text
        ):

            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API rate limit or quota reached. "
                    "Please try again later."
                )
            )


        # ====================================================
        # OTHER ERRORS
        # ====================================================

        raise HTTPException(
            status_code=500,
            detail=f"Gemini API error: {str(e)}"
        )


# ============================================================
# RESUME REVIEW API
# ============================================================

@app.post("/api/review-resume")
def review_resume(

    file: UploadFile = File(...),

    job_description: str = Form("")
):


    # ========================================================
    # API KEY CHECK
    # ========================================================

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is missing on the server."
            )
        )


    # ========================================================
    # FILE CHECK
    # ========================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No file was selected."
        )


    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )


    temp_path = None


    try:

        # ====================================================
        # READ FILE
        # ====================================================

        print("\nReceiving resume...")

        file_content = file.file.read()


        # ====================================================
        # 10 MB LIMIT
        # ====================================================

        if len(file_content) > 10 * 1024 * 1024:

            raise HTTPException(
                status_code=400,
                detail="PDF must be smaller than 10 MB."
            )


        if len(file_content) == 0:

            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF is empty."
            )


        # ====================================================
        # SAVE TEMP PDF
        # ====================================================

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_path = temp_file.name

            temp_file.write(
                file_content
            )


        print(
            "Resume saved."
        )


        # ====================================================
        # EXTRACT TEXT
        # ====================================================

        print(
            "\nExtracting resume text..."
        )

        resume_text = extract_text_from_pdf(
            temp_path
        )


        if not resume_text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract text from this PDF. "
                    "Please upload a text-based PDF resume."
                )
            )


        print(
            f"Extracted {len(resume_text)} characters."
        )


        # ====================================================
        # LIMIT RESUME SIZE
        # ====================================================

        resume_text = resume_text[:25000]


        # ====================================================
        # LIMIT JOB DESCRIPTION
        # ====================================================

        job_description = (
            job_description or ""
        ).strip()[:5000]


        # ====================================================
        # GEMINI ANALYSIS
        # ====================================================

        print(
            "\nSending resume to Gemini..."
        )


        structured_analysis = generate_ai_review(

            resume_text,

            job_description
        )


        # ====================================================
        # OLD TEXT FORMAT
        # ====================================================

        analysis_text = format_analysis(
            structured_analysis
        )


        # ====================================================
        # RETURN RESPONSE
        # ====================================================

        print(
            "\nResume analysis completed successfully."
        )


        return {

            "success": True,

            "analysis": analysis_text,

            "structured": structured_analysis,

            "meta": {

                "filename": file.filename,

                "jobDescriptionProvided": bool(
                    job_description
                ),

                "model": GEMINI_MODEL
            }
        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "\n======================================"
        )

        print(
            "RESUME REVIEW ERROR"
        )

        print(
            "======================================"
        )

        print(
            traceback.format_exc()
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    finally:

        # ====================================================
        # DELETE TEMP FILE
        # ====================================================

        if temp_path:

            try:

                if os.path.exists(
                    temp_path
                ):

                    os.remove(
                        temp_path
                    )

            except Exception as e:

                print(
                    "Could not delete temporary file:",
                    str(e)
                )