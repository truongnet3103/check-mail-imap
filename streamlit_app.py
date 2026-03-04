"""
Mail Nexus - Streamlit Email Manager
"""
import streamlit as st

# ========== PAGE CONFIG (MUST BE FIRST) ==========
st.set_page_config(
    page_title="Mail Nexus",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}
::-webkit-scrollbar {width: 6px;}
::-webkit-scrollbar-track {background: transparent;}
::-webkit-scrollbar-thumb {background: #cbd5e1; border-radius: 3px;}
.stButton > button {border-radius: 8px !important; font-weight: 500 !important;}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

# ========== IMPORTS ==========
import hashlib
import imaplib
import ssl
import email
import requests
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import date, datetime, timedelta

# Firebase - optional
FIREBASE_OK = False
FIREBASE_ERROR = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_OK = True
except Exception as e:
    FIREBASE_ERROR = str(e)

# GenAI - optional  
GENAI_OK = False
try:
    import google.generativeai as genai
    GENAI_OK = True
except:
    pass

# ========== SESSION STATE ==========
if "expanded_id" not in st.session_state:
    st.session_state.expanded_id = None
if "translations" not in st.session_state:
    st.session_state.translations = {}
if "ai_summaries" not in st.session_state:
    st.session_state.ai_summaries = {}
if "view_modes" not in st.session_state:
    st.session_state.view_modes = {}
if "active_ai" not in st.session_state:
    st.session_state.active_ai = "gemini-2.5-flash"

# ========== OFFLINE STORAGE ==========
if "offline_emails" not in st.session_state:
    st.session_state.offline_emails = []
if "offline_imap" not in st.session_state:
    st.session_state.offline_imap = {}
if "offline_ai" not in st.session_state:
    st.session_state.offline_ai = {}

# ========== FIREBASE SERVICES ==========
def get_db():
    """Get Firestore client or None"""
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

@st.cache_resource
def get_firebase_db():
    return get_db()

def save_ai_config(data):
    db = get_firebase_db()
    if db:
        try:
            db.collection("config").document("ai").set(data)
            return True
        except:
            pass
    # Offline fallback
    st.session_state.offline_ai.update(data)
    return True

def get_ai_config():
    db = get_firebase_db()
    if db:
        try:
            doc = db.collection("config").document("ai").get()
            return doc.to_dict() if doc.exists else {}
        except:
            pass
    return st.session_state.offline_ai

def save_imap_config(data):
    db = get_firebase_db()
    if db:
        try:
            db.collection("config").document("imap").set(data)
            return True
        except:
            pass
    st.session_state.offline_imap.update(data)
    return True

def get_imap_config():
    db = get_firebase_db()
    if db:
        try:
            doc = db.collection("config").document("imap").get()
            return doc.to_dict() if doc.exists else {}
        except:
            pass
    return st.session_state.offline_imap

def save_email(email_data):
    db = get_firebase_db()
    if db:
        try:
            raw_id = email_data.get("message_id") or (email_data.get("subject", "") + email_data.get("date", ""))
            doc_id = hashlib.md5(raw_id.encode()).hexdigest()
            db.collection("emails").document(doc_id).set(email_data)
            return True
        except:
            pass
    st.session_state.offline_emails.append(email_data)
    return True

def get_all_emails():
    db = get_firebase_db()
    if db:
        try:
            docs = db.collection("emails").stream()
            return [doc.to_dict() for doc in docs]
        except:
            pass
    return st.session_state.offline_emails

def delete_email(message_id):
    db = get_firebase_db()
    if db:
        try:
            db.collection("emails").document(message_id).delete()
        except:
            pass
    st.session_state.offline_emails = [
        e for e in st.session_state.offline_emails 
        if (e.get("message_id") or hashlib.md5((e.get("subject", "") + e.get("date", "")).encode()).hexdigest()) != message_id
    ]

# ========== IMAP SERVICES ==========
def test_imap_connection(host, username, password, port=993):
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=context)
        mail.login(username, password)
        mail.logout()
        return True, "Kết nối thành công!"
    except Exception as e:
        return False, str(e)

def decode_mime_words(s):
    if not s:
        return ""
    try:
        decoded_words = decode_header(s)
        decoded_string = ""
        for word, encoding in decoded_words:
            if isinstance(word, bytes):
                decoded_string += word.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_string += word
        return decoded_string
    except:
        return s

def fetch_emails_by_date(host, username, password, start_date, end_date, read_status="ALL", port=993):
    emails = []
    try:
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

        for eid in reversed(email_ids):
            try:
                status, msg_data = mail.fetch(eid, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = decode_mime_words(msg.get("Subject", ""))
                sender = msg.get("From", "")
                message_id = msg.get("Message-ID", "")
                date_raw = msg.get("Date")
                
                try:
                    email_date = parsedate_to_datetime(date_raw) if date_raw else None
                except:
                    email_date = None

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
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")

                emails.append({
                    "message_id": message_id,
                    "subject": subject or "(Không tiêu đề)",
                    "from": sender,
                    "date": email_date.isoformat() if email_date else "",
                    "has_attachment": has_attachment,
                    "snippet": body[:500]
                })
            except:
                continue

        mail.logout()
    except Exception as e:
        st.error(f"Lỗi fetch: {e}")
    return emails

# ========== AI SERVICES ==========
def get_gemini_response(text, prompt_type="summarize"):
    if not GENAI_OK:
        return "⚠️ Chưa cài google-generativeai"
    
    ai_config = get_ai_config()
    api_key = ai_config.get("api_key", "")
    
    if not api_key:
        return "⚠️ Chưa cấu hình API Key"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(st.session_state.active_ai)
        
        if prompt_type == "summarize":
            prompt = f"Tóm tắt email sau bằng tiếng Việt, ngắn gọn:\n\n{text}\n\nTóm tắt:"
        else:
            prompt = text
            
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Lỗi AI: {str(e)[:100]}"

def translate_text_google(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "vi", "dt": "t", "q": text}
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        return "".join([item[0] for item in data[0]])
    except:
        return "❌ Lỗi dịch"

# ========== UI HELPERS ==========
def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return date_str[:16].replace("T", " ") if date_str else ""

def get_initials(name):
    if not name:
        return "?"
    parts = name.replace('@', ' ').replace('.', ' ').split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[0].upper() if name else "?"

def get_avatar_color(name):
    colors = ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#10b981", "#f59e0b"]
    if not name:
        return colors[0]
    return colors[hash(name) % len(colors)]

# ========== SIDEBAR ==========
def render_sidebar():
    with st.sidebar:
        # Status indicator
        db = get_firebase_db()
        if db:
            st.success("🟢 Firebase OK")
        else:
            st.warning("🟡 Offline Mode")
        
        # Logo
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <div style="font-size: 2.5rem;">✉️</div>
            <h1 style="margin: 0; font-size: 1.5rem;">Mail Nexus</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # AI Model
        st.markdown("🤖 **AI Model**")
        ai_model = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro"], label_visibility="collapsed")
        st.session_state.active_ai = ai_model
        
        if not GENAI_OK:
            st.warning("⚠️ google-generativeai chưa cài")
        
        st.divider()
        
        # Stats
        emails = get_all_emails()
        st.markdown(f"**{len(emails)}** emails")
        
        # Config
        st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
        
        with st.expander("⚙️ Cấu hình", expanded=False):
            st.markdown("**🤖 AI**")
            ai_config = get_ai_config()
            api_key = st.text_input("API Key", value=ai_config.get("api_key", ""), type="password")
            if st.button("💾 Lưu AI", use_container_width=True):
                save_ai_config({"api_key": api_key, "model": ai_model})
                st.success("Đã lưu!")
            
            st.divider()
            
            st.markdown("**📧 IMAP**")
            imap_config = get_imap_config()
            host = st.text_input("Host", value=imap_config.get("host", ""), placeholder="imap.gmail.com")
            username = st.text_input("Username", value=imap_config.get("username", ""))
            password = st.text_input("Password", value=imap_config.get("password", ""), type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Lưu", use_container_width=True):
                    save_imap_config({"host": host, "username": username, "password": password, "port": 993, "ssl": True})
                    st.success("Đã lưu!")
            with col2:
                if st.button("🧪 Test", use_container_width=True):
                    if all([host, username, password]):
                        with st.spinner("Testing..."):
                            success, msg = test_imap_connection(host, username, password)
                            st.success(msg) if success else st.error(msg[:50])

# ========== MAIN CONTENT ==========
def render_fetch_section():
    st.markdown("### 📥 Lấy Email Mới")
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        start_date = st.date_input("Từ ngày", value=date.today(), label_visibility="collapsed")
    with col2:
        end_date = st.date_input("Đến ngày", value=date.today(), label_visibility="collapsed")
    with col3:
        mail_type = st.selectbox("Loại", ["ALL", "UNREAD", "READ"], label_visibility="collapsed")
    with col4:
        if st.button("🚀 FETCH EMAILS", use_container_width=True, type="primary"):
            imap_conf = get_imap_config()
            if not imap_conf or not all([imap_conf.get("host"), imap_conf.get("username"), imap_conf.get("password")]):
                st.error("⚠️ Chưa cấu hình IMAP!")
            else:
                with st.spinner("⏳ Đang kết nối..."):
                    emails = fetch_emails_by_date(
                        imap_conf["host"], imap_conf["username"], imap_conf["password"],
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time()),
                        mail_type
                    )
                    for mail in emails:
                        save_email(mail)
                    st.success(f"✅ Đã lấy {len(emails)} email!")

def render_email_list():
    emails = get_all_emails()
    
    if not emails:
        st.info("📭 Chưa có email. Hãy fetch từ IMAP server.")
        return
    
    emails = sorted(emails, key=lambda x: x.get("date", ""), reverse=True)
    st.markdown(f"### 📨 Danh sách ({len(emails)})")
    
    for mail in emails:
        mail_id = mail.get("message_id", "") or hashlib.md5((mail.get("subject", "") + mail.get("date", "")).encode()).hexdigest()
        is_expanded = st.session_state.expanded_id == mail_id
        
        col_avatar, col_info, col_actions = st.columns([0.5, 6, 1.5])
        
        with col_avatar:
            sender = mail.get("from", "Unknown")
            color = get_avatar_color(sender)
            initials = get_initials(sender)
            st.markdown(f'<div style="width: 40px; height: 40px; border-radius: 50%; background: {color}; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;">{initials}</div>', unsafe_allow_html=True)
        
        with col_info:
            subject = mail.get("subject", "(Không tiêu đề)")
            date_str = format_date(mail.get("date", ""))
            has_attach = " 📎" if mail.get("has_attachment") else ""
            st.markdown(f"**{subject}**{has_attach}")
            st.caption(f"{sender} • {date_str}")
        
        with col_actions:
            if st.button("Xem" if not is_expanded else "Đóng", key=f"btn_{mail_id}", use_container_width=True):
                st.session_state.expanded_id = None if is_expanded else mail_id
                st.rerun()
        
        if is_expanded:
            current_mode = st.session_state.view_modes.get(mail_id, "original")
            
            col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
            
            with col1:
                if st.button("📄 Gốc", key=f"orig_{mail_id}", type="primary" if current_mode == "original" else "secondary", use_container_width=True):
                    st.session_state.view_modes[mail_id] = "original"
                    st.rerun()
            
            with col2:
                if st.button("🌐 Dịch", key=f"trans_{mail_id}", type="primary" if current_mode == "translate" else "secondary", use_container_width=True):
                    st.session_state.view_modes[mail_id] = "translate"
                    if mail_id not in st.session_state.translations:
                        with st.spinner("Đang dịch..."):
                            st.session_state.translations[mail_id] = translate_text_google(mail.get("snippet", ""))
                    st.rerun()
            
            with col3:
                if st.button("🤖 AI", key=f"ai_{mail_id}", type="primary" if current_mode == "ai" else "secondary", use_container_width=True):
                    st.session_state.view_modes[mail_id] = "ai"
                    if mail_id not in st.session_state.ai_summaries:
                        with st.spinner("AI đang phân tích..."):
                            st.session_state.ai_summaries[mail_id] = get_gemini_response(mail.get("snippet", ""), "summarize")
                    st.rerun()
            
            with col4:
                if st.button("🗑️ Xóa", key=f"del_{mail_id}", use_container_width=True):
                    delete_email(mail_id)
                    st.success("Đã xóa!")
                    st.rerun()
            
            if current_mode == "original":
                st.text_area("", value=mail.get("snippet", ""), height=150, disabled=True, label_visibility="collapsed")
            elif current_mode == "translate":
                st.text_area("", value=st.session_state.translations.get(mail_id, "Đang dịch..."), height=150, disabled=True, label_visibility="collapsed")
            elif current_mode == "ai":
                st.info(st.session_state.ai_summaries.get(mail_id, "Đang phân tích..."))
        
        st.divider()

# ========== MAIN ==========
render_sidebar()

st.markdown("""
<div style="padding: 1rem 0;">
    <h1 style="color: #1e293b; margin: 0;">Mail Nexus</h1>
    <p style="color: #64748b; margin: 0;">Quản lý email IMAP thông minh với AI</p>
</div>
""", unsafe_allow_html=True)

st.divider()
render_fetch_section()
st.divider()
render_email_list()
