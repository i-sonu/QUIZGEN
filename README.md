# QUIZGEN - PDF to Quiz Generator

This application converts PDF documents into interactive multiple-choice quizzes using AI. It extracts text from PDFs and generates relevant quiz questions using the Groq API.

## Features

- PDF text extraction
- AI-powered quiz generation using Groq API
- Interactive web interface with modern design
- Multiple choice questions with 4 options
- Quiz review with correct/incorrect answer marking
- Quiz results download as PDF

## Prerequisites

- Python 3.7 or higher
- Groq API key

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/i-sonu/QUIZGEN.git
   cd QUIZGEN
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Groq API key:
   ```
   GROQ_API_KEY=your_api_key_here
   SECRET_KEY=your_secret_key_here
   ```

## Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

3. Upload a PDF file and specify the number of questions

4. Wait for the quiz to be generated

5. Take the quiz and review your results

## How it Works

1. The application extracts text from the uploaded PDF using PyPDF2
2. The extracted text is sent to the Groq API to generate relevant quiz questions
3. Questions are presented in an interactive format with smooth transitions
4. Users can review their answers with correct/incorrect marking
5. Quiz results and questions can be downloaded as PDF

## Note

This application uses the Groq API for question generation. Make sure you have a valid API key and sufficient credits for API usage.
