FROM python:3.11-slim

LABEL maintainer="Silvester van der Leer"
LABEL description="EVE LI XML Generator with Web Interface"

# Set working directory
WORKDIR /app

# Install system dependencies and configure timezone
ENV TZ=Europe/Amsterdam
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excludes files from .dockerignore)
COPY *.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY sql/ ./sql/

# Create necessary directories (will be mounted as volumes in production)
RUN mkdir -p logs output .cache .flask_session

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web_app.py
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "web_app.py"]
