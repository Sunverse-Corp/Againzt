import streamlit as st
import sqlite3
import os
import cv2
import numpy as np
from PIL import Image
import base64
import io
from groq import Groq
from datetime import datetime
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Againzt | Sunverse Corp", page_icon="👁️", layout="wide")

# --- HIDE STREAMLIT UI (MAKE IT LOOK LIKE A NATIVE APP) ---
hide_streamlit_style = """
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- DATABASE & VAULT SETUP ---
DB_NAME = "againzt_vault.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, join_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vault (id INTEGER PRIMARY KEY AUTOINCREMENT, amount_usd REAL, currency TEXT, tier TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def get_user_count():
    with sqlite3.connect(DB_NAME) as conn:
        result = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        return result[0] if result else 0

def add_to_vault(amount_usd, currency, tier):
    with sqlite3.connect(DB_NAME) as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO vault (amount_usd, currency, tier, timestamp) VALUES (?, ?, ?, ?)", 
                     (amount_usd, currency, tier, now))
        conn.execute("INSERT INTO users (join_date) VALUES (?)", (datetime.now().strftime("%Y-%m-%d"),))
        conn.commit()
    st.session_state.subscribed = True

def log_usage(action):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO usage (action, timestamp) VALUES (?, ?)", 
                     (action, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()

# --- SUNVERSE LOGO ---
st.markdown("""
    <style>
    .sunverse-logo {
        font-size: 30px; font-weight: 900; color: #00FFCC; letter-spacing: 2px;
        text-transform: uppercase; border: 2px solid #00FFCC; padding: 10px;
        text-align: center; border-radius: 10px; margin-bottom: 20px;
        background-color: #111;
    }
    </style>
    <div class="sunverse-logo">☀️ SUNVERSE CORP PRESENTS: AGAINZT 👁️</div>
""", unsafe_allow_html=True)

# --- CURRENCY EXCHANGE RATES ---
currencies = {
    "USD": {"symbol": "$", "rate": 1.0},
    "NGN (Nigeria)": {"symbol": "₦", "rate": 1500.0},
    "ZAR (South Africa)": {"symbol": "R", "rate": 19.0},
    "KES (Kenya)": {"symbol": "KSh", "rate": 130.0},
    "GHS (Ghana)": {"symbol": "GH₵", "rate": 13.5},
    "UGX (Uganda)": {"symbol": "USh", "rate": 3800.0},
    "RWF (Rwanda)": {"symbol": "FRw", "rate": 1280.0},
    "TZS (Tanzania)": {"symbol": "TSh", "rate": 2580.0},
    "EGP (Egypt)": {"symbol": "E£", "rate": 47.0},
    "MAD (Morocco)": {"symbol": "MAD", "rate": 10.0},
    "XOF (West Africa CFA)": {"symbol": "CFA", "rate": 600.0}
}

# --- GROQ API SETUP ---
try:
    api_key = st.secrets.get("GROQ_API_KEY", None)
    if api_key:
        groq_client = Groq(api_key=api_key)
    else:
        groq_client = None
except Exception as e:
    groq_client = None

def encode_image(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def process_and_read_image(image):
    # 1. Image Enhancement (OpenCV) to clear faded text
    img_array = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced_gray = clahe.apply(gray)
    
    # Sharpening kernel
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    sharpened = cv2.filter2D(enhanced_gray, -1, kernel)
    
    enhanced_pil = Image.fromarray(sharpened)
    
    # 2. OCR via Groq Vision API
    extracted_text = "AI Vision Offline. Check API Key in Secrets."
    if groq_client:
        try:
            base64_img = encode_image(enhanced_pil)
            response = groq_client.chat.completions.create(
                model="llama-3.2-11b-vision-preview", # Groq's dedicated vision model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "You are Againzt by Sunverse. Carefully read and extract the text from this image. It may contain rough handwriting or faded text. Output ONLY the extracted text, formatted cleanly. If it's completely illegible, state 'Illegible'."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=1024
            )
            extracted_text = response.choices[0].message.content
        except Exception as e:
            extracted_text = f"Groq Vision Error: {e}"
            
    return enhanced_pil, extracted_text

# --- SESSION STATE ---
if 'subscribed' not in st.session_state: st.session_state.subscribed = False
if 'is_boss' not in st.session_state: st.session_state.is_boss = False

# --- TABS ---
tabs = st.tabs(["🏠 Home & Offline Game", "💳 Vault Subscriptions", "👁️ Againzt Scanner", "⚙️ Boss Mode"])

# --- TAB 1: HOME & GAME ---
with tabs[0]:
    st.write("### Welcome to Againzt")
    st.write("The ultimate AI tool for restoring, enhancing, and reading rough handwriting and faded documents.")
    st.divider()
    
    st.write("### 🎮 Mini-Game: Decrypt the Scribble")
    st.caption("Train your eyes while you wait!")
    st.write("Can you guess what this badly written doctor's note says?")
    st.markdown("### 𝒫𝒶𝓇𝒶𝒸ℯ𝓉𝒶𝓂ℴ𝓁 𝟧𝟢𝟢𝓂ℊ")
    
    guess = st.text_input("Enter your guess:")
    if st.button("Submit Guess"):
        if guess.lower() in ["paracetamol 500mg", "paracetamol"]:
            st.success("Correct! You have the eyes of Againzt!")
            st.balloons()
        else:
            st.error("Incorrect! Hint: It's a common painkiller.")

# --- TAB 2: SUBSCRIPTIONS ---
with tabs[1]:
    st.write("### Choose Your Currency & Tier")
    users = get_user_count()
    
    is_early_bird = users < 50
    discount = 0.8 if is_early_bird else 1.0
    
    if is_early_bird:
        st.success(f"🎉 **EARLY BIRD PROMO!** User #{users + 1}/50. You get a 20% discount!")
    
    selected_currency = st.selectbox("Select Currency", list(currencies.keys()))
    curr_data = currencies[selected_currency]
    sym = curr_data["symbol"]
    rate = curr_data["rate"]
    
    tier_1_usd = 5.0 * discount
    tier_2_usd = 10.0 * discount
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("### Standard Enhancer")
        st.write(f"**Price:** {sym} {tier_1_usd * rate:,.2f}")
        st.write("- Clear Faded Texts\n- Standard Resolution")
        if st.button("Buy Standard"):
            add_to_vault(tier_1_usd, selected_currency, "Standard")
            st.success("Payment successful! Funds sent to Vault.")
            
    with col2:
        st.warning("### Deep Vision Pro")
        st.write(f"**Price:** {sym} {tier_2_usd * rate:,.2f}")
        st.write("- Advanced Handwriting AI\n- Auto-Contrast Tech\n- Max Resolution")
        if st.button("Buy Pro"):
            add_to_vault(tier_2_usd, selected_currency, "Pro")
            st.success("Payment successful! Funds sent to Vault.")

# --- TAB 3: AGAINZT SCANNER ---
with tabs[2]:
    st.write("### 👁️ Againzt Vision Engine")
    
    if not (st.session_state.subscribed or st.session_state.is_boss):
        st.error("🔒 Please purchase a subscription in the Vault tab to use Againzt, or login via Boss Mode.")
    else:
        st.success("🟢 System Online. Upload photos, screenshots, or rough handwriting.")
        uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            original_image = Image.open(uploaded_file)
            
            with col1:
                st.write("**Original Image**")
                st.image(original_image, use_container_width=True)
                
            if st.button("Process & Read"):
                log_usage("image_processed")
                with st.spinner("Applying Sunverse algorithms & Groq Vision..."):
                    enhanced_img, extracted_text = process_and_read_image(original_image)
                    
                    with col2:
                        st.write("**Enhanced & Cleared Image**")
                        st.image(enhanced_img, use_container_width=True, caption="Contrast & Sharpening Applied")
                        
                    st.write("### 📝 Extracted Text:")
                    st.info(extracted_text)

# --- TAB 4: BOSS MODE ---
with tabs[3]:
    st.write("### ⚙️ Boss Mode")
    password = st.text_input("Boss Password:", type="password", key="boss_pass")
    
    if password:
        correct_password = st.secrets.get("BOSSMODE_PASSWORD", "")
        if password == correct_password and correct_password != "":
            st.session_state.is_boss = True
            st.success("Welcome, Sunverse CEO. Free Scanner Access Granted.")
            
            # VAULT STATS
            st.write("### 💰 The Vault")
            with sqlite3.connect(DB_NAME) as conn:
                df_vault = pd.read_sql_query("SELECT * FROM vault", conn)
                df_users = pd.read_sql_query("SELECT * FROM users", conn)
                df_usage = pd.read_sql_query("SELECT * FROM usage", conn)
            
            total_usd = df_vault['amount_usd'].sum() if not df_vault.empty else 0.0
            st.metric("Total Pending Funds (USD equivalent)", f"${total_usd:,.2f}")
            st.caption("Link an external bank account here to withdraw once available.")
            
            # GROWTH MONITOR
            st.write("### 📈 Growth Monitor")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**User Signups Over Time**")
                if not df_users.empty:
                    user_growth = df_users.groupby('join_date').size()
                    st.line_chart(user_growth)
                else:
                    st.write("No users yet.")
                    
            with col2:
                st.write("**AI Usage / Scans Over Time**")
                if not df_usage.empty:
                    usage_growth = df_usage.groupby('timestamp').size()
                    st.bar_chart(usage_growth)
                else:
                    st.write("No usage yet.")
        else:
            st.error("Invalid Boss Password.")

st.markdown("<br><hr><center><small>Againzt by Sunverse Corp. This is a Beta Version</small></center>", unsafe_allow_html=True)
