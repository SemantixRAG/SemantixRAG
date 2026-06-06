FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for unstructured library
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice-writer \
    libreoffice-calc \
    libmagic1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create documents directory
RUN mkdir -p /app/documents

# Default command
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]