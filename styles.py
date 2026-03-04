"""
CYBER-INDUSTRIAL THEME FOR STREAMLIT
Custom CSS and UI utilities
"""
import streamlit as st

def load_custom_css():
    """Load custom CSS for cyber-industrial theme"""
    custom_css = """
    <style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%);
    }
    
    /* Main container */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Typography */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    
    h1 {
        background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 50%, #f59e0b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Sidebar */
    .css-1d391kg, .css-163ttbj {
        background-color: #12121a !important;
        border-right: 1px solid #1a1a25;
    }
    
    /* Buttons - Primary */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #0a0a0f !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
    }
    
    /* Buttons - Secondary */
    .stButton > button:not([kind="primary"]) {
        background: #1a1a25 !important;
        color: #fafafa !important;
        border: 1px solid #323240 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:not([kind="primary"]):hover {
        border-color: #f59e0b !important;
        background: #252532 !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #1a1a25 !important;
        border: 1px solid #323240 !important;
        border-radius: 8px !important;
        color: #fafafa !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #f59e0b !important;
        box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2) !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div > div {
        background-color: #1a1a25 !important;
        border: 1px solid #323240 !important;
        border-radius: 8px !important;
    }
    
    /* Date input */
    .stDateInput > div > div > input {
        background-color: #1a1a25 !important;
        border: 1px solid #323240 !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Dividers */
    .stDivider {
        border-color: #252532 !important;
    }
    
    /* Cards / Containers */
    .element-container {
        border-radius: 12px;
    }
    
    /* Expander */
    .streamlit-expander {
        background-color: #12121a !important;
        border: 1px solid #1a1a25 !important;
        border-radius: 12px !important;
        overflow: hidden;
    }
    
    .streamlit-expanderHeader {
        background-color: #1a1a25 !important;
        color: #fafafa !important;
        font-weight: 600 !important;
        padding: 1rem !important;
    }
    
    /* Success/Info/Error messages */
    .stSuccess {
        background-color: rgba(34, 197, 94, 0.1) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: 8px !important;
        color: #4ade80 !important;
    }
    
    .stInfo {
        background-color: rgba(6, 182, 212, 0.1) !important;
        border: 1px solid rgba(6, 182, 212, 0.3) !important;
        border-radius: 8px !important;
        color: #22d3ee !important;
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 8px !important;
        color: #f87171 !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0a0a0f;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #323240;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #f59e0b;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #f59e0b !important;
    }
    
    /* Sidebar title */
    .css-1d391kg h1, .css-163ttbj h1 {
        color: #f59e0b !important;
        font-size: 1.5rem !important;
    }
    
    /* Sidebar subheaders */
    .css-1d391kg h3, .css-163ttbj h3 {
        color: #fafafa !important;
        font-size: 0.9rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }
    
    /* Metrics */
    .css-1xarl3l {
        background-color: #1a1a25 !important;
        border: 1px solid #323240 !important;
        border-radius: 12px !important;
    }
    
    /* DataFrames / Tables */
    .stDataFrame {
        border: 1px solid #1a1a25 !important;
        border-radius: 12px !important;
        overflow: hidden;
    }
    
    /* Code blocks */
    code {
        background-color: #1a1a25 !important;
        color: #f59e0b !important;
        padding: 0.2rem 0.4rem !important;
        border-radius: 4px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    pre {
        background-color: #12121a !important;
        border: 1px solid #1a1a25 !important;
        border-radius: 8px !important;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def render_card(title, content, icon="📧"):
    """Render a custom card"""
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #12121a 0%, #1a1a25 100%);
        border: 1px solid #252532;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    " onmouseover="this.style.borderColor='#f59e0b'; this.style.transform='translateY(-2px)';" 
    onmouseout="this.style.borderColor='#252532'; this.style.transform='translateY(0)';">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
            <span style="font-size: 1.5rem;">{icon}</span>
            <h4 style="margin: 0; color: #fafafa; font-weight: 600;">{title}</h4>
        </div>
        <div style="color: #a1a1aa; line-height: 1.6;">{content}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_badge(text, color="amber"):
    """Render a badge pill"""
    colors = {
        "amber": ("#f59e0b", "#0a0a0f"),
        "cyan": ("#06b6d4", "#0a0a0f"),
        "red": ("#ef4444", "#ffffff"),
        "green": ("#22c55e", "#0a0a0f"),
        "purple": ("#a855f7", "#ffffff"),
    }
    bg_color, text_color = colors.get(color, colors["amber"])
    
    badge_html = f"""
    <span style="
        display: inline-block;
        background-color: {bg_color}20;
        color: {bg_color};
        border: 1px solid {bg_color}40;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: 'JetBrains Mono', monospace;
    ">{text}</span>
    """
    st.markdown(badge_html, unsafe_allow_html=True)


def render_divider():
    """Render a styled divider"""
    st.markdown("""
    <div style="
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #f59e0b 50%, transparent 100%);
        margin: 2rem 0;
        opacity: 0.3;
    "></div>
    """, unsafe_allow_html=True)


def render_header():
    """Render app header with gradient"""
    header_html = """
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 50%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.02em;
        ">📧 MAIL NEXUS</h1>
        <p style="
            color: #71717a;
            font-size: 1rem;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.2em;
        ">Cyber-Industrial Email Manager</p>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
