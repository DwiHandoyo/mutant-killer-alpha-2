# Base image for Python
FROM python:3.9-slim as python-base

# Set working directory
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app/

# Expose Flask port
EXPOSE 5000

# Command to run Flask app
CMD ["python", "main.py"]