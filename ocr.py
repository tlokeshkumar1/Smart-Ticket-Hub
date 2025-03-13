import cv2
import pytesseract
import numpy as np
from PIL import Image
import base64
import re
import os
from flask import Flask, request, jsonify, session


# Detect Docker
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

if RUNNING_IN_DOCKER:
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")
else:
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# Debug: Print Tesseract path
print("RUNNING_IN_DOCKER:", RUNNING_IN_DOCKER)
print("Tesseract Path:", pytesseract.pytesseract.tesseract_cmd)

def preprocess_image(image):
    """Convert image to grayscale and apply thresholding for better OCR accuracy."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, image = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)
    return image

def extract_qr_code(image):
    """Detect and extract QR code from the image while also returning decoded content."""
    qr_detector = cv2.QRCodeDetector()
    decoded_text, points, _ = qr_detector.detectAndDecode(image)

    if points is not None:
        points = points[0]
        x, y, w, h = cv2.boundingRect(np.int32(points))
        qr_region = image[y:y+h, x:x+w]
        return decoded_text, qr_region
    return None, None

def image_to_base64(image):
    """Convert an OpenCV image to a base64 string."""
    _, buffer = cv2.imencode('.png', image)
    return base64.b64encode(buffer).decode("utf-8")

def extract_text(file):
    """Extract text and QR code image from an uploaded file."""
    img = Image.open(file)
    img_cv = np.array(img)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    processed_img = preprocess_image(img_cv)

    extracted_text = pytesseract.image_to_string(processed_img)
    qr_decoded_text, qr_code_img = extract_qr_code(img_cv)
    qr_code_base64 = image_to_base64(qr_code_img) if qr_code_img is not None else None

    structured_data = extract_ticket_details(extracted_text)

    return {
        "qr_code_text": qr_decoded_text if qr_decoded_text else "No QR code detected",
        "qr_code_image": qr_code_base64 if qr_code_base64 else "No QR code detected",
        "extracted_text": extracted_text.strip(),
        "structured_data": structured_data if structured_data else "Could not extract structured data"
    }


def extract_ticket_details(extracted_text):
    """Extract structured movie ticket details with precise pattern matching."""
    # Normalization: Preserve original formatting while handling special cases
    text = re.sub(r'\s+', ' ', extracted_text)  # Collapse whitespace
    text = re.sub(r'(?i)\b(rs|inr)\s*\.?\s*', 'Rs.', text)  # Standardize currency
    
    extracted_data = {
        "username": session.get("username", "Guest"),  # Add username here
        "movie_name": "No Match Found",
        "language_and_dimension": "No Match Found",
        "date_and_time": "No Match Found",
        "theater_name": "No Match Found",
        "location": "No Match Found",
        "no_of_tickets": "No Match Found",
        "ticket_numbers": "No Match Found",
        "booking_id": "No Match Found",
        "total_amount": "No Match Found"
    }

    # Movie Name: Skip header and capture until (U/A) or language marker
    movie_match = re.search(
        r'(?:Your Ticket[^\n]*\n+)(.*?)(?=\s*\(?U/A\)?|\n)|^([^\n\(]+)', 
        text, 
        re.IGNORECASE
    )
    
    if movie_match:
        # Select the appropriate capture group
        raw_name = movie_match.group(1) or movie_match.group(2)
        # Clean all unwanted text and characters
        clean_name = re.sub(
            r'Your Ticket|\bU/A\b|[<>3•*]|\([^)]*\)', 
            '', 
            raw_name, 
            flags=re.IGNORECASE
        ).strip()
        extracted_data["movie_name"] = clean_name

    # Language & Dimension: Handle different formatting variations
    lang_dim = re.search(
        r'(?:\b(U/A)\s+)?(Telugu|Hindi|English)\b.*?(2D|3D|IMAX)\b',
        text,
        re.IGNORECASE
    )
    if lang_dim:
        components = [c for c in [lang_dim.group(2), lang_dim.group(3)] if c]
        extracted_data["language_and_dimension"] = ', '.join(components)

    # Date & Time: Flexible separator handling
    datetime_match = re.search(
        r'(\b[A-Za-z]{3},\s\d{1,2}\s[A-Za-z]{3}\b).*?(\d{1,2}:\d{2}\s*[AP]M)',
        text,
        re.IGNORECASE
    )
    if datetime_match:
        extracted_data["date_and_time"] = f"{datetime_match.group(1)} | {datetime_match.group(2).upper().replace(' ', '')}"

    # Theater & Location: Strict boundary control
    theater_loc = re.search(
        r'((?:Miraj|Sushma|Asian|Cinepolis)[^:,]+?)(?:[:,]\s+|\s+at\s+)([\w\s]+?)(?=\s+\b(?:Box Office|SCREEN|BOOKING))',
        text,
        re.IGNORECASE
    )
    if theater_loc:
        extracted_data["theater_name"] = re.sub(r'\b(Cinemas?|Theatre)\b', '', theater_loc.group(1), flags=re.IGNORECASE).strip()
        extracted_data["location"] = theater_loc.group(2).split('\n')[0].strip()

    # Ticket Numbers: Strict seat pattern validation
    seats = re.search(
        r'(?:BALCONY|EXECUTIVE|SEATS?)[\s\-:]+((?:[A-Z]\d{1,3}|[\d]+)(?:,\s*(?:[A-Z]?\d{1,3}))+)',
        text,
        re.IGNORECASE
    )
    if seats:
        extracted_data["ticket_numbers"] = re.sub(r'\s+', '', seats.group(1))
        extracted_data["no_of_tickets"] = str(len(extracted_data["ticket_numbers"].split(',')))

    # Booking ID: Comprehensive pattern matching
    booking_id = re.search(
        r'Booking\s+ID\s*[:\-]?\s*([A-Z0-9]{10,})(?=\s|$)',
        text,
        re.IGNORECASE
    )
    if booking_id:
        extracted_data["booking_id"] = booking_id.group(1)

    # Total Amount: Context-aware extraction
    amount = re.search(
        r'(?:Total\s+Amount|Amount\s+Payable).*?Rs\.(\d+\.\d{2})',
        text,
        re.IGNORECASE
    )
    if not amount:  # Fallback to last amount pattern
        amount = re.search(r'Rs\.(\d+\.\d{2})(?!.*\d+\.\d{2})', text)
    if amount:
        extracted_data["total_amount"] = amount.group(1)

    # Explicit Ticket Count Override
    ticket_count = re.search(r'(\d+)\s*Ticket\(s\)', text)
    if ticket_count:
        extracted_data["no_of_tickets"] = ticket_count.group(1)

    return extracted_data