import React, { useEffect, FormEvent } from "react";
import { useState } from "react";
import {
  Building2,
  Users,
  Briefcase,
  Trophy,
  ArrowRight,
  Lock,
} from "lucide-react";
import Auth from "../components/Auth";
import Modal from "@/components/modal";
import ApplicationForm from "@/components/application-form";
import { SuccessModal } from "@/components/success-modal";

export default function Landing() {
  const [isHRLoginOpen, setIsHRLoginOpen] = useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const response = await fetch(
          "http://localhost:5000/api/public/job-posts",
          {
            method: "GET",
          }
        );
        const data = await response.json();
        setJobs(data.filter((job: any) => job.status === "open"));
        console.log(data);
        console.log(jobs);
      } catch (error) {
        console.error("Error fetching jobs:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchJobs();
  }, []);

  const handleCancel = (e: FormEvent) => {
    e.preventDefault();
    setIsHRLoginOpen(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <Building2 className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">
                HireSight
              </span>
            </div>
            <button
              onClick={() => setIsHRLoginOpen(true)}
              className="flex items-center text-gray-600 hover:text-blue-600"
            >
              <Lock className="h-4 w-4 mr-1" />
              HR Login
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
              <span className="block">Shape the Future with</span>
              <span className="block text-blue-600">HireSight</span>
            </h1>
            <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
              Join our innovative team and be part of building tomorrow's
              technology. We're looking for passionate individuals who want to
              make a difference.
            </p>
            <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
              <div className="rounded-md shadow">
                <a
                  href="#openings"
                  className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 md:py-4 md:text-lg md:px-10"
                >
                  View Openings
                  <ArrowRight className="ml-2 h-5 w-5" />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="bg-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="text-center">
              <div className="flex justify-center">
                <Users className="h-12 w-12 text-blue-600" />
              </div>
              <p className="mt-2 text-3xl font-extrabold text-gray-900">500+</p>
              <p className="mt-1 text-gray-500">Global Employees</p>
            </div>
            <div className="text-center">
              <div className="flex justify-center">
                <Briefcase className="h-12 w-12 text-blue-600" />
              </div>
              <p className="mt-2 text-3xl font-extrabold text-gray-900">50+</p>
              <p className="mt-1 text-gray-500">Open Positions</p>
            </div>
            <div className="text-center">
              <div className="flex justify-center">
                <Trophy className="h-12 w-12 text-blue-600" />
              </div>
              <p className="mt-2 text-3xl font-extrabold text-gray-900">#1</p>
              <p className="mt-1 text-gray-500">Best Place to Work</p>
            </div>
          </div>
        </div>
      </div>

      {/* HR Login Modal */}
      {isHRLoginOpen && (
        <div className="fixed bg-black/50 inset-0 bg-opacity-75 p-4">
          <Auth handleCancel={handleCancel} />
        </div>
      )}

      {/* Job Openings Section */}
      <div id="openings" className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-extrabold text-gray-900">
              Open Positions
            </h2>
            <p className="mt-4 text-lg text-gray-500">
              Join our team and help shape the future of technology
            </p>
          </div>
          {loading ? (
            <div className="mt-12 text-center text-gray-500">
              Loading jobs...
            </div>
          ) : (
            <div className="mt-12 grid gap-8 lg:grid-cols-2">
              {jobs.map((job) => (
                <div
                  key={job._id}
                  className="bg-gray-50 rounded-lg p-6 hover:shadow-lg transition-shadow"
                >
                  <h3 className="text-xl font-semibold text-gray-900">
                    {job.title}
                  </h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                      {job.jobType}
                    </span>
                    <span className="inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-green-100 text-green-800">
                      Deadline: {new Date(job.deadline).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedJobId(job._id)}
                    className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600  cursor-pointer hover:bg-blue-700"
                  >
                    Apply Now
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
          {!loading && jobs.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              No current openings
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-800">
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <Building2 className="h-8 w-8 text-white" />
              <span className="ml-2 text-xl font-bold text-white">
                HireSight
              </span>
            </div>
            <p className="text-gray-400">
              &copy; 2025 HireSight. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
      {selectedJobId && (
        <Modal onClose={() => setSelectedJobId(null)}>
          <ApplicationForm
            jobId={selectedJobId}
            onSuccess={() => {
              setSelectedJobId(null);
              setShowSuccess(true);
            }}
          />
        </Modal>
      )}

      {showSuccess && <SuccessModal onClose={() => setShowSuccess(false)} />}
    </div>
  );
}
