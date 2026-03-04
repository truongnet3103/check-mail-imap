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
    initial_sidebar_state="collapsed"
)

# ========== CSS TÙY CHỈNH ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');

* { font-family: 'Be Vietnam Pro', sans-serif !important; }

/* Ẩn menu mặc định */
#MainMenu, header, .stDeployButton, [data-testid="stStatusWidget"] {display: none !important;}

/* Scrollbar */
::-webkit-scrollbar {width: 6px; height: 6px;}
::-webkit-scrollbar-track {background: transparent;}
::-webkit-scrollbar-thumb {background: #cbd5e1; border-radius: 3px;}

/* Layout chính */
.block-container {
    max-width: 1000px;
    padding: 5rem 1.5rem 1.5rem !important;
}

/* Nút */
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
    border-color: #94a3b8 !important;
    background: #f8fafc !important;
}

/* Input */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    font-size: 0.875rem !important;
}

.stTextInput > div > div > input:focus {
    border-color: #0f172a !important;
    box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.08) !important;
}

/* Sidebar */
.css-1d391kg, [data-testid="stSidebar"] {
    background: white !important;
    border-right: 1px solid #e2e8f0 !important;
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
}

.stTabs [aria-selected="true"] {
    color: #0f172a !important;
    border-bottom: 2px solid #0f172a !important;
}

/* Thông báo */
.stSuccess {
    background: #dcfce7 !important;
    border: 1px solid #86efac !important;
    color: #166534 !important;
    border-radius: 8px !important;
}

.stError {
    background: #fee2e2 !important;
    border: 1px solid #fca5a5 !important;
    color: #991b1b !important;
    border-radius: 8px !important;
}

.stInfo {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    color: #475569 !important;
    border-radius: 8px !important;
}

.stWarning {
    background: #fef3c7 !important;
    border: 1px solid #fcd34d !important;
    color: #92400e !important;
    border-radius: 8px !important;
}

/* Expander */
.streamlit-expander {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
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
        "menu_open": False,
        "email_mo_rong_id": None,
        "email_dich": {},
        "email_ai": {},
        "email_offline": [],
        "cau_hinh_offline": {
            "imap": {"host": "", "username": "", "password": ""},
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
    except:
        return None

def luu_cau_hinh(section, data):
    db = get_db()
    if db:
        try:
            db.collection("config").document(section).set(data)
            return
        except:
            pass
    st.session_state.cau_hinh_offline[section].update(data)

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
    eid = email_data.get("message_id") or hashlib.md5(
        (email_data.get("tieu_de", "") + str(email_data.get("ngay", ""))).encode()
    ).hexdigest()
    
    if db:
        try:
            db.collection("emails").document(eid).set(email_data)
            return
        except:
            pass
    
    existing = [e for e in st.session_state.email_offline
                if (e.get("message_id") or hashlib.md5((e.get("tieu_de", "") + str(e.get("ngay", ""))).encode()).hexdigest()) != eid]
    existing.append(email_data)
    st.session_state.email_offline = existing

def doc_emails():
    db = get_db()
    if db:
        try:
            return [d.to_dict() for d in db.collection("emails").stream()]
        except:
            pass
    return st.session_state.email_offline

def xoa_email(eid):
    db = get_db()
    if db:
        try:
            db.collection("emails").document(eid).delete()
        except:
            pass
    st.session_state.email_offline = [
        e for e in st.session_state.email_offline
        if (e.get("message_id") or hashlib.md5((e.get("tieu_de", "") + str(e.get("ngay", ""))).encode()).hexdigest()) != eid
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
        return "".join([
            p[0].decode(p[1] or "utf-8", errors="ignore") if isinstance(p[0], bytes) else p[0]
            for p in parts
        ])
    except:
        return s

def phan_tich_nguoi_gui(from_field):
    """Tách tên và email từ trường From"""
    if not from_field:
        return "Không xác định", ""
    
    from_field = giai_ma_mime(from_field)
    
    if "<" in from_field and ">" in from_field:
        ten = from_field.split("<")[0].strip().strip('"')
        email_addr = from_field.split("<")[1].split(">")[0].strip()
        return ten or email_addr, email_addr
    elif "@" in from_field:
        return from_field, from_field
    else:
        return from_field, ""

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
                
                tieu_de = giai_ma_mime(msg.get("Subject", ""))
                from_field = msg.get("From", "")
                ten_nguoi_gui, email_nguoi_gui = phan_tich_nguoi_gui(from_field)
                
                msg_id = msg.get("Message-ID", "")
                date_raw = msg.get("Date")
                
                try:
                    msg_date = parsedate_to_datetime(date_raw) if date_raw else None
                except:
                    msg_date = None
                
                co_dinh_kem = any(
                    part.get("Content-Disposition") and "attachment" in part.get("Content-Disposition", "").lower()
                    for part in msg.walk()
                )
                
                noi_dung = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                noi_dung = payload.decode(errors="ignore")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        noi_dung = payload.decode(errors="ignore")
                
                emails.append({
                    "message_id": msg_id,
                    "tieu_de": tieu_de or "(Không có tiêu đề)",
                    "ten_nguoi_gui": ten_nguoi_gui,
                    "email_nguoi_gui": email_nguoi_gui,
                    "ngay": msg_date.isoformat() if msg_date else "",
                    "co_dinh_kem": co_dinh_kem,
                    "noi_dung": noi_dung[:2000],
                    "xem_truoc": noi_dung[:150].replace("\n", " ").strip()
                })
            except:
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
                "X-Title": "Mail Nexus"
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
            return resp.json()["choices"][0]["message"]["content"]
            
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
def hien_sidebar():
    with st.sidebar:
        # Trạng thái
        db = get_db()
        if db:
            st.success("🟢 Đã kết nối Database")
        else:
            st.warning("🟡 Chế độ Offline")
        
        st.divider()
        
        # Cấu hình IMAP
        st.markdown("**📧 Cấu hình IMAP**")
        imap_cfg = doc_cau_hinh("imap")
        
        imap_host = st.text_input("Máy chủ", value=imap_cfg.get("host", ""), placeholder="imap.gmail.com")
        imap_user = st.text_input("Email", value=imap_cfg.get("username", ""))
        imap_pass = st.text_input("Mật khẩu", value=imap_cfg.get("password", ""), type="password")
        
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
            model = st.selectbox(
                "Model",
                ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
                index=0
            )
            if st.button("💾 Lưu cấu hình AI", use_container_width=True):
                luu_cau_hinh("ai", {"nha_cung_cap": nha_cung_cap, "api_key": api_key, "model": model})
                st.success("Đã lưu!")
        else:
            openrouter_model = st.text_input(
                "Model OpenRouter",
                value=ai_cfg.get("openrouter_model", "openai/gpt-3.5-turbo"),
                placeholder="openai/gpt-3.5-turbo"
            )
            base_url = st.text_input(
                "URL API",
                value=ai_cfg.get("base_url", "https://openrouter.ai/api/v1"),
                placeholder="https://openrouter.ai/api/v1"
            )
            if st.button("💾 Lưu cấu hình AI", use_container_width=True):
                luu_cau_hinh("ai", {
                    "nha_cung_cap": nha_cung_cap,
                    "api_key": api_key,
                    "openrouter_model": openrouter_model,
                    "base_url": base_url
                })
                st.success("Đã lưu!")

# ========== GIAO DIỆN CHÍNH ==========
# Header với nút menu
col_menu, col_brand = st.columns([0.08, 0.92])

with col_menu:
    if st.button("☰", key="nut_menu", help="Mở/đóng cài đặt"):
        st.session_state.menu_open = not st.session_state.menu_open
        st.rerun()

with col_brand:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 0.75rem; padding-top: 0.5rem;">
        <span style="font-size: 1.75rem;">✉️</span>
        <div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #0f172a;">Mail Nexus</div>
            <div style="font-size: 0.8rem; color: #64748b;">Trình quản lý email thông minh</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Hiện sidebar nếu được bật
if st.session_state.menu_open:
    hien_sidebar()

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
            st.error("⚠️ Vui lòng cấu hình IMAP trong cài đặt (☰)")
        else:
            with st.spinner("Đang kết nối..."):
                map_type = {"TẤT CẢ": "ALL", "CHƯA ĐỌC": "UNREAD", "ĐÃ ĐỌC": "READ"}
                emails = lay_emails(
                    cfg["host"], cfg["username"], cfg["password"],
                    datetime.combine(tu_ngay, datetime.min.time()),
                    datetime.combine(den_ngay, datetime.max.time()),
                    map_type[loai_mail]
                )
                for e in emails:
                    luu_email(e)
                st.success(f"✓ Đã lấy {len(emails)} email")

st.divider()

# Danh sách email
emails = doc_emails()

if not emails:
    st.info("📭 Chưa có email. Hãy cấu hình IMAP và lấy email mới.")
else:
    st.markdown(f"### 📨 Hộp thư ({len(emails)})")
    
    emails = sorted(emails, key=lambda x: x.get("ngay", ""), reverse=True)
    
    for mail in emails:
        eid = mail.get("message_id") or hashlib.md5(
            (mail.get("tieu_de", "") + str(mail.get("ngay", ""))).encode()
        ).hexdigest()
        
        is_expanded = st.session_state.email_mo_rong_id == eid
        
        # Card email với nút xóa trong tiêu đề
        with st.container():
            # Header: Thông tin ngườ gửi + nút xóa
            cols = st.columns([5, 1])
            
            with cols[0]:
                ten_nguoi_gui = mail.get("ten_nguoi_gui", "Không xác định")
                email_nguoi_gui = mail.get("email_nguoi_gui", "")
                tieu_de = mail.get("tieu_de", "(Không có tiêu đề)")
                xem_truoc = mail.get("xem_truoc", "")
                ngay = dinh_dang_ngay(mail.get("ngay", ""))
                dinh_kem = " 📎" if mail.get("co_dinh_kem") else ""
                
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="font-weight: 600; color: #0f172a; font-size: 1rem;">{tieu_de}{dinh_kem}</div>
                            <div style="color: #64748b; font-size: 0.875rem; margin-top: 0.25rem;">
                                Từ: <strong>{ten_nguoi_gui}</strong>
                                <span style="color: #94a3b8;"> ({email_nguoi_gui})</span>
                            </div>
                            
                            <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 0.5rem;">
                                {ngay} • {xem_truoc[:100]}{"..." if len(xem_truoc) > 100 else ""}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                # Nút xóa và mở rộng
                if st.button("🗑️", key=f"xoa_{eid}", help="Xóa email"):
                    xoa_email(eid)
                    st.success("Đã xóa")
                    st.rerun()
                
                btn_label = "Đóng" if is_expanded else "Đọc"
                if st.button(btn_label, key=f"doc_{eid}", use_container_width=True):
                    st.session_state.email_mo_rong_id = None if is_expanded else eid
                    st.rerun()
            
            # Nội dung mở rộng
            if is_expanded:
                tab_goc, tab_dich, tab_ai = st.tabs(["📄 Nội dung gốc", "🌐 Dịch tiếng Việt", "🤖 Tóm tắt AI"])
                
                with tab_goc:
                    st.text_area("Nội dung", value=mail.get("noi_dung", ""), height=300, disabled=True, label_visibility="collapsed")
                
                with tab_dich:
                    if st.button("🌐 Dịch sang tiếng Việt", key=f"btn_dich_{eid}"):
                        with st.spinner("Đang dịch..."):
                            st.session_state.email_dich[eid] = dich_google(mail.get("noi_dung", ""))
                    
                    da_dich = st.session_state.email_dich.get(eid, "Nhấn nút để dịch email sang tiếng Việt")
                    st.text_area("Bản dịch", value=da_dich, height=300, disabled=True, label_visibility="collapsed")
                
                with tab_ai:
                    if st.button("🤖 Tạo tóm tắt AI", key=f"btn_ai_{eid}"):
                        with st.spinner("AI đang phân tích..."):
                            st.session_state.email_ai[eid] = xu_ly_ai(mail.get("noi_dung", ""), "summarize")
                    
                    ket_qua_ai = st.session_state.email_ai.get(eid, "Nhấn nút để AI tóm tắt email")
                    st.info(ket_qua_ai)

st.markdown("<br>", unsafe_allow_html=True)
