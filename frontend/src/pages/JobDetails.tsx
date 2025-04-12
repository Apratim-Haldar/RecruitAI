import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ArrowLeft, HelpCircle } from "lucide-react";
import { ApplicantsTable } from "@/components/applicants-table";
import { ShortlistedTable } from "@/components/shortlisted-table";
import { JobDetails } from "@/components/job-details";
import { AiAssistant } from "@/components/ai-assistant";
import { useState, useEffect } from "react";
import { useParams } from "react-router";

export default function JobDashboard() {
  const [applications, setApplications] = useState([]);
  const { jobId } = useParams<{ jobId: string }>();
  const [loading, setLoading] = useState(true);
  const [shortlisted, setShortlisted] = useState([]);
  const [offers, setOffers] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [reload, setReload] = useState(false);

  const refresh = () => { 
    setReload(!reload);
  };

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const response = await fetch(`http://localhost:5000/api/applications/${jobId}`, {
          credentials: "include",
        });
        const data = await response.json();
        setApplications(data.applications);
        setShortlisted(data.shortlisted);
        setInterviews(data.interviews);
        setOffers(data.offers);
      } catch (error) {
        console.error('Error fetching job:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchApplications();
  }, [reload, jobId]); // Add reload to dependency array to trigger refetch

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center mb-6">
          <Button variant="ghost" className="mr-2" asChild>
            <a href="/hr">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Jobs
            </a>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="ml-auto flex items-center gap-1"
          >
            <HelpCircle className="h-4 w-4" />
            <span>Get AI Help</span>
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2">
            <JobDetails totalApplicantCount={applications.length} shortlistedCount={shortlisted.length} offerCount={offers.length} interviewCount={interviews.length} />
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
            <AiAssistant />
          </div>
        </div>

        <Tabs defaultValue="all" className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="all">All Applicants ({applications.length})</TabsTrigger>
            <TabsTrigger value="shortlisted">Shortlisted ({shortlisted.length})</TabsTrigger>
          </TabsList>
          <TabsContent
            value="all"
            className="bg-white rounded-lg shadow-sm border border-gray-100 p-6"
          >
            <ApplicantsTable reload={refresh} applications={applications} loading={loading} />
          </TabsContent>
          <TabsContent
            value="shortlisted"
            className="bg-white rounded-lg shadow-sm border border-gray-100 p-6"
          >
            <ShortlistedTable reload={refresh} shortlistedData={shortlisted} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}