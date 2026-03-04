import streamlit as st
from config_ui import render_config
from email_ui import render_email_section
from styles import load_custom_css

# Page config
st.set_page_config(
    page_title="Mail Nexus | Cyber-Industrial Email Manager",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
load_custom_css()

# Render app
render_config()
render_email_section()
