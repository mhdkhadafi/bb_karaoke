# Extend the base spleeter image
FROM deezer/spleeter:3.8

# Set the working directory
WORKDIR /app

# Copy the FastAPI app into the Spleeter container
COPY api.py /app/api.py

# Install FastAPI and Uvicorn (if they aren't included)
RUN pip install fastapi uvicorn

# Set the entrypoint to run the FastAPI server
ENTRYPOINT ["python3", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "5002"]