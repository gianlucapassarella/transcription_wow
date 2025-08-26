# 📖 Usage Guide

## 🌐 Open in browser
- Start the server and open:  
  [http://127.0.0.1:8000](http://127.0.0.1:8000)

💡 **Tip:** For microphone recording, use **HTTPS** or `http://localhost`.

---

## 🖥️ From the Web UI
- **🎙️ Record** → start a recording session  
- **⏸ Pause / ▶ Resume** → manage ongoing recording  
- **⏹ Stop & Transcribe** → finalize and transcribe the last block, also saves the complete file  
- **⬆ Upload** → send an existing audio file from disk  
- **🤖 AI Insights** → generates and updates summary + bullet notes from cumulative text  

👉 All files are saved automatically under:  
`Desktop/Transcription WOW/<session>/`

---

## ⚡ API Endpoints
- `GET /` → returns the main web UI  
- `POST /upload` → upload an audio block, transcribe + format  
  - **form-data params:** `file`, `title`, `sid`, `part`  
- `POST /upload_preview` → quick live preview (~5s WAV, telegraphic response)  
- `POST /save_audio` → save the complete audio file  
- `POST /summarize` → generate summary + notes (JSON)  
- `POST /save_text` → save the full transcript as formatted HTML  

### Example responses:
```json
# /upload
{ "text": "raw transcription...", "formatted": "clean paragraphs..." }

# /summarize
{ "summary": "short summary...", "notes": ["point 1", "point 2"] }
```

---

## 💾 File storage on Desktop
The app automatically creates a folder:

```
Desktop/TrascrizioniWOW/
  ├── <session>_partNNN.wav
  ├── <session>_partNNN.html
  ├── <session>_full.wav
  └── <session>_full.html
```

---

## 🔒 Security
- CSP, Referrer-Policy, and X-Content-Type-Options set via middleware  
- CORS currently open (`allow_origins=["*"]`) for simplicity  
- ⚠ For production: restrict CORS and remove `'unsafe-inline'` once JS/CSS are separated  

---

## 🛠 Troubleshooting
- **403 / microphone denied** → use HTTPS or `http://localhost`  
- **Error: `python-multipart` missing** → run `pip install python-multipart`  
- **No files saved** → check Desktop folder and write permissions  
- **API errors** → verify `OPENAI_API_KEY` and model names in `.env`  

---

## 🗺 Roadmap
- More robust **VAD** (Voice Activity Detection) with smart auto start/stop  
- **Automatic language detection**  
- **Speaker diarization** (speaker labels with timestamps)  
- **Download ZIP** for the entire session  
- Basic **unit tests + CI pipeline**  

---

## 📜 License
Choose a license (e.g., **MIT**) and add a `LICENSE` file to the repo.
