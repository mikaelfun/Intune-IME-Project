from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from uuid import uuid4
import os
import shutil
import subprocess

app = FastAPI()
app.mount("/static", StaticFiles(directory="public"), name="static")
templates = Jinja2Templates(directory="templates")

LOGS_FOLDER = "Uploaded logs"


class AnalyzeInput(BaseModel):
    sessionFolder: str
    sliderState: bool
    

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    session_folder = os.path.join(LOGS_FOLDER, str(uuid4()))

    if not os.path.exists(LOGS_FOLDER):
        os.mkdir(LOGS_FOLDER)

    if not os.path.exists(session_folder):
        os.mkdir(session_folder)

    for file in files:
        file_path = os.path.join(session_folder, file.filename)
        folder_path = os.path.dirname(file_path)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    return {"sessionFolder": session_folder}


@app.post("/analyze")
async def analyze(inputt: AnalyzeInput):
    python_script = "imeinterpreter.py"
    session_folder = inputt.sessionFolder
    slider_state = inputt.sliderState
    # Convert slider_state to a string
    slider_state_str = str(slider_state)
    # print(full_log)

    result = subprocess.run(
        ["python", python_script, session_folder, slider_state_str],
        # capture_output=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        return {"error": result.stderr}

    return {"output": result.stdout}
