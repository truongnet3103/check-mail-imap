"""
Mail Nexus - Trình Quản Lý Email Thông Minh
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
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CSS ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
* { font-family: 'Be Vietnam Pro', sans-serif !important; }
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}

/* Custom Expander Styling */
.streamlit-expander {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    margin-bottom: 0.5rem !important;
    overflow: hidden !important;
}

.streamlit-expanderHeader {
    background: white !important;
    padding: 1rem 1.25rem !important;
    font-size: 0.9rem !important;
    color: #334155 !important;
    border-bottom: 1px solid transparent !important;
    transition: background 0.2s !important;
}

.streamlit-expanderHeader:hover {
    background: #f8fafc !important;
}

/* Animation when deleting */
@keyframes fadeOutRight {
    from { opacity: 1; transform: translateX(0); }
    to { opacity: 0; transform: translateX(20px); }
}

.deleting {
    animation: fadeOutRight 0.3s ease forwards;
}

.stButton > button {
    border-radius: 6px !important;
    font-weight: 500 !important;
}
.stButton > button[kind="primary"] {
    background: #0f172a !important;
    color: white !important;
    border: none !important;
}
.stButton > button:not([kind="primary"]) {
    background: transparent !important;
    color: #64748b !important;
    border: none !important;
}

.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #e2e8f0;
}
.stTabs [data-baseweb="tab"] {
    padding: 0.75rem 1.25rem;
    font-size: 0.875rem;
    color: #64748b;
}
.stTabs [aria-selected="true"] {
    color: #0f172a !important;
    border-bottom: 2px solid #0f172a !important;
}

.delete-btn button {
    color: #ef4444 !important;
    font-size: 0.8rem !important;
    padding: 4px 12px !important;
    border: 1px solid #ef4444 !important;
    border-radius: 4px !important;
    transition: all 0.2s !important;
}
.delete-btn button:hover {
    background: #ef4444 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ========== IMPORTS ==========
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_OK = True
except:
    FIREBASE_OK = False

# ========== STATE ==========
def init():
    defaults = {
        "translations": {},
        "ai_results": {},
        "offline_emails": [],
        "config": {"imap": {}, "ai": {"provider": "gemini", "api_key": ""}},
        "deleting_id": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# ========== DATABASE ==========
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

def get_eid(data):
    raw = data.get("message_id") or (data.get("subject", "") + str(data.get("date", "")))
    return hashlib.md5(raw.encode()).hexdigest()

def save_cfg(section, data):
    db = get_db()
    if db:
        try:
            db.collection("config").document(section).set(data)
        except:
            pass
    st.session_state.config[section].update(data)

def load_cfg(section):
    db = get_db()
    if db:
        try:
            doc = db.collection("config").document(section).get()
            if doc.exists:
                return doc.to_dict()
        except:
            pass
    return st.session_state.config.get(section, {})

def save_email(data):
    db = get_db()
    eid = get_eid(data)
    if db:
        try:
            db.collection("emails").document(eid).set(data)
        except:
            pass
    existing = [e for e in st.session_state.offline_emails if get_eid(e) != eid]
    existing.append(data)
    st.session_state.offline_emails = existing

def get_emails():
    db = get_db()
    emails = []
    seen = set()
    
    if db:
        try:
            for d in db.collection("emails").stream():
                if d.exists:
                    data = d.to_dict()
                    if data:
                        eid = get_eid(data)
                        if eid not in seen:
                            emails.append(data)
                            seen.add(eid)
        except:
            pass
    
    for off in st.session_state.offline_emails:
        eid = get_eid(off)
        if eid not in seen:
            emails.append(off)
            seen.add(eid)
    
    return emails

def delete_email(eid):
    db = get_db()
    if db:
        try:
            db.collection("emails").document(eid).delete()
        except:
            pass
    st.session_state.offline_emails = [e for e in st.session_state.offline_emails if get_eid(e) != eid]

def delete_all():
    db = get_db()
    if db:
        try:
            for d in db.collection("emails").stream():
                d.reference.delete()
        except:
            pass
    st.session_state.offline_emails = []

# ========== IMAP ==========
def decode_mime(s):
    if not s:
        return ""
    try:
        parts = decode_header(s)
        result = ""
        for p in parts:
            if isinstance(p[0], bytes):
                result += p[0].decode(p[1] or "utf-8", errors="ignore")
            else:
                result += str(p[0])
        return result
    except:
        return str(s)

def parse_sender(from_field):
    if not from_field:
        return "Không xác định", ""
    text = decode_mime(from_field)
    if "<" in text and ">" in text:
        name = text.split("<")[0].strip().strip('"')
        email = text.split("<")[1].split(">")[0].strip()
        return name or email, email
    elif "@" in text:
        return text, text
    return text, ""

def test_imap(host, user, pwd, port=993):
    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        mail.login(user, pwd)
        mail.logout()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def fetch_emails(host, user, pwd, start, end, status="ALL", port=993):
    emails = []
    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        mail.login(user, pwd)
        mail.select("INBOX")
        
        crit = []
        if status == "UNREAD":
            crit.append("UNSEEN")
        elif status == "READ":
            crit.append("SEEN")
        crit.extend([f'SINCE "{start.strftime("%d-%b-%Y")}"', f'BEFORE "{(end + timedelta(days=1)).strftime("%d-%b-%Y")}"'])
        
        _, msgs = mail.search(None, " ".join(crit))
        
        for eid in reversed(msgs[0].split()[:50]):
            try:
                _, data = mail.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                
                subject = decode_mime(msg.get("Subject", ""))
                name, email_addr = parse_sender(msg.get("From", ""))
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
                            p = part.get_payload(decode=True)
                            if p:
                                body = p.decode(errors="ignore")
                                break
                else:
                    p = msg.get_payload(decode=True)
                    if p:
                        body = p.decode(errors="ignore")
                
                emails.append({
                    "message_id": msg_id or "",
                    "subject": subject or "(Không có tiêu đề)",
                    "sender_name": name,
                    "sender_email": email_addr,
                    "date": msg_date.isoformat() if msg_date else "",
                    "has_attachment": has_attach,
                    "body": body[:2000],
                })
            except:
                continue
        mail.logout()
    except Exception as e:
        st.error(f"Lỗi IMAP: {e}")
    return emails

# ========== AI ==========
def ai_process(text):
    cfg = load_cfg("ai")
    key = cfg.get("api_key", "")
    if not key:
        return "⚠️ Chưa cấu hình API key"
    
    try:
        if cfg.get("provider") == "openrouter":
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            r = requests.post(
                cfg.get("base_url", "https://openrouter.ai/api/v1") + "/chat/completions",
                headers=headers,
                json={"model": cfg.get("openrouter_model", "openai/gpt-3.5-turbo"),
                      "messages": [{"role": "user", "content": f"Tóm tắt email:\n\n{text[:2000]}"}]},
                timeout=30
            )
            return r.json()["choices"][0]["message"]["content"]
        else:
            import google.generativeai as genai
            genai.configure(api_key=key)
            return genai.GenerativeModel(cfg.get("model", "gemini-2.5-flash")).generate_content(f"Tóm tắt email:\n\n{text[:2000]}").text
    except Exception as e:
        return f"❌ Lỗi: {str(e)[:100]}"

def translate(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        r = requests.get(url, params={"client": "gtx", "sl": "auto", "tl": "vi", "dt": "t", "q": text[:1000]}, timeout=5)
        return "".join([item[0] for item in r.json()[0]])
    except:
        return "❌ Dịch thất bại"

def fmt_date(ds):
    try:
        dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
        return dt.strftime("%H:%M - %d/%m/%Y")
    except:
        return ds[:16].replace("T", " ") if ds else ""

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("## ⚙️ Cài đặt")
    
    db = get_db()
    st.success("🟢 Đã kết nối") if db else st.warning("🟡 Offline")
    
    st.divider()
    st.markdown("**📧 IMAP**")
    imap = load_cfg("imap")
    h = st.text_input("Máy chủ", value=imap.get("host", ""), placeholder="imap.gmail.com")
    u = st.text_input("Email", value=imap.get("username", ""))
    p = st.text_input("Mật khẩu", value=imap.get("password", ""), type="password")
    
    c1, c2 = st.columns(2)
    if c1.button("💾 Lưu", use_container_width=True):
        save_cfg("imap", {"host": h, "username": u, "password": p})
        st.success("Đã lưu!")
    if c2.button("🧪 Kiểm tra", use_container_width=True) and all([h, u, p]):
        with st.spinner("..."):
            ok, msg = test_imap(h, u, p)
            st.success("✓ OK") if ok else st.error(msg[:50])
    
    st.divider()
    st.markdown("**🤖 AI**")
    ai = load_cfg("ai")
    prov = st.selectbox("Nhà cung cấp", ["gemini", "openrouter"], index=0 if ai.get("provider") == "gemini" else 1)
    key = st.text_input("API Key", value=ai.get("api_key", ""), type="password")
    
    if prov == "gemini":
        m = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro"])
        if st.button("💾 Lưu AI"):
            save_cfg("ai", {"provider": prov, "api_key": key, "model": m})
            st.success("Đã lưu!")
    else:
        om = st.text_input("Model", value=ai.get("openrouter_model", "openai/gpt-3.5-turbo"))
        ou = st.text_input("URL", value=ai.get("base_url", "https://openrouter.ai/api/v1"))
        if st.button("💾 Lưu AI"):
            save_cfg("ai", {"provider": prov, "api_key": key, "openrouter_model": om, "base_url": ou})
            st.success("Đã lưu!")

# ========== MAIN ==========
st.markdown("# 📧 Hộp thư đến")

# Fetch
cols = st.columns([1.5, 1.5, 1.5, 2])
with cols[0]:
    d1 = st.date_input("Từ", value=date.today(), label_visibility="collapsed")
with cols[1]:
    d2 = st.date_input("Đến", value=date.today(), label_visibility="collapsed")
with cols[2]:
    t = st.selectbox("Loại", ["TẤT CẢ", "CHƯA ĐỌC", "ĐÃ ĐỌC"], label_visibility="collapsed")
with cols[3]:
    if st.button("🚀 Lấy email", use_container_width=True, type="primary"):
        cfg = load_cfg("imap")
        if not all([cfg.get("host"), cfg.get("username"), cfg.get("password")]):
            st.error("⚠️ Cấu hình IMAP trong sidebar")
        else:
            with st.spinner("Đang lấy..."):
                map_t = {"TẤT CẢ": "ALL", "CHƯA ĐỌC": "UNREAD", "ĐÃ ĐỌC": "READ"}
                new = fetch_emails(cfg["host"], cfg["username"], cfg["password"],
                                   datetime.combine(d1, datetime.min.time()),
                                   datetime.combine(d2, datetime.max.time()),
                                   map_t[t])
                for e in new:
                    save_email(e)
                st.success(f"✓ {len(new)} email")
                st.rerun()

st.divider()

# Email list
emails = get_emails()

if not emails:
    st.info("📭 Hộp thư trống")
else:
    # Header
    h1, h2 = st.columns([6, 1])
    with h1:
        st.markdown(f"**{len(emails)} email**")
    with h2:
        if st.button("🗑️ Xóa tất cả"):
            st.session_state.confirm_delete = True
    
    if st.session_state.get("confirm_delete"):
        st.warning("Xóa tất cả email?")
        c1, c2 = st.columns(2)
        if c1.button("✓ Xác nhận"):
            delete_all()
            st.session_state.confirm_delete = False
            st.success("Đã xóa!")
            st.rerun()
        if c2.button("✗ Hủy"):
            st.session_state.confirm_delete = False
            st.rerun()
    
    # Sort
    try:
        emails = sorted(emails, key=lambda x: x.get("date", "") or "", reverse=True)
    except:
        pass
    
    # Emails as expanders
    for mail in emails:
        eid = get_eid(mail)
        
        sender = mail.get("sender_name") or parse_sender(mail.get("from", ""))[0]
        subject = mail.get("subject", "(Không có tiêu đề)")
        attach = " 📎" if mail.get("has_attachment") else ""
        date_str = fmt_date(mail.get("date", ""))
        
        # Expander label: Sender | Subject | Attach | Date
        label = f"**{sender}** | {subject}{attach} | *{date_str}*"
        
        with st.expander(label, expanded=False):
            # Delete button inside expander
            c1, c2 = st.columns([6, 1])
            with c2:
                if st.button("🗑️ Xóa", key=f"del_{eid}"):
                    delete_email(eid)
                    st.success("Đã xóa!")
                    st.rerun()
            
            # Sender info
            sender_email = mail.get("sender_email", "")
            st.markdown(f"**Từ:** {sender} <{sender_email}>" if sender_email else f"**Từ:** {sender}")
            st.caption(date_str)
            st.divider()
            
            # Content tabs
            body = mail.get("body", "")
            tab1, tab2, tab3 = st.tabs(["📄 Nội dung", "🌐 Dịch", "🤖 AI"])
            
            with tab1:
                st.markdown(f'<div style="color: #334155; line-height: 1.7;">{body.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            
            with tab2:
                if st.button("🌐 Dịch sang tiếng Việt", key=f"tr_{eid}"):
                    with st.spinner("Đang dịch..."):
                        st.session_state.translations[eid] = translate(body)
                result = st.session_state.translations.get(eid, "Nhấn nút để dịch email")
                st.markdown(f'<div style="color: #334155; line-height: 1.7;">{result.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            
            with tab3:
                if st.button("🤖 Tóm tắt AI", key=f"ai_{eid}"):
                    with st.spinner("AI đang phân tích..."):
                        st.session_state.ai_results[eid] = ai_process(body)
                st.info(st.session_state.ai_results.get(eid, "Nhấn nút để AI tóm tắt"))
