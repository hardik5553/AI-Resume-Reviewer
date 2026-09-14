import os
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
from google import genai  # Naya official SDK

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Render Environment se nayi AQ. key aayegi
API_KEY = os.getenv("GEMINI_API_KEY")

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

@app.post("/api/review-resume")
def review_resume(file: UploadFile = File(...)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not found in environment variables")
        
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_path = f"temp_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        resume_text = extract_text_from_pdf(temp_path)
        
        prompt = f"""
        Analyze this resume and provide:
        1. Overall score out of 100
        2. Key strengths
        3. Weaknesses or missing points
        4. Actionable recommendations
        
        Resume Text:
        {resume_text}
        """
        
        # Naya SDK jo AQ. keys ko natively handle karta hai
        client = genai.Client(api_key=API_KEY)
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        return {"analysis": response.text}

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"CRASH DETAILS:\n{error_details}") 
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)