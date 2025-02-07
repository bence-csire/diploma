# Use official Python image
FROM python:3.13

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install ADB
RUN apt-get update && apt-get install -y adb sqlite3 && rm -rf /var/lib/apt/lists/*

# Set a working directory
WORKDIR /app

# Copy only requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask runs on
EXPOSE 5000

# Copy the application files
COPY app/ .

# Create a non-root user (optional but recommended for security)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default command
CMD ["python", "main.py"]