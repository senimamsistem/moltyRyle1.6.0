# Optimized Dockerfile for Railway memory constraints
FROM python:3.11-slim

WORKDIR /app

# Install only production dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy bot source (exclude cache and test files)
COPY bot/ ./bot/

# Create dirs for credentials and memory persistence
RUN mkdir -p /app/dev-agent /root/.molty-royale

# Set memory limits and optimize Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1

# Railway injects PORT env var; default 8080 for dashboard
EXPOSE 8080

CMD ["python", "-m", "bot.main"]
