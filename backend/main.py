import os
import json
import tempfile
import traceback

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber
from google import genai
from google.genai import types


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Resume Reviewer API",
    version="3.0.0"
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
# GEMINI API
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")

# Current fast model
GEMINI_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AI Resume Reviewer API is running",
        "version": "3.0.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": GEMINI_MODEL
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
# FORMAT STRUCTURED RESULT INTO TEXT
# Keeps old frontend working
# ============================================================

def format_analysis(data: dict) -> str:

    lines = []

    # --------------------------------------------------------
    # Overall Score
    # --------------------------------------------------------

    lines.append("1. OVERALL SCORE")
    lines.append(
        f"{data.get('overallScore', 0)}/100"
    )
    lines.append("")

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    lines.append("2. RESUME SUMMARY")
    lines.append(
        data.get("summary", "")
    )
    lines.append("")

    # --------------------------------------------------------
    # Strengths
    # --------------------------------------------------------

    lines.append("3. KEY STRENGTHS")

    for item in data.get("strengths", []):
        lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Weaknesses
    # --------------------------------------------------------

    lines.append("4. WEAKNESSES")

    for item in data.get("weaknesses", []):
        lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    skills = data.get("skills", {})

    lines.append("5. SKILLS ANALYSIS")
    lines.append(
        f"Skills Score: {skills.get('score', 0)}/100"
    )

    technical = skills.get("technical", [])

    if technical:
        lines.append("Technical Skills:")
        for item in technical:
            lines.append(f"- {item}")

    soft = skills.get("soft", [])

    if soft:
        lines.append("Soft Skills:")
        for item in soft:
            lines.append(f"- {item}")

    missing = skills.get("missing", [])

    if missing:
        lines.append("Missing / Recommended Skills:")
        for item in missing:
            lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    experience = data.get("experience", {})

    lines.append("6. EXPERIENCE ANALYSIS")
    lines.append(
        f"Experience Score: {experience.get('score', 0)}/100"
    )

    for item in experience.get("points", []):
        lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Projects
    # --------------------------------------------------------

    projects = data.get("projects", {})

    lines.append("7. PROJECT ANALYSIS")
    lines.append(
        f"Projects Score: {projects.get('score', 0)}/100"
    )

    for item in projects.get("points", []):
        lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    education = data.get("education", {})

    lines.append("8. EDUCATION ANALYSIS")
    lines.append(
        f"Education Score: {education.get('score', 0)}/100"
    )

    for item in education.get("points", []):
        lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # ATS
    # --------------------------------------------------------

    ats = data.get("ats", {})

    lines.append("9. ATS ANALYSIS")
    lines.append(
        f"ATS Score: {ats.get('score', 0)}/100"
    )

    keywords = ats.get("keywords", [])

    if keywords:
        lines.append("Keywords:")
        for item in keywords:
            lines.append(f"- {item}")

    formatting = ats.get("formatting", [])

    if formatting:
        lines.append("Formatting:")
        for item in formatting:
            lines.append(f"- {item}")

    issues = ats.get("issues", [])

    if issues:
        lines.append("ATS Issues:")
        for item in issues:
            lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    lines.append("10. ACTIONABLE RECOMMENDATIONS")

    for item in data.get("recommendations", []):
        lines.append(f"- {item}")

    lines.append("")

    # --------------------------------------------------------
    # Verdict
    # --------------------------------------------------------

    lines.append("11. FINAL VERDICT")
    lines.append(
        data.get("verdict", "")
    )

    return "\n".join(lines)


# ============================================================
# GEMINI AI REVIEW
# ============================================================

def generate_ai_review(resume_text: str) -> dict:

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on Render."
        )

    try:

        print("\n======================================")
        print("STARTING GEMINI REQUEST")
        print("======================================")

        print(f"Model: {GEMINI_MODEL}")

        # ----------------------------------------------------
        # Gemini Client
        # ----------------------------------------------------

        client = genai.Client(
            api_key=API_KEY
        )

        # ----------------------------------------------------
        # Structured JSON Prompt
        # ----------------------------------------------------

        prompt = f"""
You are an expert professional resume reviewer,
career advisor and ATS specialist.

Analyze the resume below carefully.

Your response MUST be valid JSON only.

DO NOT:
- use markdown
- use ```json
- add explanations outside JSON
- invent information

Return EXACTLY this JSON structure:

{{
  "overallScore": 0,

  "summary": "",

  "strengths": [],

  "weaknesses": [],

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

  "recommendations": [],

  "verdict": ""
}}

RULES:

1. overallScore must be between 0 and 100.

2. Every section score must be between 0 and 100.

3. Only use information actually present in the resume.

4. Never invent internships, jobs, projects, skills,
   achievements, certifications or experience.

5. If an important section is missing, mention that clearly.

6. Give practical recommendations.

7. Keep each bullet point concise.

8. Use simple professional English.

9. ATS analysis should consider:
   - keywords
   - formatting
   - section structure
   - readability
   - ATS compatibility

10. The verdict should be short and useful.

RESUME:

==================================================

{resume_text}

==================================================
"""

        # ----------------------------------------------------
        # ONE FAST REQUEST
        # ----------------------------------------------------

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal"
                ),

                max_output_tokens=2500,

                response_mime_type="application/json"
            )
        )

        # ----------------------------------------------------
        # Validate Response
        # ----------------------------------------------------

        if not response:

            raise RuntimeError(
                "Gemini returned no response."
            )

        if not response.text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        raw_text = response.text.strip()

        # ----------------------------------------------------
        # Remove accidental markdown
        # ----------------------------------------------------

        if raw_text.startswith("```"):

            raw_text = raw_text.replace(
                "```json",
                ""
            )

            raw_text = raw_text.replace(
                "```",
                ""
            )

            raw_text = raw_text.strip()

        # ----------------------------------------------------
        # Convert JSON
        # ----------------------------------------------------

        try:

            data = json.loads(raw_text)

        except json.JSONDecodeError as e:

            print("\nINVALID JSON FROM GEMINI:")
            print(raw_text)

            raise RuntimeError(
                f"Gemini returned invalid JSON: {str(e)}"
            )

        # ----------------------------------------------------
        # Basic Safety Defaults
        # ----------------------------------------------------

        if not isinstance(data, dict):

            raise RuntimeError(
                "Gemini returned an invalid JSON structure."
            )

        data.setdefault("overallScore", 0)
        data.setdefault("summary", "")
        data.setdefault("strengths", [])
        data.setdefault("weaknesses", [])
        data.setdefault("skills", {})
        data.setdefault("experience", {})
        data.setdefault("projects", {})
        data.setdefault("education", {})
        data.setdefault("ats", {})
        data.setdefault("recommendations", [])
        data.setdefault("verdict", "")

        # Nested defaults

        data["skills"].setdefault("score", 0)
        data["skills"].setdefault("technical", [])
        data["skills"].setdefault("soft", [])
        data["skills"].setdefault("missing", [])

        data["experience"].setdefault("score", 0)
        data["experience"].setdefault("points", [])

        data["projects"].setdefault("score", 0)
        data["projects"].setdefault("points", [])

        data["education"].setdefault("score", 0)
        data["education"].setdefault("points", [])

        data["ats"].setdefault("score", 0)
        data["ats"].setdefault("keywords", [])
        data["ats"].setdefault("formatting", [])
        data["ats"].setdefault("issues", [])

        print("\n======================================")
        print("GEMINI SUCCESS")
        print("STRUCTURED JSON RECEIVED")
        print("======================================")

        return data

    except HTTPException:

        raise

    except Exception as e:

        print("\n======================================")
        print("GEMINI ERROR")
        print("======================================")

        print(str(e))
        print(traceback.format_exc())

        error_text = str(e).lower()

        # ----------------------------------------------------
        # 503
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 429
        # ----------------------------------------------------

        if (
            "429" in error_text
            or "resource exhausted" in error_text
            or "rate limit" in error_text
        ):

            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API rate limit reached. "
                    "Please try again shortly."
                )
            )

        # ----------------------------------------------------
        # Other Errors
        # ----------------------------------------------------

        raise HTTPException(
            status_code=500,
            detail=f"Gemini API error: {str(e)}"
        )


# ============================================================
# RESUME REVIEW API
# ============================================================

@app.post("/api/review-resume")
def review_resume(
    file: UploadFile = File(...)
):

    # ========================================================
    # API KEY CHECK
    # ========================================================

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing on the server."
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

        # 10 MB limit
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

            temp_file.write(file_content)

        print("Resume saved.")

        # ====================================================
        # EXTRACT TEXT
        # ====================================================

        print("\nExtracting resume text...")

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
        # LIMIT PROMPT SIZE
        # ====================================================

        resume_text = resume_text[:25000]

        # ====================================================
        # GEMINI ANALYSIS
        # ====================================================

        print("\nSending resume to Gemini...")

        structured_analysis = generate_ai_review(
            resume_text
        )

        # ====================================================
        # CREATE OLD-FORMAT TEXT
        # Keeps current App.jsx working
        # ====================================================

        analysis_text = format_analysis(
            structured_analysis
        )

        # ====================================================
        # RETURN
        # ====================================================

        print(
            "\nResume analysis completed successfully."
        )

        return {

            "success": True,

            # Existing frontend can continue using this
            "analysis": analysis_text,

            # New structured data for our upgraded frontend
            "structured": structured_analysis

        }

    except HTTPException:

        raise

    except Exception as e:

        print("\n======================================")
        print("RESUME REVIEW ERROR")
        print("======================================")

        print(traceback.format_exc())

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

                if os.path.exists(temp_path):

                    os.remove(temp_path)

            except Exception as e:

                print(
                    "Could not delete temporary file:",
                    str(e)
                )