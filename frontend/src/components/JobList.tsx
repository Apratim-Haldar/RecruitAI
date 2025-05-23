import { useEffect, useState } from "react";
import { Calendar, MapPin, Clock, X } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface Job {
  _id: string;
  title: string;
  jobType: string;
  status: string;
  createdAt: string;
  deadline: string;
  requirements: string[];
  location: string;
}

export default function JobList() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    try {
      const response = await fetch(
        "http://localhost:5000/api/get-job-posts",
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        }
      );
      const data = await response.json();
      setJobs(data.response);
    } catch (error) {
      console.error("Error fetching jobs:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const closeJob = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigation when clicking the close button
    
    try {
      const response = await fetch(
        `http://localhost:5000/api/close-job/${jobId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        }
      );
      
      if (response.ok) {
        // Update the job status locally to avoid refetching
        setJobs(prevJobs => 
          prevJobs.map(job => 
            job._id === jobId ? { ...job, status: "closed" } : job
          )
        );
      } else {
        console.error("Failed to close job");
      }
    } catch (error) {
      console.error("Error closing job:", error);
    }
  };

  const reopenJob = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigation when clicking the reopen button
    
    try {
      const response = await fetch(
        `http://localhost:5000/api/reopen-job/${jobId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        }
      );
      
      if (response.ok) {
        // Update the job status locally to avoid refetching
        setJobs(prevJobs => 
          prevJobs.map(job => 
            job._id === jobId ? { ...job, status: "open" } : job
          )
        );
      } else {
        console.error("Failed to reopen job");
      }
    } catch (error) {
      console.error("Error reopening job:", error);
    }
  };

  const activeJobs = jobs.filter((job) => job.status === "open");
  const closedJobs = jobs.filter((job) => job.status === "closed");

  if (loading) return <div className="p-6 text-gray-500">Loading jobs...</div>;

  return (
    <div className="space-y-8">
      {/* Active Jobs Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Active Job Posts ({activeJobs.length})
          </h2>
        </div>
        <div className="divide-y divide-gray-200">
          {activeJobs.map((job) => (
            <JobItem
              key={job._id}
              job={job}
              navigate={navigate}
              isActive={true}
              onClose={closeJob}
              reopenJob={reopenJob}
            />
          ))}
          {activeJobs.length === 0 && (
            <div className="p-6 text-gray-500">No active job posts found</div>
          )}
        </div>
      </div>

      {/* Closed Jobs Section */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Closed Job Posts ({closedJobs.length})
          </h2>
        </div>
        <div className="divide-y divide-gray-200">
          {closedJobs.map((job) => (
            <JobItem
              key={job._id}
              job={job}
              navigate={navigate}
              isActive={false}
              onClose={closeJob}
              reopenJob={reopenJob}
            />
          ))}
          {closedJobs.length === 0 && (
            <div className="p-6 text-gray-500">No closed job posts found</div>
          )}
        </div>
      </div>
    </div>
  );
}

function JobItem({
  job,
  navigate,
  isActive,
  onClose,
  reopenJob,
}: {
  job: Job;
  navigate: any;
  isActive: boolean;
  onClose: (jobId: string, e: React.MouseEvent) => void;
  reopenJob: (jobId: string, e: React.MouseEvent) => void;
}) {
  return (
    <div
      className={`p-6 hover:bg-gray-50 ${isActive ? "cursor-pointer" : "cursor-default"} relative`}
      onClick={() => isActive && navigate(`/jobs/${job._id}`, { state: { job } })}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-medium text-gray-900">{job.title}</h3>
          <div className="mt-2 flex items-center text-sm text-gray-500">
            <Clock className="w-4 h-4 mr-1" />
            {job.jobType}
            <span className="mx-2">•</span>
            <Calendar className="w-4 h-4 mr-1" />
            Posted {new Date(job.createdAt).toLocaleDateString()}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              isActive
                ? "bg-green-100 text-green-800"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {isActive ? "Active" : "Closed"}
          </span>
          {isActive ? (
            <button
              onClick={(e) => onClose(job._id, e)}
              className="ml-2 p-1 bg-red-100 text-red-600 rounded-full hover:bg-red-200 transition-colors"
              title="Close Job Post"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={(e) => reopenJob(job._id, e)}
              className="ml-2 px-2 py-1 bg-green-100 text-green-600 rounded-md hover:bg-green-200 transition-colors text-xs font-medium"
              title="Reopen Job Post"
            >
              Reopen
            </button>
          )}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center text-sm text-gray-500">
            <MapPin className="w-4 h-4 mr-1" />
            Location: {job.location}
          </div>
        </div>
        {isActive && (
          <button className="text-sm font-medium text-blue-600 hover:text-blue-500">
            View Details
          </button>
        )}
      </div>
    </div>
  );
}

export type { Job };