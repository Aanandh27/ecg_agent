import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import json
import tempfile
import os
import io
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
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
st.sidebar.markdown("Get your free API key from [Google AI Studio](https://aistudio.google.com)")
api_key = st.secrets.get("GEMINI_API_KEY", "") or st.sidebar.text_input(
    "Gemini API Key", type="password", placeholder="Paste your key here"
)

# ─────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────
st.title("🫀 ECG Analyser")
st.markdown("Upload an ECG report PDF and get a complete clinical analysis instantly.")
st.divider()

# ✅ File uploader — always defined first before any conditionals
uploaded_file = st.file_uploader(
    "📄 Upload ECG PDF",
    type=["pdf"],
    help="Upload the ECG report as a PDF file"
)

# ─────────────────────────────────────────
# STANDARD RANGES
# ─────────────────────────────────────────
NORMAL_RANGES = {
    "heart_rate":   {"min": 60,  "max": 100, "unit": "bpm", "label": "Heart Rate"},
    "pr_interval":  {"min": 120, "max": 200, "unit": "ms",  "label": "PR Interval"},
    "qrs_duration": {"min": 70,  "max": 110, "unit": "ms",  "label": "QRS Duration"},
    "qt_interval":  {"min": 350, "max": 440, "unit": "ms",  "label": "QT Interval"},
    "qtc_interval": {"min": 350, "max": 450, "unit": "ms",  "label": "QTc Interval"},
}

CLINICAL_FIELDS = [
    ("ventricular_rate",     "Ventricular Rate"),
    ("cardiac_axis",         "Cardiac Axis"),
    ("sinus_rhythm",         "Sinus Rhythm Present"),
    ("other_rhythm",         "Other Rhythm"),
    ("atrial_pause",         "Atrial Pause > 2 seconds"),
    ("av_conduction",        "AV Conduction"),
    ("ventricular_ectopics", "Ventricular Ectopics"),
    ("atrial_ectopics",      "Atrial Ectopics"),
    ("st_segment",           "ST Segment"),
]

ABNORMAL_TRIGGERS = {
    "atrial_pause":          lambda v: v.lower() not in ["no","none","not found","normal","absent"],
    "av_conduction":         lambda v: v.lower() not in ["normal","not found","none","1:1"],
    "ventricular_ectopics":  lambda v: v.lower() not in ["not observed","none","absent","normal","not found"],
    "atrial_ectopics":       lambda v: v.lower() not in ["not observed","none","absent","normal","not found"],
    "p_wave_morphology":     lambda v: v.lower() not in ["normal","not found"],
    "qrs_morphology":        lambda v: v.lower() not in ["normal","within normal limits","not found"],
    "q_wave":                lambda v: v.lower() not in ["normal","within normal limits","not found","absent"],
    "t_wave_morphology":     lambda v: v.lower() not in ["normal","within normal limits","not found"],
    "st_segment":            lambda v: v.lower() not in ["normal","isoelectric","not found","within normal limits"],
    "other_rhythm":          lambda v: v.lower() not in ["none","not found","normal sinus rhythm"],
}

# ─────────────────────────────────────────
# PDF → IMAGE (all pages stitched)
# ─────────────────────────────────────────
def extract_image_from_pdf(pdf_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    doc = fitz.open(tmp_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    combined = Image.new("RGB", (max(i.width for i in images), sum(i.height for i in images)), "white")
    y = 0
    for img in images:
        combined.paste(img, (0, y))
        y += img.height
    img_path = tmp_path.replace(".pdf", ".png")
    combined.save(img_path)
    doc.close()
    os.unlink(tmp_path)
    return img_path

# ─────────────────────────────────────────
# GEMINI ANALYSIS
# Full prompt — reads BOTH printed text AND waveform
# ─────────────────────────────────────────
def analyse_ecg(image_path, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    image = Image.open(image_path)

    prompt = """
    You are a clinical ECG analysis assistant working in a hospital setting.

    You are given an ECG report image. It may contain:
    - Printed patient details (name, ID, age, gender, DOB)
    - Printed measurements (heart rate, PR interval, QRS, QT, QTc)
    - A printed interpretation / diagnosis section
    - The actual ECG waveform grid with 12 leads

    YOUR TASK — do BOTH of the following:

    PART 1 — READ PRINTED TEXT:
    Extract all patient details and measurements that are printed on the report.

    PART 2 — ANALYSE THE WAVEFORM VISUALLY:
    Look at the actual ECG waveform graph carefully and determine:
    - ECG quality (is the signal clean or noisy?)
    - Ventricular rate from the R-R intervals on the waveform
    - Cardiac axis from the QRS direction in leads I and aVF
    - Whether sinus rhythm is present (regular P waves before every QRS?)
    - Any other rhythm (AFib, flutter, junctional, etc.)
    - Atrial pause greater than 2 seconds
    - AV conduction (normal, 1st/2nd/3rd degree block?)
    - Ventricular ectopics (wide bizarre QRS complexes?)
    - Atrial ectopics (early narrow beats with different P-wave morphology?)
    - P-wave morphology (normal, peaked, bifid, absent?)
    - QRS morphology (narrow, wide, LBBB, RBBB, delta wave?)
    - Q-waves (pathological Q waves present in any lead?)
    - T-wave morphology (normal, inverted, peaked, flattened?)
    - ST segment (isoelectric, elevated, depressed? In which leads?)

    IMPORTANT RULES:
    - For numeric fields return ONLY the number, no units
    - If printed value is available, use it. If not, estimate from waveform.
    - If neither is available, write "Not found"
    - For risk_score: 0-30 = low risk, 31-60 = medium risk, 61-100 = high risk
    - Base urgency on: Normal = all clear, Needs Review = notable findings, Urgent = STEMI/severe arrhythmia

    Return ONLY a valid JSON object. No markdown. No explanation. Just JSON:
    {
        "patient_id": "ID number or Not found",
        "age": "number only or Not found",
        "gender": "Male or Female or Not found",

        "heart_rate": "number only in bpm",
        "pr_interval": "number only in ms",
        "qrs_duration": "number only in ms",
        "qt_interval": "number only in ms",
        "qtc_interval": "number only in ms",

        "ecg_quality": "Good or Acceptable or Poor — from waveform",
        "ventricular_rate": "number only in bpm — from waveform R-R intervals",
        "cardiac_axis": "Normal or Left axis deviation or Right axis deviation — from waveform",
        "sinus_rhythm": "Yes or No — from waveform",
        "other_rhythm": "describe or None — from waveform",
        "atrial_pause": "Yes or No — from waveform",
        "av_conduction": "Normal or describe block type — from waveform",
        "ventricular_ectopics": "Not observed or describe — from waveform",
        "atrial_ectopics": "Not observed or describe — from waveform",
        "p_wave_morphology": "Normal or describe — from waveform",
        "qrs_morphology": "Within normal limits or describe — from waveform",
        "q_wave": "Within normal limits or describe — from waveform",
        "t_wave_morphology": "Normal or describe — from waveform",
        "st_segment": "Normal or describe elevation/depression and leads — from waveform",

        "rhythm": "primary rhythm name e.g. Normal Sinus Rhythm",
        "key_findings": "all significant findings as one clear paragraph",
        "overall_condition": "one plain English sentence a non-doctor can understand",
        "urgency": "Normal or Needs Review or Urgent",
        "risk_score": 45
    }
    """

    response = model.generate_content([prompt, image])
    return response.text

# ─────────────────────────────────────────
# RISK GAUGE
# ─────────────────────────────────────────
def render_risk_gauge(score):
    score = max(0, min(100, int(score)))
    color = "#3b82f6" if score <= 30 else ("#8b5cf6" if score <= 60 else "#ec4899")
    label = "Low Risk" if score <= 30 else ("Medium Risk" if score <= 60 else "High Risk")
    rotation = -90 + (score / 100) * 180
    st.components.v1.html(f"""
    <div style="display:flex;flex-direction:column;align-items:center;margin:10px 0 20px 0;">
        <div style="position:relative;width:240px;height:130px;overflow:hidden;">
            <div style="position:absolute;width:220px;height:220px;border-radius:50%;top:10px;left:10px;
                background:conic-gradient(#3b82f6 0deg 54deg,#8b5cf6 54deg 108deg,#ec4899 108deg 180deg,transparent 180deg 360deg);"></div>
            <div style="position:absolute;width:140px;height:140px;background:white;border-radius:50%;top:50px;left:50px;"></div>
            <div style="position:absolute;width:4px;height:90px;background:{color};border-radius:4px;
                top:30px;left:119px;transform-origin:bottom center;transform:rotate({rotation}deg);"></div>
            <div style="position:absolute;width:14px;height:14px;background:{color};border-radius:50%;top:121px;left:113px;"></div>
        </div>
        <div style="text-align:center;margin-top:10px;">
            <span style="font-size:2rem;font-weight:700;color:{color};">{score}</span>
            <span style="font-size:1rem;color:#6b7280;">/100</span><br>
            <span style="font-size:1.1rem;font-weight:600;color:{color};">{label}</span>
        </div>
        <div style="display:flex;justify-content:space-between;width:220px;margin-top:8px;">
            <span style="font-size:0.78rem;font-weight:600;color:#3b82f6;">● Low</span>
            <span style="font-size:0.78rem;font-weight:600;color:#8b5cf6;">● Medium</span>
            <span style="font-size:0.78rem;font-weight:600;color:#ec4899;">● High</span>
        </div>
    </div>
    """, height=240)

# ─────────────────────────────────────────
# PARAMETER TABLE WITH RANGE CHECK
# ─────────────────────────────────────────
def render_parameter_table(result):
    st.markdown("#### 📋 ECG Parameters — Normal Range Check")
    rows = []
    for key, meta in NORMAL_RANGES.items():
        raw = result.get(key, "Not found")
        try:
            num = float(str(raw).replace("ms","").replace("bpm","").strip())
            display = f"{int(num)} {meta['unit']}"
            in_range = meta["min"] <= num <= meta["max"]
        except:
            display = str(raw)
            in_range = True  # can't check numerically, don't flag

        rows.append({
            "label":   meta["label"],
            "value":   display,
            "range":   f"{meta['min']} – {meta['max']} {meta['unit']}",
            "ok":      in_range
        })

    table_html = """
    <style>
        .ecg-table { width:100%; border-collapse:collapse; font-family:sans-serif; font-size:0.93rem; }
        .ecg-table th { background:#1e3a5f; color:white; padding:10px 14px; text-align:left; }
        .ecg-table td { padding:11px 14px; border-bottom:1px solid #e5e7eb; }
        .ecg-table tr:hover td { background:#f9fafb; }
        .val-normal { color:#16a34a; font-weight:700; }
        .val-abnormal { color:#dc2626; font-weight:700; }
        .range-text { color:#6b7280; font-size:0.82rem; }
        .badge-ok  { background:#dcfce7; color:#166534; border:1px solid #86efac; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
        .badge-bad { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
    </style>
    <table class="ecg-table">
        <thead><tr>
            <th>Parameter</th>
            <th>Value</th>
            <th>Normal Range</th>
            <th>Status</th>
        </tr></thead><tbody>
    """
    for r in rows:
        vc    = "val-normal" if r["ok"] else "val-abnormal"
        badge = '<span class="badge-ok">✓ Normal</span>' if r["ok"] else '<span class="badge-bad">⚠ Out of Range</span>'
        table_html += f"""<tr>
            <td><strong>{r['label']}</strong></td>
            <td class="{vc}">{r['value']}</td>
            <td class="range-text">{r['range']}</td>
            <td>{badge}</td>
        </tr>"""
    table_html += "</tbody></table>"
    st.components.v1.html(table_html, height=len(rows)*52+60, scrolling=False)

# ─────────────────────────────────────────
# CLINICAL FINDINGS CARDS
# ─────────────────────────────────────────
def render_clinical_findings(result):
    st.markdown("#### 🩺 Clinical Findings")
    cards_html = """
    <style>
        .cf-card {
            display:flex; justify-content:space-between; align-items:center;
            padding:11px 16px; margin-bottom:6px;
            border-radius:8px; border:1px solid #e5e7eb;
            background:#f9fafb; font-family:sans-serif;
        }
        .cf-card.abnormal {
            border-color:#fca5a5; background:#fff5f5;
            border-left:4px solid #ef4444;
        }
        .cf-label  { color:#374151; font-size:0.87rem; font-weight:500; }
        .cf-value  { color:#111827; font-size:0.87rem; font-weight:600; }
        .cf-value.abnormal { color:#dc2626; }
    </style>
    """
    for key, label in CLINICAL_FIELDS:
        value = result.get(key, "Not found") or "Not found"
        is_bad = False
        if key in ABNORMAL_TRIGGERS:
            try: is_bad = ABNORMAL_TRIGGERS[key](str(value))
            except: pass
        cls  = "abnormal" if is_bad else ""
        warn = " ⚠️" if is_bad else ""
        cards_html += f"""
        <div class="cf-card {cls}">
            <span class="cf-label">{label}{warn}</span>
            <span class="cf-value {cls}">{value}</span>
        </div>"""
    st.components.v1.html(cards_html, height=len(CLINICAL_FIELDS)*58+20, scrolling=False)

# ─────────────────────────────────────────
# LANDING — shown when nothing uploaded
# ─────────────────────────────────────────
if not uploaded_file:
    st.markdown("""
    ### How to use this tool:
    1. **Get a free API key** from [Google AI Studio](https://aistudio.google.com) *(takes 1 minute)*
    2. **Paste the key** in the sidebar on the left
    3. **Upload** your ECG PDF report
    4. Click **Analyse ECG** and get full clinical results instantly!

    ---
    > ⚠️ *This tool is for educational and portfolio demonstration purposes only.
    > It is not a substitute for professional medical advice.*
    """)

# ── API key warning ──
if uploaded_file and not api_key:
    st.warning("⬅️ Please enter your Gemini API key in the sidebar to continue.")

# ─────────────────────────────────────────
# MAIN ANALYSIS FLOW
# ─────────────────────────────────────────
if uploaded_file and api_key:
    if st.button("🔍 Analyse ECG", use_container_width=True, type="primary"):

        pdf_bytes = uploaded_file.read()

        with st.spinner("Extracting ECG image from PDF..."):
            img_path = extract_image_from_pdf(pdf_bytes)

        st.subheader("📋 Extracted ECG Image")
        st.image(img_path, caption="Extracted from PDF", use_container_width=True)
        st.divider()

        with st.spinner("Analysing ECG — reading text and waveform... (10–20 seconds)"):
            raw = analyse_ecg(img_path, api_key)
        os.unlink(img_path)

        try:
            result = json.loads(raw.strip().replace("```json","").replace("```","").strip())

            st.subheader("📊 ECG Analysis Report")

            # ── Patient Details ──
            st.markdown("#### 🧑 Patient Details")
            col1, col2, col3 = st.columns(3)
            col1.metric("🪪 Patient ID", result.get("patient_id", "N/A"))
            col2.metric("⚧ Gender",      result.get("gender",     "N/A"))
            col3.metric("🎂 Age",         result.get("age",        "N/A"))

            st.divider()

            # ── Risk Gauge + Urgency ──
            st.markdown("#### 🎯 ECG Risk Score")
            st.markdown("*Based on waveform findings*")
            risk = result.get("risk_score", 0)
            try: risk = int(risk)
            except: risk = 0
            render_risk_gauge(risk)

            urgency = result.get("urgency", "Normal")
            urgency_map = {
                "Normal":       "🟢 Normal",
                "Needs Review": "🟡 Needs Review",
                "Urgent":       "🔴 Urgent"
            }
            st.markdown(f"**Status:** {urgency_map.get(urgency, '⚪ ' + urgency)}")

            st.divider()

            # ── Rhythm & Key Findings ──
            st.markdown("#### 🔎 Rhythm & Key Findings")
            st.info(f"**Rhythm:** {result.get('rhythm','N/A')}\n\n{result.get('key_findings','No findings extracted')}")

            st.markdown("**📝 Plain English Summary**")
            st.success(result.get("overall_condition", "No summary available"))

            st.divider()

            # ── Parameter Table (full width) ──
            render_parameter_table(result)

            st.divider()

            # ── Clinical Findings Cards ──
            render_clinical_findings(result)

            st.divider()

            with st.expander("🧑‍💻 View Raw JSON Output"):
                st.json(result)

        except json.JSONDecodeError:
            st.warning("Could not parse AI response. Raw output:")
            st.text(raw)
