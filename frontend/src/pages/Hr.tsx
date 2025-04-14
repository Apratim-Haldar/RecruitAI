import React, { useState, useEffect } from "react";

import { Users, Briefcase, UserCheck, Bot, Plus } from "lucide-react";

import JobList from "../components/JobList";
import CandidateList from "../components/CandidateList";
import AIAssistant from "../components/AIAssistant";
import Modal from "@/components/modal";
import JobPostForm from "@/components/job-post-form";
import { set } from "mongoose";

export default function Hr() {
  const [showAI, setShowAI] = useState(false);
  const [showCreateJobPost, setShowCreateJobPost] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showPDFUploadModal, setShowPDFUploadModal] = useState(false);
  const [jobPosts, setJobPosts] = useState(0);
  const [shortlisted, setShortlisted] = useState(0);
  const [applications, setApplications] = useState(0);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState("");

  const handleCreateJobPost = async (formData: any) => {
    try {
      const response = await fetch(
        "http://localhost:5000/api/create-job-post",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({
            ...formData,
          }),
        }
      );

      if (!response.ok) throw new Error("Failed to create job post");

      setSuccessMessage("Job post created successfully!");
      setTimeout(() => {
        setShowCreateJobPost(false);
        setShowPDFUploadModal(false);
        setSuccessMessage("");
      }, 1000);
    } catch (error) {
      console.error("Error:", error);
      setSuccessMessage("Error creating job post");
    }
  };

  const handlePdfFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setPdfFile(e.target.files[0]);
    }
  };

  const handlePdfUpload = async () => {
    if (!pdfFile) {
      setUploadStatus("Please select a PDF file first");
      return;
    }

    setUploadStatus("Uploading...");

    try {
      const formData = new FormData();
      formData.append("file", pdfFile);
      const authResponse = await fetch("http://localhost:5000/api/verify-auth", {
        credentials: "include",
      });
      if (!authResponse.ok) throw new Error("Authentication failed");
      const authData = await authResponse.json();
      const userId = authData?.id || authData?.user?._id || authData?._id;

      const response = await fetch(`http://localhost:8080/upload?user_id=${userId}`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to upload PDF");
      }

      setUploadStatus("Job post created successfully from PDF!");
      setPdfFile(null);

      // Refresh job posts count
      const jobPostsResponse = await fetch(
        "http://localhost:5000/api/get-job-posts",
        {
          credentials: "include",
        }
      );
      const jobPostsData = await jobPostsResponse.json();
      setJobPosts(jobPostsData.response2.length);

      setTimeout(() => {
        setShowPDFUploadModal(false);
        setUploadStatus("");
      }, 2000);
    } catch (error) {
      console.error("Error uploading PDF:", error);
      setUploadStatus(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  };

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const response = await fetch("http://localhost:5000/api/verify-auth", {
          credentials: "include",
        });
        if (!response.ok) window.location.href = "/";
      } catch (error) {
        console.error("Auth check failed:", error);
        window.location.href = "/";
      }
    };
    verifyAuth();
    const fetchData = async () => {
      try {
        const response = await fetch(
          "http://localhost:5000/api/get-job-posts",
          {
            credentials: "include",
          }
        );
        const data = await response.json();
        // Update to use the correct property from the response
        setJobPosts(data.response2.length);

        const response2 = await fetch(
          "http://localhost:5000/api/hr/applications-summary",
          {
            credentials: "include",
          }
        );
        const data2 = await response2.json();
        setShortlisted(data2.totalShortlisted);
        setApplications(data2.totalApplications);
      } catch (error) {
        console.log("Error fetching data hr.tsx: ", error);
      }
    };
    fetchData();
  }, []);
  return (
    <div className="relative min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              HireSight HR Dashboard
            </h1>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowAI(!showAI)}
                className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                <Bot className="w-5 h-5 mr-2" />
                AI Assistant
              </button>
              <div className="relative">
                <img
                  src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                  alt="Profile"
                  className="w-8 h-8 rounded-full"
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Briefcase className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <h2 className="text-sm font-medium text-gray-500">
                  Active Job Posts
                </h2>
                <p className="text-2xl font-semibold text-gray-900">
                  {jobPosts}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg">
                <Users className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <h2 className="text-sm font-medium text-gray-500">
                  Total Candidates
                </h2>
                <p className="text-2xl font-semibold text-gray-900">
                  {applications}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-purple-100 rounded-lg">
                <UserCheck className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <h2 className="text-sm font-medium text-gray-500">
                  Shortlisted
                </h2>
                <p className="text-2xl font-semibold text-gray-900">
                  {shortlisted}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4 flex-wrap mb-4">
          <button
            className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            onClick={() => setShowCreateJobPost(true)}
          >
            <Plus className="w-5 h-5 mr-2 text-gray-500" />
            Create via Form
          </button>
          <button
            className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            onClick={() => setShowPDFUploadModal(true)}
          >
            <Plus className="w-5 h-5 mr-2" />
            Upload PDF
          </button>
        </div>

        {showCreateJobPost && (
          <Modal onClose={() => setShowCreateJobPost(false)}>
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-gray-900">
                Create New Job Post
              </h2>
              {successMessage && (
                <div
                  className={`p-3 rounded-md ${
                    successMessage.includes("Error")
                      ? "bg-red-100 text-red-700"
                      : "bg-green-100 text-green-700"
                  }`}
                >
                  {successMessage}
                </div>
              )}
              <JobPostForm onSubmit={handleCreateJobPost} />
            </div>
          </Modal>
        )}
        {showPDFUploadModal && (
          <Modal onClose={() => setShowPDFUploadModal(false)}>
            <div className="space-y-4">
              <h2 className="text-2xl font-bold text-gray-900">
                Upload Job Description PDF
              </h2>
              {uploadStatus && (
                <div
                  className={`p-3 rounded-md ${
                    uploadStatus.includes("Error")
                      ? "bg-red-100 text-red-700"
                      : uploadStatus.includes("Uploading")
                      ? "bg-blue-100 text-blue-700"
                      : "bg-green-100 text-green-700"
                  }`}
                >
                  {uploadStatus}
                </div>
              )}
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handlePdfFileChange}
                    className="hidden"
                    id="pdf-upload"
                  />
                  <label
                    htmlFor="pdf-upload"
                    className="cursor-pointer text-blue-600 hover:text-blue-800"
                  >
                    {pdfFile ? pdfFile.name : "Click to select a PDF file"}
                  </label>
                  {!pdfFile && (
                    <p className="text-sm text-gray-500 mt-2">
                      Upload a PDF file containing job description
                    </p>
                  )}
                </div>
                <button
                  onClick={handlePdfUpload}
                  disabled={!pdfFile || uploadStatus === "Uploading..."}
                  className={`w-full py-2 px-4 rounded-md text-white ${
                    !pdfFile || uploadStatus === "Uploading..."
                      ? "bg-gray-400 cursor-not-allowed"
                      : "bg-blue-600 hover:bg-blue-700"
                  }`}
                >
                  {uploadStatus === "Uploading..."
                    ? "Processing..."
                    : "Upload and Create Job Post"}
                </button>
              </div>
            </div>
          </Modal>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <JobList />
            {/*  <CandidateList /> */}
          </div>
          <div className="lg:col-span-1">{showAI && <AIAssistant />}</div>
        </div>
      </main>
    </div>
  );
}
