import asyncio
import shutil
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

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

    # Use asyncio to run the Spleeter command asynchronously
    command = [
        "spleeter", "separate", "-p", "spleeter:2stems", "-o", str(directory_name), str(file_path)
    ]

    # Start the subprocess asynchronously
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Wait for the subprocess to complete
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        # Move the accompaniment file after the subprocess has finished
        try:
            shutil.move(f'{directory_name}/{track_name}/accompaniment.wav', accompaniment_file)
            return {"message": "Audio split successfully!"}
        except Exception as e:
            return {"message": "Error moving accompaniment file", "details": str(e)}
    else:
        return {"message": "Error during audio split", "details": stderr.decode()}
