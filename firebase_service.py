import streamlit as st
import firebase_admin
import hashlib
from firebase_admin import credentials, firestore


# =========================
# INIT FIREBASE
# =========================
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()


# =========================
# AI CONFIG
# =========================
def save_ai_config(data):
    db = init_firebase()
    db.collection("config").document("ai").set(data)


def get_ai_config():
    db = init_firebase()
    doc = db.collection("config").document("ai").get()
    return doc.to_dict() if doc.exists else {}


# =========================
# IMAP CONFIG
# =========================
def save_imap_config(data):
    db = init_firebase()
    db.collection("config").document("imap").set(data)


def get_imap_config():
    db = init_firebase()
    doc = db.collection("config").document("imap").get()
    return doc.to_dict() if doc.exists else {}


# =========================
# SAVE EMAIL (ANTI DUPLICATE)
# =========================
def save_email(email_data: dict):
    db = init_firebase()
    if not db:
        return

    raw_id = email_data.get("message_id")

    if not raw_id:
        raw_id = email_data.get("subject", "") + email_data.get("date", "")

    doc_id = hashlib.md5(raw_id.encode()).hexdigest()

    db.collection("emails").document(doc_id).set(email_data)


# =========================
# GET EMAILS
# =========================
def get_all_emails():
    db = init_firebase()
    docs = db.collection("emails").stream()
    return [doc.to_dict() for doc in docs]


# =========================
# RESET EMAIL COLLECTION
# =========================
def reset_emails():
    db = init_firebase()
    docs = db.collection("emails").stream()
    for doc in docs:
        doc.reference.delete()
        
def delete_email(message_id):
    from firebase_admin import firestore
    db = firestore.client()
    db.collection("emails").document(message_id).delete()
