from pydantic import BaseModel, EmailStr
from typing import List, Optional
from fastapi import UploadFile


class Request(BaseModel):
    sender_email: EmailStr
    sender_email_pass: str
    subject: str
    body: str
    send_list: Optional[List[str]] = None
    file: UploadFile | None = None