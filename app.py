
import streamlit as st
import google.generativeai as genai
import fitz 
import json
import tempfile
import os
import io
import time
from PIL import Image

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="ECG Analyser",
    layout="centered"
)

# ─────────────────────────────────────────
# GLOBAL STYLES
# ─────────────────────────────────────────
st.markdown("""
<style>
    /* Top accent bar */
    .top-bar {
        background: linear-gradient(90deg, #1e3a5f 0%, #2563eb 100%);
        border-radius: 10px;
        padding: 18px 28px 14px 28px;
        margin-bottom: 6px;
    }
    .top-bar h1 { color: white; font-size: 1.8rem; font-weight: 800; margin: 0; }
    .top-bar p  { color: #bfdbfe; font-size: 0.95rem; margin: 4px 0 0 0; }

    /* Patient card wrapper */
    .patient-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 8px;
    }

    /* Risk + status card */
    .risk-card {
        border-radius: 10px;
        padding: 14px 20px;
        border-left: 5px solid;
        background: #f8fafc;
        margin-bottom: 4px;
    }

    /* Key findings card */
    .findings-card {
        background: #f0f7ff;
        border: 1px solid #bfdbfe;
        border-left: 5px solid #2563eb;
        border-radius: 10px;
        padding: 16px 20px;
        font-family: sans-serif;
        font-size: 0.93rem;
        line-height: 1.6;
        color: #1e3a5f;
        margin-bottom: 4px;
    }
    .findings-card strong { color: #1d4ed8; }

    /* Footer */
    .footer {
        text-align: center;
        color: #9ca3af;
        font-size: 0.78rem;
        margin-top: 32px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
st.sidebar.markdown("Get your free API key from [Google AI Studio](https://aistudio.google.com)")
api_key = st.secrets.get("GEMINI_API_KEY", "") or st.sidebar.text_input(
    "Gemini API Key", type="password", placeholder="Paste your key here"
)

# ─────────────────────────────────────────
# HEADER BANNER
# ─────────────────────────────────────────
st.markdown("""
<div class="top-bar">
    <h1>ECG Analyser</h1>
    <p>Upload an ECG report PDF and get a complete clinical analysis powered by AI</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ✅ File uploader
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
# PDF → IMAGE
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

    for attempt in range(3):
        try:
            response = model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            err = str(e)
            if "ResourceExhausted" in err or "429" in err or "quota" in err.lower():
                if attempt < 2:
                    wait = 30 * (attempt + 1)
                    st.warning(f"⏳ Gemini API rate limit hit. Retrying in {wait} seconds... (attempt {attempt + 1}/3)")
                    time.sleep(wait)
                else:
                    st.error("❌ Gemini API quota exhausted. Please wait a few minutes and try again, or check your API key limits at https://aistudio.google.com")
                    st.stop()
            else:
                raise e

# ─────────────────────────────────────────
# PARAMETER TABLE
# ─────────────────────────────────────────
def render_parameter_table(result):
    st.markdown("#### ECG Parameters — Range")
    rows = []
    for key, meta in NORMAL_RANGES.items():
        raw = result.get(key, "Not found")
        try:
            num = float(str(raw).replace("ms","").replace("bpm","").strip())
            display = f"{int(num)} {meta['unit']}"
            in_range = meta["min"] <= num <= meta["max"]
        except:
            display = str(raw)
            in_range = True

        rows.append({
            "label": meta["label"],
            "value": display,
            "range": f"{meta['min']} – {meta['max']} {meta['unit']}",
            "ok":    in_range
        })

    table_html = """
    <style>
        .ecg-table { width:100%; border-collapse:collapse; font-family:sans-serif; font-size:0.93rem; border-radius:10px; overflow:hidden; }
        .ecg-table th { background:#1e40af; color:white; padding:11px 16px; text-align:left; font-weight:600; letter-spacing:0.03em; }
        .ecg-table td { padding:11px 16px; border-bottom:1px solid #e5e7eb; }
        .ecg-table tr:nth-child(even) td { background:#f8fafc; }
        .ecg-table tr:nth-child(odd)  td { background:#ffffff; }
        .ecg-table tr:hover td { background:#eff6ff; }
        .val-normal   { color:#16a34a; font-weight:700; }
        .val-abnormal { color:#dc2626; font-weight:700; }
        .range-text   { color:#6b7280; font-size:0.82rem; }
        .badge-ok  { background:#dcfce7; color:#166534; border:1px solid #86efac; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:600; }
        .badge-bad { background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; padding:3px 12px; border-radius:20px; font-size:0.75rem; font-weight:600; }
    </style>
    <table class="ecg-table">
        <thead><tr>
            <th>Parameter</th><th>Value</th><th>Normal Range</th><th>Status</th>
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
            background:#ffffff; font-family:sans-serif;
        }
        .cf-card.abnormal {
            border-color:#fca5a5; background:#fff5f5;
            border-left:4px solid #ef4444;
        }
        .cf-card.normal { border-left:4px solid #22c55e; }
        .cf-label { color:#374151; font-size:0.87rem; font-weight:500; display:flex; align-items:center; gap:8px; }
        .cf-value { color:#111827; font-size:0.87rem; font-weight:600; }
        .cf-value.abnormal { color:#dc2626; }
        .dot-ok  { width:9px; height:9px; border-radius:50%; background:#22c55e; display:inline-block; flex-shrink:0; }
        .dot-bad { width:9px; height:9px; border-radius:50%; background:#ef4444; display:inline-block; flex-shrink:0; }
    </style>
    """
    for key, label in CLINICAL_FIELDS:
        value = result.get(key, "Not found") or "Not found"
        is_bad = False
        if key in ABNORMAL_TRIGGERS:
            try: is_bad = ABNORMAL_TRIGGERS[key](str(value))
            except: pass
        card_cls  = "abnormal" if is_bad else "normal"
        dot_cls   = "dot-bad" if is_bad else "dot-ok"
        val_cls   = "abnormal" if is_bad else ""
        cards_html += f"""
        <div class="cf-card {card_cls}">
            <span class="cf-label"><span class="{dot_cls}"></span>{label}</span>
            <span class="cf-value {val_cls}">{value}</span>
        </div>"""
    st.components.v1.html(cards_html, height=len(CLINICAL_FIELDS)*58+20, scrolling=False)

# ─────────────────────────────────────────
# LANDING
# ─────────────────────────────────────────
if not uploaded_file:
    st.markdown("""
    ### How to use this tool:
    1. **Upload** your ECG PDF report
    2. Click **Analyse ECG** and get full clinical results instantly!
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

        st.subheader("Extracted ECG Image")
        st.image(img_path, caption="Extracted from PDF", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            with st.spinner("Analysing ECG — reading text and waveform... (10–20 seconds)"):
                raw = analyse_ecg(img_path, api_key)
        except Exception as e:
            os.unlink(img_path)
            st.error(f"❌ Analysis failed: {str(e)}")
            st.stop()
        os.unlink(img_path)

        try:
            result = json.loads(raw.strip().replace("
json","").replace("
","").strip())

            st.subheader("📊 ECG Analysis Report")
            st.markdown("<br>", unsafe_allow_html=True)

            # ── Patient Details ──
            st.markdown("#### Patient Details")
            st.markdown('<div class="patient-card">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("Patient ID", result.get("patient_id", "N/A"))
            col2.metric("Gender",      result.get("gender",     "N/A"))
            col3.metric("Age",         result.get("age",        "N/A"))
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Risk Score + Status ──
            risk = result.get("risk_score", 0)
            try: risk = int(risk)
            except: risk = 0
            risk_color = "#16a34a" if risk <= 30 else ("#d97706" if risk <= 60 else "#dc2626")
            risk_label = "Low Risk" if risk <= 30 else ("Medium Risk" if risk <= 60 else "High Risk")
            urgency = result.get("urgency", "Normal")
            urgency_map = {
                "Normal":       "🟢 Normal",
                "Needs Review": "🟡 Needs Review",
                "Urgent":       "🔴 Urgent"
            }
            st.components.v1.html(
                f'<div style="border-left:5px solid {risk_color};background:#f8fafc;border-radius:10px;padding:14px 20px;font-family:sans-serif;margin-bottom:8px;">'
                f'<div style="font-size:0.82rem;color:#6b7280;font-weight:500;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">ECG Risk Score</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{risk_color};">{risk} <span style="font-size:1rem;font-weight:600;">/ 100</span> &nbsp;—&nbsp; {risk_label}</div>'
                f'<div style="font-size:0.9rem;color:#374151;margin-top:6px;font-weight:500;">Status: {urgency_map.get(urgency, "⚪ " + urgency)}</div>'
                f'</div>',
                height=110
            )
 
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Rhythm & Key Findings ──
            st.markdown("#### 🔎 Rhythm & Key Findings")
            rhythm  = result.get("rhythm", "N/A")
            findings = result.get("key_findings", "No findings extracted")
            st.markdown(
                f'<div class="findings-card">'
                f'<strong>Rhythm:</strong> {rhythm}<br><br>{findings}'
                f'</div>',
                unsafe_allow_html=True
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Parameter Table ──
            render_parameter_table(result)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Clinical Findings Cards ──
            render_clinical_findings(result)

            st.markdown("<br>", unsafe_allow_html=True)

            with st.expander("View Raw JSON Output"):
                st.json(result)

            # ── Footer ──
            st.markdown(
                '<div class="footer">⚕️ For educational and demonstration purposes only. '
                'Not a substitute for professional clinical judgment or medical advice.</div>',
                unsafe_allow_html=True
            )

        except json.JSONDecodeError:
            st.warning("Could not parse AI response. Raw output:")
            st.text(raw)
