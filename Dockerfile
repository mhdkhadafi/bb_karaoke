# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install dependencies for ffmpeg and pipx
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-pip \
    python3-venv \
    pipx \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pipx install https://get.zotify.xyz

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose the port that the Flask app runs on (for example, port 5000)
EXPOSE 5000

# Define environment variable for Flask app
ENV FLASK_APP=app.py

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]