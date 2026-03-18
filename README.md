ECG AI Analyser
----------------------------------------------------------------------------------------------------------------------------------------
An AI-powered ECG report analyser that extracts patient information and interprets ECG findings from PDF reports using Google Gemini Vision API.
----------------------------------------------------------------------------------------------------------------------------------------


Architecture

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
