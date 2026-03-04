"""
Mail Nexus - Redesigned
A modern Streamlit email manager with IMAP + AI
"""
import streamlit as st
from datetime import date, datetime, timedelta
import hashlib
import ssl
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import requests

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Mail Nexus",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CUSTOM CSS (Modern Dark Theme) ==========
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
/* Hide default Streamlit elements */
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"], footer {display: none !important;}

/* Root variables */
:root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-tertiary: #334155;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --accent-primary: #10b981;
    --accent-secondary: #6366f1;
    --accent-hover: #059669;
    --border-color: #334155;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.3), 0 4px 6px -4px rgb(0 0 0 / 0.3);
    --radius: 12px;
    --sidebar-width: 320px;
}

/* Mobile burger sidebar */
.mobile-burger {
    display: none;
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 9999;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 0.5rem;
    box-shadow: var(--shadow-md);
    cursor: pointer;
}
@media (max-width: 768px) {
    .mobile-burger { display: block; }
    section[data-testid="stSidebar"] {
        width: 66.66vw !important;
        max-width: 400px;
        position: fixed;
        height: 100vh;
        z-index: 9998;
        transform: translateX(-100%);
        transition: transform 0.3s ease;
        box-shadow: var(--shadow-lg);
    }
    section[data-testid="stSidebar"].open {
        transform: translateX(0);
    }
}

/* Global styles */
body, .stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Figtree', sans-serif;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

p, span, div, label, .stMarkdown {
    color: var(--text-secondary) !important;
}

/* Inputs and buttons */
.stButton > button {
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    border: none !important;
    transition: all 0.2s ease !important;
    font-family: 'Outfit', sans-serif !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-hover) 100%) !important;
    color: white !important;
}
.stButton > button[kind="secondary"] {
    background: var(--bg-tertiary) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border-color) !important;
}
.stButton > button:active {
    transform: translateY(0);
}
.stButton > button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Form inputs */
.stTextInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div > div {
    background-color: var(--bg-secondary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    padding: 0.5rem 0.75rem !important;
}
.stTextInput input:focus,
.stDateInput input:focus,
.stSelectbox [data-baseweb="select"]:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2) !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-color) !important;
}
section[data-testid="stSidebar"] .stExpander {
    background: transparent !important;
    border: none !important;
}
section[data-testid="stSidebar"] .stExpander header {
    background: transparent !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

/* Cards and containers */
.email-card {
    background: var(--bg-secondary);
    border-radius: var(--radius);
    padding: 1rem;
    margin-bottom: 0.75rem;
    border: 1px solid var(--border-color);
    transition: all 0.2s ease;
    cursor: pointer;
}
.email-card:hover {
    border-color: var(--accent-primary);
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}

/* Status indicators */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-online { background: var(--accent-primary); }
.status-offline { background: #f59e0b; }

/* Loading spinner */
.stSpinner > div {
    border-color: var(--accent-primary) !important;
}

/* Scrollbar */
::-webkit-scrollbar {width: 8px;}
::-webkit-scrollbar-track {background: var(--bg-primary);}
::-webkit-scrollbar-thumb {background: var(--bg-tertiary); border-radius: 4px;}
::-webkit-scrollbar-thumb:hover {background: var(--text-secondary);}

/* Animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in {
    animation: fadeIn 0.3s ease forwards;
}

/* Badge */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.5rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    background: var(--bg-tertiary);
    color: var(--text-secondary);
    margin-right: 0.25rem;
    margin-bottom: 0.25rem;
}

/* Mobile burger */
.mobile-burger {
    display: none;
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 9999;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 0.5rem;
    box-shadow: var(--shadow-md);
    cursor: pointer;
    font-size: 1.2rem;
}
@media (max-width: 768px) {
    .mobile-burger { display: block; }
    section[data-testid="stSidebar"] {
        width: 66.66vw !important;
        max-width: 400px;
        position: fixed;
        height: 100vh;
        z-index: 9998;
        transform: translateX(-100%);
        transition: transform 0.3s ease;
        box-shadow: var(--shadow-lg);
    }
    section[data-testid="stSidebar"].open {
        transform: translateX(0);
    }
}
@media (min-width: 769px) {
    button[data-testid="baseButton-secondary"]:has-text("☰") {
        display: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ========== IMPORTS (Optional dependencies) ==========
GENAI_OK = False
FIREBASE_OK = False
GENAI_ERROR = ""
FIREBASE_ERROR = ""

try:
    import google.generativeai as genai
    GENAI_OK = True
except Exception as e:
    GENAI_ERROR = str(e)

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_OK = True
except Exception as e:
    FIREBASE_ERROR = str(e)

# ========== SESSION STATE ==========
defaults = {
    "expanded_id": None,
    "translations": {},
    "ai_summaries": {},
    "view_modes": {},
    "active_ai": "gemini-2.5-flash",
    "offline_emails": [],
    "offline_imap": {},
    "offline_ai": {},
    "offline_sender_tags": {},
    "burger_open": False,
    "current_fetch_filters": {}
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ========== UTILITY FUNCTIONS ==========
def decode_mime_words(s):
    if not s:
        return ""
    try:
        decoded = decode_header(s)
        result = ""
        for part, encoding in decoded:
            if isinstance(part, bytes):
                result += part.decode(encoding or "utf-8", errors="ignore")
            else:
                result += part
        return result
    except:
        return str(s)

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
    colors = ["#10b981", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f59e0b"]
    if not name:
        return colors[0]
    return colors[hash(name) % len(colors)]

# ========== FIREBASE SERVICES ==========
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

@st.cache_resource(ttl=300)
def get_firebase_db_cached():
    return get_db()

def save_ai_config(data):
    db = get_firebase_db_cached()
    if db:
        try:
            db.collection("config").document("ai").set(data)
            return True
        except:
            pass
    st.session_state.offline_ai.update(data)
    return True

def get_ai_config():
    db = get_firebase_db_cached()
    if db:
        try:
            doc = db.collection("config").document("ai").get()
            return doc.to_dict() if doc.exists else {}
        except:
            pass
    return st.session_state.offline_ai

def save_imap_config(data):
    db = get_firebase_db_cached()
    if db:
        try:
            db.collection("config").document("imap").set(data)
            return True
        except:
            pass
    st.session_state.offline_imap.update(data)
    return True

def get_imap_config():
    db = get_firebase_db_cached()
    if db:
        try:
            doc = db.collection("config").document("imap").get()
            return doc.to_dict() if doc.exists else {}
        except:
            pass
    return st.session_state.offline_imap

# ========== TAG MANAGEMENT ==========
def get_sender_tags():
    db = get_firebase_db_cached()
    if db:
        try:
            doc = db.collection("config").document("sender_tags").get()
            return doc.to_dict() if doc.exists else {}
        except:
            pass
    return st.session_state.get("offline_sender_tags", {})

def save_sender_tags(tags_dict):
    db = get_firebase_db_cached()
    if db:
        try:
            db.collection("config").document("sender_tags").set(tags_dict)
            return True
        except:
            pass
    if "offline_sender_tags" not in st.session_state:
        st.session_state.offline_sender_tags = {}
    st.session_state.offline_sender_tags.update(tags_dict)
    return True

def get_tag_colors():
    return {
        "work": "#6366f1",
        "personal": "#10b981",
        "finance": "#f59e0b",
        "social": "#ec4899",
        "promo": "#8b5cf6",
        "important": "#f43f5e",
    }

def save_email(email_data):
    db = get_firebase_db_cached()
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

@st.cache_data(ttl=60)
def get_all_emails_cached():
    db = get_firebase_db_cached()
    if db:
        try:
            docs = db.collection("emails").stream()
            return [doc.to_dict() for doc in docs]
        except:
            pass
    return st.session_state.offline_emails

@st.cache_data(ttl=60)
def get_distinct_senders():
    emails = get_all_emails_cached()
    senders = set()
    for e in emails:
        sender = e.get("from", "")
        if sender:
            senders.add(sender)
    return sorted(list(senders))

def delete_email(message_id):
    db = get_firebase_db_cached()
    if db:
        try:
            db.collection("emails").document(message_id).delete()
        except:
            pass
    # Remove from offline cache
    st.session_state.offline_emails = [
        e for e in st.session_state.offline_emails
        if (e.get("message_id") or hashlib.md5((e.get("subject", "") + e.get("date", "")).encode()).hexdigest()) != message_id
    ]
    # Clear caches
    get_all_emails_cached.clear()

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

@st.cache_data(ttl=300)
def fetch_emails_by_date(host, username, password, start_date, end_date, read_status="ALL", port=993, sender_filters=None, subject_contains=None):
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

                email_data = {
                    "message_id": message_id,
                    "subject": subject or "(Không tiêu đề)",
                    "from": sender,
                    "date": email_date.isoformat() if email_date else "",
                    "has_attachment": has_attachment,
                    "snippet": body[:500]
                }

                # Apply filters
                if sender_filters:
                    if not any(sf.lower() in sender.lower() for sf in sender_filters):
                        continue
                if subject_contains:
                    if subject_contains.lower() not in subject.lower():
                        continue

                emails.append(email_data)
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

# ========== SIDEBAR ==========
def render_sidebar():
    with st.sidebar:
        # Mobile burger toggle button
        if st.button("☰", key="burger_btn", help="Mở menu", type="secondary"):
            st.session_state.burger_open = not st.session_state.burger_open

        # Status indicator
        db = get_firebase_db_cached()
        if db:
            st.markdown('<span class="status-dot status-online"></span> **Firebase Connected**', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-dot status-offline"></span> **Offline Mode**', unsafe_allow_html=True)

        st.divider()

        # Logo
        st.markdown("""
        <div style="text-align: center; padding: 1.5rem 0;">
            <div style="font-size: 3rem; line-height: 1;">✉️</div>
            <h1 style="margin: 0.25rem 0 0; font-size: 1.75rem; letter-spacing: -0.02em;">Mail Nexus</h1>
            <p style="margin: 0; font-size: 0.875rem; color: var(--text-secondary);">Email Intelligence</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # AI Model Selector
        st.markdown("### 🤖 AI Model")
        ai_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
        current_index = ai_models.index(st.session_state.active_ai) if st.session_state.active_ai in ai_models else 0
        selected = st.selectbox(
            "Model",
            ai_models,
            index=current_index,
            label_visibility="collapsed"
        )
        if selected != st.session_state.active_ai:
            st.session_state.active_ai = selected
            st.rerun()

        if not GENAI_OK:
            st.warning("⚠️ `google-generativeai` chưa được cài đặt", icon="⚠️")

        st.divider()

        # Stats
        emails = get_all_emails_cached()
        senders = get_distinct_senders()
        st.markdown(f"""
        <div style="padding: 0.5rem 0;">
            <div style="font-size: 0.875rem; color: var(--text-secondary);">Total Emails</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-primary);">{len(emails)}</div>
        </div>
        <div style="padding: 0.5rem 0;">
            <div style="font-size: 0.875rem; color: var(--text-secondary);">Senders</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-secondary);">{len(senders)}</div>
        </div>
        """, unsafe_allow_html=True)

        # Burger menu content (context & tags)
        if st.session_state.burger_open:
            st.markdown("---")
            st.markdown("## 📋 Context & Tags")
            
            # 1. Context Report
            st.markdown("### 🔍 Báo cáo Filter hiện tại")
            filters = st.session_state.current_fetch_filters
            if filters:
                st.write(f"**Từ ngày:** {filters.get('start_date')}")
                st.write(f"**Đến ngày:** {filters.get('end_date')}")
                st.write(f"**Trạng thái:** {filters.get('read_status')}")
                if filters.get('sender_filters'):
                    st.write(f"**Người gửi:** {', '.join(filters['sender_filters'])}")
                if filters.get('subject_filter'):
                    st.write(f"**Chủ đề chứa:** {filters['subject_filter']}")
            else:
                st.info("Chưa có filter nào được dùng.")
            
            st.divider()
            
            # 2. Tag Config
            st.markdown("### 🏷️ Cấu hình Tag")
            all_senders = get_distinct_senders()
            selected_sender = st.selectbox(
                "Chọn người gửi",
                options=all_senders,
                index=None,
                placeholder="Nhấn để chọn...",
                key="tag_sender_select"
            )
            
            if selected_sender:
                tags_dict = get_sender_tags()
                current_tag = tags_dict.get(selected_sender, "")
                tag_options = [""] + list(get_tag_colors().keys())
                new_tag = st.selectbox(
                    "Tag",
                    options=tag_options,
                    index=tag_options.index(current_tag) if current_tag in tag_options else 0,
                    format_func=lambda x: "⛝ Không có" if not x else x.capitalize(),
                    key="tag_select"
                )
                if st.button("💾 Lưu tag", use_container_width=True, key="save_tag_btn"):
                    if new_tag:
                        tags_dict[selected_sender] = new_tag
                    else:
                        tags_dict.pop(selected_sender, None)
                    save_sender_tags(tags_dict)
                    st.toast("Đã lưu tag!", icon="✅")
                    st.rerun()
            
            # Show current tags
            tags = get_sender_tags()
            if tags:
                st.markdown("**Tags hiện tại:**")
                for sender, tag in tags.items():
                    color = get_tag_colors().get(tag, "#64748b")
                    st.markdown(f'<span class="badge" style="background:{color}; color:white;">{tag}: {sender[:20]}{"..." if len(sender)>20 else ""}</span>', unsafe_allow_html=True)
            else:
                st.caption("Chưa có tag nào.")
            
            # Close button
            col1, col2 = st.columns([1,3])
            with col1:
                if st.button("❌ Đóng", use_container_width=True, key="close_burger"):
                    st.session_state.burger_open = False

        # Spacer to push config to bottom
        st.markdown('<div style="flex-grow: 1; height: 30vh;"></div>', unsafe_allow_html=True)

        st.divider()

        # Configuration Expander
        with st.expander("⚙️ Cấu hình", expanded=False):
            # Tabs for AI and IMAP
            tab1, tab2 = st.tabs(["🤖 AI", "📧 IMAP"])

            with tab1:
                st.markdown("**Google Gemini**")
                ai_config = get_ai_config()
                api_key = st.text_input(
                    "API Key",
                    value=ai_config.get("api_key", ""),
                    type="password",
                    placeholder="AIza...",
                    label_visibility="collapsed",
                    key="ai_api_key"
                )
                col1, col2 = st.columns([1,1])
                with col1:
                    if st.button("💾 Lưu", use_container_width=True, type="primary", key="ai_save_btn"):
                        save_ai_config({"api_key": api_key, "model": st.session_state.active_ai})
                        st.toast("Đã lưu AI config", icon="✅")
                with col2:
                    if st.button("🔑 Test", use_container_width=True, key="ai_test_btn"):
                        if api_key:
                            try:
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel(st.session_state.active_ai)
                                model.generate_content("Test")
                                st.toast("✅ API Key hợp lệ", icon="🎯")
                            except Exception as e:
                                st.toast(f"❌ Lỗi: {str(e)[:50]}", icon="⚠️")
                        else:
                            st.toast("Nhập API Key trước", icon="⚠️")

            with tab2:
                st.markdown("**IMAP Server**")
                imap_config = get_imap_config()
                host = st.text_input("Host", value=imap_config.get("host", ""), placeholder="imap.gmail.com", key="imap_host")
                username = st.text_input("Username", value=imap_config.get("username", ""), placeholder="user@example.com", key="imap_username")
                password = st.text_input("Password", value=imap_config.get("password", ""), type="password", key="imap_password")
                port = st.number_input("Port", value=imap_config.get("port", 993), min_value=1, max_value=65535, key="imap_port")

                col1, col2 = st.columns([1,1])
                with col1:
                    if st.button("💾 Lưu", use_container_width=True, type="primary", key="imap_save_btn"):
                        save_imap_config({"host": host, "username": username, "password": password, "port": int(port), "ssl": True})
                        st.toast("Đã lưu IMAP config", icon="✅")
                with col2:
                    if st.button("🧪 Test", use_container_width=True, key="imap_test_btn"):
                        if all([host, username, password]):
                            with st.spinner("Đang kiểm tra..."):
                                success, msg = test_imap_connection(host, username, password, int(port))
                                if success:
                                    st.toast("✅ Kết nối thành công", icon="🎯")
                                else:
                                    st.toast(f"❌ {msg[:50]}", icon="⚠️")
                        else:
                            st.toast("Điền đủ thông tin", icon="⚠️")

            st.divider()
            if st.button("🗑️ Xóa tất cả dữ liệu local", use_container_width=True, type="secondary", key="clear_offline_btn"):
                st.session_state.offline_emails = []
                st.session_state.offline_imap = {}
                st.session_state.offline_ai = {}
                st.toast("Đã xóa dữ liệu offline", icon="🗑️")

# ========== FETCH SECTION ==========
def render_fetch_section():
    st.markdown("### 📥 Lấy Email Mới")
    st.caption("Lấy email từ IMAP server trong khoảng thời gian chỉ định")

    with st.form("fetch_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Từ ngày", value=date.today(), label_visibility="collapsed")
        with col2:
            end_date = st.date_input("Đến ngày", value=date.today(), label_visibility="collapsed")
        with col3:
            mail_type = st.selectbox("Trạng thái", ["ALL", "Chưa đọc", "Đã đọc"], label_visibility="collapsed")

        st.markdown("**🔎 Lọc (tùy chọn)**")
        col_a, col_b = st.columns(2)
        with col_a:
            sender_filter = st.text_input(
                "Lọc người gửi",
                placeholder="alice@example.com, bob@... (phân cách dấu phẩy)",
                label_visibility="collapsed"
            )
        with col_b:
            subject_filter = st.text_input(
                "Lọc chủ đề chứa",
                placeholder="ví dụ: invoice, báo cáo...",
                label_visibility="collapsed"
            )

        submitted = st.form_submit_button("🚀 FETCH", type="primary", use_container_width=True)

        if submitted:
            imap_conf = get_imap_config()
            if not imap_conf or not all([imap_conf.get("host"), imap_conf.get("username"), imap_conf.get("password")]):
                st.error("⚠️ Vui lòng cấu hình IMAP trong sidebar!")
                return

            # Parse filters
            sender_list = [s.strip() for s in sender_filter.split(",") if s.strip()] if sender_filter else None
            subject_kw = subject_filter.strip() if subject_filter else None

            # Store current filters for context report
            st.session_state.current_fetch_filters = {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "read_status": mail_type,
                "sender_filters": sender_list,
                "subject_filter": subject_kw
            }

            status = st.status("⏳ Đang kết nối...", state="running")
            try:
                read_status_map = {"ALL": "ALL", "Chưa đọc": "UNREAD", "Đã đọc": "READ"}
                emails = fetch_emails_by_date(
                    imap_conf["host"],
                    imap_conf["username"],
                    imap_conf["password"],
                    datetime.combine(start_date, datetime.min.time()),
                    datetime.combine(end_date, datetime.max.time()),
                    read_status_map[mail_type],
                    int(imap_conf.get("port", 993)),
                    sender_filters=sender_list,
                    subject_contains=subject_kw
                )
                count = 0
                for mail in emails:
                    if save_email(mail):
                        count += 1
                get_all_emails_cached.clear()
                get_distinct_senders.clear()
                status.update(label=f"✅ Đã lưu {count} email mới!", state="complete")
            except Exception as e:
                status.update(label=f"❌ Lỗi: {str(e)[:100]}", state="error")

# ========== EMAIL CARD ==========
def render_email_card(mail):
    mail_id = mail.get("message_id") or hashlib.md5((mail.get("subject", "") + mail.get("date", "")).encode()).hexdigest()
    is_expanded = st.session_state.expanded_id == mail_id

    sender = mail.get("from", "Unknown")
    subject = mail.get("subject", "(Không tiêu đề)")
    date_str = format_date(mail.get("date", ""))
    has_attach = "📎" if mail.get("has_attachment") else ""

    initials = get_initials(sender)
    color = get_avatar_color(sender)

    # Card container
    card = st.container()
    with card:
        col_avatar, col_info, col_actions = st.columns([0.5, 6, 1.2])

        with col_avatar:
            st.markdown(f"""
            <div style="
                width: 40px; height: 40px; border-radius: 50%;
                background: {color}; display: flex; align-items: center; justify-content: center;
                color: white; font-weight: 700; font-size: 0.875rem;
                box-shadow: var(--shadow-sm);
            ">{initials}</div>
            """, unsafe_allow_html=True)

        with col_info:
            # Highlight sender name
            st.markdown(f"**{sender}**")
            st.markdown(f"<span style='color: var(--text-secondary);'>{subject}</span>{has_attach}", unsafe_allow_html=True)
            st.caption(date_str)

        with col_actions:
            btn_label = "▶" if not is_expanded else "🗙"
            if st.button(btn_label, key=f"btn_{mail_id}", help="Mở/Đóng email", use_container_width=True):
                st.session_state.expanded_id = None if is_expanded else mail_id
                st.rerun()

        if is_expanded:
            st.divider()
            current_mode = st.session_state.view_modes.get(mail_id, "original")

            # Mode buttons
            col_m1, col_m2, col_m3, col_space = st.columns([1,1,1,3])

            with col_m1:
                style = "primary" if current_mode == "original" else "secondary"
                if st.button("📄 Gốc", key=f"orig_{mail_id}", type=style, use_container_width=True):
                    st.session_state.view_modes[mail_id] = "original"
                    st.rerun()

            with col_m2:
                style = "primary" if current_mode == "translate" else "secondary"
                if st.button("🌐 Dịch", key=f"trans_{mail_id}", type=style, use_container_width=True):
                    st.session_state.view_modes[mail_id] = "translate"
                    if mail_id not in st.session_state.translations:
                        with st.spinner("🌐 Đang dịch..."):
                            st.session_state.translations[mail_id] = translate_text_google(mail.get("snippet", ""))
                    st.rerun()

            with col_m3:
                style = "primary" if current_mode == "ai" else "secondary"
                if st.button("🤖 AI", key=f"ai_{mail_id}", type=style, use_container_width=True):
                    st.session_state.view_modes[mail_id] = "ai"
                    if mail_id not in st.session_state.ai_summaries:
                        with st.spinner("🤖 AI đang phân tích..."):
                            st.session_state.ai_summaries[mail_id] = get_gemini_response(mail.get("snippet", ""), "summarize")
                    st.rerun()

            # Content display
            st.markdown('<div class="fade-in">', unsafe_allow_html=True)
            if current_mode == "original":
                st.text_area("", value=mail.get("snippet", ""), height=180, disabled=True, label_visibility="collapsed")
            elif current_mode == "translate":
                content = st.session_state.translations.get(mail_id, "Đang dịch...")
                st.text_area("", value=content, height=180, disabled=True, label_visibility="collapsed")
            elif current_mode == "ai":
                st.info(st.session_state.ai_summaries.get(mail_id, "Đang phân tích..."), icon="🤖")
            st.markdown('</div>', unsafe_allow_html=True)

            # Delete button
            col_del, _ = st.columns([1,5])
            with col_del:
                if st.button("🗑️ Xóa email", key=f"del_{mail_id}", use_container_width=True):
                    delete_email(mail_id)
                    st.session_state.expanded_id = None
                    st.toast("Đã xóa email", icon="🗑️")
                    st.rerun()

    # Card styling via CSS class not directly possible; using markdown wrapper
    # We inject style via the container's markdown
    card.markdown("""<style>.stContainer {background: var(--bg-secondary); border-radius: var(--radius); border: 1px solid var(--border-color); padding: 1rem; margin-bottom: 0.75rem; }</style>""", unsafe_allow_html=True)

# ========== EMAIL LIST ==========
def render_email_list():
    emails = get_all_emails_cached()
    if not emails:
        st.info("📭 Chưa có email nào. Hãy fetch từ IMAP server.", icon="📭")
        return

    # Filter by sender
    all_senders = get_distinct_senders()
    selected_senders = st.multiselect(
        "📌 Lọc theo người gửi",
        options=all_senders,
        default=[],
        help="Chọn một hoặc nhiều người gửi để lọc"
    )

    # Apply filter
    if selected_senders:
        emails = [e for e in emails if e.get("from") in selected_senders]

    emails = sorted(emails, key=lambda x: x.get("date", ""), reverse=True)
    st.markdown(f"### 📨 Danh sách email ({len(emails)})")

    # Show all emails
    for mail in emails:
        render_email_card(mail)
        st.divider()

# ========== MAIN ==========
def main():
    render_sidebar()

    # Header
    st.markdown("""
    <div style="padding: 1.5rem 0 1rem;">
        <h1 style="margin: 0; font-size: 2rem;">Mail Nexus</h1>
        <p style="margin: 0.25rem 0 0; font-size: 1rem; color: var(--text-secondary);">
            Quản lý email IMAP thông minh với AI tích hợp
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    render_fetch_section()
    st.divider()
    render_email_list()

if __name__ == "__main__":
    main()