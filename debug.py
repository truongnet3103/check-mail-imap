"""
Mail Nexus - Debug Version
"""
import streamlit as st

# ========== DEBUG MODE ==========
st.set_page_config(page_title="Mail Nexus Debug", layout="wide")

st.title("🔧 Debug Mode")

# Test 1: Basic imports
st.markdown("### 1. Testing imports...")
try:
    import firebase_admin
    st.success("✅ firebase_admin imported")
except Exception as e:
    st.error(f"❌ firebase_admin: {e}")

try:
    from firebase_admin import credentials, firestore
    st.success("✅ credentials, firestore imported")
except Exception as e:
    st.error(f"❌ credentials/firestore: {e}")

try:
    import google.generativeai as genai
    st.success("✅ google-generativeai imported")
except Exception as e:
    st.warning(f"⚠️ google-generativeai: {e}")

# Test 2: Secrets
st.markdown("### 2. Testing secrets...")
try:
    if hasattr(st, "secrets"):
        st.success("✅ st.secrets exists")
        if "firebase" in st.secrets:
            st.success("✅ [firebase] section exists")
            fb = st.secrets["firebase"]
            st.write("Keys found:", list(fb.keys()) if hasattr(fb, 'keys') else "N/A")
            
            # Check critical fields
            critical = ["type", "project_id", "private_key", "client_email"]
            for field in critical:
                if field in fb:
                    st.success(f"  ✅ {field}")
                else:
                    st.error(f"  ❌ {field} MISSING")
        else:
            st.error("❌ [firebase] section NOT FOUND")
    else:
        st.error("❌ st.secrets not found")
except Exception as e:
    st.error(f"❌ Error reading secrets: {e}")
    import traceback
    st.code(traceback.format_exc())

# Test 3: Firebase init
st.markdown("### 3. Testing Firebase...")
try:
    if not firebase_admin._apps:
        st.info("Firebase not initialized, trying to init...")
        if "firebase" in st.secrets:
            fb_config = dict(st.secrets["firebase"])
            cred = credentials.Certificate(fb_config)
            firebase_admin.initialize_app(cred)
            st.success("✅ Firebase initialized!")
        else:
            st.error("❌ Cannot init - no firebase secrets")
    else:
        st.success("✅ Firebase already initialized")
    
    # Try to get client
    db = firestore.client()
    st.success("✅ Firestore client created")
    
    # Try to read
    docs = db.collection("emails").limit(1).stream()
    st.success("✅ Can read from Firestore")
    
except Exception as e:
    st.error(f"❌ Firebase error: {e}")
    import traceback
    st.code(traceback.format_exc())

st.markdown("---")
st.info("If all checks pass but main app still fails, check the main app code.")
