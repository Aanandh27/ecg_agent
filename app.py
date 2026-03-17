import streamlit as st
import google.generativeai as genai
import fitz 
import json
import tempfile
import os
import io
import time
from PIL import Image

st.set_page_config(page_title="ECG Analyser", layout="centered")

# ───────────────── STYLES ─────────────────
st.markdown("""
<style>
.top-bar {
    background: linear-gradient(90deg, #1e3a5f 0%, #2563eb 100%);
    border-radius: 10px;
    padding: 18px 28px;
}
.patient-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px;
}
.findings-card {
    background: #f0f7ff;
    border-left: 5px solid #2563eb;
    border-radius: 10px;
    padding: 16px;
}
.footer {
    text-align: center;
    color: #9ca3af;
    font-size: 0.78rem;
    margin-top: 32px;
}
</style>
""", unsafe_allow_html=True)

# ───────────────── SIDEBAR ─────────────────
st.sidebar.title("⚙️ Setup")
api_key = st.sidebar.text_input("Gemini API Key", type="password")

# ───────────────── HEADER ─────────────────
st.markdown("""
<div class="top-bar">
<h1 style="color:white;">ECG Analyser</h1>
<p style="color:#bfdbfe;">Upload ECG PDF → Get AI Analysis</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload ECG PDF", type=["pdf"])

# ───────────────── FUNCTIONS ─────────────────
def extract_image_from_pdf(pdf_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    doc = fitz.open(tmp_path)

    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        images.append(Image.open(io.BytesIO(pix.tobytes("png"))))

    combined = Image.new("RGB", (max(i.width for i in images), sum(i.height for i in images)))
    y = 0
    for img in images:
        combined.paste(img, (0, y))
        y += img.height

    path = tmp_path.replace(".pdf", ".png")
    combined.save(path)
    doc.close()
    os.unlink(tmp_path)
    return path


def analyse_ecg(image_path, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    image = Image.open(image_path)

    prompt = "Analyse ECG and return JSON with rhythm, findings, risk_score, urgency"

    response = model.generate_content([prompt, image])
    return response.text


# ───────────────── MAIN ─────────────────
if uploaded_file and api_key:
    if st.button("Analyse ECG"):

        img_path = extract_image_from_pdf(uploaded_file.read())
        st.image(img_path)

        raw = analyse_ecg(img_path, api_key)
        os.unlink(img_path)

        result = json.loads(raw)

        st.subheader("ECG Report")

        # ── Patient ──
        st.markdown("### Patient Details")
        col1, col2, col3 = st.columns(3)
        col1.metric("ID", result.get("patient_id"))
        col2.metric("Gender", result.get("gender"))
        col3.metric("Age", result.get("age"))

        # ── Parameters ──
        st.markdown("### ECG Parameters")
        st.write(result.get("heart_rate"), "bpm")

        # ── Clinical Findings ──
        st.markdown("### Clinical Findings")
        st.write(result.get("st_segment"))

        # ✅ ── NEW ORDER STARTS HERE ──

        # ── Rhythm ──
        st.markdown("### 🔎 Rhythm")
        st.markdown(
            f'<div class="findings-card"><strong>{result.get("rhythm")}</strong></div>',
            unsafe_allow_html=True
        )

        # ── Key Findings ──
        st.markdown("### 🧾 Key Findings")
        st.markdown(
            f'<div class="findings-card">{result.get("key_findings")}</div>',
            unsafe_allow_html=True
        )

        # ── Risk Score ──
        risk = int(result.get("risk_score", 0))
        urgency = result.get("urgency")

        color = "green" if risk < 30 else ("orange" if risk < 60 else "red")

        st.markdown(f"""
        <div style="border-left:5px solid {color};padding:15px;">
        <h3>Risk Score: {risk}/100</h3>
        <p>Status: {urgency}</p>
        </div>
        """, unsafe_allow_html=True)

        # ✅ ── NEW ORDER ENDS HERE ──

        st.json(result)

        st.markdown('<div class="footer">Demo only</div>', unsafe_allow_html=True)
