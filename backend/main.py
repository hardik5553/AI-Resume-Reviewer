import os
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key setup
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# FIX: 'async def' ko hata kar sirf 'def' kiya gaya hai taaki ASGI crash na ho
@app.post("/api/review-resume")
def review_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_path = f"temp_{file.filename}"
    
    try:
        # FIX: await file.read() ki jagah file.file.read() use kiya hai (synchronous read)
        with open(temp_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        # Extract text from PDF
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
        
        # Call Gemini API
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return {"analysis": response.text}

    except Exception as e:
        # CRASH CATCHER: Ab agar API key ya PDF mein koi bhi issue aaya, toh log mein saaf dikhega
        error_details = traceback.format_exc()
        print(f"CRASH DETAILS:\n{error_details}") 
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)