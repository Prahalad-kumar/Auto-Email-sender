import smtplib
import re
import asyncio
import pandas as pd
from docx import Document
from fastapi import HTTPException
from email.mime.text import MIMEText

from Schema import Request
from logger_config import logger


EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


def extract_emails(text: str):
    return re.findall(EMAIL_REGEX, text)


def get_email_from_file(file):

    if not file:
        return []

    filename = file.filename.lower()

    try:

        if filename.endswith(".txt"):
            content = file.file.read().decode("utf-8")
            emails = extract_emails(content)
            return list(set(emails))

        elif filename.endswith(".csv"):
            df = pd.read_csv(file.file)

            emails = []
            for column in df.columns:
                emails.extend(df[column].dropna().astype(str).tolist())

            emails = extract_emails(" ".join(emails))
            return list(set(emails))

        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(file.file)

            emails = []
            for column in df.columns:
                emails.extend(df[column].dropna().astype(str).tolist())

            emails = extract_emails(" ".join(emails))
            return list(set(emails))

        elif filename.endswith(".docx"):

            document = Document(file.file)

            text = []
            for para in document.paragraphs:
                text.append(para.text)

            emails = extract_emails(" ".join(text))
            return list(set(emails))

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use txt, csv, xlsx, xls, or docx"
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def verify_smtp_login(sender_email, password):

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, password)

        return True

    except smtplib.SMTPAuthenticationError:
        return False


# NEW FUNCTION
def verify_recipient(sender_email, password, receiver):

    try:

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, password)

            server.mail(sender_email)
            code, message = server.rcpt(receiver)

            if code != 250:
                logger.error(f"Invalid recipient -> {receiver}")
                return False

        return True

    except Exception as e:
        logger.error(f"Recipient verification failed -> {receiver} | {str(e)}")
        return False


async def send_single_email(sender_email, password, receiver, subject, body):

    try:

        def smtp_send():

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = receiver

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver, msg.as_string())

        await asyncio.to_thread(smtp_send)

        logger.info(f"Email sent successfully -> {receiver}")
        return {"email": receiver, "status": "sent"}

    except Exception as e:

        logger.error(f"Failed to send email -> {receiver} | {str(e)}")

        return {
            "email": receiver,
            "status": "failed"
        }


async def send_email(request: Request):

    sender_email = request.sender_email
    password = request.sender_email_pass
    subject = request.subject
    body = request.body

    receiver_list = request.send_list or []
    file_receiver_list = get_email_from_file(request.file) if request.file else []

    email_list = list(set(receiver_list + file_receiver_list))

    if not email_list:
        raise HTTPException(400, "Receiver list is empty")

    # verify login
    auth_ok = verify_smtp_login(sender_email, password)

    if not auth_ok:
        raise HTTPException(
            status_code=400,
            detail="Invalid sender email or app password"
        )

    logger.info(f"Starting async email process | Sender: {sender_email}")
    logger.info(f"Total recipients: {len(email_list)}")

    valid_emails = []
    failed = []

    # VERIFY RECIPIENTS FIRST
    for email in email_list:

        if verify_recipient(sender_email, password, email):
            valid_emails.append(email)
        else:
            failed.append({
                "email": email,
                "status": "failed"
            })

    semaphore = asyncio.Semaphore(2)

    async def sem_task(email):
        async with semaphore:
            result = await send_single_email(sender_email, password, email, subject, body)
            await asyncio.sleep(2)
            return result

    tasks = [sem_task(email) for email in valid_emails]

    results = await asyncio.gather(*tasks)

    success = [r["email"] for r in results if r["status"] == "sent"]

    failed.extend([r for r in results if r["status"] == "failed"])

    logger.info(
        f"Email process completed | Success: {len(success)} | Failed: {len(failed)}"
    )

    return {
        "status": "completed",
        "total_requested": len(email_list),
        "success_count": len(success),
        "failed_count": len(failed),
        "success_emails": success,
        "failed_details": failed
    }