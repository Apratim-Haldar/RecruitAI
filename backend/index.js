import express from 'express';
import cors from 'cors';
import JobPosts from './models/JobPosts.js';
import dbConnect from './config/db.js'; 
import dotenv from "dotenv";
import cookieParser from 'cookie-parser';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import Users from './models/Users.js'
import jobRouter from './routes/jobRoutes.js';
import Applications from './models/Applications.js';
// Add at the top with other imports
import { S3Client } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { PutObjectCommand } from '@aws-sdk/client-s3';
import fetch from 'node-fetch';
// Configure S3 client
const s3 = new S3Client({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY,
    secretAccessKey: process.env.AWS_SECRET_KEY
  }
});

dotenv.config();

const app = express();
app.use(cors({
  origin: ['http://localhost:5173','http://127.0.0.1:8080/ask'],
  credentials: true
}));
const PORT = process.env.PORT || 3000;

dbConnect();
app.use(express.json());

app.use(cookieParser());
const JWT_SECRET = process.env.JWT_SECRET || 'your_jwt_secret_here';
const HR_SECRET_CODE = process.env.HR_SECRET || 'COMPANY_HR_CODE_123';

app.use("/api/job-routes", jobRouter);


app.post('/api/signup', async (req, res) => {
  try {
    const { name, email, password, role, companyCode } = req.body;
    
    // Add input validation
    if (!name || !email || !password) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    if (role === 'hr') {
      if (!companyCode) {
        return res.status(400).json({ error: 'Company code required for HR registration' });
      }
      if (companyCode !== HR_SECRET_CODE) {
        return res.status(403).json({ error: 'Invalid company code' });
      }
    }

    // Ensure password is a string
    if (typeof password !== 'string') {
      return res.status(400).json({ error: 'Invalid password format' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const user = await Users.create({
      name,
      email,
      password: hashedPassword,
      role: role || 'candidate'
    });

    const token = jwt.sign({ id: user._id, role: user.role }, JWT_SECRET);
    res.cookie('authToken', token, { httpOnly: true, secure: true, maxAge: 86400000 });
    res.json({ user: { id: user._id, name: user.name, role: user.role } });
  } catch (error) {
    console.error('Signup error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const user = await Users.findOne({ email });
    
    if (!user || !(await bcrypt.compare(password, user.password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = jwt.sign({ id: user._id, role: user.role }, JWT_SECRET);
    res.cookie('authToken', token, { httpOnly: true, secure:false,sameSite: 'lax' ,sameSite: 'lax' });
    res.json({ user: { id: user._id, name: user.name, role: user.role, maxAge: 86400000  }});
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/verify-auth', async (req, res) => {
  const token = req.cookies.authToken;
  if (!token) return res.status(401).json({ error: 'Unauthorized' });

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const user = await Users.findById(decoded.id);
    res.json({ role: user.role, user:user });
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Add auth middleware
const authenticateHR = async (req, res, next) => {
  const token = req.cookies.authToken;
  if (!token) return res.status(401).json({ error: 'Unauthorized' });

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    if (decoded.role !== 'hr') throw new Error();
    
    const user = await Users.findById(decoded.id);
    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

app.post("/api/upload-pdf", authenticateHR, async (req, res) => {
  try {
    // Get the multipart form data from the request
    if (!req.files || !req.files.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }
    
    const pdfFile = req.files.file;
    
    // Check if it's a PDF
    if (!pdfFile.name.endsWith('.pdf')) {
      return res.status(400).json({ error: "File must be a PDF" });
    }
    
    // Create a FormData object to send to the Python service
    const formData = new FormData();
    formData.append('file', pdfFile.data, {
      filename: pdfFile.name,
      contentType: 'application/pdf'
    });
    
    // Add the user ID to the request
    const userId = req.user._id.toString();
    
    // Call the Python service
    const pythonResponse = await fetch(`http://localhost:8080/upload?user_id=${userId}`, {
      method: 'POST',
      body: formData
    });
    
    // Get the response from the Python service
    const data = await pythonResponse.json();
    
    if (!pythonResponse.ok) {
      throw new Error(data.detail || "Failed to process PDF");
    }
    
    // Return the response to the frontend
    res.json(data);
  } catch (error) {
    console.error("Error uploading PDF:", error);
    res.status(500).json({ error: error.message });
  }
});
// Update create-job-post route to use auth middleware
app.post("/api/create-job-post", authenticateHR, async (req, res) => {
  try {
    const { title, description, noOfOpenings, deadline, location,jobType } = req.body;
    const response = await JobPosts.create({
      title,
      location,
      jobType,
      description,
      noOfOpenings,
      deadline,
      createdBy: req.user._id, // Now using the authenticated user's ID
      status: "open"
    });
    res.json(response);
  }
  catch (e) {
    res.status(500).json({ error: e.message });
  }
});
app.get("/api/get-job-posts", authenticateHR, async (req, res) => {
  try {
    const response = await JobPosts.find({ createdBy: req.user._id });
    const response2 = await JobPosts.find({ createdBy: req.user._id, status: 'open' });
    // Fix: Use an object to return both responses
    res.json({ response, response2 });
  }
  catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/hr/applications-summary', authenticateHR, async (req, res) => {
  try {
    // First get all job posts created by this HR
    const hrJobs = await JobPosts.find({ createdBy: req.user._id });
    
    // Extract job IDs
    const jobIds = hrJobs.map(job => job._id);
    
    // Get all applications for these jobs
    const allApplications = await Applications.find({ jobPost: { $in: jobIds } });
    
    // Get shortlisted applications
    const shortlistedApplications = allApplications.filter(app => app.status === 'shortlisted');
    
    // Get applications with interview dates
    const interviewApplications = allApplications.filter(app => app.interviewDate != null);
    
    // Get applications with offer letters
    const offerApplications = allApplications.filter(app => app.offerLetter === true);
    
    res.json({
      totalJobs: hrJobs.length,
      totalApplications: allApplications.length,
      totalShortlisted: shortlistedApplications.length,
      totalInterviews: interviewApplications.length,
      totalOffers: offerApplications.length
    });
  } catch (error) {
    console.error('Error fetching application summary:', error);
    res.status(500).json({ error: error.message });
  }
});
// Route to reopen a job post
app.put("/api/reopen-job/:jobId", authenticateHR, async (req, res) => {
  try {
    const jobId = req.params.jobId;
    
    // Find the job and verify it belongs to this HR
    const job = await JobPosts.findOne({ 
      _id: jobId,
      createdBy: req.user._id 
    });
    
    if (!job) {
      return res.status(404).json({ error: "Job not found or unauthorized" });
    }
    
    // Update the job status to open
    job.status = "open";
    await job.save();
    
    res.json({ success: true, job });
  } catch (e) {
    console.error("Error reopening job:", e);
    res.status(500).json({ error: e.message });
  }
});

app.put("/api/close-job/:jobId", authenticateHR, async (req, res) => {
  try {
    const jobId = req.params.jobId;
    
    // Find the job and verify it belongs to this HR
    const job = await JobPosts.findOne({ 
      _id: jobId,
      createdBy: req.user._id 
    });
    
    if (!job) {
      return res.status(404).json({ error: "Job not found or unauthorized" });
    }
    
    // Update the job status to closed
    job.status = "closed";
    await job.save();
    
    res.json({ success: true, job });
  } catch (e) {
    console.error("Error closing job:", e);
    res.status(500).json({ error: e.message });
  }
});
// Keep public job posts for landing page
app.get("/api/public/job-posts", async (req, res) => {
  try {
    const response = await JobPosts.find({ status: 'open' });
    res.json(response);
  }
  catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/api/public/job-posts/:id", async (req, res) => {
  try {
    const job = await JobPosts.findById(req.params.id);
    if (!job) return res.status(404).json({ error: "Job not found" });
    res.json(job);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Add to existing routes
// ... existing code ...

// Update the apply route to handle duplicate applications
app.post('/api/apply', async (req, res) => {
  try {
    const applicationData = {
      ...req.body,
      appliedAt: new Date(),
      status: "applied"
    };
    
    const application = await Applications.create(applicationData);
    res.json(application);
  } catch (error) {
    console.error('Application submission error:', error);
    
    // Check if this is a duplicate key error
    if (error.code === 11000 && error.keyPattern && error.keyPattern.email && error.keyPattern.jobPost) {
      return res.status(400).json({ 
        error: "You have already applied for this position",
        isDuplicate: true
      });
    }
    
    res.status(400).json({ 
      error: error.message,
      details: error.errors // Mongoose validation details
    });
  }
});

// ... rest of the code ...

app.get('/api/s3-presigned-url', async (req, res) => {
  const { fileName, fileType } = req.query;
  
  const command = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET,
    Key: `resumes/${Date.now()}_${fileName}`,
    ContentType: fileType
  });

  try {
    const url = await getSignedUrl(s3, command, { expiresIn: 300 });
    res.json({ 
      url,
      key: command.input.Key 
    });
  } catch (error) {
    console.error('S3 Presigned URL Error:', error);
    res.status(500).json({ error: 'Failed to generate upload URL' });
  }
});

// Add to existing routes
app.get('/api/applications/:jobId', authenticateHR, async (req, res) => {
  try {
    const applications = await Applications.find({ jobPost: req.params.jobId });
    const shortlisted = applications.filter(app => app.status === 'shortlisted');
    const interviews = applications.filter(app => app.interviewDate!=null);
    const offers = applications.filter(app => app.offerLetter===true);
    res.json({applications, shortlisted, interviews, offers});
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/applications/:applicationId/:status', authenticateHR, async (req, res) => {
  try {
    const { applicationId, status } = req.params;
    const application = await Applications.findByIdAndUpdate(
      req.params.applicationId,
      { status },
      { new: true }
    );
    
    if (!application) {
      return res.status(404).json({ error: 'Application not found' });
    }
    
    res.json(application);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

//*******AWS ROUTES******************************************************************************/

import { GetObjectCommand } from "@aws-sdk/client-s3";


app.get('/api/get-pdfFile/:key', async (req, res) => {
  const key = req.params.key;
  
  const params = {
    Bucket: process.env.S3_BUCKET || 'genai-job-applications',
    Key: key
  };
  
  try {
    const command = new GetObjectCommand(params);
    const response = await s3.send(command);
    const pdfBuffer = await response.Body.transformToByteArray();
    
    res.set('Content-Type', 'application/pdf');
    res.send(Buffer.from(pdfBuffer));

  } catch (error) {
    console.error('PDF download error:', error);
    res.status(500).json({ 
      error: 'Failed to retrieve PDF',
      message: error.message 
    });
  }
});



// Start the Express server
app.listen(5000, () => {
  console.log("Server is running on port 5000");
});