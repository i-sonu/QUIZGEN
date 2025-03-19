# PDF to Quiz Generator

This application converts PDF documents into interactive multiple-choice quizzes using AI. It extracts text from PDFs (including scanned documents using OCR) and generates relevant quiz questions using the Groq API.

## Features

- PDF text extraction with OCR support
- AI-powered quiz generation
- Interactive web interface
- Topic-based question organization
- Multiple choice questions with 4 options

## Prerequisites

- Python 3.7 or higher
- Tesseract OCR installed on your system
  - Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
  - Linux: `sudo apt-get install tesseract-ocr`
  - macOS: `brew install tesseract`

## Installation

1. Clone this repository
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Flask application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

3. Upload a PDF file using the web interface

4. Wait for the quiz to be generated

5. Answer the questions and check your responses

## How it Works

1. The application extracts text from the uploaded PDF using PyPDF2 and Tesseract OCR
2. The extracted text is sent to the Groq API to generate relevant quiz questions
3. Questions are organized by topics and displayed in an interactive format
4. Users can select answers and see their responses

## Note

This application uses the Groq API for question generation. Make sure you have a valid API key and sufficient credits for API usage. 