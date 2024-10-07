from fastapi import FastAPI
import os
import subprocess
from pydantic import BaseModel
import shutil
from pathlib import Path

app = FastAPI()

# Define a model for the expected request body
class AudioRequest(BaseModel):
    file_path: str
    accompaniment_file: str

@app.post("/split-audio")
async def split_audio(request: AudioRequest):
    # Run Spleeter on the given file
    file_path = request.file_path
    accompaniment_file = request.accompaniment_file
    track_name = Path(file_path).stem
    directory_name = Path(file_path).parent
    command = f"spleeter separate -p spleeter:2stems -o {directory_name} {file_path}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    shutil.move(f'{directory_name}/{track_name}/accompaniment.wav', accompaniment_file)

    if result.returncode == 0:
        return {"message": "Audio split successfully!"}
    else:
        return {"message": "Error during audio split", "details": result.stderr}
