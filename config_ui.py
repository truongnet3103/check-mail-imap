import streamlit as st
from firebase_service import (
    save_ai_config,
    get_ai_config,
    save_imap_config,
    get_imap_config
)
from imap_service import test_imap_connection


def render_config():
    """Render configuration sidebar with cyber-industrial design"""
    
    # Sidebar header
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid #252532; margin-bottom: 1.5rem;">
        <div style="
            width: 50px;
            height: 50px;
            margin: 0 auto 0.75rem;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
        ">⚙️</div>
        <h2 style="
            margin: 0;
            font-size: 1.25rem;
            font-weight: 700;
            color: #f59e0b;
            letter-spacing: -0.01em;
        ">SYSTEM CONFIG</h2>
        <p style="
            margin: 0.25rem 0 0;
            font-size: 0.7rem;
            color: #71717a;
            font-family: monospace;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        ">IMAP + AI Settings</p>
    </div>
    """, unsafe_allow_html=True)
    
    # AI CONFIG SECTION
    st.sidebar.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        padding: 0.75rem;
        background: #1a1a25;
        border-radius: 8px;
        border-left: 3px solid #f59e0b;
    ">
        <span style="font-size: 1.2rem;">🤖</span>
        <span style="font-weight: 600; color: #fafafa;">AI Configuration</span>
    </div>
    """, unsafe_allow_html=True)
    
    ai_config = get_ai_config()
    
    api_key = st.sidebar.text_input(
        "🔑 Gemini API Key",
        value=ai_config.get("api_key", ""),
        type="password",
        help="API key từ Google AI Studio"
    )
    
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.sidebar.button("💾 Save AI Config", use_container_width=True, type="primary"):
            save_ai_config({
                "api_key": api_key,
                "model": "gemini-2.5-flash"
            })
            st.sidebar.success("✅ AI Config Saved!")
    
    st.sidebar.markdown("""
    <div style="
        padding: 0.75rem;
        background: #12121a;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid #252532;
    ">
        <p style="margin: 0; font-size: 0.8rem; color: #71717a;">
            💡 Lấy API key từ <a href="https://makersuite.google.com/app/apikey" target="_blank" style="color: #f59e0b; text-decoration: none;">Google AI Studio →</a>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Divider
    st.sidebar.markdown("""
    <div style="
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #323240 50%, transparent 100%);
        margin: 1.5rem 0;
    "></div>
    """, unsafe_allow_html=True)
    
    # IMAP CONFIG SECTION
    st.sidebar.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        padding: 0.75rem;
        background: #1a1a25;
        border-radius: 8px;
        border-left: 3px solid #06b6d4;
    ">
        <span style="font-size: 1.2rem;">📧</span>
        <span style="font-weight: 600; color: #fafafa;">IMAP Configuration</span>
    </div>
    """, unsafe_allow_html=True)
    
    imap_config = get_imap_config()
    
    host = st.sidebar.text_input(
        "🌐 IMAP Host",
        value=imap_config.get("host", ""),
        placeholder="imap.gmail.com"
    )
    
    username = st.sidebar.text_input(
        "👤 Username",
        value=imap_config.get("username", ""),
        placeholder="email@example.com"
    )
    
    password = st.sidebar.text_input(
        "🔒 Password / App Password",
        value=imap_config.get("password", ""),
        type="password",
        help="Dùng App Password cho Gmail/Outlook"
    )
    
    # IMAP Action Buttons
    col_save, col_test = st.sidebar.columns(2)
    
    with col_save:
        if st.button("💾 Save", use_container_width=True, type="primary"):
            save_imap_config({
                "host": host,
                "username": username,
                "password": password,
                "port": 993,
                "ssl": True
            })
            st.sidebar.success("✅ Saved!")
    
    with col_test:
        if st.button("🧪 Test", use_container_width=True):
            if not all([host, username, password]):
                st.sidebar.error("⚠️ Nhập đầy đủ thông tin")
            else:
                with st.spinner("Testing..."):
                    success, message = test_imap_connection(
                        host,
                        username,
                        password,
                        port=993
                    )
                    if success:
                        st.sidebar.success(f"✅ {message}")
                    else:
                        st.sidebar.error(f"❌ {message}")
    
    # Help text
    st.sidebar.markdown("""
    <div style="
        padding: 0.75rem;
        background: #12121a;
        border-radius: 8px;
        margin-top: 1rem;
        border: 1px solid #252532;
    ">
        <p style="margin: 0; font-size: 0.75rem; color: #71717a; line-height: 1.5;">
            💡 Gmail/Outlook cần <strong style="color: #f59e0b;">App Password</strong> thay vì password thường.<br>
            <a href="https://myaccount.google.com/apppasswords" target="_blank" style="color: #06b6d4; text-decoration: none;">Tạo App Password →</a>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.sidebar.markdown("""
    <div style="
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem;
        background: #0a0a0f;
        border-top: 1px solid #1a1a25;
        text-align: center;
    ">
        <p style="
            margin: 0;
            font-size: 0.7rem;
            color: #52525b;
            font-family: monospace;
        ">Mail Nexus v1.0 | Cyber-Industrial</p>
    </div>
    """, unsafe_allow_html=True)
