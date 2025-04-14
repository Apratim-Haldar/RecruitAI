import express from 'express';
import multer from "multer";

const jobRouter = express.Router();

import { deleteJobPost, closeJobPost } from '../controllers/jobController.js';

jobRouter.route("/delete").post(deleteJobPost);
jobRouter.route("/close").post(closeJobPost);


export default jobRouter;