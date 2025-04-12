import mongoose from "mongoose";

const jobPostSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: { type: String, required: true },
  jobType:{type: String, required: true},
  createdBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Users',
    required: true
  },
  location: { type: String, required: true },
  noOfOpenings: {type: Number, required: true},
  createdAt: { type: Date, default: Date.now },
  deadline: { type: Date, required: true },
  status: { type: String, enum: ["open", "closed"], default: "open" },
});

const JobPosts = mongoose.model("JobPosts", jobPostSchema);

export default JobPosts;