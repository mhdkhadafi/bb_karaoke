from fastapi import FastAPI
import os
import subprocess

app = FastAPI()

@app.post("/split")
def split_audio(file_path: str):
    # Run Spleeter on the given file
    result = subprocess.run(
        ["spleeter", "separate", "-i", file_path, "-p", "spleeter:2stems", "-o", "/app/shared/"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        return {"message": "Audio split successfully!"}
    else:
        return {"message": "Error during audio split", "details": result.stderr}