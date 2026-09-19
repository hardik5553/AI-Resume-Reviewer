import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton, useUser } from "@clerk/clerk-react";
import html2pdf from "html2pdf.js";

const BACKEND_URL =
  "https://ai-resume-reviewer-e412.onrender.com/api/review-resume";
const GET_REPORTS_URL = 
  "https://ai-resume-reviewer-e412.onrender.com/api/user-reports";

export default function App() {
  const { user } = useUser(); // NEW: Clerk se current user laane ke liye
  
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);

  // Backend structured result
  const [structured, setStructured] = useState(null);

  // Old text response
  const [result, setResult] = useState("");

  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  // =========================================================
  // DASHBOARD STATES & FETCH LOGIC (NEW)
  // =========================================================
  const [showDashboard, setShowDashboard] = useState(false);
  const [reportsList, setReportsList] = useState([]);
  const [loadingReports, setLoadingReports] = useState(false);

  // =========================================================
  // FEATURE 2: INTERACTIVE RESUME BUILDER (FIX IT LIVE) STATES
  // =========================================================
  const [showBuilder, setShowBuilder] = useState(false);
  const resumePrintRef = useRef(null);

  const [builderData, setBuilderData] = useState({
    fullName: "Your Full Name",
    email: "email@example.com",
    phone: "+91 XXXXXXXXXX",
    location: "India",
    summary: "",
    technicalSkills: "",
    softSkills: "",
    experience: [],
    projects: [],
    education: []
  });

  // Automatically pre-fill builder when analysis result arrives
  useEffect(() => {
    if (structured) {
      setBuilderData({
        fullName: user?.fullName || "Your Full Name",
        email: user?.primaryEmailAddress?.emailAddress || "email@example.com",
        phone: "+91 9876543210",
        location: "India",
        summary: structured.summary || "",
        technicalSkills: (structured.skills?.technical || []).join(", "),
        softSkills: (structured.skills?.soft || []).join(", "),
        experience: structured.experience?.points && structured.experience.points.length > 0 
          ? [...structured.experience.points] 
          : [
              "Engineered scalable backend REST APIs improving service performance by 25%.",
              "Integrated real-time database management and client authentication modules."
            ],
        projects: structured.projects?.points && structured.projects.points.length > 0 
          ? [...structured.projects.points] 
          : [
              "AI Resume Intelligence: Developed full-stack analysis engine with automated scoring."
            ],
        education: structured.education?.points && structured.education.points.length > 0 
          ? [...structured.education.points] 
          : [
              "Bachelor of Technology in Information Technology"
            ]
      });
    }
  }, [structured, user]);

  const exportAtsPdf = () => {
    const element = resumePrintRef.current;
    if (!element) return;

    const opt = {
      margin: [10, 10, 10, 10],
      filename: `${builderData.fullName.trim().replace(/\s+/g, "_")}_ATS_Optimized_Resume.pdf`,
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, letterRendering: true },
      jsPDF: { unit: "mm", format: "a4", orientation: "portrait" }
    };

    html2pdf().set(opt).from(element).save();
  };

  const fetchUserReports = async () => {
    if (!user || !user.id) return;
    
    setLoadingReports(true);
    try {
      const response = await axios.get(`${GET_REPORTS_URL}?user_id=${user.id}`);
      if (response.data?.success) {
        setReportsList(response.data.reports);
      }
    } catch (err) {
      console.error("Error fetching reports:", err);
    } finally {
      setLoadingReports(false);
    }
  };

  // Jab dashboard open ho tab API call karo
  useEffect(() => {
    if (showDashboard && user) {
      fetchUserReports();
    }
  }, [showDashboard, user]);

  const loadPastReport = (report) => {
    setFileName(report.file_name);
    setJobDescription(report.job_description || "");
    setStructured(report.structured_data);
    setResult(""); 
    setShowDashboard(false);
    setShowBuilder(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // =========================================================
  // FILE SELECTION
  // =========================================================

  const selectFile = (selectedFile) => {
    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF resume.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("PDF must be smaller than 10MB.");
      return;
    }

    setFile(selectedFile);
    setFileName(selectedFile.name);
    setStructured(null);
    setResult("");
    setError("");
  };

  const handleFileChange = (e) => {
    selectFile(e.target.files[0]);
  };

  // =========================================================
  // DRAG & DROP
  // =========================================================

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);

    const droppedFile = e.dataTransfer.files[0];
    selectFile(droppedFile);
  };

  // =========================================================
  // ANALYZE RESUME
  // =========================================================

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError("Please upload your PDF resume first.");
      return;
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append("job_description", jobDescription);
    
    // NEW: Agar user logged in hai, toh user_id backend ko bhejo
    if (user && user.id) {
      formData.append("user_id", user.id);
    }

    setLoading(true);
    setError("");
    setStructured(null);
    setResult("");

    try {
      const response = await axios.post(
        BACKEND_URL,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 180000,
        }
      );

      console.log("BACKEND RESPONSE:", response.data);

      if (response.data?.structured) {
        setStructured(response.data.structured);
        setResult(response.data.analysis || "");
      } else if (response.data?.analysis) {
        setResult(response.data.analysis);
        setError(
          "Resume analyzed, but structured result was not returned."
        );
      } else {
        setError("AI returned an empty analysis.");
      }
    } catch (err) {
      console.error("Resume Analysis Error:", err);

      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (err.code === "ECONNABORTED") {
        setError(
          "The AI server is taking longer than expected. Please try again."
        );
      } else {
        setError(
          "Unable to connect with the AI server. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // SCORE HELPERS
  // =========================================================

  const safeScore = (value) => {
    const number = Number(value);

    if (Number.isNaN(number)) return null;

    return Math.min(100, Math.max(0, number));
  };

  const overallScore = safeScore(structured?.overallScore);
  const atsScore = safeScore(structured?.ats?.score);
  const skillsScore = safeScore(structured?.skills?.score);
  const experienceScore = safeScore(structured?.experience?.score);
  const projectsScore = safeScore(structured?.projects?.score);
  const educationScore = safeScore(structured?.education?.score);
  const jobMatchScore = safeScore(structured?.jobMatch?.score);

  // =========================================================
  // SCORE MESSAGE
  // =========================================================

  const getScoreMessage = () => {
    if (overallScore === null) return "Resume Analysis";

    if (overallScore >= 90) return "Exceptional Resume 🚀";
    if (overallScore >= 85) return "Excellent Resume 🔥";
    if (overallScore >= 75) return "Strong Resume 💪";
    if (overallScore >= 65) return "Good Foundation 👍";
    if (overallScore >= 50) return "Needs Improvement ⚡";

    return "Major Improvements Needed 🔧";
  };

  // =========================================================
  // SCORE COLOR
  // =========================================================

  const getScoreColor = (value) => {
    if (value === null) return "text-slate-400";
    if (value >= 85) return "text-emerald-400";
    if (value >= 70) return "text-cyan-400";
    if (value >= 50) return "text-yellow-400";

    return "text-red-400";
  };

  // =========================================================
  // COPY REPORT
  // =========================================================

  const copyReport = async () => {
    try {
      const report = JSON.stringify(
        structured,
        null,
        2
      );

      await navigator.clipboard.writeText(report);

      alert("Report copied successfully!");
    } catch {
      alert("Unable to copy report.");
    }
  };

  // =========================================================
  // DOWNLOAD REPORT
  // =========================================================

  const downloadReport = () => {
    const content = `
AI RESUME INTELLIGENCE
================================

Resume:
${fileName}

TARGET JOB DESCRIPTION:
${jobDescription || "Not provided"}

OVERALL SCORE:
${overallScore ?? "N/A"}/100

JOB MATCH SCORE:
${jobMatchScore ?? "N/A"}/100

SUMMARY:
${structured?.summary || "N/A"}

STRENGTHS:
${(structured?.strengths || [])
  .map((item) => `- ${item}`)
  .join("\n")}

WEAKNESSES:
${(structured?.weaknesses || [])
  .map((item) => `- ${item}`)
  .join("\n")}

JOB MATCH ANALYSIS:
${structured?.jobMatch?.summary || "N/A"}

Matched Keywords:
${(structured?.jobMatch?.matchedKeywords || [])
  .map((item) => `- ${item}`)
  .join("\n")}

Missing Keywords:
${(structured?.jobMatch?.missingKeywords || [])
  .map((item) => `- ${item}`)
  .join("\n")}

Job Specific Recommendations:
${(structured?.jobMatch?.recommendations || [])
  .map((item) => `- ${item}`)
  .join("\n")}

SKILLS:
Score: ${skillsScore ?? "N/A"}/100

Technical:
${(structured?.skills?.technical || [])
  .map((item) => `- ${item}`)
  .join("\n")}

Soft:
${(structured?.skills?.soft || [])
  .map((item) => `- ${item}`)
  .join("\n")}

Missing:
${(structured?.skills?.missing || [])
  .map((item) => `- ${item}`)
  .join("\n")}

EXPERIENCE:
Score: ${experienceScore ?? "N/A"}/100

${(structured?.experience?.points || [])
  .map((item) => `- ${item}`)
  .join("\n")}

PROJECTS:
Score: ${projectsScore ?? "N/A"}/100

${(structured?.projects?.points || [])
  .map((item) => `- ${item}`)
  .join("\n")}

EDUCATION:
Score: ${educationScore ?? "N/A"}/100

${(structured?.education?.points || [])
  .map((item) => `- ${item}`)
  .join("\n")}

ATS:
Score: ${atsScore ?? "N/A"}/100

Keywords:
${(structured?.ats?.keywords || [])
  .map((item) => `- ${item}`)
  .join("\n")}

Formatting:
${(structured?.ats?.formatting || [])
  .map((item) => `- ${item}`)
  .join("\n")}

ATS Issues:
${(structured?.ats?.issues || [])
  .map((item) => `- ${item}`)
  .join("\n")}

GENERAL RECOMMENDATIONS:
${(structured?.recommendations || [])
  .map((item) => `- ${item}`)
  .join("\n")}

FINAL VERDICT:
${structured?.verdict || "N/A"}

================================
Generated by AI Resume Intelligence
`;

    const blob = new Blob(
      [content],
      {
        type: "text/plain;charset=utf-8",
      }
    );

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download =
      "AI-Resume-Intelligence-Report.txt";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };

  // =========================================================
  // RESET
  // =========================================================

  const resetAnalysis = () => {
    setFile(null);
    setFileName("");
    setJobDescription("");
    setStructured(null);
    setResult("");
    setError("");
    setLoading(false);
    setShowBuilder(false);
  };

  // =========================================================
  // SCORE MINI CARD
  // =========================================================

  const ScoreMiniCard = ({
    title,
    value,
    icon,
  }) => {
    return (
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 hover:border-indigo-500/40 transition">
        <div className="flex items-center justify-between">
          <span className="text-2xl">
            {icon}
          </span>

          <span
            className={`text-2xl font-black ${
              value !== null
                ? getScoreColor(value)
                : "text-slate-500"
            }`}
          >
            {value !== null ? `${value}%` : "—"}
          </span>
        </div>

        <p className="mt-3 text-sm font-semibold text-white">
          {title}
        </p>

        <div className="mt-3 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-cyan-400 rounded-full transition-all duration-1000"
            style={{
              width: `${value ?? 0}%`,
            }}
          />
        </div>
      </div>
    );
  };

  // =========================================================
  // LIST
  // =========================================================

  const ListItems = ({ items }) => {
    if (!items || items.length === 0) {
      return (
        <p className="text-slate-500">
          No specific information provided.
        </p>
      );
    }

    return (
      <ul className="space-y-3">
        {items.map((item, index) => (
          <li
            key={`${item}-${index}`}
            className="flex gap-3"
          >
            <span className="text-indigo-400 mt-1">
              •
            </span>

            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
  };

  // =========================================================
  // SECTION CARD
  // =========================================================

  const SectionCard = ({
    title,
    icon,
    children,
    wide = false,
  }) => {
    return (
      <div
        className={`bg-slate-900/70 border border-slate-700/70 rounded-2xl p-5 md:p-6 
        hover:border-indigo-500/50 hover:bg-slate-900/90 
        transition-all duration-300 
        ${wide ? "md:col-span-2" : ""}`}
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-xl">
            {icon}
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-white mb-4">
              {title}
            </h3>

            <div className="text-sm md:text-base text-slate-300 leading-7">
              {children}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // =========================================================
  // UI
  // =========================================================

  return (
    <div className="min-h-screen bg-[#070b16] text-slate-100 overflow-x-hidden">

      {/* BACKGROUND */}

      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl" />

        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />

        <div className="absolute bottom-0 left-1/3 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl" />
      </div>

      {/* HEADER */}

      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-[#070b16]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-5 md:px-8 py-4 flex items-center justify-between">

          <div className="flex items-center gap-3">

            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/20">
              ✦
            </div>

            <div>
              <h1 
                className="font-bold text-white tracking-tight cursor-pointer"
                onClick={() => { setShowDashboard(false); setShowBuilder(false); }}
              >
                AI Resume Intelligence
              </h1>

              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Career Intelligence Platform
              </p>
            </div>

          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-slate-400">
                AI Engine Online
              </span>
            </div>

            {/* CLERK AUTHENTICATION BUTTONS */}
            <div className="ml-2 pl-4 border-l border-slate-700/50 flex items-center h-full gap-4">
              <SignedOut>
                <SignInButton mode="modal">
                  <button className="text-slate-300 hover:text-white text-sm font-semibold transition-colors">
                    Sign In
                  </button>
                </SignInButton>
                
                <SignUpButton mode="modal">
                  <button className="px-4 py-1.5 rounded-lg bg-indigo-600 border border-indigo-500 text-white text-sm font-semibold hover:bg-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-500/20">
                    Sign Up
                  </button>
                </SignUpButton>
              </SignedOut>
              <SignedIn>
                {/* MY REPORTS BUTTON */}
                <button 
                  onClick={() => { setShowDashboard(!showDashboard); setShowBuilder(false); }}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 hover:border-indigo-500/50 text-slate-300 hover:text-white text-sm font-semibold transition-all duration-300"
                >
                  {showDashboard ? "Back to Analysis" : "My Reports"}
                </button>
                <UserButton appearance={{ elements: { avatarBox: "w-9 h-9" } }} />
              </SignedIn>
            </div>
          </div>

        </div>
      </header>

      {/* MAIN */}

      <main className="relative max-w-6xl mx-auto px-5 md:px-8 py-10 md:py-16">

        {/* =====================================================
            DASHBOARD VIEW
        ===================================================== */}
        {showDashboard ? (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-3xl font-black text-white flex items-center gap-3">
                <span>📁</span> My Analysis History
              </h2>
            </div>

            {loadingReports ? (
              <div className="text-center py-20">
                <span className="w-8 h-8 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto block mb-4" />
                <p className="text-slate-400">Loading your past reports...</p>
              </div>
            ) : reportsList.length === 0 ? (
              <div className="text-center py-20 bg-slate-900/50 border border-slate-800 rounded-3xl">
                <div className="text-5xl mb-4">📭</div>
                <h3 className="text-xl font-bold text-white mb-2">No Reports Found</h3>
                <p className="text-slate-400 mb-6">You haven't analyzed any resumes yet.</p>
                <button 
                  onClick={() => setShowDashboard(false)}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 text-white font-semibold hover:bg-indigo-500 transition-colors"
                >
                  Analyze First Resume
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {reportsList.map((report) => (
                  <div 
                    key={report._id} 
                    className="bg-slate-900/70 border border-slate-700 rounded-2xl p-5 hover:border-indigo-500/50 hover:bg-slate-900 cursor-pointer transition-all duration-300 group"
                    onClick={() => loadPastReport(report)}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-xl border border-indigo-500/20">
                        📄
                      </div>
                      <div className="text-right">
                        <span className={`text-xl font-black ${getScoreColor(report.overall_score)}`}>
                          {report.overall_score}/100
                        </span>
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">Overall</p>
                      </div>
                    </div>
                    
                    <h4 className="font-bold text-white truncate mb-1" title={report.file_name}>
                      {report.file_name}
                    </h4>
                    
                    <p className="text-xs text-slate-400 mb-4 line-clamp-2">
                      {report.job_description ? `Role: ${report.job_description}` : "No specific role targeted"}
                    </p>
                    
                    <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                      <span className="text-xs text-slate-500">
                        {new Date(report.created_at).toLocaleDateString()}
                      </span>
                      <span className="text-xs font-semibold text-indigo-400 group-hover:text-indigo-300 flex items-center gap-1">
                        View Report <span className="text-lg leading-none">→</span>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        ) : showBuilder ? (
          /* =====================================================
              FEATURE 2: INTERACTIVE RESUME BUILDER (FIX IT LIVE)
          ===================================================== */
          <section className="animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4 mb-8">
              <div>
                <h2 className="text-3xl font-black text-white flex items-center gap-3">
                  <span>🛠️</span> Interactive Resume Builder (Fix It Live)
                </h2>
                <p className="text-sm text-slate-400 mt-1">
                  AI insights apply karke bullet points edit karo aur ATS-friendly formatted PDF export karo.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowBuilder(false)}
                  className="px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-900 text-slate-300 hover:text-white transition"
                >
                  ← Back to Report
                </button>
                <button
                  onClick={exportAtsPdf}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 font-bold text-white shadow-lg shadow-emerald-500/20 hover:brightness-110 transition flex items-center gap-2"
                >
                  📥 Export ATS PDF
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
              {/* EDITING FORM */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 md:p-8 space-y-6 backdrop-blur-xl">
                <h3 className="text-lg font-bold text-white flex items-center gap-2 pb-2 border-b border-slate-800">
                  <span>✏️</span> Actionable Live Editing
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Full Name</label>
                    <input
                      type="text"
                      value={builderData.fullName}
                      onChange={(e) => setBuilderData({ ...builderData, fullName: e.target.value })}
                      className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Email Address</label>
                    <input
                      type="text"
                      value={builderData.email}
                      onChange={(e) => setBuilderData({ ...builderData, email: e.target.value })}
                      className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Phone Number</label>
                    <input
                      type="text"
                      value={builderData.phone}
                      onChange={(e) => setBuilderData({ ...builderData, phone: e.target.value })}
                      className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Location / City</label>
                    <input
                      type="text"
                      value={builderData.location}
                      onChange={(e) => setBuilderData({ ...builderData, location: e.target.value })}
                      className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400">Professional Summary</label>
                  <textarea
                    rows={3}
                    value={builderData.summary}
                    onChange={(e) => setBuilderData({ ...builderData, summary: e.target.value })}
                    className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 p-3 text-sm text-white focus:border-indigo-500 outline-none resize-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400">Technical Skills (Comma separated)</label>
                  <input
                    type="text"
                    value={builderData.technicalSkills}
                    onChange={(e) => setBuilderData({ ...builderData, technicalSkills: e.target.value })}
                    className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400">Soft Skills</label>
                  <input
                    type="text"
                    value={builderData.softSkills}
                    onChange={(e) => setBuilderData({ ...builderData, softSkills: e.target.value })}
                    className="mt-1 w-full rounded-xl bg-slate-950/80 border border-slate-700 px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none"
                  />
                </div>

                {/* EXPERIENCE EDITING */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-xs font-semibold text-slate-400">Experience & Achievements Points</label>
                    <button
                      onClick={() => setBuilderData({ ...builderData, experience: [...builderData.experience, "Implemented performant microservice architecture reducing response times by 30%."] })}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      + Add Point
                    </button>
                  </div>
                  <div className="space-y-2">
                    {builderData.experience.map((exp, idx) => (
                      <div key={idx} className="flex gap-2 items-start">
                        <textarea
                          rows={2}
                          value={exp}
                          onChange={(e) => {
                            const updated = [...builderData.experience];
                            updated[idx] = e.target.value;
                            setBuilderData({ ...builderData, experience: updated });
                          }}
                          className="w-full rounded-xl bg-slate-950/80 border border-slate-700 p-2.5 text-sm text-white focus:border-indigo-500 outline-none resize-none"
                        />
                        <button
                          onClick={() => {
                            const updated = builderData.experience.filter((_, i) => i !== idx);
                            setBuilderData({ ...builderData, experience: updated });
                          }}
                          className="text-slate-500 hover:text-red-400 text-sm px-2 pt-2 transition"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* PROJECTS EDITING */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-xs font-semibold text-slate-400">Key Projects</label>
                    <button
                      onClick={() => setBuilderData({ ...builderData, projects: [...builderData.projects, "Built high-availability cloud application deployed on Render and AWS."] })}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      + Add Project
                    </button>
                  </div>
                  <div className="space-y-2">
                    {builderData.projects.map((proj, idx) => (
                      <div key={idx} className="flex gap-2 items-start">
                        <textarea
                          rows={2}
                          value={proj}
                          onChange={(e) => {
                            const updated = [...builderData.projects];
                            updated[idx] = e.target.value;
                            setBuilderData({ ...builderData, projects: updated });
                          }}
                          className="w-full rounded-xl bg-slate-950/80 border border-slate-700 p-2.5 text-sm text-white focus:border-indigo-500 outline-none resize-none"
                        />
                        <button
                          onClick={() => {
                            const updated = builderData.projects.filter((_, i) => i !== idx);
                            setBuilderData({ ...builderData, projects: updated });
                          }}
                          className="text-slate-500 hover:text-red-400 text-sm px-2 pt-2 transition"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* EDUCATION EDITING */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-xs font-semibold text-slate-400">Education Details</label>
                    <button
                      onClick={() => setBuilderData({ ...builderData, education: [...builderData.education, "Bachelor of Technology in Computer Science & Engineering"] })}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      + Add Education
                    </button>
                  </div>
                  <div className="space-y-2">
                    {builderData.education.map((edu, idx) => (
                      <div key={idx} className="flex gap-2 items-start">
                        <textarea
                          rows={1}
                          value={edu}
                          onChange={(e) => {
                            const updated = [...builderData.education];
                            updated[idx] = e.target.value;
                            setBuilderData({ ...builderData, education: updated });
                          }}
                          className="w-full rounded-xl bg-slate-950/80 border border-slate-700 p-2.5 text-sm text-white focus:border-indigo-500 outline-none resize-none"
                        />
                        <button
                          onClick={() => {
                            const updated = builderData.education.filter((_, i) => i !== idx);
                            setBuilderData({ ...builderData, education: updated });
                          }}
                          className="text-slate-500 hover:text-red-400 text-sm px-2 pt-2 transition"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* LIVE ATS PREVIEW PANEL (Rendered to PDF) */}
              <div className="sticky top-24">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                    Live ATS Compliant Preview
                  </h3>
                  <span className="text-[11px] text-emerald-400 font-medium">
                    ✓ Clean Single-Column Layout
                  </span>
                </div>

                <div
                  ref={resumePrintRef}
                  className="bg-white text-slate-950 p-8 rounded-lg shadow-2xl font-sans text-xs leading-relaxed"
                  style={{ minHeight: "700px", fontFamily: "Arial, Helvetica, sans-serif" }}
                >
                  {/* RESUME HEADER */}
                  <div className="text-center border-b pb-3 mb-4 border-slate-300">
                    <h1 className="text-xl font-bold tracking-wider uppercase text-slate-900">
                      {builderData.fullName}
                    </h1>
                    <p className="text-slate-600 mt-1 text-[11px]">
                      {builderData.email} • {builderData.phone} • {builderData.location}
                    </p>
                  </div>

                  {/* SUMMARY */}
                  {builderData.summary && (
                    <div className="mb-4">
                      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-400 pb-0.5 mb-1.5">
                        Professional Summary
                      </h2>
                      <p className="text-slate-800 text-[11px] leading-normal text-justify">
                        {builderData.summary}
                      </p>
                    </div>
                  )}

                  {/* TECHNICAL SKILLS */}
                  {(builderData.technicalSkills || builderData.softSkills) && (
                    <div className="mb-4">
                      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-400 pb-0.5 mb-1.5">
                        Core Competencies & Skills
                      </h2>
                      {builderData.technicalSkills && (
                        <p className="text-slate-800 text-[11px]">
                          <strong>Technical:</strong> {builderData.technicalSkills}
                        </p>
                      )}
                      {builderData.softSkills && (
                        <p className="text-slate-800 text-[11px] mt-0.5">
                          <strong>Professional:</strong> {builderData.softSkills}
                        </p>
                      )}
                    </div>
                  )}

                  {/* EXPERIENCE */}
                  {builderData.experience?.length > 0 && (
                    <div className="mb-4">
                      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-400 pb-0.5 mb-1.5">
                        Experience & Key Contributions
                      </h2>
                      <ul className="list-disc pl-4 space-y-1 text-slate-800 text-[11px]">
                        {builderData.experience.map((exp, i) => (
                          <li key={i}>{exp}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* PROJECTS */}
                  {builderData.projects?.length > 0 && (
                    <div className="mb-4">
                      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-400 pb-0.5 mb-1.5">
                        Featured Projects
                      </h2>
                      <ul className="list-disc pl-4 space-y-1 text-slate-800 text-[11px]">
                        {builderData.projects.map((proj, i) => (
                          <li key={i}>{proj}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* EDUCATION */}
                  {builderData.education?.length > 0 && (
                    <div className="mb-4">
                      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-400 pb-0.5 mb-1.5">
                        Education
                      </h2>
                      <ul className="list-disc pl-4 space-y-1 text-slate-800 text-[11px]">
                        {builderData.education.map((edu, i) => (
                          <li key={i}>{edu}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>
        ) : (

        /* =====================================================
            NORMAL UPLOAD & RESULT VIEW
        ===================================================== */
        <>
          {/* UPLOAD SCREEN */}
          {!structured && (
            <>
              {/* HERO */}

              <section className="text-center max-w-3xl mx-auto mb-10">

                <div className="inline-flex items-center gap-2 px-4 py-2 mb-5 rounded-full border border-indigo-500/20 bg-indigo-500/5 text-indigo-300 text-xs font-medium">
                  ✨ AI-Powered Career Intelligence
                </div>

                <h2 className="text-4xl md:text-6xl font-black tracking-tight leading-tight text-white">
                  Turn Your Resume Into

                  <span className="block bg-gradient-to-r from-indigo-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
                    Your Career Advantage.
                  </span>
                </h2>

                <p className="mt-5 text-slate-400 text-sm md:text-base leading-7 max-w-2xl mx-auto">
                  Analyze your resume, discover missing skills
                  and get actionable career insights.
                </p>

              </section>

              {/* UPLOAD */}

              <section className="max-w-3xl mx-auto">

                <form
                  onSubmit={handleSubmit}
                  className="bg-slate-900/70 border border-slate-800 rounded-3xl p-5 md:p-7 shadow-2xl shadow-black/20 backdrop-blur-xl"
                >

                  {/* RESUME */}

                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`relative rounded-2xl border-2 border-dashed p-8 md:p-12 text-center transition-all duration-300 ${
                      dragActive
                        ? "border-indigo-400 bg-indigo-500/10 scale-[1.01]"
                        : "border-slate-700 bg-slate-950/50 hover:border-indigo-500/50"
                    }`}
                  >

                    <input
                      type="file"
                      accept=".pdf"
                      onChange={handleFileChange}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />

                    <div className="pointer-events-none">

                      <div className="mx-auto mb-5 w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/10 border border-indigo-500/20 flex items-center justify-center text-3xl">
                        📄
                      </div>

                      {fileName ? (
                        <>
                          <p className="text-indigo-300 font-semibold break-all">
                            {fileName}
                          </p>

                          <p className="mt-2 text-xs text-emerald-400">
                            ✓ Resume ready for analysis
                          </p>
                        </>
                      ) : (
                        <>
                          <p className="text-white font-semibold text-lg">
                            Drop your resume here
                          </p>

                          <p className="text-slate-500 text-sm mt-2">
                            or click to browse from your computer
                          </p>
                        </>
                      )}

                      <p className="text-xs text-slate-600 mt-4">
                        PDF only • Maximum 10MB
                      </p>

                    </div>
                  </div>

                  {/* JOB DESCRIPTION */}

                  <div className="mt-6">

                    <div className="flex items-center justify-between mb-3">

                      <div>
                        <label className="text-sm font-bold text-white">
                          🎯 Target Job Description
                        </label>

                        <p className="text-xs text-slate-500 mt-1">
                          Paste a real job posting for personalized matching.
                        </p>
                      </div>

                      <span className="text-xs text-slate-600">
                        {jobDescription.length}/5000
                      </span>

                    </div>

                    <textarea
                      value={jobDescription}
                      onChange={(e) =>
                        setJobDescription(
                          e.target.value.slice(0, 5000)
                        )
                      }
                      placeholder={`Paste the job description here...

Example:

Java Developer

Spring Boot
REST APIs
MongoDB
SQL
Git
Problem Solving...`}
                      rows={8}
                      className="w-full resize-none rounded-2xl bg-slate-950/70 border border-slate-700 p-4 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/10 transition"
                    />

                    <p className="mt-2 text-xs text-slate-600">
                      💡 Tip: A real job posting gives better match insights.
                    </p>

                  </div>

                  {/* ERROR */}

                  {error && (
                    <div className="mt-4 p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-red-300 text-sm">
                      ⚠️ {error}
                    </div>
                  )}

                  {/* BUTTON */}

                  <button
                    type="submit"
                    disabled={loading}
                    className="mt-5 w-full py-4 rounded-xl font-bold text-white bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 shadow-lg shadow-indigo-600/20 transition-all duration-300 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                  >

                    {loading ? (
                      <>
                        <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />

                        AI is analyzing your career profile...
                      </>
                    ) : (
                      <>
                        ✨ Analyze Resume
                      </>
                    )}

                  </button>

                </form>

                {/* LOADING */}

                {loading && (
                  <div className="mt-6 text-center">

                    <p className="text-sm text-slate-400">
                      🔍 Analyzing your resume...
                    </p>

                    <p className="text-xs text-slate-600 mt-1">
                      AI is preparing your personalized career intelligence report.
                    </p>

                  </div>
                )}

              </section>
            </>
          )}

          {/* =====================================================
              RESULTS SCREEN
          ===================================================== */}

          {structured && !loading && (

            <section className="mt-12">

              {/* REPORT HEADER */}

              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

                <div>

                  <div className="flex items-center gap-2">

                    <span className="text-2xl">
                      📊
                    </span>

                    <h2 className="text-2xl md:text-3xl font-black text-white">
                      Career Intelligence Report
                    </h2>

                  </div>

                  <p className="text-sm text-slate-500 mt-2">
                    AI-generated insights for {fileName}
                  </p>

                </div>

                <div className="flex flex-wrap gap-2">

                  {/* FEATURE 2: OPEN INTERACTIVE RESUME BUILDER */}
                  <button
                    onClick={() => setShowBuilder(true)}
                    className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 text-sm font-bold text-white hover:brightness-110 shadow-lg shadow-indigo-500/20 transition flex items-center gap-2"
                  >
                    🛠️ Fix It Live (Builder)
                  </button>

                  <button
                    onClick={copyReport}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-slate-300 hover:text-white hover:border-indigo-500/40 transition"
                  >
                    📋 Copy
                  </button>

                  <button
                    onClick={downloadReport}
                    className="px-4 py-2.5 rounded-xl bg-indigo-600 text-sm font-semibold text-white hover:bg-indigo-500 transition"
                  >
                    ↓ Download
                  </button>

                </div>

              </div>

              {/* MAIN SCORE */}

              {overallScore !== null && (

                <div className="mb-6 bg-gradient-to-br from-indigo-950/60 to-slate-900/80 border border-indigo-500/20 rounded-3xl p-6 md:p-8">

                  <div className="flex flex-col md:flex-row items-center gap-8">

                    <div
                      className="w-36 h-36 rounded-full flex items-center justify-center"
                      style={{
                        background: `conic-gradient(#6366f1 ${
                          overallScore * 3.6
                        }deg, #1e293b 0deg)`,
                      }}
                    >

                      <div className="w-28 h-28 rounded-full bg-[#0b1020] flex flex-col items-center justify-center">

                        <span className="text-4xl font-black text-white">
                          {overallScore}
                        </span>

                        <span className="text-xs text-slate-500">
                          OUT OF 100
                        </span>

                      </div>

                    </div>

                    <div className="text-center md:text-left">

                      <p className="text-xs uppercase tracking-[0.2em] text-indigo-400 font-bold">
                        Overall Resume Score
                      </p>

                      <h3 className="text-2xl font-bold text-white mt-2">
                        {getScoreMessage()}
                      </h3>

                      <p className="text-sm text-slate-400 mt-2 max-w-xl">
                        Your score reflects resume quality,
                        skills, experience, projects and ATS readiness.
                      </p>

                    </div>

                  </div>

                </div>
              )}

              {/* SCORE BREAKDOWN */}

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">

                <ScoreMiniCard
                  title="Overall Score"
                  value={overallScore}
                  icon="🏆"
                />

                <ScoreMiniCard
                  title="Job Match"
                  value={jobMatchScore}
                  icon="🎯"
                />

                <ScoreMiniCard
                  title="ATS Score"
                  value={atsScore}
                  icon="🤖"
                />

                <ScoreMiniCard
                  title="Skills Score"
                  value={skillsScore}
                  icon="🧠"
                />

              </div>

              {/* QUICK INSIGHTS */}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">

                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">
                  <div className="text-2xl mb-2">
                    💪
                  </div>

                  <h3 className="font-bold text-white">
                    Strengths
                  </h3>

                  <p className="text-xs text-slate-400 mt-2">
                    Strong areas identified from your resume.
                  </p>
                </div>

                <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-5">
                  <div className="text-2xl mb-2">
                    🧩
                  </div>

                  <h3 className="font-bold text-white">
                    Skill Gaps
                  </h3>

                  <p className="text-xs text-slate-400 mt-2">
                    Skills that can improve your profile.
                  </p>
                </div>

                <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-5">
                  <div className="text-2xl mb-2">
                    🚀
                  </div>

                  <h3 className="font-bold text-white">
                    Next Actions
                  </h3>

                  <p className="text-xs text-slate-400 mt-2">
                    Recommended improvements for your resume.
                  </p>
                </div>

              </div>

              {/* =================================================
                  ANALYSIS CARDS
              ================================================= */}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

                {/* JOB MATCH ANALYSIS */}
                {structured.jobMatch && structured.jobMatch.score > 0 && (
                  <SectionCard
                    title={`Target Job Match — ${jobMatchScore ?? "N/A"}/100`}
                    icon="🎯"
                    wide
                  >
                    <div className="space-y-6">
                      {structured.jobMatch.summary && (
                        <p className="text-slate-300">
                          {structured.jobMatch.summary}
                        </p>
                      )}
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-4">
                          <h4 className="font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                            <span>✓</span> Matched Keywords
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {structured.jobMatch.matchedKeywords?.length > 0 ? (
                              structured.jobMatch.matchedKeywords.map((kw, idx) => (
                                <span key={idx} className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs rounded-md">
                                  {kw}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-500">None found</span>
                            )}
                          </div>
                        </div>

                        <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-4">
                          <h4 className="font-semibold text-red-400 mb-3 flex items-center gap-2">
                            <span>⚠</span> Missing Keywords
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {structured.jobMatch.missingKeywords?.length > 0 ? (
                              structured.jobMatch.missingKeywords.map((kw, idx) => (
                                <span key={idx} className="px-2 py-1 bg-red-500/10 border border-red-500/20 text-red-300 text-xs rounded-md">
                                  {kw}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-500">None missing!</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {structured.jobMatch.recommendations?.length > 0 && (
                        <div>
                          <h4 className="font-semibold text-white mb-2 mt-2">
                            Job-Specific Recommendations
                          </h4>
                          <ListItems items={structured.jobMatch.recommendations} />
                        </div>
                      )}
                    </div>
                  </SectionCard>
                )}

                {/* SUMMARY */}

                <SectionCard
                  title="Resume Summary"
                  icon="📝"
                >
                  <p>
                    {structured.summary ||
                      "No summary available."}
                  </p>
                </SectionCard>

                {/* STRENGTHS */}

                <SectionCard
                  title="Key Strengths"
                  icon="💪"
                >
                  <ListItems
                    items={structured.strengths}
                  />
                </SectionCard>

                {/* WEAKNESSES */}

                <SectionCard
                  title="Weaknesses"
                  icon="⚠️"
                >
                  <ListItems
                    items={structured.weaknesses}
                  />
                </SectionCard>

                {/* SKILLS */}

                <SectionCard
                  title={`Skills Analysis — ${skillsScore ?? "N/A"}/100`}
                  icon="🧠"
                >

                  <div className="space-y-5">

                    <div>
                      <h4 className="font-semibold text-white mb-2">
                        Technical Skills
                      </h4>

                      <ListItems
                        items={
                          structured.skills?.technical
                        }
                      />
                    </div>

                    <div>
                      <h4 className="font-semibold text-white mb-2">
                        Soft Skills
                      </h4>

                      <ListItems
                        items={
                          structured.skills?.soft
                        }
                      />
                    </div>

                    <div>
                      <h4 className="font-semibold text-white mb-2">
                        Missing / Recommended Skills
                      </h4>

                      <ListItems
                        items={
                          structured.skills?.missing
                        }
                      />
                    </div>

                  </div>

                </SectionCard>

                {/* EXPERIENCE */}

                <SectionCard
                  title={`Experience Analysis — ${experienceScore ?? "N/A"}/100`}
                  icon="💼"
                >
                  <ListItems
                    items={
                      structured.experience?.points
                    }
                  />
                </SectionCard>

                {/* PROJECTS */}

                <SectionCard
                  title={`Project Analysis — ${projectsScore ?? "N/A"}/100`}
                  icon="🚀"
                >
                  <ListItems
                    items={
                      structured.projects?.points
                    }
                  />
                </SectionCard>

                {/* EDUCATION */}

                <SectionCard
                  title={`Education Analysis — ${educationScore ?? "N/A"}/100`}
                  icon="🎓"
                >
                  <ListItems
                    items={
                      structured.education?.points
                    }
                  />
                </SectionCard>

                {/* ATS */}

                <SectionCard
                  title={`ATS Analysis — ${atsScore ?? "N/A"}/100`}
                  icon="🤖"
                >

                  <div className="space-y-5">

                    <div>
                      <h4 className="font-semibold text-white mb-2">
                        Keywords
                      </h4>

                      <ListItems
                        items={
                          structured.ats?.keywords
                        }
                      />
                    </div>

                    <div>
                      <h4 className="font-semibold text-white mb-2">
                        Formatting
                      </h4>

                      <ListItems
                        items={
                          structured.ats?.formatting
                        }
                      />
                    </div>

                    <div>
                      <h4 className="font-semibold text-white mb-2">
                        ATS Issues
                      </h4>

                      <ListItems
                        items={
                          structured.ats?.issues
                        }
                      />
                    </div>

                  </div>

                </SectionCard>

                {/* RECOMMENDATIONS */}

                <SectionCard
                  title="Actionable Recommendations"
                  icon="💡"
                  wide
                >
                  <ListItems
                    items={
                      structured.recommendations
                    }
                  />
                </SectionCard>

                {/* VERDICT */}

                <SectionCard
                  title="Final Verdict"
                  icon="🏆"
                  wide
                >
                  <p>
                    {structured.verdict ||
                      "No final verdict available."}
                  </p>
                </SectionCard>

              </div>

              {/* =================================================
                  CAREER ROADMAP
              ================================================= */}

              <div className="mt-6 bg-gradient-to-br from-indigo-950/40 to-slate-900/80 border border-indigo-500/20 rounded-3xl p-6">

                <div className="flex items-center gap-3 mb-6">

                  <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-xl">
                    🗺️
                  </div>

                  <div>

                    <h3 className="text-lg font-bold text-white">
                      Career Improvement Roadmap
                    </h3>

                    <p className="text-xs text-slate-500 mt-1">
                      A simple path to improve your resume
                    </p>

                  </div>

                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                  <div className="p-5 rounded-2xl bg-slate-950/50 border border-slate-800">

                    <span className="text-xs font-bold text-indigo-400">
                      STEP 01
                    </span>

                    <h4 className="mt-2 font-bold text-white">
                      Fix Resume Gaps
                    </h4>

                    <p className="mt-2 text-xs text-slate-400 leading-6">
                      Improve weak sections and missing information identified by AI.
                    </p>

                  </div>

                  <div className="p-5 rounded-2xl bg-slate-950/50 border border-slate-800">

                    <span className="text-xs font-bold text-cyan-400">
                      STEP 02
                    </span>

                    <h4 className="mt-2 font-bold text-white">
                      Build Missing Skills
                    </h4>

                    <p className="mt-2 text-xs text-slate-400 leading-6">
                      Focus on skills and technologies relevant to your target role.
                    </p>

                  </div>

                  <div className="p-5 rounded-2xl bg-slate-950/50 border border-slate-800">

                    <span className="text-xs font-bold text-emerald-400">
                      STEP 03
                    </span>

                    <h4 className="mt-2 font-bold text-white">
                      Apply With Confidence
                    </h4>

                    <p className="mt-2 text-xs text-slate-400 leading-6">
                      Re-analyze your improved resume before applying.
                    </p>

                  </div>

                </div>

              </div>

              {/* RAW RESPONSE */}

              {result && (

                <details className="mt-6 bg-slate-900/70 border border-slate-800 rounded-2xl p-5">

                  <summary className="cursor-pointer text-sm font-semibold text-slate-400 hover:text-white">
                    ▶ View complete AI response
                  </summary>

                  <div className="mt-4 whitespace-pre-wrap text-sm text-slate-400 leading-7">
                    {result}
                  </div>

                </details>

              )}

              {/* RESET */}

              <div className="text-center mt-8">

                <button
                  onClick={resetAnalysis}
                  className="px-6 py-3 rounded-xl border border-slate-700 bg-slate-900 text-slate-300 hover:text-white hover:border-indigo-500/50 transition"
                >
                  ↻ Analyze Another Resume
                </button>

              </div>

            </section>
          )}
        </>
        )}

      </main>

      {/* FOOTER */}

      <footer className="border-t border-slate-800/80 py-6 text-center">

        <p className="text-xs text-slate-600">
          AI Resume Intelligence • Built for smarter career decisions
        </p>

      </footer>

    </div>
  );
}