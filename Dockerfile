# Use full Debian-based Python image (not slim)
FROM python:3.9

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV TESSERACT_PATH="/usr/bin/tesseract"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Check if Tesseract is installed
RUN tesseract --version

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Flask port
EXPOSE 5000

# Start Flask app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
