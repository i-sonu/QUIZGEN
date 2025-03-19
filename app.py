from groq import Groq
from fpdf import FPDF
import json
import os
from flask import Flask, render_template, request, send_file, flash, session, redirect, url_for
import tempfile
import PyPDF2
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
logger.info("Flask application initialized")

# Configure upload folder with absolute path
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Upload folder configured at: {UPLOAD_FOLDER}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """Extract text from all pages of a PDF file"""
    text = ""
    try:
        logger.info(f"Starting text extraction from PDF: {pdf_path}")
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {num_pages} pages")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text += page.extract_text() + "\n"
                logger.debug(f"Extracted text from page {page_num}/{num_pages}")
                
        logger.info(f"Successfully extracted text from PDF. Text length: {len(text)} characters")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}", exc_info=True)
        return None

class QuizGenerator:
    def __init__(self, groq_api_key):
        try:
            logger.info("Initializing Groq client")
            self.client = Groq(api_key=groq_api_key)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Groq client: {str(e)}", exc_info=True)
            self.client = None

    def _get_llm_response(self, prompt):
        """Get structured response from LLM"""
        if not self.client:
            logger.error("Groq client not initialized")
            return None
            
        try:
            logger.info("Sending request to Groq API")
            completion = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that returns only JSON data. Generate quiz questions based on the provided study material."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            response = completion.choices[0].message.content
            logger.info("Received response from Groq API")
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}", exc_info=True)
            return None

    def generate_quiz(self, study_material, num_questions):
        """Generate quiz using LLM based on study material"""
        logger.info(f"Generating quiz with {num_questions} questions")
        prompt = f"""
        Based on the following study material, generate a quiz with {num_questions} questions.
        Make sure the questions are directly related to the content in the study material.
        
        Study Material:
        {study_material}
        
        Return ONLY a JSON array:
        [
            {{"question": "Question 1", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "Correct Answer"}},
            {{"question": "Question 2", "options": ["Option A", "Option B", "Option C", "Option D"], "answer": "Correct Answer"}},
            ...
        ]
        """
        quiz_data = self._get_llm_response(prompt)
        if quiz_data:
            logger.info(f"Successfully generated quiz with {len(quiz_data)} questions")
        else:
            logger.error("Failed to generate quiz")
        return quiz_data

    def save_quiz_to_pdf(self, quiz_data, filename):
        """Save quiz data to PDF"""
        try:
            logger.info(f"Saving quiz to PDF: {filename}")
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)

            pdf.cell(0, 10, "Generated Quiz", ln=True, align="C")
            pdf.ln(10)

            for i, q in enumerate(quiz_data):
                pdf.set_font("Arial", "B", 12)
                pdf.multi_cell(0, 10, f"{i + 1}. {q['question']}")
                pdf.set_font("Arial", "", 12)
                for option in q['options']:
                    pdf.multi_cell(0, 10, f"  - {option}")

                pdf.ln(5)

                # Answer section (Optional)
                pdf.set_font("Arial", "I", 10)
                pdf.multi_cell(0, 10, f"Answer: {q['answer']}")
                pdf.ln(5)

            pdf.output(filename)
            logger.info(f"Successfully saved quiz to PDF: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving quiz to PDF: {str(e)}", exc_info=True)
            return None

# Initialize QuizGenerator with API key from environment variable
logger.info("Initializing QuizGenerator")
generator = QuizGenerator(os.environ.get('GROQ_API_KEY'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        logger.info("Received POST request to index route")
        if 'file' not in request.files:
            logger.warning("No file uploaded in request")
            flash('No file uploaded', 'error')
            return render_template('index.html')
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("Empty filename in uploaded file")
            flash('No file selected', 'error')
            return render_template('index.html')
        
        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            flash('Invalid file type. Please upload a PDF file.', 'error')
            return render_template('index.html')
        
        num_questions = int(request.form.get('num_questions', 5))
        logger.info(f"Processing PDF upload: {file.filename} with {num_questions} questions")
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logger.info(f"Saved uploaded file to: {filepath}")
        
        # Extract text from PDF
        study_material = extract_text_from_pdf(filepath)
        if not study_material:
            logger.error("Failed to extract text from PDF")
            flash('Failed to extract text from PDF. Please try again.', 'error')
            return render_template('index.html')
        
        # Generate quiz
        quiz = generator.generate_quiz(study_material, num_questions)
        
        if quiz:
            # Store quiz data in session
            session['quiz_data'] = quiz
            session['pdf_path'] = filepath
            logger.info("Successfully generated quiz and stored in session")
            flash(f'Successfully uploaded {filename}! Generating quiz...', 'success')
            return redirect(url_for('take_quiz'))
        else:
            logger.error("Failed to generate quiz")
            flash('Failed to generate quiz. Please try again.', 'error')
            # Clean up the uploaded file
            os.remove(filepath)
            logger.info(f"Cleaned up uploaded file: {filepath}")
    
    logger.info("Rendering index page")
    return render_template('index.html')

@app.route('/quiz', methods=['GET'])
def take_quiz():
    if 'quiz_data' not in session:
        logger.warning("Attempted to access quiz page without quiz data in session")
        return redirect(url_for('index'))
    logger.info("Rendering quiz page")
    return render_template('quiz.html', quiz_data=session['quiz_data'])

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'quiz_data' not in session:
        logger.warning("Attempted to submit quiz without quiz data in session")
        return redirect(url_for('index'))
    
    logger.info("Processing quiz submission")
    quiz_data = session['quiz_data']
    answers = []
    score = 0
    
    # Get user answers
    for i in range(len(quiz_data)):
        answer = request.form.get(f'q{i}')
        answers.append(answer if answer else '')  # Handle unanswered questions
        if answer == quiz_data[i]['answer']:
            score += 1
    
    # Calculate percentage
    percentage = (score / len(quiz_data)) * 100
    logger.info(f"Quiz results - Score: {score}/{len(quiz_data)} ({percentage:.1f}%)")
    
    # Store results in session
    session['score'] = score
    session['total'] = len(quiz_data)
    session['percentage'] = percentage
    session['answers'] = answers
    
    return render_template('quiz.html', 
                         quiz_data=quiz_data, 
                         show_results=True, 
                         score=score, 
                         total=len(quiz_data), 
                         percentage=percentage,
                         answers=answers)

@app.route('/download_quiz')
def download_quiz():
    if 'quiz_data' not in session or 'pdf_path' not in session:
        logger.warning("Attempted to download quiz without required session data")
        return redirect(url_for('index'))
    
    logger.info("Generating quiz PDF for download")
    # Create a temporary file for the quiz PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        pdf_path = generator.save_quiz_to_pdf(session['quiz_data'], tmp.name)
        if pdf_path:
            # Clean up the uploaded file
            os.remove(session['pdf_path'])
            logger.info("Successfully generated and cleaned up quiz PDF")
            return send_file(pdf_path, as_attachment=True, download_name='quiz.pdf')
        else:
            logger.error("Failed to generate quiz PDF")
            flash('Failed to generate quiz PDF. Please try again.', 'error')
            return redirect(url_for('index'))

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True)
