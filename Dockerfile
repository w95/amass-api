# Use an amd64-based Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies and required tools
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libc6 \
    && rm -rf /var/lib/apt/lists/*

# Install Amass v4.2.0
RUN wget https://github.com/OWASP/Amass/releases/download/v4.2.0/amass_linux_amd64.zip \
    && unzip amass_linux_amd64.zip \
    && mv amass_Linux_amd64/amass /usr/local/bin/amass \
    && rm -rf amass_linux_amd64.zip amass_Linux_amd64

# Copy application requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose the port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production

# Run the application
CMD ["python", "app.py"]
