from groq import Groq
from fpdf import FPDF
import json
import os
from flask import Flask, render_template, request, send_file, flash, session, redirect, url_for, jsonify
import tempfile
import PyPDF2
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from threading import Thread
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configure upload folder with absolute path
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """Extract text from all pages of a PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None
    return text

class QuizGenerator:
    def __init__(self, groq_api_key):
        try:
            self.client = Groq(api_key=groq_api_key)
        except Exception as e:
            print(f"Error initializing Groq client: {str(e)}")
            self.client = None

    def _get_llm_response(self, prompt):
        """Get structured response from LLM"""
        if not self.client:
            print("Groq client not initialized")
            return None
            
        try:
            completion = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that returns only JSON data. Generate quiz questions based on the provided study material."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"Error getting LLM response: {str(e)}")
            return None

    def generate_quiz(self, study_material, num_questions):
        """Generate quiz using LLM based on study material"""
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
        return self._get_llm_response(prompt)

    def save_quiz_to_pdf(self, quiz_data, filename):
        """Save quiz data to PDF"""
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
        return filename

# Initialize QuizGenerator with API key from environment variable
generator = QuizGenerator(os.environ.get('GROQ_API_KEY'))

class QuizStatus:
    def __init__(self):
        self.status = "pending"
        self.quiz_data = None
        self.error = None

quiz_status = QuizStatus()

def generate_quiz_async(study_material, num_questions, filepath):
    """Generate quiz in background"""
    try:
        quiz = generator.generate_quiz(study_material, num_questions)
        if quiz:
            quiz_status.quiz_data = quiz
            quiz_status.status = "completed"
        else:
            quiz_status.status = "error"
            quiz_status.error = "Failed to generate quiz"
            os.remove(filepath)
    except Exception as e:
        quiz_status.status = "error"
        quiz_status.error = str(e)
        os.remove(filepath)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return render_template('index.html')
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return render_template('index.html')
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a PDF file.', 'error')
            return render_template('index.html')
        
        num_questions = int(request.form.get('num_questions', 5))
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text from PDF
        study_material = extract_text_from_pdf(filepath)
        if not study_material:
            flash('Failed to extract text from PDF. Please try again.', 'error')
            return render_template('index.html')
        
        # Reset quiz status
        quiz_status.status = "pending"
        quiz_status.quiz_data = None
        quiz_status.error = None
        
        # Start quiz generation in background
        thread = Thread(target=generate_quiz_async, args=(study_material, num_questions, filepath))
        thread.daemon = True
        thread.start()
        
        # Store filepath in session for later use
        session['pdf_path'] = filepath
        flash(f'Successfully uploaded {filename}! Generating quiz...', 'success')
        return render_template('index.html', generating=True)
    
    return render_template('index.html')

@app.route('/check_quiz_status')
def check_quiz_status():
    if quiz_status.status == "completed":
        session['quiz_data'] = quiz_status.quiz_data
        return jsonify({"status": "completed"})
    elif quiz_status.status == "error":
        return jsonify({"status": "error", "message": quiz_status.error})
    return jsonify({"status": "pending"})

@app.route('/quiz', methods=['GET'])
def take_quiz():
    if 'quiz_data' not in session:
        return redirect(url_for('index'))
    return render_template('quiz.html', quiz_data=session['quiz_data'])

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'quiz_data' not in session:
        return redirect(url_for('index'))
    
    quiz_data = session['quiz_data']
    answers = []
    score = 0
    
    print("\n=== Quiz Submission Debug ===")
    print(f"Total questions: {len(quiz_data)}")
    
    # Get user answers
    for i in range(len(quiz_data)):
        answer = request.form.get(f'q{i}')
        answers.append(answer if answer else '')  # Handle unanswered questions
        
        print(f"\nQuestion {i+1}:")
        print(f"User's answer: '{answer}'")
        print(f"Correct answer: '{quiz_data[i]['answer']}'")
        print(f"Options: {quiz_data[i]['options']}")
        
        # Check if the selected option matches the correct answer
        if answer and answer == quiz_data[i]['answer']:
            score += 1
            print("✓ Correct!")
        else:
            print("✗ Wrong!")
    
    print(f"\nFinal Score: {score}/{len(quiz_data)}")
    
    # Calculate percentage
    percentage = (score / len(quiz_data)) * 100
    
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
                         answers=answers)  # Pass answers to template

@app.route('/download_quiz')
def download_quiz():
    if 'quiz_data' not in session or 'pdf_path' not in session:
        return redirect(url_for('index'))
    
    # Create a temporary file for the quiz PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        pdf_path = generator.save_quiz_to_pdf(session['quiz_data'], tmp.name)
        # Clean up the uploaded file
        os.remove(session['pdf_path'])
        return send_file(pdf_path, as_attachment=True, download_name='quiz.pdf')

if __name__ == '__main__':
    app.run(debug=True)
