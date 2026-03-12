import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import json
import tempfile
import os
from PIL import Image

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="ECG Analyser",
    page_icon="🫀",
    layout="centered"
)

# ─────────────────────────────────────────
#  API Key
# ─────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
st.sidebar.markdown("Get your free API key from [Google AI Studio](https://aistudio.google.com)")
api_key = st.secrets.get("GEMINI_API_KEY", "") or st.sidebar.text_input("Gemini API Key", type="password", placeholder="Paste your key here")

# ─────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────
st.title("🫀 ECG Analyser")
st.markdown("Upload an ECG report PDF and get a simple, plain-English analysis instantly.")
st.divider()

# ─────────────────────────────────────────
#  Upload PDF
# ─────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload ECG PDF",
    type=["pdf"],
    help="Upload the ECG report as a PDF file"
)

# ─────────────────────────────────────────
#  Extract first page of PDF as image
# ─────────────────────────────────────────
def extract_image_from_pdf(pdf_bytes):
    """
    Converts the first page of a PDF into a PNG image.
    ECG reports are usually on the first page.
    """
    # Write PDF bytes to a temp file (PyMuPDF needs a file path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    # Open PDF and render first page at 2x zoom for better image quality
    doc = fitz.open(tmp_path)
    page = doc[0]
    mat = fitz.Matrix(2, 2)         
    pix = page.get_pixmap(matrix=mat)

    # Save rendered page as PNG to another temp file
    img_path = tmp_path.replace(".pdf", ".png")
    pix.save(img_path)

    doc.close()
    os.unlink(tmp_path)  # Clean up temp PDF

    return img_path

# ─────────────────────────────────────────
#  Send image to Gemini and get analysis
# ─────────────────────────────────────────
def analyse_ecg(image_path, api_key):
    """
    Sends the ECG image to Gemini 1.5 Flash.
    Returns structured JSON with patient info + ECG findings.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    image = Image.open(image_path)

    prompt = """
    You are a medical assistant that helps read ECG reports.
    
    Look at this ECG report image carefully and extract the following information.
    If any field is not visible in the image, write "Not found".

    Return ONLY a valid JSON object with exactly these fields:
    {
        "patient_id": "the patient ID or ID or Report ID if shown",
        "age": "patient age",
        "gender": "Male / Female / Not found",
        "heart_rate": "beats per minute if shown",
        "rhythm": "e.g. Normal Sinus Rhythm, Atrial Fibrillation, etc.",
        "key_findings": "list the main ECG findings in simple terms",
        "overall_condition": "one sentence plain English summary of how this ECG looks",
        "urgency": "Normal / Needs Review / Urgent"
    }

    Do NOT include any explanation outside the JSON. Return only the JSON.
    """

    response = model.generate_content([prompt, image])
    return response.text

# ─────────────────────────────────────────
#  Analyse Button and Display Results
# ─────────────────────────────────────────
if uploaded_file and api_key:
    if st.button("🔍 Analyse ECG", use_container_width=True, type="primary"):

        with st.spinner("Extracting ECG image from PDF..."):
            img_path = extract_image_from_pdf(uploaded_file.read())

        # Show the extracted ECG image so user can verify
        st.subheader("📋 Extracted ECG Image")
        st.image(img_path, caption="Page extracted from your PDF", use_container_width=True)
        st.divider()

        with st.spinner("Analysing ECG with AI... this takes 5-10 seconds"):
            raw_response = analyse_ecg(img_path, api_key)

        # Clean up temp image file
        os.unlink(img_path)

        # ── Parse the JSON response ──
        try:
            # Strip markdown code fences if Gemini adds them
            clean = raw_response.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)

            # ── Display results in a clean layout ──
            st.subheader("ECG Analysis Report")

            # Patient info row
            col1, col2, col3 = st.columns(3)
            col1.metric("Patient ID", result.get("patient_id", "N/A"))
            col2.metric("Age", result.get("age", "N/A"))
            col3.metric("Gender", result.get("gender", "N/A"))

            st.divider()

            # ECG findings row
            col4, col5 = st.columns(2)
            col4.metric("Heart Rate", result.get("heart_rate", "N/A"))
            col5.metric("Rhythm", result.get("rhythm", "N/A"))

            # Key findings
            st.markdown("**Key Findings**")
            st.info(result.get("key_findings", "No findings extracted"))

            # Overall summary
            st.markdown("**Overall Condition**")
            st.success(result.get("overall_condition", "No summary available"))

            # Urgency badge
            urgency = result.get("urgency", "Normal")
            urgency_colors = {"Normal": "🟢", "Needs Review": "🟡", "Urgent": "🔴"}
            st.markdown(f"**Status:** {urgency_colors.get(urgency, '⚪')} {urgency}")

            st.divider()

            # Expandable raw JSON for developers / interviewers
            with st.expander("🧑‍💻 View Raw JSON Output"):
                st.json(result)

        except json.JSONDecodeError:
            # If JSON parsing fails, show raw text
            st.warning("Could not parse structured output. Showing raw AI response:")
            st.text(raw_response)

elif uploaded_file and not api_key:
    st.warning("⬅️ Please enter your Gemini API key in the sidebar to continue.")

elif not uploaded_file:
    # Show instructions when nothing is uploaded yet
    st.markdown("""
    ### How to use this tool:
    1. **Upload** your ECG PDF report
    2. Click **Analyse ECG** and get results!
    
    ---
    > ⚠️ *This tool is for educational and portfolio demonstration purposes only.  
    > It is not a substitute for professional medical advice.*
    """)
