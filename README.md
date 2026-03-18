ECG AI AGENT
----------------------------------------------------------------------------------------------------------------------------------------
An AI-powered ECG report analyser that extracts patient information and interprets ECG findings from PDF reports using Google Gemini Vision API.
----------------------------------------------------------------------------------------------------------------------------------------
## Architecture
```
User uploads ECG PDF
↓
PyMuPDF extracts page 1 as high-res PNG (2x zoom)
↓
Image sent to Gemini 2.5 Flash Vision API
↓
Gemini reads printed text + interprets waveform
↓
Returns structured JSON
↓
Streamlit displays patient info + ECG findings
```
## Features
- Extracts ECG waveform from uploaded PDF
- Reads printed measurements and visually interprets waveform using Gemini
- Detects rhythm, ST segment, AV conduction, ectopics
- Normal range validation for HR, PR, QRS, QT, QTc
- Risk score with Low / Medium / High classification
- Urgency status — Normal / Needs Review / Urgent
- Raw JSON output for debugging

## Future Scope
- FHIR API integration with hospital ECG machines
- EHR connection for patient history cross-reference
- Automated cardiologist alerting on STEMI detection
- Multi-turn conversational agent for follow-up queries
- Formula-based explainable risk scoring
- Audit trail for clinical compliance

## How to Use

### Step 1 — Open the app
Click the Streamlit app link:
https://ecgagent-qvuqejw3szdaq2tn5tujej.streamlit.app/

### Step 2 — Upload your ECG report
- Click **Browse files** or drag and drop your ECG PDF
- Supported format: `.pdf` only

### Step 3 — Analyse
- Click the **🔍 Analyse ECG** button
- Wait 10–20 seconds while the AI reads the report

### Step 4 — View results
You will see:
- Patient details (ID, age, gender)
- ECG risk score and urgency status
- Rhythm and key findings
- ECG parameter table with normal range check
- Clinical findings with abnormality flags

> ⚠️ If you see a rate limit error, wait 1–2 minutes and try again.
> This is a free API quota limit from Google Gemini.

##Demo - Screenshots

<img width="500" height="500" alt="Screenshot 2026-03-18 at 12 30 47 pm" src="https://github.com/user-attachments/assets/08eccea8-6fa8-4a0d-b122-71a0da97fd18" />
<img width="500" height="500" alt="Screenshot 2026-03-18 at 12 31 04 pm" src="https://github.com/user-attachments/assets/cc15f665-4f15-4cc9-8117-fbaedb0f505e" />
<img width="500" height="500" alt="Screenshot 2026-03-18 at 12 31 19 pm" src="https://github.com/user-attachments/assets/49658be3-17f9-47da-a7b1-c948fdb1ba0b" />
<img width="500" height="500" alt="Screenshot 2026-03-18 at 12 31 27 pm" src="https://github.com/user-attachments/assets/7fae3540-431c-4ce5-9983-3286291c08e7" />
<img width="500" height="500" alt="Screenshot 2026-03-18 at 12 31 37 pm" src="https://github.com/user-attachments/assets/a18c0cf5-a653-40b1-b119-87019bdca874" />




