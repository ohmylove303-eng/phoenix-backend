# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for state
RUN mkdir -p /app/data

# Railway injects PORT at runtime
ENV PORT=8080

# Run gunicorn directly - no shell script needed
# Use 0.0.0.0 to bind to all interfaces for Railway proxy
CMD gunicorn api.server:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
