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

# Render Environment variable se API key fetch karna
API_KEY = os.getenv("GEMINI_API_KEY")

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

@app.post("/api/review-resume")
def review_resume(file: UploadFile = File(...)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not found in Render environment")
        
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_path = f"temp_{file.filename}"
    
    try:
        # 1. File save karna
        with open(temp_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        # 2. PDF se text extract karna
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
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        # 3. BULLETPROOF AUTO-FALLBACK: Alag-alag models try karega taaki 404 error na aaye
        models_to_try = ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-flash-latest"]
        api_response = None
        
        for model_name in models_to_try:
            # Header ki jagah URL parameter mein key bhej rahe hain (Sabse stable tareeka)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                api_response = response
                break  # Jaise hi success milega, loop ruk jayega
            else:
                print(f"Skipping {model_name} due to error: {response.status_code}")
                api_response = response # Aakhiri error ko save rakhega
        
        # Agar saare models fail ho jayein tab hi error throw karega
        if api_response.status_code != 200:
            raise Exception(f"Google API Error: {api_response.text}")
            
        # 4. JSON parse karke result nikalna
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