import imaplib
import ssl
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone


# =========================
# TEST IMAP CONNECTION
# =========================
def test_imap_connection(host, username, password, port=993):
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=context)
        mail.login(username, password)
        mail.logout()
        return True, "IMAP connection successful"
    except Exception as e:
        return False, str(e)


# =========================
# DECODE SUBJECT
# =========================
def decode_mime_words(s):
    if not s:
        return ""

    decoded_words = decode_header(s)
    decoded_string = ""

    for word, encoding in decoded_words:
        if isinstance(word, bytes):
            decoded_string += word.decode(encoding or "utf-8", errors="ignore")
        else:
            decoded_string += word

    return decoded_string


# =========================
# FETCH EMAILS
# =========================
def fetch_emails_by_date(host, username, password, start_date, end_date, read_status="ALL", port=993):

    import imaplib
    import ssl
    import email
    from email.header import decode_header
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timedelta

    context = ssl.create_default_context()
    mail = imaplib.IMAP4_SSL(host, port, ssl_context=context)
    mail.login(username, password)
    mail.select("INBOX")

    criteria = []

    if read_status == "UNREAD":
        criteria.append("UNSEEN")
    elif read_status == "READ":
        criteria.append("SEEN")

    start_str = start_date.strftime("%d-%b-%Y")
    end_plus_one = end_date + timedelta(days=1)
    end_str = end_plus_one.strftime("%d-%b-%Y")

    criteria.append(f'SINCE "{start_str}"')
    criteria.append(f'BEFORE "{end_str}"')

    search_query = " ".join(criteria)

    status, messages = mail.search(None, search_query)
    email_ids = messages[0].split()

    emails = []

    for eid in reversed(email_ids):

        status, msg_data = mail.fetch(eid, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        message_id = msg.get("Message-ID", "")
        date_raw = msg.get("Date")

        email_date = parsedate_to_datetime(date_raw) if date_raw else None

        # Check attachment
        has_attachment = False
        for part in msg.walk():
            content_disposition = part.get("Content-Disposition")
            if content_disposition and "attachment" in content_disposition.lower():
                has_attachment = True
                break

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        emails.append({
            "message_id": message_id,
            "subject": subject,
            "from": sender,
            "date": email_date.isoformat() if email_date else "",
            "has_attachment": has_attachment,
            "snippet": body[:300]
        })

    mail.logout()
    return emails
