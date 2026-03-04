"""
Mail Nexus - Trình Quản Lý Email Thông Minh
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

# ========== CẤU HÌNH TRANG ==========
st.set_page_config(
    page_title="Mail Nexus",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CSS TÙY CHỈNH ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');

* { font-family: 'Be Vietnam Pro', sans-serif !important; }

#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}

::-webkit-scrollbar {width: 6px; height: 6px;}
::-webkit-scrollbar-track {background: transparent;}
::-webkit-scrollbar-thumb {background: #cbd5e1; border-radius: 3px;}

.block-container {
    max-width: 1100px;
    padding: 1rem 1.5rem !important;
}

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

.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #e2e8f0;
}

.stTabs [data-baseweb="tab"] {
    padding: 0.75rem 1.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #64748b;
}

.stTabs [aria-selected="true"] {
    color: #0f172a !important;
    border-bottom: 2px solid #0f172a !important;
}

.email-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
}

.email-card:hover {
    border-color: #cbd5e1;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
</style>
""", unsafe_allow_html=True)

# ========== IMPORTS TÙY CHỌN ==========
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_OK = True
except:
    FIREBASE_OK = False

# ========== KHỞI TẠO SESSION STATE ==========
def init_state():
    defaults = {
        "email_mo_rong_id": None,
        "email_dich": {},
        "email_ai": {},
        "email_offline": [],
        "cau_hinh_offline": {
            "imap": {},
            "ai": {"nha_cung_cap": "gemini", "api_key": "", "model": "gemini-2.5-flash", "openrouter_model": "", "base_url": ""}
        }
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ========== LAYER DATABASE ==========
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
    except Exception as e:
        st.error(f"DB Error: {e}")
        return None

def get_email_id(email_data):
    """Tạo ID duy nhất cho email"""
    raw = email_data.get("message_id") or (email_data.get("subject", "") + str(email_data.get("date", "")))
    return hashlib.md5(raw.encode()).hexdigest()

def luu_cau_hinh(section, data):
    db = get_db()
    if db:
        try:
            db.collection("config").document(section).set(data)
            return True
        except Exception as e:
            st.error(f"Lỗi lưu cấu hình: {e}")
    st.session_state.cau_hinh_offline[section].update(data)
    return True

def doc_cau_hinh(section):
    db = get_db()
    if db:
        try:
            doc = db.collection("config").document(section).get()
            if doc.exists:
                return doc.to_dict()
        except:
            pass
    return st.session_state.cau_hinh_offline.get(section, {})

def luu_email(email_data):
    db = get_db()
    eid = get_email_id(email_data)
    
    if db:
        try:
            db.collection("emails").document(eid).set(email_data)
        except Exception as e:
            st.error(f"Lỗi lưu email: {e}")
    
    # Lưu offline
    existing_ids = [get_email_id(e) for e in st.session_state.email_offline]
    if eid not in existing_ids:
        st.session_state.email_offline.append(email_data)

def doc_emails():
    db = get_db()
    emails = []
    if db:
        try:
            docs = db.collection("emails").stream()
            for d in docs:
                data = d.to_dict()
                if data:
                    emails.append(data)
        except Exception as e:
            st.error(f"Lỗi đọc emails: {e}")
    
    # Merge với offline
    offline_ids = [get_email_id(e) for e in emails]
    for off in st.session_state.email_offline:
        if get_email_id(off) not in offline_ids:
            emails.append(off)
    
    return emails

def xoa_email(eid):
    db = get_db()
    if db:
        try:
            db.collection("emails").document(eid).delete()
        except:
            pass
    
    st.session_state.email_offline = [
        e for e in st.session_state.email_offline
        if get_email_id(e) != eid
    ]

# ========== DỊCH VỤ IMAP ==========
def kiem_tra_imap(host, user, pwd, port=993):
    try:
        ctx = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
        mail.login(user, pwd)
        mail.logout()
        return True, "Đã kết nối"
    except Exception as e:
        return False, str(e)

def giai_ma_mime(s):
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

def phan_tich_nguoi_gui(from_field):
    if not from_field:
        return "Không xác định", ""
    
    try:
        from_field = giai_ma_mime(from_field)
        
        if "<" in from_field and ">" in from_field:
            parts = from_field.split("<")
            ten = parts[0].strip().strip('"').strip("'")
            email = parts[1].split(">")[0].strip()
            return ten or email, email
        elif "@" in from_field:
            return from_field, from_field
        else:
            return from_field, ""
    except:
        return str(from_field), ""

def lay_emails(host, user, pwd, start, end, status="ALL", port=993):
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
        
        for eid in reversed(msgs[0].split()[:50]):
            try:
                _, data = mail.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                
                subject = giai_ma_mime(msg.get("Subject", ""))
                from_field = msg.get("From", "")
                sender_name, sender_email = phan_tich_nguoi_gui(from_field)
                
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
                
                email_data = {
                    "message_id": msg_id or "",
                    "subject": subject or "(Không có tiêu đề)",
                    "from": from_field,
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "date": msg_date.isoformat() if msg_date else "",
                    "has_attachment": has_attach,
                    "body": body[:2000],
                    "preview": body[:150].replace("\n", " ").strip()
                }
                emails.append(email_data)
            except Exception as e:
                continue
        
        mail.logout()
    except Exception as e:
        st.error(f"Lỗi IMAP: {e}")
    return emails

# ========== DỊCH VỤ AI ==========
def xu_ly_ai(text, mode="summarize"):
    cfg = doc_cau_hinh("ai")
    nha_cung_cap = cfg.get("nha_cung_cap", "gemini")
    api_key = cfg.get("api_key", "")
    
    if not api_key:
        return "⚠️ Chưa cấu hình API key"
    
    try:
        if nha_cung_cap == "openrouter":
            model = cfg.get("openrouter_model", "openai/gpt-3.5-turbo")
            base_url = cfg.get("base_url", "https://openrouter.ai/api/v1")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://mail-nexus.streamlit.app",
                "X-Title": "Mail Nexus",
                "Content-Type": "application/json"
            }
            
            if mode == "summarize":
                content = f"Tóm tắt email sau bằng tiếng Việt, ngắn gọn:\n\n{text[:2000]}"
            else:
                content = f"Dịch sang tiếng Việt:\n\n{text[:2000]}"
            
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": content}]
                },
                timeout=30
            )
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            try:
                import google.generativeai as genai
            except:
                return "⚠️ Chưa cài google-generativeai"
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(cfg.get("model", "gemini-2.5-flash"))
            
            if mode == "summarize":
                prompt = f"Tóm tắt email sau bằng tiếng Việt, ngắn gọn:\n\n{text[:2000]}\n\nTóm tắt:"
            else:
                prompt = f"Dịch sang tiếng Việt:\n\n{text[:2000]}\n\nBản dịch:"
            
            resp = model.generate_content(prompt)
            return resp.text
    except Exception as e:
        return f"❌ Lỗi AI: {str(e)[:150]}"

def dich_google(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "auto", "tl": "vi", "dt": "t", "q": text[:1000]}
        r = requests.get(url, params=params, timeout=5)
        return "".join([item[0] for item in r.json()[0]])
    except:
        return "❌ Dịch thất bại"

# ========== UI HELPERS ==========
def dinh_dang_ngay(ds):
    try:
        dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
        return dt.strftime("%d/%m %H:%M")
    except:
        return ds[:16].replace("T", " ") if ds else ""

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("## ⚙️ Cài đặt")
    
    db = get_db()
    if db:
        st.success("🟢 Đã kết nối")
    else:
        st.warning("🟡 Chế độ Offline")
    
    st.divider()
    
    # Cấu hình IMAP
    st.markdown("**📧 Cấu hình IMAP**")
    imap_cfg = doc_cau_hinh("imap")
    
    imap_host = st.text_input("Máy chủ", value=imap_cfg.get("host", ""), placeholder="imap.gmail.com", key="imap_host")
    imap_user = st.text_input("Email", value=imap_cfg.get("username", ""), key="imap_user")
    imap_pass = st.text_input("Mật khẩu", value=imap_cfg.get("password", ""), type="password", key="imap_pass")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Lưu", use_container_width=True):
            luu_cau_hinh("imap", {"host": imap_host, "username": imap_user, "password": imap_pass, "port": 993})
            st.success("Đã lưu!")
    with col2:
        if st.button("🧪 Kiểm tra", use_container_width=True):
            if all([imap_host, imap_user, imap_pass]):
                with st.spinner("Đang kiểm tra..."):
                    ok, msg = kiem_tra_imap(imap_host, imap_user, imap_pass)
                    st.success("✓ Kết nối thành công") if ok else st.error(msg[:50])
    
    st.divider()
    
    # Cấu hình AI
    st.markdown("**🤖 Cấu hình AI**")
    ai_cfg = doc_cau_hinh("ai")
    
    nha_cung_cap = st.selectbox(
        "Nhà cung cấp",
        ["gemini", "openrouter"],
        index=0 if ai_cfg.get("nha_cung_cap", "gemini") == "gemini" else 1
    )
    
    api_key = st.text_input("API Key", value=ai_cfg.get("api_key", ""), type="password")
    
    if nha_cung_cap == "gemini":
        model = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"])
        if st.button("💾 Lưu AI", use_container_width=True):
            luu_cau_hinh("ai", {"nha_cung_cap": nha_cung_cap, "api_key": api_key, "model": model})
            st.success("Đã lưu!")
    else:
        or_model = st.text_input("Model", value=ai_cfg.get("openrouter_model", "openai/gpt-3.5-turbo"))
        or_url = st.text_input("API URL", value=ai_cfg.get("base_url", "https://openrouter.ai/api/v1"))
        if st.button("💾 Lưu AI", use_container_width=True):
            luu_cau_hinh("ai", {"nha_cung_cap": nha_cung_cap, "api_key": api_key, "openrouter_model": or_model, "base_url": or_url})
            st.success("Đã lưu!")

# ========== GIAO DIỆN CHÍNH ==========
# Header
st.markdown("""
<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem;">
    <span style="font-size: 2rem;">✉️</span>
    <div>
        <div style="font-size: 1.75rem; font-weight: 700; color: #0f172a;">Mail Nexus</div>
        <div style="font-size: 0.875rem; color: #64748b;">Trình quản lý email thông minh</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Phần lấy email
st.markdown("### 📥 Lấy email mới")

col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 2])

with col1:
    tu_ngay = st.date_input("Từ ngày", value=date.today(), label_visibility="collapsed")
with col2:
    den_ngay = st.date_input("Đến ngày", value=date.today(), label_visibility="collapsed")
with col3:
    loai_mail = st.selectbox("Loại", ["TẤT CẢ", "CHƯA ĐỌC", "ĐÃ ĐỌC"], label_visibility="collapsed")
with col4:
    if st.button("🚀 Lấy email", use_container_width=True, type="primary"):
        cfg = doc_cau_hinh("imap")
        if not all([cfg.get("host"), cfg.get("username"), cfg.get("password")]):
            st.error("⚠️ Vui lòng cấu hình IMAP trong sidebar")
        else:
            with st.spinner("Đang kết nối..."):
                map_type = {"TẤT CẢ": "ALL", "CHƯA ĐỌC": "UNREAD", "ĐÃ ĐỌC": "READ"}
                emails_moi = lay_emails(
                    cfg["host"], cfg["username"], cfg["password"],
                    datetime.combine(tu_ngay, datetime.min.time()),
                    datetime.combine(den_ngay, datetime.max.time()),
                    map_type[loai_mail]
                )
                for e in emails_moi:
                    luu_email(e)
                st.success(f"✓ Đã lấy {len(emails_moi)} email")
                st.rerun()

st.divider()

# Danh sách email
emails = doc_emails()

if not emails:
    st.info("📭 Chưa có email. Hãy cấu hình IMAP và lấy email mới.")
else:
    st.markdown(f"### 📨 Hộp thư ({len(emails)})")
    
    # Sắp xếp theo ngày giảm dần
    try:
        emails = sorted(emails, key=lambda x: x.get("date", "") or "", reverse=True)
    except:
        pass
    
    for mail in emails:
        eid = get_email_id(mail)
        is_expanded = st.session_state.email_mo_rong_id == eid
        
        # Card email
        with st.container():
            st.markdown('<div class="email-card">', unsafe_allow_html=True)
            
            # Row 1: Tiêu đề + Nút
            cols = st.columns([5, 1.2, 0.8])
            
            with cols[0]:
                tieu_de = mail.get("subject") or mail.get("tieu_de") or "(Không có tiêu đề)"
                dinh_kem = " 📎" if (mail.get("has_attachment") or mail.get("co_dinh_kem")) else ""
                st.markdown(f"**{tieu_de}**{dinh_kem}")
            
            with cols[1]:
                btn_label = "Đóng" if is_expanded else "Đọc"
                if st.button(btn_label, key=f"doc_{eid}", use_container_width=True):
                    st.session_state.email_mo_rong_id = None if is_expanded else eid
                    st.rerun()
            
            with cols[2]:
                if st.button("🗑️", key=f"xoa_{eid}", help="Xóa email"):
                    xoa_email(eid)
                    st.success("Đã xóa!")
                    st.rerun()
            
            # Row 2: Ngườ gửi
            ten_nguoi_gui = mail.get("sender_name") or mail.get("ten_nguoi_gui") or "Không xác định"
            email_nguoi_gui = mail.get("sender_email") or mail.get("email_nguoi_gui") or ""
            st.markdown(f"<span style='color: #64748b;'>Từ:</span> **{ten_nguoi_gui}** <span style='color: #94a3b8;'>({email_nguoi_gui})</span>", unsafe_allow_html=True)
            
            # Row 3: Ngày + preview
            ngay = dinh_dang_ngay(mail.get("date") or mail.get("ngay", ""))
            preview = mail.get("preview") or mail.get("xem_truoc", "")
            st.markdown(f"<span style='color: #94a3b8; font-size: 0.8rem;'>{ngay} • {preview[:100]}{'...' if len(str(preview)) > 100 else ''}</span>", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Nội dung mở rộng
            if is_expanded:
                noi_dung = mail.get("body") or mail.get("noi_dung", "")
                
                tab_goc, tab_dich, tab_ai = st.tabs(["📄 Nội dung gốc", "🌐 Dịch", "🤖 AI"])
                
                with tab_goc:
                    st.text_area("", value=noi_dung, height=250, disabled=True, label_visibility="collapsed")
                
                with tab_dich:
                    if st.button("🌐 Dịch sang tiếng Việt", key=f"btn_dich_{eid}"):
                        with st.spinner("Đang dịch..."):
                            st.session_state.email_dich[eid] = dich_google(noi_dung)
                    
                    da_dich = st.session_state.email_dich.get(eid, "Nhấn nút để dịch email")
                    st.text_area("", value=da_dich, height=250, disabled=True, label_visibility="collapsed")
                
                with tab_ai:
                    if st.button("🤖 Tóm tắt AI", key=f"btn_ai_{eid}"):
                        with st.spinner("AI đang phân tích..."):
                            st.session_state.email_ai[eid] = xu_ly_ai(noi_dung, "summarize")
                    
                    ket_qua_ai = st.session_state.email_ai.get(eid, "Nhấn nút để AI tóm tắt")
                    st.info(ket_qua_ai)
