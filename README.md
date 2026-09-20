# ✦ AI Resume Intelligence Platform

An advanced, full-stack AI career intelligence platform that transforms traditional resume parsing into actionable, multi-dimensional career strategy. Built to help candidates align their profiles with specific job descriptions, benchmark against industry standards, and generate ATS-optimized PDFs in real-time.

![AI Resume Intelligence](https://img.shields.io/badge/Status-Live-success)
![Version](https://img.shields.io/badge/Version-1.0-blue)
![React](https://img.shields.io/badge/Frontend-React%20%7C%20Tailwind-61DAFB?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-009688?logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/Database-MongoDB%20Atlas-47A248?logo=mongodb&logoColor=white)
![Gemini](https://img.shields.io/badge/AI_Engine-Google%20Gemini%203.6-8E75B2?logo=google&logoColor=white)

## 🚀 Enterprise-Grade Features

* **🔐 Smart Auth & History Dashboard:** 
  Secure user authentication powered by Clerk. Automatically saves all previous resume analyses to a MongoDB Atlas cluster, allowing users to reload and review past reports instantly from a dedicated dashboard.
* **🛠️ Interactive Resume Builder (Fix It Live):** 
  A dynamic, real-time editing interface where users can apply AI-suggested improvements directly to their bullet points. Includes a 1-click export to a perfectly formatted, single-column ATS-compliant PDF using `html2pdf.js`.
* **📈 Market Benchmarking & Analytics:** 
  Visually positions the candidate against industry standards using 6-dimension Multiaxial Radar Charts and comparative Bar Charts (powered by Recharts), calculating precise applicant percentiles.
* **🎯 Multi-Role Targeting & Alignment:** 
  Parallel suitability analysis that evaluates a single resume across multiple job profiles (e.g., Frontend, Backend, Full Stack). Provides dynamic highlighting, primary project spotlighting, and section re-ordering advice based on the active role.

## 💻 Tech Stack Architecture

* **Frontend:** React, Vite, Tailwind CSS, Clerk (Authentication), Recharts (Data Visualization), html2pdf.js (Client-side PDF Generation). Hosted on **Vercel**.
* **Backend:** Python, FastAPI, Uvicorn, Google Gemini AI API, pdfplumber (Text Extraction). Hosted on **Render**.
* **Database:** MongoDB Atlas (NoSQL) with PyMongo integration for secure user report storage.

## ⚙️ Local Development Setup

### 1. Clone the repository
```bash
git clone [https://github.com/hardik5553/ai-resume-intelligence.git](https://github.com/hardik5553/ai-resume-intelligence.git)
cd ai-resume-intelligence
```
### 2. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Create a .env file in the backend directory:
# GEMINI_API_KEY=your_google_ai_studio_key
# MONGO_URI=your_mongodb_atlas_connection_string

uvicorn main:app --reload
```
### 3. Frontend Setup
```
cd frontend
npm install

# Create a .env.local file in the frontend directory:
# VITE_CLERK_PUBLISHABLE_KEY=your_clerk_key

npm run dev
```
### 📝 Resume Integration Guide
(Feel free to use these bullet points in your own resume to showcase this project)

Architected a full-stack AI Resume Intelligence platform using React, Tailwind CSS, and FastAPI, integrating the Google Gemini API to provide automated career insights, keyword matching, and multi-role targeting.

Engineered a real-time Interactive Resume Builder with client-side ATS-compliant PDF generation, enhancing user engagement and actionable resume restructuring.

Implemented MongoDB Atlas and Clerk authentication for secure data persistence, rendering complex multidimensional benchmarking analytics via Recharts.

Developed by: Hardik Soni


