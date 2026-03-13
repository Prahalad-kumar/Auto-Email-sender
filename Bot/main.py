from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional

from Schema import Request
from Src.Send_mail import send_email
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Email Bot API",
    description="FastAPI Gmail Email Automation Bot",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (e.g., your React app port)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods including POST and OPTIONS
    allow_headers=["*"],  # Allows all headers
)
@app.get("/")
def home():
    return {"message": "Email API running"}


@app.post("/send-email")
async def send_email_api(
    sender_email: str = Form(...),
    sender_email_pass: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    send_list: Optional[List[str]] = Form(None),
    file: Optional[UploadFile] = File(None)
):

    request = Request(
        sender_email=sender_email,
        sender_email_pass=sender_email_pass,
        subject=subject,
        body=body,
        send_list=send_list,
        file=file
    )

    return await send_email(request)