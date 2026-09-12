import React, { useState } from 'react';
import axios from 'axios';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [fileName, setFileName] = useState('');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please upload a PDF resume first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setResult('');
    try {
      const response = await axios.post("http://localhost:8000/api/review-resume", formData);
      setResult(response.data.analysis);
    } catch (error) {
      console.error(error);
      alert("Failed to analyze resume. Ensure backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-700/60 bg-slate-900/50 backdrop-blur-md sticky top-0 z-10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-xl text-white font-bold shadow-lg shadow-indigo-500/30">
            ✨
          </div>
          <span className="text-xl font-bold tracking-wide bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            AI Resume Intelligence
          </span>
        </div>
        <span className="text-xs uppercase tracking-wider bg-slate-800 border border-slate-700 px-3 py-1 rounded-full text-indigo-300">
          Gemini 2.5 Flash Engine
        </span>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-10 flex flex-col gap-8">
        <div className="text-center space-y-2">
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-white">
            Elevate Your Career with <span className="text-indigo-400">AI Precision</span>
          </h1>
          <p className="text-slate-400 text-sm md:text-base max-w-xl mx-auto">
            Upload your resume to get deep professional insights, formatting analysis, and actionable improvement suggestions instantly.
          </p>
        </div>

        {/* Upload Card */}
        <form onSubmit={handleSubmit} className="bg-slate-800/60 border border-slate-700/80 backdrop-blur-xl p-8 rounded-2xl shadow-2xl flex flex-col gap-6">
          <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-600 hover:border-indigo-500 transition rounded-xl p-8 bg-slate-900/40 relative cursor-pointer group">
            <input 
              type="file" 
              accept=".pdf" 
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />
            <div className="flex flex-col items-center text-center gap-2 pointer-events-none">
              <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition">
                📄
              </div>
              <p className="text-sm font-medium text-slate-200">
                {fileName ? <span className="text-indigo-300 font-semibold">{fileName}</span> : "Drop your PDF resume here, or browse"}
              </p>
              <p className="text-xs text-slate-400">Supports PDF format up to 10MB</p>
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 text-white font-semibold py-3 px-6 rounded-xl shadow-lg shadow-indigo-600/30 hover:opacity-95 transition-all duration-200 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                Analyzing Profile...
              </>
            ) : (
              "Generate AI Review"
            )}
          </button>
        </form>

        {/* Results Section */}
        {result && (
          <div className="bg-slate-800/80 border border-slate-700/80 backdrop-blur-xl p-6 md:p-8 rounded-2xl shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-700 pb-4 mb-6">
              <h2 className="text-lg font-bold text-indigo-300 flex items-center gap-2">
                📊 Comprehensive Evaluation Report
              </h2>
              <button 
                onClick={() => navigator.clipboard.writeText(result)}
                className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1.5 rounded-lg transition"
              >
                Copy Report
              </button>
            </div>
            <div className="whitespace-pre-wrap text-slate-300 text-sm md:text-base leading-relaxed bg-slate-900/50 p-6 rounded-xl border border-slate-800">
              {result}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}