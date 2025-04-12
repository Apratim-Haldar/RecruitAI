import React, { useState, useEffect } from "react";

import {
  Users,
  Briefcase,
  UserCheck,
  Bot,
  Plus,
} from "lucide-react";

import JobList from "../components/JobList";
import CandidateList from "../components/CandidateList";
import AIAssistant from "../components/AIAssistant";
import Modal from "@/components/modal";
import JobPostForm from "@/components/job-post-form";

export default function Hr() {
  const [showAI, setShowAI] = useState(false);
  const [showCreateJobPost, setShowCreateJobPost] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const handleCreateJobPost = async (formData: any) => {
    try {
      const response = await fetch(
        "http://localhost:5000/api/create-job-post",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: 'include',
          body: JSON.stringify({
            ...formData,
          }),
        }
      );

      if (!response.ok) throw new Error("Failed to create job post");

      setSuccessMessage("Job post created successfully!");
      setTimeout(() => {
        setShowCreateJobPost(false);
        setSuccessMessage("");
      }, 2000);
    } catch (error) {
      console.error("Error:", error);
      setSuccessMessage("Error creating job post");
    }
  };
  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/verify-auth', {
          credentials: 'include'
        });
        if (!response.ok) window.location.href = '/';
      } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/';
      }
    };
    verifyAuth();
  }, []);
  return (
    <div className="relative min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              TechCorp HR Dashboard
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
                <p className="text-2xl font-semibold text-gray-900">24</p>
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
                <p className="text-2xl font-semibold text-gray-900">156</p>
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
                <p className="text-2xl font-semibold text-gray-900">42</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
          <button
            className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            onClick={() => setShowCreateJobPost(true)}
          >
            <Plus className="w-5 h-5 mr-2 text-gray-500" />
            Create a New Job Post
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
