import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Yahan apni API key seedha quotes mein daal dein
import os
API_KEY = os.getenv("GEMINI_API_KEY")
def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

@app.post("/api/review-resume")
async def review_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        resume_text = extract_text_from_pdf(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    prompt = f"""
    Analyze this resume and provide:
    1. Overall score out of 100
    2. Key strengths
    3. Weaknesses or missing points
    4. Actionable recommendations
    
    Resume Text:
    {resume_text}
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return {"analysis": response.text}