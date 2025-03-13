# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true  

# Set working directory
WORKDIR /app

# Install system dependencies (Tesseract)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .  

# Install dependencies
COPY requirements.txt .  
RUN pip install --no-cache-dir -r requirements.txt

# Copy .env file (Optional, if using locally)
COPY .env .env  

# Expose Flask port
EXPOSE 5000

# Start Flask app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
