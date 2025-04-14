import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { X, Star, Filter, Search, Calendar, RotateCcw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { CandidateModal } from "@/components/candidate-modal";
import { applicantType } from "@/lib";
import Modal from "./modal";

interface Props {
  shortlistedData: applicantType[];
  reload: () => void;
}

export function ShortlistedTable({ shortlistedData, reload }: Props) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [actionCandidate, setActionCandidate] = useState<{id: string, name: string, action: string} | null>(null);

  const filteredApplicants = shortlistedData.filter(
    (applicant) =>
      applicant.firstName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      applicant.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      /*       applicant.skills.some((skill) => skill.toLowerCase().includes(searchTerm.toLowerCase())), */
      applicant.lastName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  function handleRowClick(candidate) {
    setSelectedCandidate(candidate);
    setIsModalOpen(true);
  }

  const handleActionClick = (id: string, firstName: string, lastName: string, action: string) => {
    setActionCandidate({
      id,
      name: `${firstName} ${lastName}`,
      action
    });
    setShowConfirmModal(true);
  };

  const updateStatus = async (applicationId: string, status: string) => {
    try {
      const response = await fetch(
        `http://localhost:5000/api/applications/${applicationId}/${status}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        }
      );
      
      if (!response.ok) throw new Error("Update failed");
      
      // Call reload function from parent component
      if (reload) {
        reload();
      }
      
      setShowSuccessModal(true);
    } catch (error) {
      console.log("Error updating status at shortlisted-table.tsx: ", error);
    }
  };

  const confirmAction = () => {
    if (actionCandidate) {
      updateStatus(actionCandidate.id, actionCandidate.action);
      setShowConfirmModal(false);
    }
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
        <h2 className="text-xl font-semibold">Shortlisted Candidates</h2>
        <div className="flex w-full sm:w-auto gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
            <Input
              placeholder="Search shortlisted..."
              className="pl-8"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          {/* <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button> */}
        </div>
      </div>

      <div className="rounded-md border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Candidate</TableHead>
              <TableHead>Applied On</TableHead>
              {/* <TableHead>Shortlisted On</TableHead> */}
              <TableHead>Experience</TableHead>
              <TableHead>Match</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredApplicants.map((applicant) => (
              <TableRow
                key={applicant._id}
                className="cursor-pointer hover:bg-gray-50"
                onClick={() => handleRowClick(applicant)}
              >
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar>
                      {/* <AvatarImage src={applicant.avatar} /> */}
                      <AvatarFallback>
                        {applicant.firstName.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="font-medium">
                        {applicant.firstName} {applicant.lastName}
                      </div>
                      <div className="text-sm text-gray-500">
                        {applicant.email}
                      </div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  {new Date(applicant.appliedAt).toLocaleDateString("en-GB")}
                </TableCell>
                {/* <TableCell>{applicant.shortlistedDate}</TableCell> */}
                <TableCell>{applicant.experience} years</TableCell>
                {/* <TableCell>
                   <div className="flex flex-wrap gap-1">
                    {applicant.skills.slice(0, 2).map((skill, index) => (
                      <Badge key={index} variant="secondary" className="text-xs">
                        {skill}
                      </Badge>
                    ))}
                    {applicant.skills.length > 2 && (
                      <Badge variant="outline" className="text-xs">
                        +{applicant.skills.length - 2}
                      </Badge>
                    )}
                  </div> 
                </TableCell>  */}
                
                <TableCell>
                  <div className="flex items-center">
                    <span
                      className={`font-medium ${
                        applicant.match >= 80
                          ? "text-emerald-600"
                          : applicant.match >= 60
                          ? "text-amber-600"
                          : "text-gray-600"
                      }`}
                    >
                      {/* {applicant.match}% */}
                    </span>
                  </div>
                </TableCell>
                
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" className="h-8 w-8 p-0">
                      <Calendar className="h-4 w-4 text-purple-600" />
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="h-8 w-8 p-0"
                      onClick={() => handleActionClick(applicant._id, applicant.firstName, applicant.lastName, "applied")}
                    >
                      <RotateCcw className="h-4 w-4 text-green-600" />
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="h-8 w-8 p-0"
                      onClick={() => handleActionClick(applicant._id, applicant.firstName, applicant.lastName, "rejected")}
                    >
                      <X className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
                </TableCell>
                
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {selectedCandidate && (
        <CandidateModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          candidate={selectedCandidate}
        />
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && actionCandidate && (
        <Modal onClose={() => setShowConfirmModal(false)}>
          <div className="flex flex-col items-center text-center">
            <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mb-4">
              {actionCandidate.action === "shortlisted" && <Check className="h-8 w-8 text-blue-600" />}
              {actionCandidate.action === "rejected" && <X className="h-8 w-8 text-red-600" />}
              {actionCandidate.action === "applied" && <RotateCcw className="h-8 w-8 text-green-600" />}
            </div>
            <h3 className="text-xl font-semibold mb-2">
              {actionCandidate.action === "shortlisted" && "Confirm Shortlist"}
              {actionCandidate.action === "rejected" && "Confirm Rejection"}
              {actionCandidate.action === "applied" && "Confirm Status Change"}
            </h3>
            <p className="text-gray-600 mb-6">
              {actionCandidate.action === "shortlisted" && (
                <>Are you sure you want to shortlist <span className="font-medium">{actionCandidate.name}</span>? 
                This candidate will move to the next stage of the hiring process.</>
              )}
              {actionCandidate.action === "rejected" && (
                <>Are you sure you want to reject <span className="font-medium">{actionCandidate.name}</span>? 
                This action will mark the candidate as rejected.</>
              )}
              {actionCandidate.action === "applied" && (
                <>Are you sure you want to revert <span className="font-medium">{actionCandidate.name}</span> to applied status? 
                This will move the candidate back to the initial application stage.</>
              )}
            </p>
            <div className="flex gap-3 w-full sm:w-auto">
              <Button 
                variant="outline" 
                onClick={() => setShowConfirmModal(false)}
                className="flex-1 sm:flex-initial"
              >
                Cancel
              </Button>
              <Button 
                onClick={confirmAction}
                className={`flex-1 sm:flex-initial ${
                  actionCandidate.action === "shortlisted" 
                    ? "bg-emerald-600 hover:bg-emerald-700" 
                    : actionCandidate.action === "rejected"
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-blue-600 hover:bg-blue-700"
                }`}
              >
                {actionCandidate.action === "shortlisted" && "Yes, Shortlist"}
                {actionCandidate.action === "rejected" && "Yes, Reject"}
                {actionCandidate.action === "applied" && "Yes, Change Status"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Success Modal */}
      {showSuccessModal && actionCandidate && (
        <Modal onClose={() => setShowSuccessModal(false)}>
          <div className="flex flex-col items-center text-center">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
              actionCandidate.action === "shortlisted" 
                ? "bg-emerald-50" 
                : actionCandidate.action === "rejected"
                  ? "bg-red-50"
                  : "bg-blue-50"
            }`}>
              {actionCandidate.action === "shortlisted" && <Check className="h-8 w-8 text-emerald-600" />}
              {actionCandidate.action === "rejected" && <X className="h-8 w-8 text-red-600" />}
              {actionCandidate.action === "applied" && <RotateCcw className="h-8 w-8 text-blue-600" />}
            </div>
            <h3 className="text-xl font-semibold mb-2">
              {actionCandidate.action === "shortlisted" && "Candidate Shortlisted!"}
              {actionCandidate.action === "rejected" && "Candidate Rejected"}
              {actionCandidate.action === "applied" && "Status Changed"}
            </h3>
            <p className="text-gray-600 mb-6">
              {actionCandidate.action === "shortlisted" && (
                <><span className="font-medium">{actionCandidate.name}</span> has been successfully shortlisted.
                You can now schedule an interview or review their application in detail.</>
              )}
              {actionCandidate.action === "rejected" && (
                <><span className="font-medium">{actionCandidate.name}</span> has been marked as rejected.
                They will no longer appear in your active candidates list.</>
              )}
              {actionCandidate.action === "applied" && (
                <><span className="font-medium">{actionCandidate.name}</span> has been moved back to applied status.
                You can now review their application again.</>
              )}
            </p>
            <Button 
              onClick={() => setShowSuccessModal(false)}
              className={`${
                actionCandidate.action === "shortlisted" 
                  ? "bg-emerald-600 hover:bg-emerald-700" 
                  : actionCandidate.action === "rejected"
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              Done
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}