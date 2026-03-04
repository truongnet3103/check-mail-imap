"""
Mail Nexus - Intelligent Email Manager
Design: Refined Light - Clean, professional, minimal
"""
import streamlit as st
import hashlib
import imaplib
import ssl
import email
import requests
import json
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import date, datetime, timedelta

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Mail Nexus",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== SIDEBAR TOGGLE BUTTON ==========
sidebar_state = st.session_state.get("sidebar_open", False)

# Top bar with menu button
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

* { font-family: 'Plus Jakarta Sans', sans-serif !important; }

/* Hide default Streamlit elements */
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}

/* Clean scrollbar */
::-webkit-scrollbar {width: 6px; height: 6px;}
::-webkit-scrollbar-track {background: transparent;}
::-webkit-scrollbar-thumb {background: #cbd5e1; border-radius: 3px;}
::-webkit-scrollbar-thumb:hover {background: #94a3b8;}

/* Top navigation bar */
.top-nav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid #e2e8f0;
    z-index: 1000;
    display: flex;
    align-items: center;
    padding: 0 1.5rem;
}

.menu-btn {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 8px;
    transition: background 0.2s;
}

.menu-btn:hover { background: #f1f5f9; }

/* Main content offset for fixed header */
.main-content {
    margin-top: 80px;
    padding: 0 1.5rem;
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
}

/* Buttons */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: all 0.2s ease !important;
}

.stButton > button[kind="primary"] {
    background: #0f172a !important;
    color: white !important;
    border: none !important;
}

.stButton > button[kind="primary"]:hover {
    background: #1e293b !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15) !important;
}

.stButton > button:not([kind="primary"]) {
    background: white !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
}

.stButton > button:not([kind="primary"]):hover {
    border-color: #cbd5e1 !important;
    background: #f8fafc !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    background: white !important;
    font-size: 0.875rem !important;
}

.stTextInput > div > div > input:focus,
.stSelectbox > div > div > div:focus {
    border-color: #0f172a !important;
    box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.08) !important;
}

/* Email card */
.email-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 0.75rem;
    transition: all 0.2s ease;
}

.email-card:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.email-sender {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.95rem;
}

.email-address {
    color: #64748b;
    font-size: 0.8rem;
}

.email-subject {
    color: #334155;
    font-size: 0.9rem;
    margin-top: 0.25rem;
}

.email-meta {
    color: #94a3b8;
    font-size: 0.75rem;
    margin-top: 0.5rem;
}

/* Expanded content */
.email-expanded {
    background: #f8fafc;
    border-radius: 8px;
    padding: 1.25rem;
    margin-top: 0.75rem;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #e2e8f0;
}

.stTabs [data-baseweb="tab"] {
    padding: 0.75rem 1.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #64748b;
    border: none;
    background: transparent;
}

.stTabs [aria-selected="true"] {
    color: #0f172a !important;
    border-bottom: 2px solid #0f172a !important;
}

/* Status indicators */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
}

.status-online { background: #dcfce7; color: #166534; }
.status-offline { background: #fef3c7; color: #92400e; }

/* Section headers */
.section-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-bottom: 0.75rem;
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

# ========== SESSION STATE ==========
def init_state():
    defaults = {
        "sidebar_open": False,
        "expanded_email_id": None,
        "email_translations": {},
        "email_ai_results": {},
        "email_view_mode": {},
        "offline_emails": [],
        "offline_config": {
            "imap": {"host": "", "username": "", "password": ""},
            "ai": {"provider": "gemini", "api_key": "", "model": "gemini-2.5-flash", "openrouter_model": "", "base_url": ""}
        }
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

def save_config(section, data):
    db = get_db()
    if db:
        try:
            db.collection("config").document(section).set(data)
            return
        except:
            pass
    st.session_state.offline_config[section].update(data)

def load_config(section):
    db = get_db()
    if db:
        try:
            doc = db.collection("config").document(section).get()
            if doc.exists:
                return doc.to_dict()
        except:
            pass
    return st.session_state.offline_config.get(section, {})

def save_email(email_data):
    db = get_db()
    eid = email_data.get("message_id") or hashlib.md5(
        (email_data.get("subject", "") + str(email_data.get("date", ""))).encode()
    ).hexdigest()
    
    if db:
        try:
            db.collection("emails").document(eid).set(email_data)
            return
        except:
            pass
    
    existing = [e for e in st.session_state.offline_emails
                if (e.get("message_id") or hashlib.md5((e.get("subject", "") + str(e.get("date", ""))).encode()).hexdigest()) != eid]
    existing.append(email_data)
    st.session_state.offline_emails = existing

def get_emails():
    db = get_db()
    if db:
        try:
            return [d.to_dict() for d in db.collection("emails").stream()]
        except:
            pass
    return st.session_state.offline_emails

def delete_email(eid):
    db = get_db()
    if db:
        try:
            db.collection("emails").document(eid).delete()
        except:
            pass
    st.session_state.offline_emails = [
        e for e in st.session_state.offline_emails
        if (e.get("message_id") or hashlib.md5((e.get("subject", "") + str(e.get("date", ""))).encode()).hexdigest()) != eid
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

def parse_sender(from_field):
    """Parse sender into name and email"""
    if not from_field:
        return "Unknown", ""
    
    from_field = decode_mime(from_field)
    
    if "<" in from_field and ">" in from_field:
        # Format: "Name <email@domain.com>"
        name = from_field.split("<")[0].strip().strip('"')
        email = from_field.split("<")[1].split(">")[0].strip()
        return name or email, email
    elif "@" in from_field:
        # Just email
        return from_field, from_field
    else:
        return from_field, ""

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
        
        for eid in reversed(msgs[0].split()[:50]):  # Limit 50 emails
            try:
                _, data = mail.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                
                subject = decode_mime(msg.get("Subject", ""))
                from_field = msg.get("From", "")
                sender_name, sender_email = parse_sender(from_field)
                
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
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "date": msg_date.isoformat() if msg_date else "",
                    "has_attachment": has_attach,
                    "body": body[:2000],
                    "preview": body[:150].replace("\n", " ").strip()
                })
            except:
                continue
        
        mail.logout()
    except Exception as e:
        st.error(f"IMAP Error: {e}")
    return emails

# ========== AI SERVICES ==========
def ai_process(text, mode="summarize"):
    cfg = load_config("ai")
    provider = cfg.get("provider", "gemini")
    api_key = cfg.get("api_key", "")
    
    if not api_key:
        return "⚠️ API key not configured"
    
    try:
        if provider == "openrouter":
            # OpenRouter API
            model = cfg.get("openrouter_model", "openai/gpt-3.5-turbo")
            base_url = cfg.get("base_url", "https://openrouter.ai/api/v1")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://mail-nexus.streamlit.app",
                "X-Title": "Mail Nexus"
            }
            
            if mode == "summarize":
                content = f"Summarize this email in Vietnamese, be concise:\n\n{text[:2000]}"
            else:
                content = f"Translate to Vietnamese:\n\n{text[:2000]}"
            
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": content}]
                },
                timeout=30
            )
            return resp.json()["choices"][0]["message"]["content"]
            
        else:
            # Gemini
            try:
                import google.generativeai as genai
            except:
                return "⚠️ google-generativeai not installed"
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(cfg.get("model", "gemini-2.5-flash"))
            
            if mode == "summarize":
                prompt = f"Tóm tắt email sau bằng tiếng Việt, ngắn gọn:\n\n{text[:2000]}\n\nTóm tắt:"
            else:
                prompt = f"Dịch sang tiếng Việt:\n\n{text[:2000]}\n\nBản dịch:"
            
            resp = model.generate_content(prompt)
            return resp.text
            
    except Exception as e:
        return f"❌ AI Error: {str(e)[:150]}"

def translate_google(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "vi", "dt": "t", "q": text[:1000]}
        r = requests.get(url, params=params, timeout=5)
        return "".join([item[0] for item in r.json()[0]])
    except:
        return "❌ Translation failed"

# ========== UI HELPERS ==========
def fmt_date(ds):
    try:
        dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
        return dt.strftime("%d/%m %H:%M")
    except:
        return ds[:16].replace("T", " ") if ds else ""

# ========== SIDEBAR ==========
def render_sidebar():
    with st.sidebar:
        # Status
        db = get_db()
        if db:
            st.markdown('<div class="status-badge status-online">● Online</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-offline">● Offline Mode</div>', unsafe_allow_html=True)
        
        st.divider()
        
        # IMAP Config
        st.markdown('<div class="section-title">📧 IMAP Configuration</div>', unsafe_allow_html=True)
        imap_cfg = load_config("imap")
        
        imap_host = st.text_input("Server", value=imap_cfg.get("host", ""), placeholder="imap.gmail.com")
        imap_user = st.text_input("Email", value=imap_cfg.get("username", ""))
        imap_pass = st.text_input("Password", value=imap_cfg.get("password", ""), type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                save_config("imap", {"host": imap_host, "username": imap_user, "password": imap_pass, "port": 993})
                st.success("Saved!")
        with col2:
            if st.button("🧪 Test", use_container_width=True):
                if all([imap_host, imap_user, imap_pass]):
                    with st.spinner("Testing..."):
                        ok, msg = test_imap(imap_host, imap_user, imap_pass)
                        st.success("✓ Connected") if ok else st.error(msg[:50])
        
        st.divider()
        
        # AI Config
        st.markdown('<div class="section-title">🤖 AI Configuration</div>', unsafe_allow_html=True)
        ai_cfg = load_config("ai")
        
        provider = st.selectbox(
            "Provider",
            ["gemini", "openrouter"],
            index=0 if ai_cfg.get("provider", "gemini") == "gemini" else 1
        )
        
        api_key = st.text_input("API Key", value=ai_cfg.get("api_key", ""), type="password")
        
        if provider == "gemini":
            model = st.selectbox(
                "Model",
                ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
                index=0
            )
            save_config("ai", {"provider": provider, "api_key": api_key, "model": model})
        else:
            openrouter_model = st.text_input(
                "OpenRouter Model",
                value=ai_cfg.get("openrouter_model", "openai/gpt-3.5-turbo"),
                placeholder="openai/gpt-3.5-turbo"
            )
            base_url = st.text_input(
                "Base URL",
                value=ai_cfg.get("base_url", "https://openrouter.ai/api/v1"),
                placeholder="https://openrouter.ai/api/v1"
            )
            if st.button("💾 Save AI Config", use_container_width=True):
                save_config("ai", {
                    "provider": provider,
                    "api_key": api_key,
                    "openrouter_model": openrouter_model,
                    "base_url": base_url
                })
                st.success("Saved!")

# ========== MAIN CONTENT ==========
# Toggle sidebar button
col_nav, col_title = st.columns([0.1, 0.9])
with col_nav:
    if st.button("☰", key="menu_btn"):
        st.session_state.sidebar_open = not st.session_state.sidebar_open
        st.rerun()

with col_title:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 0.75rem;">
        <span style="font-size: 1.5rem;">✉️</span>
        <div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a;">Mail Nexus</div>
            <div style="font-size: 0.75rem; color: #64748b;">Intelligent Email Manager</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Show sidebar if toggled
if st.session_state.sidebar_open:
    render_sidebar()

st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Fetch Section
st.markdown('<div style="margin: 1.5rem 0;">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Fetch Emails</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 2])

with col1:
    start_date = st.date_input("From", value=date.today(), label_visibility="collapsed")
with col2:
    end_date = st.date_input("To", value=date.today(), label_visibility="collapsed")
with col3:
    mail_type = st.selectbox("Type", ["ALL", "UNREAD", "READ"], label_visibility="collapsed")
with col4:
    if st.button("🚀 Fetch Emails", use_container_width=True, type="primary"):
        cfg = load_config("imap")
        if not all([cfg.get("host"), cfg.get("username"), cfg.get("password")]):
            st.error("⚠️ Configure IMAP in settings first")
        else:
            with st.spinner("Fetching..."):
                emails = fetch_emails(
                    cfg["host"], cfg["username"], cfg["password"],
                    datetime.combine(start_date, datetime.min.time()),
                    datetime.combine(end_date, datetime.max.time()),
                    mail_type
                )
                for e in emails:
                    save_email(e)
                st.success(f"✓ Fetched {len(emails)} emails")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Email List
emails = get_emails()

if not emails:
    st.info("📭 No emails yet. Configure IMAP settings and fetch emails.")
else:
    st.markdown(f'<div class="section-title">Inbox ({len(emails)})</div>', unsafe_allow_html=True)
    
    emails = sorted(emails, key=lambda x: x.get("date", ""), reverse=True)
    
    for mail in emails:
        eid = mail.get("message_id") or hashlib.md5(
            (mail.get("subject", "") + str(mail.get("date", ""))).encode()
        ).hexdigest()
        
        is_expanded = st.session_state.expanded_email_id == eid
        
        # Email Card
        with st.container():
            cols = st.columns([4, 1.5, 1])
            
            with cols[0]:
                sender_name = mail.get("sender_name", "Unknown")
                sender_email = mail.get("sender_email", "")
                subject = mail.get("subject", "(No Subject)")
                preview = mail.get("preview", "")
                date_str = fmt_date(mail.get("date", ""))
                attach = " 📎" if mail.get("has_attachment") else ""
                
                st.markdown(f"""
                <div class="email-card">
                    <div class="email-sender">{sender_name}{attach}</div>
                    <div class="email-address">{sender_email}</div>
                    <div class="email-subject">{subject}</div>
                    <div class="email-meta">{date_str} • {preview[:80]}{"..." if len(preview) > 80 else ""}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                btn_label = "Close" if is_expanded else "Read"
                if st.button(btn_label, key=f"read_{eid}", use_container_width=True):
                    st.session_state.expanded_email_id = None if is_expanded else eid
                    st.rerun()
            
            with cols[2]:
                if st.button("🗑️", key=f"del_{eid}"):
                    delete_email(eid)
                    st.success("Deleted")
                    st.rerun()
            
            # Expanded View
            if is_expanded:
                current_mode = st.session_state.email_view_mode.get(eid, "original")
                
                tab_orig, tab_trans, tab_ai = st.tabs(["📄 Original", "🌐 Translate", "🤖 AI"])
                
                with tab_orig:
                    st.text_area("Content", value=mail.get("body", ""), height=250, disabled=True, label_visibility="collapsed")
                
                with tab_trans:
                    if st.button("Translate to Vietnamese", key=f"btn_trans_{eid}"):
                        with st.spinner("Translating..."):
                            st.session_state.email_translations[eid] = translate_google(mail.get("body", ""))
                    
                    translated = st.session_state.email_translations.get(eid, "Click Translate to see Vietnamese version")
                    st.text_area("Translation", value=translated, height=250, disabled=True, label_visibility="collapsed")
                
                with tab_ai:
                    if st.button("Generate AI Summary", key=f"btn_ai_{eid}"):
                        with st.spinner("AI analyzing..."):
                            st.session_state.email_ai_results[eid] = ai_process(mail.get("body", ""), "summarize")
                    
                    ai_result = st.session_state.email_ai_results.get(eid, "Click Generate to see AI summary")
                    st.info(ai_result)

st.markdown('</div>', unsafe_allow_html=True)
