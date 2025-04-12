import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import axios from "axios"
import {
  Briefcase,
  GraduationCap,
  MapPin,
  Phone,
  Mail,
  Globe,
  Calendar,
  FileText,
  MessageSquare,
  X,
  Star,
} from "lucide-react"

export function CandidateModal({ isOpen, onClose, candidate }) {
  const [activeTab, setActiveTab] = useState("profile")
  const [newNote, setNewNote] = useState("")
  const [notes, setNotes] = useState(candidate?.notes || [])
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!candidate) return null

  const addNote = async () => {
    if (!newNote.trim()) return
    
    setIsSubmitting(true)
    try {
      const response = await axios.post(`http://localhost:5000/api/applications/${candidate._id}/notes`, {
        note: newNote
      })
      
      if (response.data) {
        setNotes([...notes, newNote])
        setNewNote("")
      }
    } catch (error) {
      console.error("Failed to add note:", error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const viewResume = () => {
    if (candidate.s3FileKey) {
      window.open(`https://${process.env.S3_BUCKET}.s3.amazonaws.com/${candidate.s3FileKey}`, '_blank')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-white max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 font-semibold text-3xl w-16">
                <AvatarFallback>{candidate.firstName?.charAt(0)}{candidate.lastName?.charAt(0)}</AvatarFallback>
              </Avatar>
              <div>
                <DialogTitle className="text-2xl font-bold">{candidate.firstName} {candidate.lastName}</DialogTitle>
                {candidate.experience && (
                  <div className="text-black mt-1">{candidate.experience} years experience</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {candidate.aiEvaluation?.matchPercentage && (
                <Badge
                  className={`${
                    candidate.aiEvaluation.matchPercentage >= 80
                      ? "bg-emerald-100 text-emerald-800"
                      : candidate.aiEvaluation.matchPercentage >= 60
                        ? "bg-amber-100 text-amber-800"
                        : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {candidate.aiEvaluation.matchPercentage}% Match
                </Badge>
              )}
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="profile" className="mt-6" onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-3 mb-6">
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="resume">Resume</TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="col-span-2 space-y-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-medium mb-3">Contact Information</h3>
                  <div className="space-y-3">
                    {candidate.email && (
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-gray-500" />
                        <span>{candidate.email}</span>
                      </div>
                    )}
                    {candidate.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-gray-500" />
                        <span>{candidate.phone}</span>
                      </div>
                    )}
                    {candidate.appliedAt && (
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-gray-500" />
                        <span>Applied on {new Date(candidate.appliedAt).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>

                {candidate.aiEvaluation?.strengths && candidate.aiEvaluation?.strengths.length > 0 && (
                  <div>
                    <h3 className="font-medium mb-3">Strengths</h3>
                    <ul className="list-disc pl-5 space-y-1">
                      {candidate.aiEvaluation.strengths.map((strength, index) => (
                        <li key={index} className="text-gray-700">{strength}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {candidate.aiEvaluation?.weaknesses && candidate.aiEvaluation?.weaknesses.length > 0 && (
                  <div>
                    <h3 className="font-medium mb-3">Areas for Improvement</h3>
                    <ul className="list-disc pl-5 space-y-1">
                      {candidate.aiEvaluation.weaknesses.map((weakness, index) => (
                        <li key={index} className="text-gray-700">{weakness}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="font-medium mb-3">Application Details</h3>
                  <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                    {candidate.status && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Status</span>
                        <Badge className="capitalize">{candidate.status}</Badge>
                      </div>
                    )}
                    {candidate.experience !== undefined && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Experience</span>
                        <span>{candidate.experience} years</span>
                      </div>
                    )}
                    {candidate.immediateJoiner !== undefined && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Immediate Joiner</span>
                        <Badge variant={candidate.immediateJoiner ? "default" : "outline"}>
                          {candidate.immediateJoiner ? "Yes" : "No"}
                        </Badge>
                      </div>
                    )}
                    {candidate.interviewDate && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Interview Date</span>
                        <span>{new Date(candidate.interviewDate).toLocaleDateString()}</span>
                      </div>
                    )}
                    {candidate.offerLetter !== undefined && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Offer Letter</span>
                        <Badge variant={candidate.offerLetter ? "default" : "outline"}>
                          {candidate.offerLetter ? "Sent" : "Not Sent"}
                        </Badge>
                      </div>
                    )}
                  </div>
                </div>

                {candidate.aiEvaluation?.score && (
                  <div>
                    <h3 className="font-medium mb-3">AI Evaluation Score</h3>
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="flex justify-between text-sm mb-1">
                        <span>Overall Score</span>
                        <span>{candidate.aiEvaluation.score}/100</span>
                      </div>
                      <Progress value={candidate.aiEvaluation.score} className="h-2" />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="resume">
            <div className="bg-gray-50 p-6 rounded-lg min-h-[400px] flex flex-col items-center justify-center">
              <FileText className="h-12 w-12 text-gray-400 mb-4" />
              <h3 className="font-medium text-lg mb-2">Resume Preview</h3>
              <p className="text-gray-500 mb-4 text-center max-w-md">
                {candidate.s3FileKey 
                  ? "View the candidate's full resume to get a comprehensive understanding of their experience and qualifications."
                  : "No resume available for this candidate."}
              </p>
              {candidate.s3FileKey && (
                <Button onClick={viewResume}>
                  <FileText className="h-4 w-4 mr-2" />
                  View Full Resume
                </Button>
              )}
            </div>
          </TabsContent>

          <TabsContent value="notes">
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-3">Interview Notes</h3>
                {notes.length > 0 ? (
                  <div className="space-y-4">
                    {notes.map((note, index) => (
                      <div key={index} className="bg-white p-4 rounded-lg border border-gray-200">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <div className="text-sm text-gray-500">Note #{index + 1}</div>
                          </div>
                        </div>
                        <p className="text-sm text-gray-700">{note}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-gray-50 p-4 rounded-lg text-center">
                    <p className="text-gray-500">No notes have been added yet.</p>
                  </div>
                )}
              </div>

              <div>
                <div className="flex justify-between items-center mb-3">
                  <h3 className="font-medium">Add Note</h3>
                </div>
                <textarea
                  className="w-full p-3 border border-gray-300 rounded-md h-24 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="Add your notes about this candidate..."
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                />
                <div className="flex justify-end mt-2">
                  <Button 
                    size="sm" 
                    onClick={addNote} 
                    disabled={isSubmitting || !newNote.trim()}
                  >
                    <MessageSquare className="h-4 w-4 mr-2" />
                    {isSubmitting ? "Saving..." : "Save Note"}
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex justify-between items-center border-t pt-4 mt-4">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              className="border-red-200 text-red-600 hover:bg-red-50"
              onClick={async () => {
                try {
                  await axios.put(`http://localhost:5000/api/applications/${candidate._id}/status`, {
                    status: "rejected"
                  });
                  onClose();
                } catch (error) {
                  console.error("Failed to reject candidate:", error);
                }
              }}
            >
              <X className="h-4 w-4 mr-1" />
              Reject
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              className="border-amber-200 text-amber-600 hover:bg-amber-50"
              onClick={async () => {
                try {
                  await axios.put(`http://localhost:5000/api/applications/${candidate._id}/status`, {
                    status: "shortlisted"
                  });
                  onClose();
                } catch (error) {
                  console.error("Failed to shortlist candidate:", error);
                }
              }}
            >
              <Star className="h-4 w-4 mr-1" />
              Shortlist
            </Button>
            <Button 
              size="sm" 
              className="bg-purple-600 hover:bg-purple-700"
              onClick={async () => {
                const date = prompt("Enter interview date (YYYY-MM-DD):");
                if (!date) return;
                
                try {
                  await axios.put(`http://localhost:5000/api/applications/${candidate._id}/interview`, {
                    interviewDate: new Date(date)
                  });
                  onClose();
                } catch (error) {
                  console.error("Failed to schedule interview:", error);
                }
              }}
            >
              <Calendar className="h-4 w-4 mr-1" />
              Schedule Interview
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}