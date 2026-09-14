import os
import traceback
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aapki key seedha yahan hardcode kar di hai taaki Render env issues na aayein
API_KEY = os.getenv("GEMINI_API_KEY")
def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

@app.post("/api/review-resume")
def review_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_path = f"temp_{file.filename}"
    
    try:
        # File save karna
        with open(temp_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        # PDF se text nikalna
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
        
        # Direct REST API call (Buggy Python SDK bypass kar diya)
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": API_KEY 
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        api_response = requests.post(url, headers=headers, json=payload)
        
        if api_response.status_code != 200:
            raise Exception(f"Gemini API Error: {api_response.text}")
            
        # Response parse karna
        response_data = api_response.json()
        analysis_text = response_data['candidates'][0]['content']['parts'][0]['text']
        
        return {"analysis": analysis_text}

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"CRASH DETAILS:\n{error_details}") 
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)