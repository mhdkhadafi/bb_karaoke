# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install dependencies for ffmpeg and pipx
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-pip \
    python3-venv \
    pipx \
    git \
    docker.io \
    unifont \
    fonts-noto-core \
    fonts-noto-cjk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pipx install https://get.zotify.xyz
RUN pipx install yt-dlp

# Add /root/.local/bin to PATH so pipx-installed tools are accessible
ENV PATH="/root/.local/bin:${PATH}"

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV ZOTIFY_USERNAME=$ZOTIFY_USERNAME
ENV ZOTIFY_AUTHDATA=$ZOTIFY_AUTHDATA

# Copy the requirements file
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Docker CLI
RUN curl -fsSL https://get.docker.com | sh

# Copy the current directory contents into the container at /app
COPY . .

# Make the script executable
RUN chmod +x /app/replace_zotify_credentials.sh

# Expose the port that the Flask app runs on (for example, port 5000)
EXPOSE 5000

# Define environment variable for Flask app
ENV FLASK_APP="app:create_app()"

# Run the application
CMD ["/bin/bash", "-c", "/app/replace_zotify_credentials.sh && flask run --host=0.0.0.0"]
