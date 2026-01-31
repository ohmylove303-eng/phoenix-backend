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

# Create a minimal startup script inline
RUN echo '#!/bin/sh\necho "Starting Phoenix Backend..."\necho "PORT=$PORT"\nexec python -m gunicorn api.server:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -' > /app/run.sh && chmod +x /app/run.sh

# Railway injects PORT at runtime
ENV PORT=8080

# Use exec form with shell to ensure env vars expand
CMD ["/bin/sh", "/app/run.sh"]
