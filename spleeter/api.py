import asyncio
import shutil
import logging
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)

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

    # Log the command being executed
    command = [
        "spleeter", "separate", "-p", "spleeter:2stems", "-o", str(directory_name), str(file_path)
    ]
    logging.info(f"Running command: {command}")

    # Start the subprocess asynchronously
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Wait for the subprocess to complete
    stdout, stderr = await process.communicate()

    # Log the stdout and stderr
    logging.info(f"Command stdout: {stdout.decode()}")
    logging.error(f"Command stderr: {stderr.decode()}")

    if process.returncode == 0:
        try:
            # Log file move action
            logging.info(f"Moving accompaniment file from {directory_name}/{track_name}/accompaniment.wav to {accompaniment_file}")
            shutil.move(f'{directory_name}/{track_name}/accompaniment.wav', accompaniment_file)
            return {"message": "Audio split successfully!"}
        except Exception as e:
            logging.error(f"Error moving accompaniment file: {str(e)}")
            return {"message": "Error moving accompaniment file", "details": str(e)}
    else:
        return {"message": "Error during audio split", "details": stderr.decode()}

