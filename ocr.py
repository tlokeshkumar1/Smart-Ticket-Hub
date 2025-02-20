import cv2
import pytesseract
import numpy as np
from PIL import Image
import base64
import requests
import json
import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv  # Load environment variables

app = Flask(__name__)

# Load API key from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Set the Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(image):
    """Convert image to grayscale and apply thresholding for better OCR accuracy."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    _, image = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)  # Apply thresholding
    return image

def extract_qr_code(image):
    """Detect and extract QR code from the image while also returning decoded content."""
    qr_detector = cv2.QRCodeDetector()
    decoded_text, points, _ = qr_detector.detectAndDecode(image)

    if points is not None:
        points = points[0]  # Get bounding box points
        x, y, w, h = cv2.boundingRect(np.int32(points))
        qr_region = image[y:y+h, x:x+w]  # Crop QR code region
        return decoded_text, qr_region
    return None, None

def image_to_base64(image):
    """Convert an OpenCV image to a base64 string."""
    _, buffer = cv2.imencode('.png', image)
    return base64.b64encode(buffer).decode("utf-8")

def generate_llm_prompt(extracted_text):
    """Generate LLM prompt for structured movie ticket details."""
    return f'''
    Extract structured data from the following raw text and format it into this JSON structure
    {{
      "movie_name": "",
      "language_and_dimension": "",
      "date_and_time": "",
      "theater_name": "",
      "location": "",
      "no_of_tickets": "",
      "ticket_numbers": "",
      "booking_id": "",
      "total_amount": ""
    }}
    
    Raw Text: """{extracted_text}"""
    '''

def extract_text(file):
    """Extract text and QR code image from an uploaded file."""
    img = Image.open(file)
    img_cv = np.array(img)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    processed_img = preprocess_image(img_cv)

    # Extract text using Tesseract OCR
    extracted_text = pytesseract.image_to_string(processed_img)

    # Extract QR code (both decoded text and image)
    qr_decoded_text, qr_code_img = extract_qr_code(img_cv)
    qr_code_base64 = image_to_base64(qr_code_img) if qr_code_img is not None else None

    # Extract structured data using LLM
    structured_data = process_with_llm(extracted_text)

    return {
        "extracted_text": extracted_text.strip(),
        "qr_code_text": qr_decoded_text if qr_decoded_text else "No QR code detected",
        "qr_code_image": qr_code_base64 if qr_code_base64 else "No QR code detected",
        "structured_data": structured_data if structured_data else "Could not extract structured data"
    }

API_KEY = os.getenv("GEMINI_API_KEY")

def process_with_llm(extracted_text):
    """Send extracted text to Google Gemini API and return structured data."""
    if not API_KEY:
        print("Error: GEMINI_API_KEY is missing or not loaded.")
        return None

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": generate_llm_prompt(extracted_text)}]}]
    }

    try:
        response = requests.post(url, headers=headers, params={"key": API_KEY}, json=payload)
        llm_response = response.json()
        print("Raw LLM Response:", json.dumps(llm_response, indent=2))  # Debugging

        # Extract structured data safely
        candidates = llm_response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                llm_text = parts[0].get("text", "{}").strip()
                try:
                    structured_data = json.loads(llm_text)
                    return structured_data
                except json.JSONDecodeError:
                    print("Failed to parse JSON response. Check the API output format.")
                    return None
        print("Could not extract structured data.")
        return None

    except Exception as e:
        print(f"Error processing with LLM: {str(e)}")
        return None
