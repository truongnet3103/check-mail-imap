"""
Mail Nexus - Intelligent Email Manager
Design: Editorial Dark - Refined, modern, professional
"""
import streamlit as st
import hashlib
import imaplib
import ssl
import email
import requests
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import date, datetime, timedelta

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Mail Nexus",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== DESIGN SYSTEM - EDITORIAL DARK ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Text:wght@400;600;700&family=Source+Sans+3:wght@300;400;500;600&display=swap');

:root {
    --bg-primary: #0f1419;
    --bg-secondary: #1a1f2e;
    --bg-tertiary: #242b3d;
    --accent-gold: #f4d03f;
    --accent-cyan: #5dade2;
    --accent-rose: #e74c3c;
    --text-primary: #f8f9fa;
    --text-secondary: #a0aec0;
    --text-muted: #64748b;
    --border: #2d3748;
}

/* Hide Streamlit chrome */
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}

/* Global */
.stApp {
    background: var(--bg-primary);
    font-family: 'Source Sans 3', sans-serif;
}

/* Scrollbar */
::-webkit-scrollbar {width: 6px;}
::-webkit-scrollbar-track {background: var(--bg-primary);}
::-webkit-scrollbar-thumb {background: var(--bg-tertiary); border-radius: 3px;}
::-webkit-scrollbar-thumb:hover {background: var(--accent-gold);}

/* Typography */
h1, h2, h3 {
    font-family: 'Crimson Text', serif !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

/* Buttons */
.stButton > button {
    border-radius: 6px !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
}

.stButton > button[kind="primary"] {
    background: var(--accent-gold) !important;
    color: var(--bg-primary) !important;
    border: none !important;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(244, 208, 63, 0.3) !important;
}

.stButton > button:not([kind="primary"]) {
    background: var(--bg-tertiary) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
}

.stButton > button:not([kind="primary"]):hover {
    border-color: var(--accent-gold) !important;
    color: var(--text-primary) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stDateInput > div > div > input {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text-primary) !important;
    font-family: 'Source Sans 3', sans-serif !important;
}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div > div:focus,
.stDateInput > div > div > input:focus {
    border-color: var(--accent-gold) !important;
    box-shadow: 0 0 0 2px rgba(244, 208, 63, 0.1) !important;
}

/* Expander */
.streamlit-expander {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

.streamlit-expanderHeader {
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

/* Dividers */
.stDivider {
    border-color: var(--border) !important;
}

/* Success/Error/Warning */
.stSuccess {
    background: rgba(46, 204, 113, 0.1) !important;
    border: 1px solid rgba(46, 204, 113, 0.3) !important;
    color: #2ecc71 !important;
    border-radius: 6px !important;
}

.stError {
    background: rgba(231, 76, 60, 0.1) !important;
    border: 1px solid rgba(231, 76, 60, 0.3) !important;
    color: #e74c3c !important;
    border-radius: 6px !important;
}

.stWarning {
    background: rgba(244, 208, 63, 0.1) !important;
    border: 1px solid rgba(244, 208, 63, 0.3) !important;
    color: var(--accent-gold) !important;
    border-radius: 6px !important;
}

/* Info */
.stInfo {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
}
</style>
""", unsafe_allow_html=True)

# ========== OPTIONAL IMPORTS ==========
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_OK = True
except:
    FIREBASE_OK = False

try:
    import google.generativeai as genai
    GENAI_OK = True
except:
    GENAI_OK = False

# ========== SESSION STATE ==========
def init_state():
    defaults = {
        "expanded_email_id": None,
        "email_translations": {},
        "email_ai_results": {},
        "email_view_mode": {},  # email_id -> "original" | "translate" | "ai"
        "selected_ai_model": "gemini-2.5-flash",
        "offline_emails": [],
        "offline_config": {"imap": {}, "ai": {"api_key": ""}},
        "show_config": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ========== DATABASE LAYER ==========
@st.cache_resource
def get_db():
    if not FIREBASE_OK:
        return None
    try:
        if not firebase_admin._apps:
            if "firebase" not in st.secrets:
                return None
            cred = credentials.Certificate(dict(st.secrets["firebase"]))
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except:
        return None

def db_save_config(type_key, data):
    db = get_db()
    if db:
        try:
            db.collection("config").document(type_key).set(data)
            return
        except:
            pass
    st.session_state.offline_config[type_key] = data

def db_get_config(type_key):
    db = get_db()
    if db:
        try:
            doc = db.collection("config").document(type_key).get()
            if doc.exists:
                return doc.to_dict()
        except:
            pass
    return st.session_state.offline_config.get(type_key, {})

def db_save_email(email_data):
    db = get_db()
    email_id = email_data.get("message_id") or hashlib.md5(
        (email_data.get("subject", "") + email_data.get("date", "")).encode()
    ).hexdigest()
    
    if db:
        try:
            db.collection("emails").document(email_id).set(email_data)
            return
        except:
            pass
    
    # Update offline storage
    existing = [e for e in st.session_state.offline_emails 
                if (e.get("message_id") or hashlib.md5((e.get("subject", "") + e.get("date", "")).encode()).hexdigest()) != email_id]
    existing.append(email_data)
    st.session_state.offline_emails = existing

def db_get_emails():
    db = get_db()
    if db:
        try:
            docs = db.collection("emails").stream()
            return [d.to_dict() for d in docs]
        except:
            pass
    return st.session_state.offline_emails

def db_delete_email(email_id):
    db = get_db()
    if db:
        try:
            db.collection("emails").document(email_id).delete()
        except:
            pass
    st.session_state.offline_emails = [
        e for e in st.session_state.offline_emails
        if (e.get("message_id") or hashlib.md5((e.get("subject", "") + e.get("date", "")).encode()).hexdigest()) != email_id
    ]

# ========== IMAP SERVICES ==========
def test_imap(host, user, pwd, port=993):
    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        mail.login(user, pwd)
        mail.logout()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

def decode_mime(s):
    if not s:
        return ""
    try:
        parts = decode_header(s)
        return "".join([
            p[0].decode(p[1] or "utf-8", errors="ignore") if isinstance(p[0], bytes) else p[0]
            for p in parts
        ])
    except:
        return s

def fetch_emails(host, user, pwd, start, end, status="ALL", port=993):
    emails = []
    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        mail.login(user, pwd)
        mail.select("INBOX")
        
        criteria = []
        if status == "UNREAD":
            criteria.append("UNSEEN")
        elif status == "READ":
            criteria.append("SEEN")
        
        criteria.extend([
            f'SINCE "{start.strftime("%d-%b-%Y")}"',
            f'BEFORE "{(end + timedelta(days=1)).strftime("%d-%b-%Y")}"'
        ])
        
        _, msgs = mail.search(None, " ".join(criteria))
        
        for eid in reversed(msgs[0].split()):
            try:
                _, data = mail.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                
                subject = decode_mime(msg.get("Subject", ""))
                sender = msg.get("From", "")
                msg_id = msg.get("Message-ID", "")
                date_raw = msg.get("Date")
                
                try:
                    msg_date = parsedate_to_datetime(date_raw) if date_raw else None
                except:
                    msg_date = None
                
                has_attach = any(
                    part.get("Content-Disposition") and "attachment" in part.get("Content-Disposition", "").lower()
                    for part in msg.walk()
                )
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")
                
                emails.append({
                    "message_id": msg_id,
                    "subject": subject or "(No Subject)",
                    "from": sender,
                    "date": msg_date.isoformat() if msg_date else "",
                    "has_attachment": has_attach,
                    "body": body[:1000],
                    "preview": body[:200].replace("\n", " ")
                })
            except:
                continue
        
        mail.logout()
    except Exception as e:
        st.error(f"IMAP Error: {e}")
    return emails

# ========== AI SERVICES ==========
def ai_process(text, mode="summarize"):
    if not GENAI_OK:
        return "⚠️ AI module not available"
    
    cfg = db_get_config("ai")
    key = cfg.get("api_key", "")
    
    if not key:
        return "⚠️ API key not configured"
    
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(st.session_state.selected_ai_model)
        
        if mode == "summarize":
            prompt = f"Summarize this email in Vietnamese, be concise:\n\n{text}\n\nSummary:"
        elif mode == "translate":
            prompt = f"Translate to Vietnamese:\n\n{text}\n\nTranslation:"
        else:
            prompt = text
        
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"❌ AI Error: {str(e)[:100]}"

def translate_google(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "vi", "dt": "t", "q": text}
        r = requests.get(url, params=params, timeout=5)
        return "".join([item[0] for item in r.json()[0]])
    except:
        return "❌ Translation failed"

# ========== UI HELPERS ==========
def fmt_date(ds):
    try:
        return datetime.fromisoformat(ds.replace('Z', '+00:00')).strftime("%d/%m %H:%M")
    except:
        return ds[:16].replace("T", " ") if ds else ""

def get_initials(name):
    if not name:
        return "?"
    parts = name.replace('@', ' ').replace('.', ' ').split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else name[0].upper()

def get_color(name):
    colors = ["#f4d03f", "#5dade2", "#e74c3c", "#9b59b6", "#1abc9c", "#e67e22"]
    return colors[hash(name) % len(colors)] if name else colors[0]

# ========== SIDEBAR ==========
def render_sidebar():
    with st.sidebar:
        # Brand
        st.markdown("""
        <div style="padding: 1.5rem 0; border-bottom: 1px solid #2d3748; margin-bottom: 1.5rem;">
            <div style="font-family: 'Crimson Text', serif; font-size: 1.75rem; font-weight: 700; color: #f8f9fa;">
                ◉ Mail Nexus
            </div>
            <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.15em; margin-top: 0.25rem;">
                Intelligent Email
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # AI Model Selection
        st.markdown("<p style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>AI Model</p>", unsafe_allow_html=True)
        
        model = st.selectbox(
            "",
            ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
            index=0,
            label_visibility="collapsed"
        )
        st.session_state.selected_ai_model = model
        
        if not GENAI_OK:
            st.warning("AI module not installed")
        
        st.divider()
        
        # Stats
        emails = db_get_emails()
        st.markdown(f"""
        <div style="background: #1a1f2e; border-radius: 8px; padding: 1rem; border: 1px solid #2d3748;">
            <div style="color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;">Total Emails</div>
            <div style="font-family: 'Crimson Text', serif; font-size: 2rem; color: #f4d03f; font-weight: 600;">{len(emails)}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Spacer to push config down
        st.markdown("<div style='height: 30vh;'></div>", unsafe_allow_html=True)
        
        # Configuration Panel (Bottom)
        with st.expander("⚙️ Configuration", expanded=False):
            # AI Config
            st.markdown("<p style='color: #f4d03f; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em;'>🤖 AI Settings</p>", unsafe_allow_html=True)
            ai_cfg = db_get_config("ai")
            api_key = st.text_input("Gemini API Key", value=ai_cfg.get("api_key", ""), type="password", label_visibility="collapsed")
            if st.button("Save AI Config", use_container_width=True):
                db_save_config("ai", {"api_key": api_key, "model": model})
                st.success("Saved!")
            
            st.divider()
            
            # IMAP Config
            st.markdown("<p style='color: #5dade2; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em;'>📧 IMAP Settings</p>", unsafe_allow_html=True)
            imap_cfg = db_get_config("imap")
            host = st.text_input("Host", value=imap_cfg.get("host", ""), placeholder="imap.gmail.com")
            username = st.text_input("Email", value=imap_cfg.get("username", ""))
            password = st.text_input("Password", value=imap_cfg.get("password", ""), type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save", use_container_width=True):
                    db_save_config("imap", {"host": host, "username": username, "password": password, "port": 993})
                    st.success("Saved!")
            with col2:
                if st.button("Test", use_container_width=True):
                    if all([host, username, password]):
                        with st.spinner("Testing..."):
                            ok, msg = test_imap(host, username, password)
                            st.success("Connected") if ok else st.error(msg[:50])

# ========== FETCH SECTION ==========
def render_fetch():
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <h2 style="margin: 0; font-size: 1.25rem;">Fetch Emails</h2>
        <p style="color: #64748b; margin: 0.25rem 0 0; font-size: 0.875rem;">Retrieve emails from your IMAP server</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    
    with c1:
        start = st.date_input("From", value=date.today(), label_visibility="collapsed")
    with c2:
        end = st.date_input("To", value=date.today(), label_visibility="collapsed")
    with c3:
        mail_type = st.selectbox("Type", ["ALL", "UNREAD", "READ"], label_visibility="collapsed")
    with c4:
        if st.button("Fetch Emails →", use_container_width=True, type="primary"):
            cfg = db_get_config("imap")
            if not all([cfg.get("host"), cfg.get("username"), cfg.get("password")]):
                st.error("Configure IMAP first ⚙️")
            else:
                with st.spinner("Connecting..."):
                    emails = fetch_emails(
                        cfg["host"], cfg["username"], cfg["password"],
                        datetime.combine(start, datetime.min.time()),
                        datetime.combine(end, datetime.max.time()),
                        mail_type
                    )
                    for e in emails:
                        db_save_email(e)
                    st.success(f"Fetched {len(emails)} emails")

# ========== EMAIL LIST ==========
def render_emails():
    emails = db_get_emails()
    
    if not emails:
        st.info("📭 No emails yet. Configure IMAP and fetch emails.")
        return
    
    emails = sorted(emails, key=lambda x: x.get("date", ""), reverse=True)
    
    st.markdown(f"<h2 style='margin: 1.5rem 0 1rem; font-size: 1.25rem;'>Inbox ({len(emails)})</h2>", unsafe_allow_html=True)
    
    for mail in emails:
        email_id = mail.get("message_id") or hashlib.md5(
            (mail.get("subject", "") + mail.get("date", "")).encode()
        ).hexdigest()
        
        is_expanded = st.session_state.expanded_email_id == email_id
        
        # Email Card Header
        cols = st.columns([0.6, 5, 1.2])
        
        with cols[0]:
            sender = mail.get("from", "Unknown")
            color = get_color(sender)
            initials = get_initials(sender)
            st.markdown(f"""
            <div style="width: 44px; height: 44px; border-radius: 50%; background: {color}; 
                        display: flex; align-items: center; justify-content: center;
                        color: #0f1419; font-weight: 700; font-size: 0.9rem; font-family: 'Source Sans 3', sans-serif;">
                {initials}
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            subject = mail.get("subject", "(No Subject)")
            date_str = fmt_date(mail.get("date", ""))
            attach_icon = " 📎" if mail.get("has_attachment") else ""
            
            st.markdown(f"<div style='font-weight: 600; color: #f8f9fa; font-size: 0.95rem;'>{subject}{attach_icon}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color: #64748b; font-size: 0.8rem;'>{sender} • {date_str}</div>", unsafe_allow_html=True)
        
        with cols[2]:
            btn_text = "Close" if is_expanded else "Open"
            if st.button(btn_text, key=f"toggle_{email_id}", use_container_width=True):
                st.session_state.expanded_email_id = None if is_expanded else email_id
                st.rerun()
        
        # Expanded Content
        if is_expanded:
            with st.container():
                st.markdown("<div style='margin: 0.75rem 0 1.5rem; padding: 1.25rem; background: #1a1f2e; border-radius: 8px; border: 1px solid #2d3748;'>", unsafe_allow_html=True)
                
                # Mode Toggle Buttons
                current_mode = st.session_state.email_view_mode.get(email_id, "original")
                
                btn_cols = st.columns([1, 1, 1, 2])
                
                with btn_cols[0]:
                    if st.button("📄 Original", key=f"orig_{email_id}", 
                               type="primary" if current_mode == "original" else "secondary",
                               use_container_width=True):
                        st.session_state.email_view_mode[email_id] = "original"
                        st.rerun()
                
                with btn_cols[1]:
                    if st.button("🌐 Translate", key=f"trans_{email_id}",
                               type="primary" if current_mode == "translate" else "secondary",
                               use_container_width=True):
                        st.session_state.email_view_mode[email_id] = "translate"
                        if email_id not in st.session_state.email_translations:
                            with st.spinner("Translating..."):
                                st.session_state.email_translations[email_id] = translate_google(mail.get("body", ""))
                        st.rerun()
                
                with btn_cols[2]:
                    if st.button("🤖 AI Summary", key=f"ai_{email_id}",
                               type="primary" if current_mode == "ai" else "secondary",
                               use_container_width=True):
                        st.session_state.email_view_mode[email_id] = "ai"
                        if email_id not in st.session_state.email_ai_results:
                            with st.spinner("AI analyzing..."):
                                st.session_state.email_ai_results[email_id] = ai_process(mail.get("body", ""), "summarize")
                        st.rerun()
                
                with btn_cols[3]:
                    if st.button("🗑️ Delete", key=f"del_{email_id}", use_container_width=True):
                        db_delete_email(email_id)
                        st.success("Deleted")
                        st.rerun()
                
                st.divider()
                
                # Content Display
                if current_mode == "original":
                    st.markdown("<p style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>Original Content</p>", unsafe_allow_html=True)
                    st.text_area("", value=mail.get("body", ""), height=200, disabled=True, label_visibility="collapsed")
                
                elif current_mode == "translate":
                    st.markdown("<p style='color: #5dade2; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>🌐 Vietnamese Translation</p>", unsafe_allow_html=True)
                    translated = st.session_state.email_translations.get(email_id, "Translating...")
                    st.text_area("", value=translated, height=200, disabled=True, label_visibility="collapsed")
                
                elif current_mode == "ai":
                    st.markdown("<p style='color: #f4d03f; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;'>🤖 AI Summary</p>", unsafe_allow_html=True)
                    ai_result = st.session_state.email_ai_results.get(email_id, "Analyzing...")
                    st.info(ai_result)
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.divider()

# ========== MAIN ==========
render_sidebar()

st.markdown("""
<div style="padding: 0.5rem 0 1.5rem;">
    <h1 style="margin: 0; font-size: 2rem;">Inbox Intelligence</h1>
    <p style="color: #64748b; margin: 0.25rem 0 0;">AI-powered email management</p>
</div>
""", unsafe_allow_html=True)

render_fetch()
st.divider()
render_emails()
