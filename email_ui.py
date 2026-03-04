import streamlit as st
import requests
from datetime import date, datetime
from imap_service import fetch_emails_by_date
from firebase_service import (
    get_all_emails,
    save_email,
    reset_emails,
    get_imap_config,
    delete_email,
)


def translate_text(text):
    """Google Translate (Free)"""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "vi",
            "dt": "t",
            "q": text,
        }
        r = requests.get(url, params=params)
        data = r.json()
        return "".join([item[0] for item in data[0]])
    except:
        return "❌ Lỗi dịch"


def format_date(date_str):
    """Format ISO date to readable string"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return date_str[:16].replace("T", " ")


def get_initials(name):
    """Get initials from name/email"""
    if not name:
        return "?"
    parts = name.replace('@', ' ').replace('.', ' ').split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[0].upper() if name else "?"


def get_avatar_color(name):
    """Get deterministic color for avatar"""
    colors = ["#f59e0b", "#06b6d4", "#ef4444", "#a855f7", "#22c55e", "#f97316"]
    if not name:
        return colors[0]
    return colors[hash(name) % len(colors)]


def render_email_card(mail, mail_id, is_expanded):
    """Render a single email card"""
    sender = mail.get("from", "Unknown")
    subject = mail.get("subject", "(Không tiêu đề)")
    date_str = format_date(mail.get("date", ""))
    has_attach = mail.get("has_attachment", False)
    snippet = mail.get("snippet", "")
    
    initials = get_initials(sender)
    avatar_color = get_avatar_color(sender)
    
    # Card container
    card_style = """
        background: linear-gradient(135deg, #12121a 0%, #1a1a25 100%);
        border: 1px solid #252532;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
    """
    
    if is_expanded:
        card_style = card_style.replace("#252532", "#f59e0b50")
    
    st.markdown(f"""
    <div style="{card_style}" id="email_{mail_id}">
        <div style="display: flex; gap: 1rem; align-items: flex-start;">
            <div style="
                width: 45px;
                height: 45px;
                min-width: 45px;
                border-radius: 10px;
                background: linear-gradient(135deg, {avatar_color}80 0%, {avatar_color} 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                color: #0a0a0f;
                font-size: 0.9rem;
                box-shadow: 0 4px 15px {avatar_color}40;
            ">{initials}</div>
            
            <div style="flex: 1; min-width: 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <span style="font-weight: 600; color: #fafafa; font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{sender}</span>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        {'<span style="font-size: 1rem;">📎</span>' if has_attach else ''}
                        <span style="font-family: monospace; font-size: 0.75rem; color: #71717a;">{date_str}</span>
                    </div>
                </div>
                <div style="color: #a1a1aa; font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{subject}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_email_section():
    """Main email section with cyber-industrial design"""
    
    # Initialize session state
    if "expanded_id" not in st.session_state:
        st.session_state.expanded_id = None
    if "translations" not in st.session_state:
        st.session_state.translations = {}
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0 2rem;">
        <h1 style="
            font-size: 2.25rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 50%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        ">📧 MAIL NEXUS</h1>
        <p style="
            margin: 0.5rem 0 0;
            color: #71717a;
            font-family: monospace;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-size: 0.8rem;
        ">Cyber-Industrial Email Manager</p>
    </div>
    """, unsafe_allow_html=True)
    
    # FETCH SECTION
    st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 1.5rem 0 1rem;
        padding: 0.75rem 1rem;
        background: linear-gradient(135deg, #1a1a25 0%, #252532 100%);
        border-radius: 10px;
        border-left: 3px solid #f59e0b;
    ">
        <span style="font-size: 1.2rem;">⚡</span>
        <span style="font-weight: 600; color: #fafafa;">Fetch Emails</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Date filters
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        start_date = st.date_input("📅 Từ ngày", value=date.today())
    
    with col2:
        end_date = st.date_input("📅 Đến ngày", value=date.today())
    
    with col3:
        mail_type = st.selectbox("📨 Loại Mail", ["ALL", "UNREAD", "READ"])
    
    # Fetch button
    col_fetch, col_spacer = st.columns([2, 4])
    with col_fetch:
        if st.button("🚀 FETCH EMAILS", use_container_width=True, type="primary"):
            imap_conf = get_imap_config()
            
            if not imap_conf:
                st.error("⚠️ Chưa có cấu hình IMAP. Vui lòng cấu hình trong sidebar.")
            else:
                with st.spinner("⏳ Đang kết nối đến IMAP server..."):
                    emails = fetch_emails_by_date(
                        imap_conf["host"],
                        imap_conf["username"],
                        imap_conf["password"],
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time()),
                        mail_type,
                    )
                    
                    for mail in emails:
                        save_email(mail)
                    
                    st.success(f"✅ Đã lấy và lưu {len(emails)} email!")
                    st.balloons()
    
    # Divider
    st.markdown("""
    <div style="
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #f59e0b 50%, transparent 100%);
        margin: 2rem 0;
        opacity: 0.3;
    "></div>
    """, unsafe_allow_html=True)
    
    # EMAIL LIST SECTION
    emails = get_all_emails()
    
    if not emails:
        st.info("📭 Chưa có email nào trong hệ thống. Hãy fetch emails từ IMAP server.")
        return
    
    # Sort emails
    emails = sorted(emails, key=lambda x: x.get("date", ""), reverse=True)
    
    # Header with count
    col_header, col_reset = st.columns([6, 2])
    with col_header:
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
        ">
            <span style="font-size: 1.2rem;">📨</span>
            <span style="font-weight: 600; color: #fafafa;">Danh sách Email</span>
            <span style="
                background: #f59e0b20;
                color: #f59e0b;
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                font-family: monospace;
                border: 1px solid #f59e0b40;
            ">{len(emails)}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_reset:
        if st.button("🗑️ Xóa tất cả", use_container_width=True):
            if st.checkbox("Xác nhận xóa tất cả email?"):
                reset_emails()
                st.success("✅ Đã xóa toàn bộ email!")
                st.rerun()
    
    # Render email list
    for mail in emails:
        mail_id = mail.get("message_id", "")
        if not mail_id:
            mail_id = mail.get("subject", "") + mail.get("date", "")
        
        is_expanded = st.session_state.expanded_id == mail_id
        
        # Email card with expand button
        col_card, col_delete = st.columns([12, 1])
        
        with col_card:
            if st.button(
                f"{mail.get('from', 'Unknown')} | {mail.get('subject', '')[:40]}...",
                key=f"row_{mail_id}",
                use_container_width=True,
            ):
                if st.session_state.expanded_id == mail_id:
                    st.session_state.expanded_id = None
                else:
                    st.session_state.expanded_id = mail_id
                st.rerun()
        
        with col_delete:
            if st.button("🗑️", key=f"del_{mail_id}"):
                delete_email(mail_id)
                st.success("✅ Đã xóa!")
                st.rerun()
        
        # Expanded content
        if is_expanded:
            with st.container():
                st.markdown("""
                <div style="
                    background: #0a0a0f;
                    border: 1px solid #f59e0b40;
                    border-radius: 12px;
                    padding: 1.5rem;
                    margin: 0.5rem 0 1.5rem;
                ">
                """, unsafe_allow_html=True)
                
                # Email content
                snippet = mail.get("snippet", "")
                st.markdown(f"""
                <div style="color: #d4d4d8; line-height: 1.7; font-size: 0.95rem;">{snippet}</div>
                """, unsafe_allow_html=True)
                
                # Action buttons
                col_trans, col_spacer = st.columns([2, 4])
                
                with col_trans:
                    if st.button("🌐 Dịch nội dung", key=f"trans_{mail_id}", use_container_width=True):
                        if mail_id not in st.session_state.translations:
                            with st.spinner("🔄 Đang dịch..."):
                                translated = translate_text(snippet)
                                st.session_state.translations[mail_id] = translated
                        st.rerun()
                
                # Show translation
                if mail_id in st.session_state.translations:
                    st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #06b6d420 0%, #06b6d410 100%);
                        border: 1px solid #06b6d440;
                        border-radius: 8px;
                        padding: 1rem;
                        margin-top: 1rem;
                    ">
                        <div style="font-weight: 600; color: #06b6d4; margin-bottom: 0.5rem;">🇻🇳 Bản dịch:</div>
                        <div style="color: #d4d4d8; line-height: 1.6;">{}</div>
                    </div>
                    """.format(st.session_state.translations[mail_id]), unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
