# file_utils.py
from unstructured.partition.auto import partition
import os

# Create a dedicated folder for uploads if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def save_uploaded_file(uploaded_file_object):
    """Saves a file-like object (from web framework) to the UPLOAD_FOLDER."""
    # In a real web app, 'uploaded_file_object' would have a filename attribute
    # For now, let's simulate or require a filename parameter
    # This needs adaptation based on how files are handled in your eventual web app
    # Placeholder: Assume filename is 'uploaded_resume.<ext>'
    # filename = uploaded_file_object.filename # Ideal case with web framework object
    
    # Basic simulation: if it's just a path passed, use that directly
    if isinstance(uploaded_file_object, str):
         # If it's already a path, maybe just return it? Or copy it?
         # Let's assume for now it's a path to an existing file we want to ensure is readable
         if os.path.exists(uploaded_file_object):
             print(f"File exists at path: {uploaded_file_object}")
             # We might want to copy it to our uploads folder for consistency
             # For simplicity now, just return the valid path
             return uploaded_file_object 
         else:
              print(f"Error: File path provided does not exist: {uploaded_file_object}")
              return None # Indicate error
    
    # If it's a file object (like from 'open()'), this is tricky without a name
    # This part definitely needs modification for web framework integration
    print("Error: Direct file object handling without filename is not fully implemented yet.")
    # Example placeholder: saving with a generic name (NOT ROBUST)
    # temp_filename = "temp_uploaded_file"
    # save_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    # try:
    #      with open(save_path, 'wb') as f:
    #           # If uploaded_file_object has a read method
    #           f.write(uploaded_file_object.read())
    #      return save_path
    # except Exception as e:
    #      print(f"Error saving file object: {e}")
    return None # Indicate failure / need for real implementation


def extract_text_from_file(file_path):
    """Extracts text from PDF, DOCX, DOC, TXT files using unstructured."""
    
    # Check if the file path is valid first
    if not file_path or not isinstance(file_path, str):
         print(f"Error: Invalid file_path provided: {file_path}")
         return "Error: Invalid file path."
         
    # Ensure the file actually exists before passing to partition
    if not os.path.exists(file_path):
        print(f"Error: File not found at path: {file_path}")
        return "Error: File not found."
        
    print(f"Attempting to extract text from: {file_path}") # Debug print
    try:
        # Using unstructured's partition function
        elements = partition(filename=file_path)
        # Concatenate the text content of all detected elements
        full_text = "\n".join([str(el) for el in elements])
        if not full_text.strip():
             print(f"Warning: No text extracted from {file_path}. File might be empty or image-based.")
             return "Warning: No text extracted (file might be empty or image-based)."
        return full_text
    except Exception as e:
        # Catch potential errors during partitioning (e.g., corrupted file, unsupported format)
        print(f"Error processing file {file_path} with unstructured: {e}")
        # Optional: Add a fallback for simple .txt files if unstructured fails
        if file_path.lower().endswith(".txt"):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    print("Attempting fallback text read for .txt file.")
                    return f.read()
            except Exception as fallback_e:
                 print(f"Fallback reading error for {file_path}: {fallback_e}")
                 
        # Return a specific error message if all attempts fail
        return f"Error: Could not extract text from file. Exception: {e}"

# --- Simple Test ---
if __name__ == "__main__":
    # Create a dummy .txt file in the project directory for testing
    TEST_FILENAME = 'sample_resume.txt'
    try:
        with open(TEST_FILENAME, 'w') as f:
            f.write("John Sample\n")
            f.write("Software Developer\n\n")
            f.write("Skills: Python, Java, SQL\n")
            f.write("Experience: 3 years at Tech Solutions Inc.\n")
        print(f"Created dummy file: {TEST_FILENAME}")

        # Test text extraction
        extracted_text = extract_text_from_file(TEST_FILENAME)
        print("\n--- Extracted Text ---")
        if "Error:" not in extracted_text and "Warning:" not in extracted_text :
            print(extracted_text)
        else:
            print(f"Extraction failed or file empty: {extracted_text}")
            
        # Clean up the dummy file
        # os.remove(TEST_FILENAME) # Keep it for now for other tests
        # print(f"\nRemoved dummy file: {TEST_FILENAME}")

    except Exception as test_e:
        print(f"\nError during test setup or execution: {test_e}")
