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
    page_title="CardioScan AI — ECG Analysis System",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    * { font-family: 'IBM Plex Sans', sans-serif !important; }
    .stApp { background: #0a0f1e !important; color: #e2e8f0 !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    section[data-testid="stSidebar"] { background: #0d1425 !important; border-right: 1px solid #1e3a5f !important; }
    section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] .stTextInput input { background: #1a2540 !important; border: 1px solid #2d4a7a !important; color: #e2e8f0 !important; border-radius: 6px !important; }
    section[data-testid="stSidebar"] h1 { color: #38bdf8 !important; font-size: 1rem !important; font-weight: 600 !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; }
    [data-testid="stFileUploader"] { background: #111827 !important; border: 2px dashed #1e3a5f !important; border-radius: 12px !important; padding: 20px !important; }
    [data-testid="stFileUploader"]:hover { border-color: #38bdf8 !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #0ea5e9, #0284c7) !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 1rem !important; letter-spacing: 0.03em !important; padding: 14px 28px !important; transition: all 0.2s ease !important; box-shadow: 0 4px 15px rgba(14,165,233,0.3) !important; }
    .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #38bdf8, #0ea5e9) !important; box-shadow: 0 6px 20px rgba(14,165,233,0.5) !important; transform: translateY(-1px) !important; }
    [data-testid="stMetric"] { background: #111827 !important; border: 1px solid #1e3a5f !important; border-radius: 10px !important; padding: 16px !important; }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.75rem !important; font-weight: 500 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }
    [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stExpander"] { background: #111827 !important; border: 1px solid #1e3a5f !important; border-radius: 10px !important; }
    .stSpinner > div { border-top-color: #38bdf8 !important; }
    hr { border-color: #1e3a5f !important; margin: 24px 0 !important; }
    [data-testid="stImage"] img { border-radius: 12px !important; border: 1px solid #1e3a5f !important; }
    [data-testid="stJson"] { background: #0d1425 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# TOP NAV BAR
# ─────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(90deg,#0d1425 0%,#0f1f3d 100%);border-bottom:1px solid #1e3a5f;
    padding:0 32px;display:flex;align-items:center;justify-content:space-between;height:64px;
    position:sticky;top:0;z-index:999;">
    <div style="display:flex;align-items:center;gap:14px;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,#0ea5e9,#0369a1);
            border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;">🫀</div>
        <div>
            <div style="color:#e2e8f0;font-size:1.1rem;font-weight:700;letter-spacing:0.02em;">CardioScan AI</div>
            <div style="color:#38bdf8;font-size:0.7rem;font-weight:500;letter-spacing:0.12em;text-transform:uppercase;">ECG Analysis System</div>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:24px;">
        <div style="display:flex;align-items:center;gap:8px;">
            <div style="width:8px;height:8px;background:#22c55e;border-radius:50%;box-shadow:0 0 6px #22c55e;"></div>
            <span style="color:#64748b;font-size:0.8rem;">System Online</span>
        </div>
        <div style="color:#64748b;font-size:0.8rem;font-family:'IBM Plex Mono',monospace;">v2.0.0</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 0 10px 0;">
        <div style="color:#38bdf8;font-size:0.7rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:16px;">
            ⚙️ Configuration
        </div>
    </div>
    """, unsafe_allow_html=True)

    api_key = st.secrets.get("GEMINI_API_KEY", "") or st.text_input(
        "GEMINI API KEY", type="password", placeholder="AIza••••••••••••••••••••"
    )

    st.markdown("""
    <div style="margin-top:8px;">
        <a href="https://aistudio.google.com" target="_blank"
            style="color:#38bdf8;font-size:0.78rem;text-decoration:none;">↗ Get free API key</a>
    </div>
    <hr style="border-color:#1e3a5f;margin:24px 0;">
    <div style="color:#38bdf8;font-size:0.7rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:12px;">
        📖 How to Use
    </div>
    <div style="color:#64748b;font-size:0.82rem;line-height:1.8;">
        <div style="margin-bottom:6px;">① Enter API key above</div>
        <div style="margin-bottom:6px;">② Upload ECG PDF report</div>
        <div style="margin-bottom:6px;">③ Click Run ECG Analysis</div>
        <div>④ Review clinical report</div>
    </div>
    <hr style="border-color:#1e3a5f;margin:24px 0;">
    <div style="background:#0c1a2e;border:1px solid #1e3a5f;border-left:3px solid #f59e0b;
        border-radius:8px;padding:12px;font-size:0.75rem;color:#94a3b8;line-height:1.6;">
        ⚠️ For educational use only. Not a substitute for professional medical diagnosis.
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# STANDARD RANGES & CLINICAL FIELDS
# ─────────────────────────────────────────
NORMAL_RANGES = {
    "heart_rate":   {"min": 60,  "max": 100, "unit": "bpm", "label": "Heart Rate"},
    "pr_interval":  {"min": 120, "max": 200, "unit": "ms",  "label": "PR Interval"},
    "qrs_duration": {"min": 70,  "max": 110, "unit": "ms",  "label": "QRS Duration"},
    "qt_interval":  {"min": 350, "max": 440, "unit": "ms",  "label": "QT Interval"},
    "qtc_interval": {"min": 350, "max": 450, "unit": "ms",  "label": "QTc Interval"},
}

CLINICAL_FIELDS = [
    ("ecg_quality",          "ECG Quality"),
    ("ventricular_rate",     "Ventricular Rate"),
    ("pr_interval",          "PR Interval"),
    ("qrs_duration",         "QRS Duration"),
    ("qtc_interval",         "QTc Interval"),
    ("cardiac_axis",         "Cardiac Axis"),
    ("sinus_rhythm",         "Sinus Rhythm Present"),
    ("other_rhythm",         "Other Rhythm"),
    ("atrial_pause",         "Atrial Pause > 2 seconds"),
    ("av_conduction",        "AV Conduction"),
    ("ventricular_ectopics", "Ventricular Ectopics"),
    ("atrial_ectopics",      "Atrial Ectopics"),
    ("p_wave_morphology",    "P-Wave Morphology"),
    ("qrs_morphology",       "QRS Morphology"),
    ("q_wave",               "Q-Wave"),
    ("t_wave_morphology",    "T-Wave Morphology"),
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
# HELPER FUNCTIONS
# ─────────────────────────────────────────
def section_header(icon, title, subtitle=""):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin:28px 0 16px 0;">
        <div style="width:34px;height:34px;background:linear-gradient(135deg,#0ea5e9,#0369a1);
            border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">{icon}</div>
        <div>
            <div style="color:#e2e8f0;font-size:1rem;font-weight:600;">{title}</div>
            {"<div style='color:#475569;font-size:0.78rem;margin-top:1px;'>"+subtitle+"</div>" if subtitle else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)


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
        combined.paste(img, (0, y)); y += img.height
    img_path = tmp_path.replace(".pdf", ".png")
    combined.save(img_path)
    doc.close(); os.unlink(tmp_path)
    return img_path


def analyse_ecg(image_path, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    image = Image.open(image_path)
    prompt = """
    You are a clinical ECG analysis assistant used in a hospital setting.
    Carefully read ALL text and waveform data in this ECG report image.
    For numeric fields return ONLY the number (no units).
    If not visible write "Not found".
    risk_score 0-100: 0-30 low, 31-60 medium, 61-100 high risk.
    Return ONLY valid JSON, no markdown, no explanation:
    {
        "patient_name":"","patient_id":"","age":"","gender":"","date_of_birth":"","recorded_on":"",
        "heart_rate":"","pr_interval":"","qrs_duration":"","qt_interval":"","qtc_interval":"",
        "ecg_quality":"","ventricular_rate":"","cardiac_axis":"","sinus_rhythm":"","other_rhythm":"",
        "atrial_pause":"","av_conduction":"","ventricular_ectopics":"","atrial_ectopics":"",
        "p_wave_morphology":"","qrs_morphology":"","q_wave":"","t_wave_morphology":"","st_segment":"",
        "rhythm":"","key_findings":"","overall_condition":"","urgency":"","risk_score":45
    }
    """
    return model.generate_content([prompt, image]).text


def render_risk_gauge(score):
    score = max(0, min(100, int(score)))
    color = "#22c55e" if score <= 30 else ("#f59e0b" if score <= 60 else "#ef4444")
    label = "Low Risk" if score <= 30 else ("Medium Risk" if score <= 60 else "High Risk")
    rotation = -90 + (score / 100) * 180
    st.components.v1.html(f"""
    <div style="display:flex;flex-direction:column;align-items:center;padding:10px 0;">
        <div style="position:relative;width:200px;height:105px;overflow:hidden;">
            <div style="position:absolute;width:180px;height:180px;border-radius:50%;top:10px;left:10px;
                background:conic-gradient(#22c55e 0deg 54deg,#f59e0b 54deg 108deg,#ef4444 108deg 180deg,#1e3a5f 180deg 360deg);"></div>
            <div style="position:absolute;width:120px;height:120px;background:#111827;border-radius:50%;top:40px;left:40px;"></div>
            <div style="position:absolute;width:3px;height:76px;background:{color};border-radius:3px;
                top:26px;left:99px;transform-origin:bottom center;transform:rotate({rotation}deg);
                box-shadow:0 0 8px {color};"></div>
            <div style="position:absolute;width:12px;height:12px;background:{color};border-radius:50%;
                top:97px;left:94px;box-shadow:0 0 6px {color};"></div>
        </div>
        <div style="text-align:center;margin-top:10px;">
            <span style="font-size:2.2rem;font-weight:700;color:{color};font-family:'IBM Plex Mono',monospace;">{score}</span>
            <span style="font-size:0.9rem;color:#475569;">/100</span><br>
            <span style="font-size:0.9rem;font-weight:600;color:{color};letter-spacing:0.05em;">{label}</span>
        </div>
        <div style="display:flex;justify-content:space-between;width:180px;margin-top:6px;">
            <span style="font-size:0.7rem;color:#22c55e;">LOW</span>
            <span style="font-size:0.7rem;color:#f59e0b;">MED</span>
            <span style="font-size:0.7rem;color:#ef4444;">HIGH</span>
        </div>
    </div>
    """, height=190)


def render_parameter_table(result):
    rows = []
    for key, meta in NORMAL_RANGES.items():
        raw = result.get(key, "Not found")
        try:
            num = float(str(raw).replace("ms","").replace("bpm","").strip())
            display = f"{int(num)} {meta['unit']}"
            in_range = meta["min"] <= num <= meta["max"]
        except:
            display = str(raw); in_range = True
        rows.append({"label": meta["label"], "value": display,
                     "range": f"{meta['min']} – {meta['max']} {meta['unit']}", "ok": in_range})

    html = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        .pt{width:100%;border-collapse:collapse;font-family:'IBM Plex Sans',sans-serif;}
        .pt thead tr{background:#0d1f3c;}
        .pt thead th{padding:12px 16px;text-align:left;color:#38bdf8;font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;border-bottom:1px solid #1e3a5f;}
        .pt tbody tr{border-bottom:1px solid #1a2a45;transition:background 0.15s;}
        .pt tbody tr:hover{background:#0d1f3c;}
        .pt tbody td{padding:13px 16px;font-size:0.88rem;color:#cbd5e1;}
        .pt .param{font-weight:600;color:#e2e8f0;}
        .pt .val-ok{color:#22c55e;font-weight:700;font-family:'IBM Plex Mono',monospace;}
        .pt .val-bad{color:#ef4444;font-weight:700;font-family:'IBM Plex Mono',monospace;}
        .pt .range{color:#475569;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;}
        .badge-ok{background:#052e16;color:#22c55e;border:1px solid #166534;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;}
        .badge-bad{background:#2d0808;color:#ef4444;border:1px solid #7f1d1d;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;}
    </style>
    <table class="pt">
        <thead><tr><th>Parameter</th><th>Measured Value</th><th>Normal Range</th><th>Status</th></tr></thead>
        <tbody>"""
    for r in rows:
        vc = "val-ok" if r["ok"] else "val-bad"
        badge = '<span class="badge-ok">✓ Normal</span>' if r["ok"] else '<span class="badge-bad">⚠ Abnormal</span>'
        html += f'<tr><td class="param">{r["label"]}</td><td class="{vc}">{r["value"]}</td><td class="range">{r["range"]}</td><td>{badge}</td></tr>'
    html += "</tbody></table>"
    st.components.v1.html(html, height=len(rows)*52+58, scrolling=False)


def render_clinical_findings(result):
    cards_html = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
        .cf-card{font-family:'IBM Plex Sans',sans-serif;display:flex;justify-content:space-between;align-items:center;
            padding:12px 18px;margin-bottom:6px;border-radius:8px;border:1px solid #1e3a5f;background:#0d1425;transition:all 0.15s;}
        .cf-card:hover{background:#111f3a;}
        .cf-card.abnormal{border-color:#7f1d1d;background:#1a0808;border-left:3px solid #ef4444;}
        .cf-label{color:#94a3b8;font-size:0.85rem;font-weight:500;}
        .cf-label.abnormal{color:#fca5a5;}
        .cf-value{color:#e2e8f0;font-size:0.85rem;font-weight:600;}
        .cf-value.abnormal{color:#ef4444;}
    </style>"""
    for key, label in CLINICAL_FIELDS:
        value = result.get(key, "Not found") or "Not found"
        is_bad = False
        if key in ABNORMAL_TRIGGERS:
            try: is_bad = ABNORMAL_TRIGGERS[key](str(value))
            except: pass
        cls = "abnormal" if is_bad else ""
        warn = " ⚠️" if is_bad else ""
        cards_html += f"""
        <div class="cf-card {cls}">
            <span class="cf-label {cls}">{label}{warn}</span>
            <span class="cf-value {cls}">{value}</span>
        </div>"""
    st.components.v1.html(cards_html, height=len(CLINICAL_FIELDS)*58+30, scrolling=False)

# ─────────────────────────────────────────
# MAIN CONTENT — uploaded_file defined HERE first
# This is the fix: widget is always called unconditionally
# ─────────────────────────────────────────
st.markdown("<div style='padding:32px 40px;'>", unsafe_allow_html=True)

section_header("📁", "Upload ECG Report", "Supports single and multi-page PDF reports")

# ✅ FILE UPLOADER — defined at top level, always runs
uploaded_file = st.file_uploader(
    "Drop your ECG PDF here or click to browse",
    type=["pdf"],
    label_visibility="collapsed"
)

# ── Landing cards — shown only when nothing uploaded ──
if not uploaded_file:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1f3c,#0a1628);border:1px solid #1e3a5f;
        border-radius:16px;padding:48px;text-align:center;margin:24px 0 32px 0;">
        <div style="font-size:3rem;margin-bottom:16px;">🫀</div>
        <h1 style="color:#e2e8f0;font-size:1.8rem;font-weight:700;margin:0 0 8px 0;">CardioScan AI</h1>
        <p style="color:#38bdf8;font-size:0.9rem;letter-spacing:0.1em;text-transform:uppercase;margin:0 0 20px 0;">
            Clinical ECG Analysis System</p>
        <p style="color:#64748b;font-size:0.95rem;max-width:480px;margin:0 auto;line-height:1.7;">
            Upload an ECG PDF report for instant AI-powered analysis including patient details,
            clinical measurements, rhythm interpretation, and risk assessment.</p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    for col, icon, title, desc in [
        (col_a, "📄", "Multi-page PDF",    "Auto-detects ECG page from any report format"),
        (col_b, "🔬", "Clinical Analysis", "17 clinical parameters with normal range checks"),
        (col_c, "🎯", "Risk Scoring",      "AI-generated risk score with visual gauge"),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:#0d1425;border:1px solid #1e3a5f;border-radius:12px;padding:24px;text-align:center;">
                <div style="font-size:1.8rem;margin-bottom:10px;">{icon}</div>
                <div style="color:#e2e8f0;font-weight:600;font-size:0.95rem;margin-bottom:6px;">{title}</div>
                <div style="color:#475569;font-size:0.8rem;line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

# ── API key warning ──
if uploaded_file and not api_key:
    st.markdown("""
    <div style="background:#1c1000;border:1px solid #92400e;border-radius:10px;
        padding:14px 18px;color:#fbbf24;font-size:0.88rem;margin-top:12px;">
        ⬅️ Please enter your Gemini API key in the sidebar to continue.
    </div>
    """, unsafe_allow_html=True)

# ── Analysis ──
if uploaded_file and api_key:
    if st.button("🔍 Run ECG Analysis", use_container_width=True, type="primary"):

        pdf_bytes = uploaded_file.read()

        with st.spinner("Extracting ECG image from PDF..."):
            img_path = extract_image_from_pdf(pdf_bytes)

        section_header("🖼", "Extracted ECG Report", f"Source: {uploaded_file.name}")
        st.image(img_path, use_container_width=True)

        with st.spinner("AI analysing ECG... this takes 5–15 seconds"):
            raw = analyse_ecg(img_path, api_key)
        os.unlink(img_path)

        try:
            result = json.loads(raw.strip().replace("```json","").replace("```","").strip())

            # ── Patient Banner ──
            st.markdown(f"""
            <div style="background:linear-gradient(90deg,#0d1f3c,#0f2a4a);border:1px solid #1e3a5f;
                border-radius:12px;padding:20px 28px;margin:24px 0;
                display:flex;align-items:center;gap:24px;">
                <div style="width:52px;height:52px;background:linear-gradient(135deg,#0ea5e9,#0369a1);
                    border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">👤</div>
                <div style="flex:1;">
                    <div style="color:#e2e8f0;font-size:1.2rem;font-weight:700;">{result.get('patient_name','Unknown Patient')}</div>
                    <div style="color:#64748b;font-size:0.82rem;margin-top:3px;">
                        ID: {result.get('patient_id','—')} &nbsp;·&nbsp;
                        {result.get('gender','—')} &nbsp;·&nbsp;
                        Age: {result.get('age','—')} &nbsp;·&nbsp;
                        DOB: {result.get('date_of_birth','—')}
                    </div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <div style="color:#475569;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em;">Recorded</div>
                    <div style="color:#94a3b8;font-size:0.85rem;font-weight:500;margin-top:2px;">{result.get('recorded_on','—')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Patient Metrics ──
            section_header("🧑", "Patient Details")
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("Name",        result.get("patient_name","—"))
            c2.metric("Patient ID",  result.get("patient_id","—"))
            c3.metric("Gender",      result.get("gender","—"))
            c4.metric("Age",         result.get("age","—"))
            c5.metric("DOB",         result.get("date_of_birth","—"))
            c6.metric("Recorded",    result.get("recorded_on","—"))

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Table + Gauge ──
            left, right = st.columns([3, 2])
            with left:
                section_header("📋", "ECG Parameter Analysis", "Values checked against clinical normal ranges")
                render_parameter_table(result)
            with right:
                section_header("🎯", "Risk Assessment")
                risk = result.get("risk_score", 0)
                try: risk = int(risk)
                except: risk = 0
                render_risk_gauge(risk)

                urgency = result.get("urgency","Normal")
                urg_cfg = {
                    "Normal":       ("#052e16","#22c55e","#166534","✓ Normal"),
                    "Needs Review": ("#1c1000","#f59e0b","#92400e","⚠ Needs Review"),
                    "Urgent":       ("#2d0808","#ef4444","#7f1d1d","🚨 Urgent"),
                }.get(urgency, ("#052e16","#22c55e","#166534","✓ Normal"))

                st.markdown(f"""
                <div style="background:{urg_cfg[0]};border:1px solid {urg_cfg[2]};border-radius:10px;
                    padding:14px 18px;text-align:center;margin-top:8px;">
                    <div style="color:{urg_cfg[1]};font-size:1rem;font-weight:700;">{urg_cfg[3]}</div>
                    <div style="color:#475569;font-size:0.75rem;margin-top:4px;text-transform:uppercase;letter-spacing:0.08em;">Clinical Status</div>
                </div>
                <div style="background:#0d1425;border:1px solid #1e3a5f;border-radius:10px;padding:16px 18px;margin-top:12px;">
                    <div style="color:#38bdf8;font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;">Primary Rhythm</div>
                    <div style="color:#e2e8f0;font-size:0.9rem;font-weight:600;">{result.get('rhythm','—')}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Findings + Summary ──
            section_header("🔎", "Clinical Interpretation")
            fi, su = st.columns(2)
            with fi:
                st.markdown(f"""
                <div style="background:#0d1425;border:1px solid #1e3a5f;border-left:3px solid #38bdf8;
                    border-radius:10px;padding:18px;">
                    <div style="color:#38bdf8;font-size:0.72rem;font-weight:600;letter-spacing:0.1em;
                        text-transform:uppercase;margin-bottom:10px;">Key Findings</div>
                    <div style="color:#cbd5e1;font-size:0.88rem;line-height:1.7;">{result.get('key_findings','No findings extracted')}</div>
                </div>
                """, unsafe_allow_html=True)
            with su:
                st.markdown(f"""
                <div style="background:#052e16;border:1px solid #166534;border-left:3px solid #22c55e;
                    border-radius:10px;padding:18px;">
                    <div style="color:#22c55e;font-size:0.72rem;font-weight:600;letter-spacing:0.1em;
                        text-transform:uppercase;margin-bottom:10px;">Plain English Summary</div>
                    <div style="color:#bbf7d0;font-size:0.88rem;line-height:1.7;">{result.get('overall_condition','No summary available')}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── Clinical Findings ──
            section_header("🩺", "Detailed Clinical Findings", "17 parameters with abnormality detection")
            render_clinical_findings(result)

            st.markdown("<hr>", unsafe_allow_html=True)

            with st.expander("🧑‍💻 Raw JSON Output — Developer View"):
                st.json(result)

            st.markdown("""
            <div style="background:#0d1425;border:1px solid #1e3a5f;border-radius:10px;
                padding:14px 20px;margin-top:16px;text-align:center;color:#475569;font-size:0.78rem;line-height:1.6;">
                ⚠️ This report is generated by an AI system for educational and demonstration purposes only.
                All findings must be reviewed and confirmed by a qualified medical professional.
            </div>
            """, unsafe_allow_html=True)

        except json.JSONDecodeError:
            st.warning("Could not parse AI response. Raw output:")
            st.text(raw)

st.markdown("</div>", unsafe_allow_html=True)
