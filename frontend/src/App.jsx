import React, { useMemo, useState } from "react";
import axios from "axios";

const BACKEND_URL =
  "https://ai-resume-reviewer-e412.onrender.com/api/review-resume";

export default function App() {
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

    // Current backend doesn't process this yet,
    // but keeping it here for the next backend upgrade.
    formData.append("job_description", jobDescription);

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

  // =========================================================
  // JOB KEYWORDS
  // =========================================================

  const keywords = useMemo(() => {
    if (!jobDescription.trim()) return [];

    const commonWords = new Set([
      "and",
      "the",
      "for",
      "with",
      "from",
      "this",
      "that",
      "are",
      "you",
      "your",
      "have",
      "has",
      "will",
      "our",
      "their",
      "into",
      "about",
      "using",
      "work",
      "working",
      "experience",
      "years",
      "role",
      "job",
      "candidate",
      "skills",
      "required",
      "preferred",
      "should",
      "must",
      "can",
      "who",
      "all",
      "any",
      "not",
      "but",
      "was",
      "were",
      "been",
      "being",
      "they",
      "them",
      "its",
      "also",
      "more",
      "than",
      "such",
      "other",
    ]);

    const words = jobDescription
      .toLowerCase()
      .replace(/[^a-z0-9+#.\- ]/g, " ")
      .split(/\s+/)
      .filter(
        (word) =>
          word.length >= 3 &&
          !commonWords.has(word)
      );

    return [...new Set(words)].slice(0, 12);
  }, [jobDescription]);

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

RECOMMENDATIONS:
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
              <h1 className="font-bold text-white tracking-tight">
                AI Resume Intelligence
              </h1>

              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Career Intelligence Platform
              </p>
            </div>

          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />

            <span className="text-slate-400">
              AI Engine Online
            </span>
          </div>

        </div>
      </header>

      {/* MAIN */}

      <main className="relative max-w-6xl mx-auto px-5 md:px-8 py-10 md:py-16">

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

        {/* =====================================================
            RESULTS
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

              <div className="flex gap-2">

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

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">

              <ScoreMiniCard
                title="Overall Score"
                value={overallScore}
                icon="🏆"
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

            {/* JOB KEYWORDS */}

            {jobDescription && keywords.length > 0 && (

              <div className="mb-6 bg-slate-900/70 border border-slate-800 rounded-2xl p-5">

                <div className="flex items-center gap-3 mb-4">

                  <span className="text-xl">
                    🔑
                  </span>

                  <div>

                    <h3 className="font-bold text-white">
                      Target Job Keywords
                    </h3>

                    <p className="text-xs text-slate-500 mt-1">
                      Important terms detected from your job description
                    </p>

                  </div>

                </div>

                <div className="flex flex-wrap gap-2">

                  {keywords.map((keyword) => (

                    <span
                      key={keyword}
                      className="px-3 py-1.5 rounded-full text-xs font-medium bg-indigo-500/10 border border-indigo-500/20 text-indigo-300"
                    >
                      {keyword}
                    </span>

                  ))}

                </div>

              </div>

            )}

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