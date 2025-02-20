import cv2 
import pytesseract
import numpy as np
from PIL import Image
import base64

# Set the Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image(image):
    """Convert image to grayscale and apply thresholding for better OCR accuracy."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    _, image = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY)  # Apply thresholding
    return image

def extract_qr_code(image):
    """Detect and extract QR code from the image without decoding it."""
    qr_detector = cv2.QRCodeDetector()
    _, points, _ = qr_detector.detectAndDecode(image)
    
    if points is not None:
        points = points[0]  # Get bounding box points
        x, y, w, h = cv2.boundingRect(np.int32(points))
        qr_region = image[y:y+h, x:x+w]  # Crop QR code region
        return qr_region
    return None

def image_to_base64(image):
    """Convert an OpenCV image to a base64 string."""
    _, buffer = cv2.imencode('.png', image)
    return base64.b64encode(buffer).decode("utf-8")

def extract_text(file):
    """Extract text and QR code image from an uploaded file."""
    img = Image.open(file)

    # Convert PIL image to OpenCV format
    img_cv = np.array(img)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

    # Preprocess the image
    processed_img = preprocess_image(img_cv)

    # Perform OCR
    extracted_text = pytesseract.image_to_string(processed_img)

    # Extract QR code image without decoding it
    qr_code_img = extract_qr_code(img_cv)
    qr_code_base64 = image_to_base64(qr_code_img) if qr_code_img is not None else None

    return {
        "extracted_text": extracted_text,
        "qr_code_image": qr_code_base64 if qr_code_base64 else "No QR code detected"
    }