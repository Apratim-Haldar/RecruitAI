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
  origin: 'http://localhost:5173',
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
    res.json({ role: user.role });
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
    res.json(response);
  }
  catch (e) {
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
    res.status(400).json({ 
      error: error.message,
      details: error.errors // Mongoose validation details
    });
  }
});

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
    const { status } = req.params;
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


app.get('/api/get-pdfFile', async (req, res) => {
  const params = {
    Bucket: 'genai-job-applications',
    Key: 'resumes/1744444924642_Apratim_Haldar_CV.pdf'
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