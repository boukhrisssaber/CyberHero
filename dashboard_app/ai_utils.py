import os
import google.generativeai as genai

# Configure the Gemini API client
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash') # Use the fast and capable model
except Exception as e:
    print(f"Error configuring Gemini AI: {e}")
    model = None

def generate_content(content_type, prompt):
    """
    Generates content using the Gemini API based on the type and prompt.
    """
    if not model:
        return "Error: Gemini AI model is not configured. Check API key."

    # We use a "system prompt" to give the AI context and instructions
    if content_type == 'phishing_email':
        system_prompt = """
        You are a cybersecurity expert specializing in creating realistic phishing email templates for security awareness training.
        Your task is to generate a complete, well-formatted HTML email based on the user's prompt.
        The email must contain a clear call-to-action link. For the link's href, you MUST use the exact placeholder '{{.URL}}'.
        Do not add any explanations. Only output the raw HTML code.
        """
        full_prompt = f"{system_prompt}\n\nUser Prompt: {prompt}"
    
    elif content_type == 'moodle_quiz':
        system_prompt = """
        You are an expert in instructional design for cybersecurity.
        Your task is to create a set of multiple-choice quiz questions based on the user's prompt.
        Format the output in a clean, human-readable text format. For each question, provide the question, four options (A, B, C, D), and clearly indicate the correct answer.
        Do not add any explanations. Only output the formatted quiz questions and answers.
        """
        full_prompt = f"{system_prompt}\n\nUser Prompt: {prompt}"
    
    else:
        return "Error: Invalid content type specified."

    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return f"An error occurred while generating content: {e}"