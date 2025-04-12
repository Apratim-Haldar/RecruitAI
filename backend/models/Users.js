import mongoose from "mongoose";

const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  role: { type: String, enum: ["hr", "candidate"], default: "candidate" },
  applications: [{ type: mongoose.Schema.Types.ObjectId, ref: "Application" }],
  createdAt: { type: Date, default: Date.now },
});

const Users = mongoose.model("Users", userSchema);

export default Users;
