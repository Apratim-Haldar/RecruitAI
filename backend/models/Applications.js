import mongoose from "mongoose";


const applicationSchema = new mongoose.Schema({
  firstName: { type: String, required: true },
  lastName: { type: String, required: true },
  email: { type: String, required: true },
  phone: {type: String, required: true},
  jobPost: { 
    type: mongoose.Schema.Types.ObjectId,
    ref: "JobPosts",
    required: true
  },
  s3FileKey: { type: String, required: true }, // Changed from resumePath
  status: {
    type: String,
    enum: ["applied", "shortlisted", "rejected", "selected"],
    default: "applied"
  },
  phone: {
    type: String,
    required: true,
    validate: {
      validator: function(v) {
        return /^\+?[0-9\s-]{7,}$/.test(v);
      },
      message: props => `${props.value} is not a valid phone number!`
    }
  },
  experience:{
    type:Number,
    required:true,
    min:0,
    max:99,
  },
  interviewDate: { type: Date, default:null },
  offerLetter: { type: Boolean, default: false },
  appliedAt: { type: Date, default: Date.now },
  immediateJoiner: { type: Boolean, default: false },
  aiEvaluation: {
    score: Number,
    matchPercentage: Number,
    strengths: [String],
    weaknesses: [String],
  },
  notes: {type:[String] ,default:[], required: false},
});

applicationSchema.index({ candidate: 1, jobPost: 1 }, { unique: true });

const Applications = mongoose.model("Applications", applicationSchema);

export default Applications;
