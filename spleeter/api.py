from fastapi import FastAPI
import os
import subprocess
from pydantic import BaseModel

app = FastAPI()

# Define a model for the expected request body
class AudioRequest(BaseModel):
    file_path: str

@app.post("/split-audio")
async def split_audio(request: AudioRequest):
    # Run Spleeter on the given file
    file_path = request.file_path
    command = f"spleeter separate -p spleeter:2stems -o /app/shared/output {file_path}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        return {"message": "Audio split successfully!"}
    else:
        return {"message": "Error during audio split", "details": result.stderr}
