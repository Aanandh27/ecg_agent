import streamlit as st
import google.generativeai as genai
import fitz
import json
import tempfile
import os
from PIL import Image
import pandas as pd

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="ECG Analyser",
    page_icon="🫀",
    layout="centered"
)

# ─────────────────────────────────────────
# LOAD GEMINI KEY FROM STREAMLIT SECRETS
# ─────────────────────────────────────────
api_key = st.secrets["GEMINI_API_KEY"]

# ─────────────────────────────────────────
# STANDARD ECG RANGES
# ─────────────────────────────────────────
ECG_RANGES = {
    "PR Interval": (120, 200),
    "QRS Interval": (80, 120),
    "QT Interval": (350, 440),
    "QTc Interval": (350, 440),
    "Heart Rate": (60, 100)
}

# ─────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────
st.title("🫀 ECG Analyser")
st.markdown("Upload an ECG report PDF and receive an AI-powered analysis.")
st.divider()

uploaded_file = st.file_uploader(
    "Upload ECG PDF",
    type=["pdf"]
)

# ─────────────────────────────────────────
# PDF → IMAGE
# ─────────────────────────────────────────
def extract_image_from_pdf(pdf_bytes):

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    doc = fitz.open(tmp_path)
    page = doc[0]

    mat = fitz.Matrix(2,2)
    pix = page.get_pixmap(matrix=mat)

    img_path = tmp_path.replace(".pdf",".png")
    pix.save(img_path)

    doc.close()
    os.unlink(tmp_path)

    return img_path

# ─────────────────────────────────────────
# GEMINI ECG ANALYSIS
# ─────────────────────────────────────────
def analyse_ecg(image_path):

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    image = Image.open(image_path)

    prompt = """
You are a medical assistant that reads ECG reports.

Look carefully at the ECG report image and extract the following values.
If a value is not visible write "Not found".

Return ONLY valid JSON.

{
"patient_id":"",
"age":"",
"gender":"",
"heart_rate":"",
"rhythm":"",
"key_findings":"",
"overall_condition":"",
"urgency":"",

"ecg_parameters":{
    "PR_interval":"",
    "QRS_interval":"",
    "QT_interval":"",
    "QTc_interval":"",
    "heart_rate":""
},

"detailed_analysis":{
    "ECG_quality":"",
    "ventricular_rate":"",
    "PR_interval":"",
    "QRS_duration":"",
    "QTc_interval":"",
    "cardiac_axis":"",
    "sinus_rhythm_present":"",
    "other_rhythm":"",
    "AV_conduction":"",
    "P_wave_morphology":"",
    "QRS_morphology":"",
    "Q_wave":"",
    "T_wave_morphology":"",
    "ST_segment":""
},

"clinical_interpretation":{
    "possible_conditions":"",
    "recommended_tests":"",
    "patient_friendly_summary":""
}

}

Return only JSON.
"""

    response = model.generate_content([prompt, image])

    return response.text

# ─────────────────────────────────────────
# ANALYSIS BUTTON
# ─────────────────────────────────────────
if uploaded_file:

    if st.button("🔍 Analyse ECG", use_container_width=True):

        with st.spinner("Extracting ECG image..."):
            img_path = extract_image_from_pdf(uploaded_file.read())

        st.subheader("Extracted ECG Image")
        st.image(img_path, use_container_width=True)

        st.divider()

        with st.spinner("Analysing ECG with AI..."):
            raw = analyse_ecg(img_path)

        os.unlink(img_path)

        clean = raw.replace("```json","").replace("```","").strip()

        try:

            result = json.loads(clean)

            # ─────────────────────────────────────────
            # PATIENT INFO
            # ─────────────────────────────────────────
            st.subheader("ECG Report")

            col1,col2,col3 = st.columns(3)

            col1.metric("Patient ID", result.get("patient_id","N/A"))
            col2.metric("Age", result.get("age","N/A"))
            col3.metric("Gender", result.get("gender","N/A"))

            st.divider()

            col4,col5 = st.columns(2)

            col4.metric("Heart Rate", result.get("heart_rate","N/A"))
            col5.metric("Rhythm", result.get("rhythm","N/A"))

            st.divider()

            # ─────────────────────────────────────────
            # ECG PARAMETER TABLE
            # ─────────────────────────────────────────
            st.subheader("ECG Parameter Table")

            params = result.get("ecg_parameters",{})

            data = []

            for key,value in params.items():

                name = key.replace("_"," ").title()

                try:
                    num = float(str(value).replace("ms","").replace("bpm","").strip())
                except:
                    num = None

                if name in ECG_RANGES:

                    low,high = ECG_RANGES[name]

                    if num and (num < low or num > high):
                        value_display = f"<span style='color:red'>{value}</span>"
                    else:
                        value_display = value

                    range_display = f"{low}-{high}"

                else:

                    value_display = value
                    range_display = "N/A"

                data.append([name,value_display,range_display])

            df = pd.DataFrame(
                data,
                columns=[
                    "ECG Parameter",
                    "Value",
                    "Standard Range"
                ]
            )

            st.markdown(
                df.to_html(escape=False,index=False),
                unsafe_allow_html=True
            )

            st.divider()

            # ─────────────────────────────────────────
            # DETAILED ECG ANALYSIS
            # ─────────────────────────────────────────
            st.subheader("Detailed ECG Analysis")

            details = result.get("detailed_analysis",{})

            abnormal_words = [
                "abnormal",
                "prolonged",
                "short",
                "block",
                "tachy",
                "brady",
                "elevated",
                "depressed",
                "irregular"
            ]

            for key,value in details.items():

                label = key.replace("_"," ").title()

                warning=""

                if any(w in str(value).lower() for w in abnormal_words):
                    warning=" ⚠️"

                st.write(f"**{label}:** {value}{warning}")

            st.divider()

            # ─────────────────────────────────────────
            # KEY FINDINGS
            # ─────────────────────────────────────────
            st.markdown("### Key Findings")
            st.info(result.get("key_findings","Not found"))

            # ─────────────────────────────────────────
            # OVERALL CONDITION
            # ─────────────────────────────────────────
            st.markdown("### Overall Condition")
            st.success(result.get("overall_condition","Not found"))

            # ─────────────────────────────────────────
            # AI CLINICAL INTERPRETATION (NEW)
            # ─────────────────────────────────────────
            st.divider()
            st.subheader("AI Clinical Interpretation")

            interpretation = result.get("clinical_interpretation",{})

            st.markdown("**Possible Conditions**")
            st.warning(
                interpretation.get(
                    "possible_conditions",
                    "Not found"
                )
            )

            st.markdown("**Recommended Next Tests**")
            st.info(
                interpretation.get(
                    "recommended_tests",
                    "Not found"
                )
            )

            st.markdown("**Simple Explanation for Patients**")
            st.success(
                interpretation.get(
                    "patient_friendly_summary",
                    "Not found"
                )
            )

            st.divider()

            # ─────────────────────────────────────────
            # STATUS
            # ─────────────────────────────────────────
            urgency = result.get("urgency","Normal")

            colors = {
                "Normal":"🟢",
                "Needs Review":"🟡",
                "Urgent":"🔴"
            }

            st.markdown(
                f"### Status: {colors.get(urgency,'⚪')} {urgency}"
            )

            # ─────────────────────────────────────────
            # RAW JSON
            # ─────────────────────────────────────────
            with st.expander("View Raw JSON"):
                st.json(result)

        except:

            st.error("Could not parse AI response")
            st.text(raw)

else:

    st.markdown(
"""
### How to use

1️⃣ Upload ECG PDF  
2️⃣ Click **Analyse ECG**

AI will extract ECG parameters and generate a report.

⚠️ This tool is for educational use only.
"""
)
