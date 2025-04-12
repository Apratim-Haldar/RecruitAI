import mongoose from "mongoose";

export type ApplicationStatus = 
  | "applied" 
  | "shortlisted" 
  | "rejected" 
  | "selected";

export interface Application {
  _id: string;
  firstName: string;
  lastName: string;
  email: string;
  jobPost: string;
  status: ApplicationStatus;
  appliedAt: string;
  s3FileKey: string;
  phone?: string;
  aiEvaluation?: {
    score: number;
    matchPercentage: number;
    strengths: string[];
    weaknesses: string[];
  };
}

export type applicantType = {
  _id:string,
  firstName:string,
  lastName:string,
  email:string,
  jobPost: mongoose.Schema.Types.ObjectId,
  phone:string,
  s3FileKey: string,
  status:string,
  experience: number,
  immediateJoiner: boolean,
  aiEvaluation:{
    score: number,
    matchPercentage: number,
    strengths: [string],
    weaknesses: [string],
  },
  appliedAt: Date
}