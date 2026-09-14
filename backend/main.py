import os
import time
import tempfile
import traceback

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber
from google import genai


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Resume Reviewer API",
    version="1.0.0"
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
# GEMINI API KEY
# ============================================================

API_KEY = os.getenv("GEMINI_API_KEY")


# ============================================================
# GEMINI MODELS
# ============================================================

# IMPORTANT:
# Do NOT use Gemini 1.5 or 2.5 here.
# Your API key is reporting that those models are unavailable
# to new users.

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]


# ============================================================
# HOME / HEALTH CHECK
# ============================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AI Resume Reviewer API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(file_path: str) -> str:

    text = ""

    try:

        with pdfplumber.open(file_path) as pdf:

            for page in pdf.pages:

                extracted = page.extract_text()

                if extracted:
                    text += extracted + "\n"

    except Exception as e:

        raise RuntimeError(
            f"Failed to extract text from PDF: {str(e)}"
        )

    return text.strip()


# ============================================================
# GEMINI AI REVIEW
# ============================================================

def generate_ai_review(prompt: str) -> str:

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on Render."
        )

    # --------------------------------------------------------
    # Create Gemini client
    # --------------------------------------------------------

    try:

        client = genai.Client(
            api_key=API_KEY
        )

    except Exception as e:

        print("GEMINI CLIENT ERROR:")
        print(traceback.format_exc())

        raise HTTPException(
            status_code=500,
            detail=f"Could not initialize Gemini: {str(e)}"
        )

    last_error = None

    # --------------------------------------------------------
    # Try models one by one
    # --------------------------------------------------------

    for model_name in GEMINI_MODELS:

        print("\n======================================")
        print(f"Trying Gemini model: {model_name}")
        print("======================================")

        # Try the same model up to 2 times
        for attempt in range(2):

            try:

                print(
                    f"Attempt {attempt + 1}/2 "
                    f"for {model_name}"
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )

                # ------------------------------------------------
                # Validate response
                # ------------------------------------------------

                if response and response.text:

                    print(
                        f"\nSUCCESS: {model_name}"
                    )

                    return response.text

                print(
                    f"{model_name} returned empty response."
                )

                last_error = Exception(
                    "Gemini returned an empty response."
                )

                break

            except Exception as e:

                last_error = e

                error_text = str(e).lower()

                print(
                    f"\nERROR from {model_name}:"
                )

                print(str(e))

                # ------------------------------------------------
                # 404 = model unavailable
                # ------------------------------------------------

                if (
                    "404" in error_text
                    or "not_found" in error_text
                    or "not found" in error_text
                    or "no longer available" in error_text
                ):

                    print(
                        f"{model_name} is unavailable."
                    )

                    # Don't retry same unavailable model
                    break

                # ------------------------------------------------
                # 503 / high demand
                # ------------------------------------------------

                temporary_error = (
                    "503" in error_text
                    or "unavailable" in error_text
                    or "high demand" in error_text
                    or "temporarily" in error_text
                    or "overloaded" in error_text
                )

                # ------------------------------------------------
                # 429 / rate limit
                # ------------------------------------------------

                rate_limit_error = (
                    "429" in error_text
                    or "resource exhausted" in error_text
                    or "rate limit" in error_text
                )

                if temporary_error or rate_limit_error:

                    if attempt == 0:

                        print(
                            "Temporary error."
                        )

                        print(
                            "Waiting 2 seconds before retry..."
                        )

                        time.sleep(2)

                        continue

                # ------------------------------------------------
                # Other error
                # ------------------------------------------------

                print(
                    f"Moving to next model..."
                )

                break

    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    print("\n======================================")
    print("ALL GEMINI MODELS FAILED")
    print("======================================")

    if last_error:

        print(str(last_error))

    raise HTTPException(
        status_code=503,
        detail=(
            "Gemini AI service is currently unavailable. "
            "All configured Gemini models failed. "
            "Please try again in a few moments."
        )
    )


# ============================================================
# RESUME REVIEW API
# ============================================================

@app.post("/api/review-resume")
def review_resume(
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing on the server."
        )

    # --------------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------------

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
        # SAVE PDF TEMPORARILY
        # ====================================================

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_path = temp_file.name

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

            temp_file.write(file_content)

        # ====================================================
        # EXTRACT RESUME TEXT
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
            f"Resume text extracted: "
            f"{len(resume_text)} characters"
        )

        # Avoid unnecessarily huge prompts
        resume_text = resume_text[:50000]

        # ====================================================
        # AI PROMPT
        # ====================================================

        prompt = f"""
You are an expert professional resume reviewer,
career advisor and ATS specialist.

Analyze the resume below carefully.

Give a professional, honest and constructive review.

Your response MUST contain these sections:

1. OVERALL SCORE
Give a score out of 100.

2. RESUME SUMMARY
Give a short overall assessment.

3. KEY STRENGTHS
List the strongest points.

4. WEAKNESSES
List missing, weak or unclear areas.

5. SKILLS ANALYSIS
Analyze technical and soft skills.

6. EXPERIENCE ANALYSIS
Analyze internships, jobs and practical experience.

7. PROJECT ANALYSIS
Analyze the projects mentioned in the resume.

8. EDUCATION ANALYSIS
Review the education section.

9. ATS ANALYSIS
Check:
- ATS friendliness
- Keywords
- Formatting
- Section structure
- Readability

10. ACTIONABLE RECOMMENDATIONS
Give specific improvements the candidate should make.

11. FINAL VERDICT
Give a short conclusion.

IMPORTANT:
- Do not invent information.
- Only use information actually present in the resume.
- Be constructive.
- Give practical recommendations.
- Use simple professional language.

RESUME:
==================================================

{resume_text}

==================================================
"""

        # ====================================================
        # GENERATE AI REVIEW
        # ====================================================

        print("\nSending resume to Gemini...")

        analysis = generate_ai_review(
            prompt
        )

        # ====================================================
        # RETURN RESULT
        # ====================================================

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

                if os.path.exists(temp_path):

                    os.remove(temp_path)

            except Exception as e:

                print(
                    "Could not delete temporary file:",
                    str(e)
                )