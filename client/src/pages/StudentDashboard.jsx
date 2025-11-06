import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import {
  DocumentTextIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowUpTrayIcon,
  AcademicCapIcon,
  EyeIcon,
  SparklesIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const StudentDashboard = () => {
  const user = JSON.parse(localStorage.getItem("user")); // real logged-in user
  const studentId = user?.student_id || user?.id;

  const [activeTab, setActiveTab] = useState("results");
  const [availableExams, setAvailableExams] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [selectedExamResults, setSelectedExamResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState(new Set());
  const [error, setError] = useState("");

  useEffect(() => {
    if (!studentId) {
      toast.error("No student ID found. Please log in again.");
      return;
    }
    fetchData();
  }, [activeTab]);

  // ---------- Fetch Data ----------
  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === "results") {
        const res = await fetch(
          `${API_BASE_URL}/results/student/${studentId}/available-exams`
        );
        if (!res.ok) throw new Error("Failed to fetch exams");
        const data = await res.json();
        setAvailableExams(data.exams || []);
      } else if (activeTab === "uploads") {
        const res = await fetch(
          `${API_BASE_URL}/upload/student/${studentId}/uploads`
        );
        if (!res.ok) throw new Error("Failed to fetch uploads");
        const data = await res.json();
        setUploads(data.uploads || []);
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchExamResults = async (examId) => {
    setDetailsLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${API_BASE_URL}/results/student/${studentId}?exam_id=${examId}`
      );
      if (!res.ok) throw new Error("Failed to fetch results");
      const data = await res.json();
      if (data.exams && data.exams.length > 0) {
        setSelectedExamResults(data.exams[0]);
      } else {
        setError("No results available for this exam yet");
      }
    } catch (err) {
      setError(err.message);
      toast.error("Failed to load exam results");
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleExamSelect = (exam) => {
    if (exam.has_results) {
      fetchExamResults(exam.exam_id);
    } else {
      toast.info("Results not available yet");
    }
  };

  // ---------- UI Helpers ----------
  const formatDate = (date) =>
    new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });

  const formatFileSize = (bytes) => {
    if (!bytes) return "—";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`;
  };

  const getGradeColor = (grade) =>
    ({
      "A+": "text-green-600",
      A: "text-green-500",
      "B+": "text-blue-600",
      B: "text-blue-500",
      "C+": "text-yellow-600",
      C: "text-yellow-500",
      F: "text-red-600",
    }[grade] || "text-gray-600");

  const getStatusBadge = (exam) => {
    if (exam.has_results) {
      return (
        <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 flex items-center gap-1">
          <CheckCircleIcon className="h-3 w-3" /> Available
        </span>
      );
    }

    const statusConfig = {
      uploaded: {
        text: "Uploaded",
        color: "bg-blue-100 text-blue-800",
        icon: ClockIcon,
      },
      processing: {
        text: "Processing",
        color: "bg-yellow-100 text-yellow-800",
        icon: ClockIcon,
      },
      processed: {
        text: "Grading...",
        color: "bg-purple-100 text-purple-800",
        icon: ClockIcon,
      },
      failed: {
        text: "Failed",
        color: "bg-red-100 text-red-800",
        icon: ExclamationCircleIcon,
      },
      pending: {
        text: "Not Uploaded",
        color: "bg-gray-100 text-gray-800",
        icon: DocumentTextIcon,
      },
    };

    const config = statusConfig[exam.upload_status] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <span
        className={`px-3 py-1 rounded-full text-xs font-medium ${config.color} flex items-center gap-1`}
      >
        <Icon className="h-3 w-3" /> {config.text}
      </span>
    );
  };

  // ---------- Render ----------
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Student Dashboard
            </h1>
            <p className="text-gray-600">Welcome back, {user?.full_name}</p>
          </div>
          <button
            onClick={() => {
              localStorage.clear();
              window.location.href = "/login";
            }}
            className="px-4 py-2 text-gray-600 hover:text-red-600 font-medium transition"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-blue-600 text-white rounded-xl p-6 shadow-md">
            <DocumentTextIcon className="h-6 w-6 mb-2 opacity-80" />
            <p className="text-3xl font-bold">{availableExams.length}</p>
            <p className="text-blue-100">Available Exams</p>
          </div>

          <div className="bg-green-600 text-white rounded-xl p-6 shadow-md">
            <CheckCircleIcon className="h-6 w-6 mb-2 opacity-80" />
            <p className="text-3xl font-bold">
              {availableExams.filter((e) => e.has_results).length}
            </p>
            <p className="text-green-100">Results Available</p>
          </div>

          <div className="bg-purple-600 text-white rounded-xl p-6 shadow-md">
            <ChartBarIcon className="h-6 w-6 mb-2 opacity-80" />
            <p className="text-3xl font-bold">
              {selectedExamResults?.percentage ?? "--"}%
            </p>
            <p className="text-purple-100">Latest Score</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-2xl shadow border">
          <div className="flex border-b">
            {[
              { id: "results", label: "My Results", icon: AcademicCapIcon },
              { id: "uploads", label: "Upload History", icon: ArrowUpTrayIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-6 text-sm font-medium flex items-center space-x-2 ${
                  activeTab === tab.id
                    ? "text-indigo-600 border-b-2 border-indigo-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <tab.icon className="h-5 w-5" /> <span>{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="p-6">
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin h-12 w-12 border-4 border-indigo-600 border-t-transparent rounded-full" />
              </div>
            ) : activeTab === "results" ? (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Exam list */}
                <div>
                  <h3 className="font-semibold text-gray-800 mb-4">
                    Available Exams
                  </h3>
                  {availableExams.length === 0 ? (
                    <p className="text-gray-500 text-center py-6">
                      No exams available yet
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {availableExams.map((exam) => (
                        <button
                          key={exam.exam_id}
                          onClick={() => handleExamSelect(exam)}
                          disabled={!exam.has_results}
                          className={`w-full p-4 rounded-lg border-2 text-left transition ${
                            selectedExamResults?.exam_id === exam.exam_id
                              ? "border-indigo-500 bg-indigo-50"
                              : "border-gray-200 hover:border-indigo-300"
                          } ${
                            !exam.has_results && "opacity-60 cursor-not-allowed"
                          }`}
                        >
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-semibold text-gray-800 text-sm">
                                {exam.exam_code}
                              </p>
                              <p className="text-xs text-gray-600">
                                {exam.exam_name}
                              </p>
                            </div>
                            {getStatusBadge(exam)}
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {formatDate(exam.exam_date)}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Results */}
                <div className="lg:col-span-2">
                  {detailsLoading ? (
                    <div className="flex justify-center py-12">
                      <div className="animate-spin h-12 w-12 border-4 border-indigo-600 border-t-transparent rounded-full" />
                    </div>
                  ) : error ? (
                    <p className="text-center text-gray-600 py-8">{error}</p>
                  ) : selectedExamResults ? (
                    <div className="space-y-6">
                      {/* Summary */}
                      <div className="bg-indigo-50 p-6 rounded-xl border border-indigo-100">
                        <div className="flex justify-between items-center mb-4">
                          <div>
                            <h3 className="font-bold text-gray-800 text-lg">
                              {selectedExamResults.exam_name}
                            </h3>
                            <p className="text-sm text-gray-600">
                              {selectedExamResults.exam_code} •{" "}
                              {selectedExamResults.exam_type}
                            </p>
                          </div>
                          <p
                            className={`text-3xl font-bold ${getGradeColor(
                              selectedExamResults.grade
                            )}`}
                          >
                            {selectedExamResults.grade}
                          </p>
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                          <div className="text-center bg-white p-3 rounded-lg shadow-sm">
                            <p className="text-2xl font-bold">
                              {selectedExamResults.obtained_marks}
                            </p>
                            <p className="text-xs text-gray-500">Obtained</p>
                          </div>
                          <div className="text-center bg-white p-3 rounded-lg shadow-sm">
                            <p className="text-2xl font-bold">
                              {selectedExamResults.max_obtainable}
                            </p>
                            <p className="text-xs text-gray-500">Total</p>
                          </div>
                          <div className="text-center bg-white p-3 rounded-lg shadow-sm">
                            <p className="text-2xl font-bold">
                              {selectedExamResults.percentage}%
                            </p>
                            <p className="text-xs text-gray-500">Score</p>
                          </div>
                        </div>
                      </div>

                      {/* Question breakdown */}
                      <div className="bg-white rounded-xl border border-gray-200 p-6">
                        <h4 className="font-semibold text-gray-800 mb-4">
                          Question-wise Results
                        </h4>
                        <div className="space-y-3">
                          {selectedExamResults.questions.map((q) => (
                            <div
                              key={q.question_number}
                              className="border border-gray-200 rounded-lg overflow-hidden"
                            >
                              <button
                                onClick={() => {
                                  const newSet = new Set(expandedQuestions);
                                  newSet.has(q.question_number)
                                    ? newSet.delete(q.question_number)
                                    : newSet.add(q.question_number);
                                  setExpandedQuestions(newSet);
                                }}
                                className="w-full flex justify-between items-center p-4 hover:bg-gray-50"
                              >
                                <div className="flex items-center gap-4">
                                  <span className="w-8 h-8 flex items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-semibold text-sm">
                                    {q.question_number}
                                  </span>
                                  <p className="font-medium text-gray-800 text-sm">
                                    {q.question_text}
                                  </p>
                                </div>
                                <div className="text-right text-sm">
                                  <span className="font-semibold text-gray-800">
                                    {q.obtained_marks}
                                  </span>
                                  /{q.max_marks}
                                </div>
                              </button>

                              {expandedQuestions.has(q.question_number) && (
                                <div className="p-4 bg-gray-50 border-t border-gray-200 space-y-3">
                                  <div>
                                    {q.student_answer?.trim() ? (
                                      <div>
                                        <p className="text-sm font-medium text-gray-700 mb-1">
                                          Your Answer:
                                        </p>
                                        <div className="bg-white p-3 rounded border border-gray-200">
                                          <p className="text-sm text-gray-800 whitespace-pre-wrap">
                                            {q.student_answer}
                                          </p>
                                        </div>
                                      </div>
                                    ) : null}
                                  </div>

                                  {q.ai_feedback && (
                                    <div className="bg-blue-50 p-3 rounded border border-blue-200">
                                      <p className="text-sm font-medium text-blue-700 mb-1 flex items-center">
                                        <SparklesIcon className="w-4 h-4 mr-1" />{" "}
                                        AI Feedback
                                      </p>
                                      <p className="text-sm text-blue-900">
                                        {q.ai_feedback}
                                      </p>
                                    </div>
                                  )}

                                  {q.teacher_feedback && (
                                    <div className="bg-green-50 p-3 rounded border border-green-200">
                                      <p className="text-sm font-medium text-green-700 mb-1 flex items-center">
                                        <AcademicCapIcon className="w-4 h-4 mr-1" />{" "}
                                        Teacher Feedback
                                      </p>
                                      <p className="text-sm text-green-900">
                                        {q.teacher_feedback}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 py-8">
                      Select an exam to view results
                    </p>
                  )}
                </div>
              </div>
            ) : (
              // Upload tab
              <div className="grid gap-4">
                {uploads.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <ArrowUpTrayIcon className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                    <p>No uploads yet</p>
                  </div>
                ) : (
                  uploads.map((upload) => (
                    <div
                      key={upload.id}
                      className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm"
                    >
                      <h3 className="font-semibold text-gray-800">
                        {upload.exam_name}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {upload.exam_code}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-600">
                        <span>Size: {formatFileSize(upload.file_size)}</span>
                        <span>Type: {upload.file_type?.toUpperCase()}</span>
                        <span>Uploaded: {formatDate(upload.uploaded_at)}</span>
                      </div>
                      <p className="mt-2 text-xs text-gray-500">
                        Status: {upload.processing_status}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default StudentDashboard;
