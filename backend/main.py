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

app = FastAPI(title="AI Resume Reviewer API")


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
# HEALTH CHECK
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

                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"

    except Exception as e:

        raise RuntimeError(
            f"Could not read PDF: {str(e)}"
        )

    return text.strip()


# ============================================================
# GET AVAILABLE GEMINI MODEL
# ============================================================

def get_available_model(client):

    """
    Find a currently available Gemini model.

    We don't blindly depend on one model name because
    models can become unavailable, overloaded, or deprecated.
    """

    preferred_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    ]

    try:

        available_models = list(client.models.list())

        available_names = []

        for model in available_models:

            name = getattr(model, "name", "")

            if name:
                name = name.replace("models/", "")
                available_names.append(name)

        print("\nAVAILABLE GEMINI MODELS:")
        print(available_names)

        # First try preferred models
        for preferred in preferred_models:

            if preferred in available_names:
                print(
                    f"\nUsing Gemini model: {preferred}"
                )

                return preferred

        # Fallback:
        # Find any model which looks like a Flash model
        for name in available_names:

            lower_name = name.lower()

            if (
                "gemini" in lower_name
                and "flash" in lower_name
                and "embedding" not in lower_name
                and "tts" not in lower_name
                and "image" not in lower_name
            ):

                print(
                    f"\nUsing fallback Gemini model: {name}"
                )

                return name

    except Exception as e:

        print(
            "\nCould not list Gemini models:"
        )

        print(str(e))

    return None


# ============================================================
# GENERATE AI REVIEW
# ============================================================

def generate_ai_review(prompt: str):

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is not configured "
                "on the server."
            )
        )

    try:

        client = genai.Client(
            api_key=API_KEY
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not initialize Gemini: {str(e)}"
        )

    # --------------------------------------------------------
    # Find available model
    # --------------------------------------------------------

    model_name = get_available_model(client)

    if not model_name:

        raise HTTPException(
            status_code=503,
            detail=(
                "No usable Gemini model was found "
                "for this API key."
            )
        )

    # --------------------------------------------------------
    # Try selected model
    # --------------------------------------------------------

    max_attempts = 3

    last_error = None

    for attempt in range(max_attempts):

        try:

            print(
                f"\nGemini request attempt "
                f"{attempt + 1}/{max_attempts}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            if response and response.text:

                print(
                    f"\nGemini response received "
                    f"using {model_name}"
                )

                return response.text

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        except Exception as e:

            last_error = e

            error_text = str(e).lower()

            print(
                f"\nGemini error with {model_name}:"
            )

            print(str(e))

            # ------------------------------------------------
            # Retry temporary errors
            # ------------------------------------------------

            temporary_error = (
                "503" in error_text
                or "unavailable" in error_text
                or "high demand" in error_text
                or "429" in error_text
                or "resource exhausted" in error_text
                or "timeout" in error_text
            )

            if temporary_error:

                if attempt < max_attempts - 1:

                    wait_time = 2 ** attempt

                    print(
                        f"Temporary Gemini error."
                        f" Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                    continue

            # Non-temporary error
            break

    # --------------------------------------------------------
    # All attempts failed
    # --------------------------------------------------------

    print("\nGEMINI FINAL ERROR:")
    print(traceback.format_exc())

    raise HTTPException(
        status_code=503,
        detail=(
            "Gemini AI service is currently unavailable. "
            "Please try again after a short while. "
            f"Model used: {model_name}. "
            f"Error: {str(last_error)}"
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
    # API KEY CHECK
    # --------------------------------------------------------

    if not API_KEY:

        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is not configured "
                "on the server."
            )
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

        # ----------------------------------------------------
        # SAVE PDF TEMPORARILY
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_path = temp_file.name

            file_content = file.file.read()

            if not file_content:

                raise HTTPException(
                    status_code=400,
                    detail="Uploaded PDF is empty."
                )

            # 10 MB limit
            if len(file_content) > 10 * 1024 * 1024:

                raise HTTPException(
                    status_code=400,
                    detail="PDF size must be less than 10 MB."
                )

            temp_file.write(file_content)

        # ----------------------------------------------------
        # EXTRACT TEXT
        # ----------------------------------------------------

        resume_text = extract_text_from_pdf(
            temp_path
        )

        if not resume_text:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract text from this PDF. "
                    "Please upload a text-based resume PDF."
                )
            )

        # ----------------------------------------------------
        # LIMIT TEXT SIZE
        # ----------------------------------------------------

        # Prevent unnecessarily huge prompts
        resume_text = resume_text[:50000]

        # ----------------------------------------------------
        # AI PROMPT
        # ----------------------------------------------------

        prompt = f"""
You are an expert professional resume reviewer and career advisor.

Analyze the following resume carefully.

Provide the review in a clean, professional and easy-to-read format.

Include:

1. OVERALL SCORE
Give a score out of 100.

2. RESUME SUMMARY
Give a short assessment of the resume.

3. KEY STRENGTHS
Mention the strongest parts of the resume.

4. WEAKNESSES
Identify missing, weak or unclear areas.

5. SKILLS ANALYSIS
Evaluate the technical and soft skills.

6. EXPERIENCE ANALYSIS
Evaluate projects, internships and work experience.

7. EDUCATION ANALYSIS
Evaluate the education section.

8. ATS ANALYSIS
Check ATS friendliness, keywords, formatting and structure.

9. ACTIONABLE RECOMMENDATIONS
Give specific improvements the candidate should make.

10. FINAL VERDICT
Give a short final conclusion.

Be honest but constructive.

Do not invent information that is not present in the resume.

RESUME TEXT:
-------------------------

{resume_text}

-------------------------
"""

        # ----------------------------------------------------
        # GENERATE REVIEW
        # ----------------------------------------------------

        analysis = generate_ai_review(
            prompt
        )

        # ----------------------------------------------------
        # RETURN TO FRONTEND
        # ----------------------------------------------------

        return {
            "success": True,
            "analysis": analysis
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "\n=============================="
        )

        print(
            "RESUME REVIEW ERROR"
        )

        print(
            "=============================="
        )

        print(
            traceback.format_exc()
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        # ----------------------------------------------------
        # DELETE TEMP FILE
        # ----------------------------------------------------

        if temp_path:

            try:

                if os.path.exists(temp_path):
                    os.remove(temp_path)

            except Exception as cleanup_error:

                print(
                    "Temporary file cleanup failed:",
                    cleanup_error
                )