import os
import traceback
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import pdfplumber
from google import genai


app = FastAPI()


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Gemini API Key
# --------------------------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")


# --------------------------------------------------
# PDF TEXT EXTRACTION
# --------------------------------------------------

def extract_text_from_pdf(file_path: str) -> str:
    text = ""

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()

            if extracted:
                text += extracted + "\n"

    return text.strip()


# --------------------------------------------------
# RESUME REVIEW API
# --------------------------------------------------

@app.post("/api/review-resume")
def review_resume(file: UploadFile = File(...)):

    # Check Gemini API key
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on the server."
        )

    # Check file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    temp_path = None

    try:

        # --------------------------------------------------
        # Save uploaded PDF temporarily
        # --------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as temp_file:

            temp_path = temp_file.name

            file_content = file.file.read()
            temp_file.write(file_content)


        # --------------------------------------------------
        # Extract resume text
        # --------------------------------------------------

        resume_text = extract_text_from_pdf(temp_path)

        if not resume_text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the PDF."
            )


        # --------------------------------------------------
        # Gemini Prompt
        # --------------------------------------------------

        prompt = f"""
You are a professional resume reviewer and career advisor.

Analyze the following resume carefully.

Provide the response in a clear and professional format.

Include:

1. Overall Resume Score out of 100
2. Key Strengths
3. Weaknesses / Missing Information
4. ATS Compatibility Analysis
5. Skills Analysis
6. Education Analysis
7. Experience / Projects Analysis
8. Specific Actionable Recommendations
9. A short improved summary/profile suggestion

Be honest and practical.
Do not invent information that is not present in the resume.

Resume Text:
-------------------------
{resume_text}
-------------------------
"""


        # --------------------------------------------------
        # Gemini Client
        # --------------------------------------------------

        client = genai.Client(
            api_key=API_KEY
        )


        # --------------------------------------------------
        # Generate AI Review
        # --------------------------------------------------

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )


        # --------------------------------------------------
        # Validate Gemini Response
        # --------------------------------------------------

        if not response or not response.text:
            raise HTTPException(
                status_code=500,
                detail="Gemini returned an empty response."
            )


        # --------------------------------------------------
        # Send result to frontend
        # --------------------------------------------------

        return {
            "analysis": response.text
        }


    except HTTPException:
        raise


    except Exception as e:

        error_details = traceback.format_exc()

        print("\n========== GEMINI / BACKEND ERROR ==========")
        print(error_details)
        print("============================================\n")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    finally:

        # --------------------------------------------------
        # Delete temporary PDF
        # --------------------------------------------------

        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass