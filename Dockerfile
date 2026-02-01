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

# Use our Python startup script with extensive logging
CMD ["python", "startup.py"]
