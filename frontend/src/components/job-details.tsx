import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Job } from './JobList';
import { useState,useEffect } from "react";
import { useParams } from "react-router";

interface Props {
  totalApplicantCount: number,
  shortlistedCount: number,
  interviewCount: number,
  offerCount: number
}

export function JobDetails({ totalApplicantCount, shortlistedCount, interviewCount, offerCount }: Props) {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const response = await fetch(`http://localhost:5000/api/public/job-posts/${jobId}`);
        const data = await response.json();
        setJob(data);
      } catch (error) {
        console.error('Error fetching job:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [jobId]);

  if (loading) return <div>Loading...</div>;
  if (!job) return <div>Job not found</div>;
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-2xl font-bold mb-1">{job.title}</CardTitle>
            <div className="text-gray-500">{job.jobType}</div>
          </div>
          <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">{job.status}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="flex flex-col">
            <span className="text-sm text-gray-500">Job Type</span>
            <span className="font-medium">{job.jobType}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-sm text-gray-500">Posted On</span>
            <span className="font-medium">{new Date(job.createdAt).toLocaleDateString()}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-sm text-gray-500">Closing Date</span>
            <span className="font-medium">{new Date(job.deadline).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="space-y-4">
          {/* <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm font-medium">Hiring Progress</span>
              <span className="text-sm text-gray-500">27%</span>
            </div>
            <Progress value={27} className="w-full h-2" />
          </div> */}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
            <div className="bg-gray-50 p-3 rounded-md text-center">
              <div className="text-xl font-semibold">{totalApplicantCount}</div>
              <div className="text-xs text-gray-500">Total Applicants</div>
            </div>
            <div className="bg-gray-50 p-3 rounded-md text-center">
              <div className="text-xl font-semibold">{shortlistedCount}</div>
              <div className="text-xs text-gray-500">Shortlisted</div>
            </div>
            <div className="bg-gray-50 p-3 rounded-md text-center">
              <div className="text-xl font-semibold">{interviewCount}</div>
              <div className="text-xs text-gray-500">Interviews</div>
            </div>
            <div className="bg-gray-50 p-3 rounded-md text-center">
              <div className="text-xl font-semibold">{offerCount}</div>
              <div className="text-xs text-gray-500">Offers</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

