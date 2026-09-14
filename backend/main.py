import os
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
    version="2.0.0"
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

# Fast model
GEMINI_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AI Resume Reviewer API is running"
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
# GEMINI AI REVIEW
# ============================================================

def generate_ai_review(prompt: str) -> str:

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
        # Create Gemini client
        # ----------------------------------------------------

        client = genai.Client(
            api_key=API_KEY
        )

        # ----------------------------------------------------
        # ONE REQUEST ONLY
        # No retry
        # No model switching
        # ----------------------------------------------------

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=types.GenerateContentConfig(

                # Minimum reasoning = faster response
                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal"
                ),

                # Keep answer reasonably sized
                max_output_tokens=2500
            )
        )

        # ----------------------------------------------------
        # Validate response
        # ----------------------------------------------------

        if not response:

            raise RuntimeError(
                "Gemini returned no response."
            )

        if not response.text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        print("\n======================================")
        print("GEMINI SUCCESS")
        print("======================================")

        return response.text

    except Exception as e:

        print("\n======================================")
        print("GEMINI ERROR")
        print("======================================")

        print(str(e))
        print(traceback.format_exc())

        error_text = str(e).lower()

        # ----------------------------------------------------
        # 503 / overloaded
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
        # Other Gemini errors
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

        # 25,000 characters is enough for most resumes
        resume_text = resume_text[:25000]

        # ====================================================
        # AI PROMPT
        # ====================================================

        prompt = f"""
You are an expert professional resume reviewer,
career advisor and ATS specialist.

Analyze the resume below.

Give a concise but useful professional review.

Use exactly these sections:

1. OVERALL SCORE
Give a score out of 100.

2. RESUME SUMMARY
Give a short assessment.

3. KEY STRENGTHS
List the strongest points.

4. WEAKNESSES
List important weaknesses.

5. SKILLS ANALYSIS
Analyze technical and soft skills.

6. EXPERIENCE ANALYSIS
Analyze internships, jobs and practical experience.

7. PROJECT ANALYSIS
Analyze projects mentioned in the resume.

8. EDUCATION ANALYSIS
Review education.

9. ATS ANALYSIS
Check:
- ATS friendliness
- Keywords
- Formatting
- Section structure
- Readability

10. ACTIONABLE RECOMMENDATIONS
Give practical improvements.

11. FINAL VERDICT
Give a short conclusion.

IMPORTANT RULES:

- Do not invent information.
- Only use information present in the resume.
- Be honest and constructive.
- Keep the response concise.
- Use simple professional language.
- Use bullet points where appropriate.

RESUME:

==================================================

{resume_text}

==================================================
"""

        # ====================================================
        # GEMINI
        # ====================================================

        print("\nSending resume to Gemini...")

        analysis = generate_ai_review(
            prompt
        )

        # ====================================================
        # RETURN
        # ====================================================

        print("\nResume analysis completed successfully.")

        return {
            "success": True,
            "analysis": analysis
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