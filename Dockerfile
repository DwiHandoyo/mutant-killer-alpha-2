# Base image for Python
FROM python:3.9-slim as python-base

# Set working directory
WORKDIR /app

# Install system dependencies for PHP and Composer
RUN apt-get update && apt-get install -y \
    php-cli php-mbstring php-xml git unzip curl && \
    apt-get clean

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

# Copy Python dependencies
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app/

# Expose Flask port only (frontend is served by Flask)
EXPOSE 5000

# Command to run Flask app
CMD ["python", "main.py"]