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

# ========== CẤU HÌNH TRANG ==========
st.set_page_config(
    page_title="Mail Nexus",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== CSS ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
* { font-family: 'Be Vietnam Pro', sans-serif !important; }
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}
::-webkit-scrollbar {width: 6px;}
::-webkit-scrollbar-thumb {background: #cbd5e1; border-radius: 3px;}

.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
}
.stButton > button[kind="primary"] {
    background: #0f172a !important;
    color: white !important;
    border: none !important;
}
.stButton > button:not([kind="primary"]) {
    background: white !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
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

.email-item {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    transition: all 0.2s;
}
.email-item:hover {
    border-color: #94a3b8;
}

.email-sender-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}

.email-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 600;
    font-size: 0.875rem;
    flex-shrink: 0;
}

.email-info {
    flex: 1;
    min-width: 0;
}

.email-name {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.95rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.email-address {
    color: #64748b;
    font-size: 0.8rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.email-subject {
    font-size: 0.9rem;
    color: #334155;
    margin: 0.25rem 0;
}

.email-meta {
    color: #94a3b8;
    font-size: 0.75rem;
}

.email-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
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
        "sidebar_visible": False,
        "email_expanded": None,
        "email_translations": {},
        "email_ai": {},
        "offline_emails": [],
        "offline_config": {"imap": {}, "ai": {"provider": "gemini", "api_key": "", "model": "gemini-2.5-flash"}}
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
            return
        except:
            pass
    st.session_state.offline_config[section].update(data)

def load_cfg(section):
    db = get_db()
    if db:
        try:
            doc = db.collection("config").document(section).get()
            if doc.exists:
                return doc.to_dict()
        except:
            pass
    return st.session_state.offline_config.get(section, {})

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
    if db:
        try:
            for d in db.collection("emails").stream():
                if d.exists:
                    emails.append(d.to_dict())
        except:
            pass
    # Merge offline
    existing_ids = {get_eid(e) for e in emails}
    for off in st.session_state.offline_emails:
        if get_eid(off) not in existing_ids:
            emails.append(off)
    return emails

def delete_email(eid):
    db = get_db()
    if db:
        try:
            db.collection("emails").document(eid).delete()
        except:
            pass
    st.session_state.offline_emails = [e for e in st.session_state.offline_emails if get_eid(e) != eid]

def delete_all_emails():
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
    try:
        text = decode_mime(from_field)
        if "<" in text and ">" in text:
            name = text.split("<")[0].strip().strip('"').strip("'")
            email = text.split("<")[1].split(">")[0].strip()
            return name or email, email
        elif "@" in text:
            return text, text
        return text, ""
    except:
        return str(from_field), ""

def get_initials(name):
    if not name:
        return "?"
    parts = str(name).replace("@", " ").replace(".", " ").split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[0].upper() if name else "?"

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
                    "preview": body[:120].replace("\n", " ").strip()
                })
            except:
                continue
        mail.logout()
    except Exception as e:
        st.error(f"Lỗi IMAP: {e}")
    return emails

# ========== AI ==========
def ai_process(text, mode="summarize"):
    cfg = load_cfg("ai")
    provider = cfg.get("provider", "gemini")
    key = cfg.get("api_key", "")
    
    if not key:
        return "⚠️ Chưa cấu hình API key"
    
    try:
        if provider == "openrouter":
            headers = {
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "https://mail-nexus.streamlit.app",
                "Content-Type": "application/json"
            }
            model = cfg.get("openrouter_model", "openai/gpt-3.5-turbo")
            url = cfg.get("base_url", "https://openrouter.ai/api/v1") + "/chat/completions"
            
            content = f"Tóm tắt email bằng tiếng Việt:\n\n{text[:2000]}" if mode == "summarize" else f"Dịch sang tiếng Việt:\n\n{text[:2000]}"
            
            r = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": content}]}, timeout=30)
            return r.json()["choices"][0]["message"]["content"]
        else:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel(cfg.get("model", "gemini-2.5-flash"))
            
            prompt = f"Tóm tắt email bằng tiếng Việt:\n\n{text[:2000]}" if mode == "summarize" else f"Dịch sang tiếng Việt:\n\n{text[:2000]}"
            return model.generate_content(prompt).text
    except Exception as e:
        return f"❌ Lỗi: {str(e)[:100]}"

def translate(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "vi", "dt": "t", "q": text[:1000]}
        return "".join([item[0] for item in requests.get(url, params=params, timeout=5).json()[0]])
    except:
        return "❌ Dịch thất bại"

def fmt_date(ds):
    try:
        return datetime.fromisoformat(ds.replace('Z', '+00:00')).strftime("%d/%m %H:%M")
    except:
        return ds[:16].replace("T", " ") if ds else ""

# ========== SIDEBAR ==========
if st.session_state.sidebar_visible:
    with st.sidebar:
        st.markdown("## ⚙️ Cài đặt")
        
        db = get_db()
        st.success("🟢 Đã kết nối") if db else st.warning("🟡 Offline")
        
        # IMAP
        st.divider()
        st.markdown("**📧 IMAP**")
        imap = load_cfg("imap")
        h = st.text_input("Máy chủ", value=imap.get("host", ""), placeholder="imap.gmail.com")
        u = st.text_input("Email", value=imap.get("username", ""))
        p = st.text_input("Mật khẩu", value=imap.get("password", ""), type="password")
        
        c1, c2 = st.columns(2)
        if c1.button("💾 Lưu", use_container_width=True):
            save_cfg("imap", {"host": h, "username": u, "password": p, "port": 993})
            st.success("Đã lưu!")
        if c2.button("🧪 Kiểm tra", use_container_width=True) and all([h, u, p]):
            with st.spinner("..."):
                ok, msg = test_imap(h, u, p)
                st.success("✓ OK") if ok else st.error(msg[:50])
        
        # AI
        st.divider()
        st.markdown("**🤖 AI**")
        ai = load_cfg("ai")
        prov = st.selectbox("Nhà cung cấp", ["gemini", "openrouter"], index=0 if ai.get("provider", "gemini") == "gemini" else 1)
        key = st.text_input("API Key", value=ai.get("api_key", ""), type="password")
        
        if prov == "gemini":
            m = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro"])
            if st.button("💾 Lưu AI", use_container_width=True):
                save_cfg("ai", {"provider": prov, "api_key": key, "model": m})
                st.success("Đã lưu!")
        else:
            om = st.text_input("Model", value=ai.get("openrouter_model", "openai/gpt-3.5-turbo"))
            ou = st.text_input("URL", value=ai.get("base_url", "https://openrouter.ai/api/v1"))
            if st.button("💾 Lưu AI", use_container_width=True):
                save_cfg("ai", {"provider": prov, "api_key": key, "openrouter_model": om, "base_url": ou})
                st.success("Đã lưu!")

# ========== MAIN UI ==========
# Header with toggle
c1, c2 = st.columns([0.08, 0.92])
with c1:
    if st.button("☰", key="menu"):
        st.session_state.sidebar_visible = not st.session_state.sidebar_visible
        st.rerun()
with c2:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span style="font-size: 1.75rem;">✉️</span>
        <div>
            <div style="font-size: 1.5rem; font-weight: 700;">Mail Nexus</div>
            <div style="font-size: 0.8rem; color: #64748b;">Trình quản lý email thông minh</div>
        </div>
    </div>""", unsafe_allow_html=True)

# Fetch section
st.markdown("### 📥 Lấy email mới")
col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 2])

with col1:
    d1 = st.date_input("Từ", value=date.today(), label_visibility="collapsed")
with col2:
    d2 = st.date_input("Đến", value=date.today(), label_visibility="collapsed")
with col3:
    t = st.selectbox("Loại", ["TẤT CẢ", "CHƯA ĐỌC", "ĐÃ ĐỌC"], label_visibility="collapsed")
with col4:
    if st.button("🚀 Lấy email", use_container_width=True, type="primary"):
        cfg = load_cfg("imap")
        if not all([cfg.get("host"), cfg.get("username"), cfg.get("password")]):
            st.error("⚠️ Cấu hình IMAP trong ☰")
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
    st.info("📭 Chưa có email")
else:
    # Header with delete all
    h1, h2 = st.columns([6, 1])
    with h1:
        st.markdown(f"### 📨 Hộp thư ({len(emails)})")
    with h2:
        if st.button("🗑️ Xóa tất cả", use_container_width=True):
            if st.checkbox("Xác nhận xóa tất cả?"):
                delete_all_emails()
                st.success("Đã xóa tất cả!")
                st.rerun()
    
    try:
        emails = sorted(emails, key=lambda x: x.get("date", "") or "", reverse=True)
    except:
        pass
    
    for mail in emails:
        eid = get_eid(mail)
        is_exp = st.session_state.email_expanded == eid
        
        # Get sender info with fallback
        sender_name = mail.get("sender_name") or mail.get("from", "Không xác định")
        sender_email = mail.get("sender_email") or ""
        
        # Parse if still have raw from field
        if not sender_email and "from" in mail:
            sender_name, sender_email = parse_sender(mail.get("from", ""))
        
        subject = mail.get("subject", "(Không có tiêu đề)")
        preview = mail.get("preview", "")
        date_str = fmt_date(mail.get("date", ""))
        attach = " 📎" if mail.get("has_attachment") else ""
        
        with st.container():
            st.markdown('<div class="email-item">', unsafe_allow_html=True)
            
            # Sender row with avatar
            st.markdown(f"""
            <div class="email-sender-row">
                <div class="email-avatar">{get_initials(sender_name)}</div>
                <div class="email-info">
                    <div class="email-name">{sender_name}</div>
                    <div class="email-address">{sender_email or "Không có email"}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Subject
            st.markdown(f'<div class="email-subject"><strong>{subject}</strong>{attach}</div>', unsafe_allow_html=True)
            
            # Meta
            st.markdown(f'<div class="email-meta">{date_str} • {preview[:80]}{"..." if len(str(preview)) > 80 else ""}</div>', unsafe_allow_html=True)
            
            # Actions
            c1, c2, c3 = st.columns([1, 1, 4])
            with c1:
                if st.button("Đọc" if not is_exp else "Đóng", key=f"btn_{eid}", use_container_width=True):
                    st.session_state.email_expanded = None if is_exp else eid
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"del_{eid}", help="Xóa"):
                    delete_email(eid)
                    st.success("Đã xóa!")
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Expanded content
            if is_exp:
                body = mail.get("body", "")
                tab1, tab2, tab3 = st.tabs(["📄 Gốc", "🌐 Dịch", "🤖 AI"])
                
                with tab1:
                    st.text_area("", value=body, height=200, disabled=True, label_visibility="collapsed")
                
                with tab2:
                    if st.button("🌐 Dịch", key=f"tr_{eid}"):
                        with st.spinner("..."):
                            st.session_state.email_translations[eid] = translate(body)
                    st.text_area("", value=st.session_state.email_translations.get(eid, "Nhấn để dịch"), height=200, disabled=True, label_visibility="collapsed")
                
                with tab3:
                    if st.button("🤖 AI", key=f"ai_{eid}"):
                        with st.spinner("..."):
                            st.session_state.email_ai[eid] = ai_process(body)
                    st.info(st.session_state.email_ai.get(eid, "Nhấn để tóm tắt"))
