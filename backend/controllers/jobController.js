import JobPosts from "../models/JobPosts.js";

const deleteJobPost = async (req, res) => {
    try {
        const id = req.body;
        const response = await JobPosts.findByIdAndDelete(id);
    }
    catch (err) {
        console.log("Error deleting job post: ", err);
    }
}

const closeJobPost = async(req,res)=>{
    try{
         const id = req.body;
         const response = await JobPosts.findByIdAndUpdate(id,{status:"closed"}); 
         res.json("Job post closed successfully: ", response);
    }catch(error){res.json("Error closing job post: ",error);
}
}

export { deleteJobPost, closeJobPost };