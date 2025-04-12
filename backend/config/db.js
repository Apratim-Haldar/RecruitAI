import mongoose from "mongoose";
import dotenv from "dotenv";
dotenv.config();

const dbConnect = () =>{
  /* console.log(process.env.MONGODB_URI); */
mongoose
  .connect(process.env.MONGODB_URI)
  .then(() => console.log("Connected to MongoDB"))
  .catch((err) => console.error("Could not connect to MongoDB", err));
}

export default dbConnect