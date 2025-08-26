#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Transcription WOW — a FastAPI-based web app for voice recording, file transcription,
low-latency live draft (PCM→WAV), automatic text cleanup/reformatting, and AI-powered
summary + bullet notes. It also performs incremental auto-saves and stores the full
session output on stop under your Desktop folder.

Key features:
- Record from the browser microphone (HTTPS or localhost required)
- Upload existing audio files for transcription
- Live 5s draft preview while speaking (low latency)
- Cleans watermarks and reformats into readable paragraphs
- Generates a concise summary and bullet-point notes
- Automatically saves partial chunks and the final session to:
  Desktop/Transcription WOW

Requirements:
  pip install fastapi uvicorn httpx python-dotenv python-multipart jinja2 openai

Recommended .env:
  OPENAI_API_KEY=sk-...
  OPENAI_TRANSCRIBE_MODEL=gpt-4o-transcribe        # or gpt-4o-mini-transcribe, whisper-1 (slower)
  OPENAI_TEXT_MODEL=gpt-4o-mini
  LOGO_NAME=Gianluca P.
  RELOAD=false
  LIVE_DRAFT_ENABLED=true
  LANGUAGE=it                                       # optional, 2-letter code (e.g., it, en, fr)
  TEMPERATURE=0
  PORT=8000
"""
import os
import re
import json
import time
from typing import List, Dict, Callable, Awaitable, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

# ---------- Setup ----------
load_dotenv()

try:
    import multipart  # noqa: F401
except Exception as e:
    raise RuntimeError("Manca 'python-multipart'. Installa: pip install python-multipart") from e

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY non impostata nel .env")

OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
PREVIEW_TRANSCRIBE_MODEL = os.getenv("PREVIEW_TRANSCRIBE_MODEL", OPENAI_TRANSCRIBE_MODEL)
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

# Normalizza la lingua: accetta solo codici a 2 lettere (es. "it")
def _normalize_lang(val: Optional[str]) -> str:
    if not val:
        return ""
    # estrae le prime 2 lettere alfabetiche e le rende minuscole
    m = re.match(r"([A-Za-z]{2})", val.strip())
    return m.group(1).lower() if m else ""

LANGUAGE = _normalize_lang(os.getenv("LANGUAGE", "it"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
LOGO_NAME = os.getenv("LOGO_NAME", "Gianluca P.")
RELOAD = os.getenv("RELOAD", "false").lower() == "true"
LIVE_DRAFT_ENABLED = os.getenv("LIVE_DRAFT_ENABLED", "true").lower() == "true"

# ---------- Percorso salvataggi Desktop ----------
def _desktop_dir() -> str:
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Scrivania"),  # macOS IT
        os.path.join(home, "Bureau"),     # fr
        os.path.join(home, "Escritorio"), # es
    ]
    for d in candidates:
        if os.path.isdir(d):
            return d
    return home  # fallback

SAVE_ROOT = os.path.join(_desktop_dir(), "Transcription WOW")
os.makedirs(SAVE_ROOT, exist_ok=True)

_SAFE_NAME_RX = re.compile(r"[^A-Za-z0-9._-]+")
def _safe_name(s: Optional[str]) -> str:
    if not s: return "sessione"
    return (_SAFE_NAME_RX.sub("_", s))[:60] or "sessione"

def _save_bytes(content: bytes, sid: Optional[str], filename: str) -> str:
    folder = os.path.join(SAVE_ROOT, _safe_name(sid)) if sid else SAVE_ROOT
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(content)
    print(f"[save] {path} ({len(content)} bytes)")
    return path

def _build_html_document(title: str, logo_name: str, formatted_text: str) -> str:
    """Genera un HTML standalone, gradevole alla lettura/stampa, con paragrafi già formattati."""
    # formatted_text è testo con paragrafi separati da linee vuote
    paras = [p.strip() for p in re.split(r"\n\s*\n", formatted_text.strip()) if p.strip()]
    body_html = []
    for i, p in enumerate(paras):
        if re.match(r"^.{1,70}:\s*$", p):
            heading = re.sub(r":\s*$", "", p)
            body_html.append(f"<h3>{heading}</h3>")
        else:
            cls = ' class="lead"' if i == 0 else ''
            body_html.append(f"<p{cls}>{p}</p>")
    body = "\n".join(body_html)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{logo_name} · {title}</title>
<style>
:root{{ --ink:#111528; --muted:#51607f; --paper:#fff; --pri:#2b59ff; }}
*{{ box-sizing:border-box }}
html,body{{ height:100% }}
body{{
  margin:0; background: #f4f6fb; color:var(--ink);
  font-family: "Newsreader", Georgia, "Times New Roman", serif;
}}
.wrapper{{ max-width: 900px; margin: 28px auto; padding: 0 18px; }}
.header{{ display:flex; align-items:center; gap:10px; margin-bottom:14px; }}
.logo{{ width:18px; height:18px; border-radius:6px; background:linear-gradient(135deg,#6ea8ff,#b16eff); }}
.brand{{ font: 600 14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial; color:#33415c; letter-spacing:.2px }}
.paper{{
  background: var(--paper);
  border-radius: 14px;
  border: 1px solid #e5e9f5;
  box-shadow: 0 14px 45px rgba(22,30,51,.06);
  padding: 34px 40px;
}}
h1{{ margin:0 0 .6rem 0; font-weight:700; font-size: 22px; letter-spacing:.2px }}
.meta{{ margin:0 0 1.2rem 0; color:#6b7aa6; font: 500 13px/1.5 system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
.doc{{ font-size: 20px; line-height: 1.9; letter-spacing:.15px; color:#1b243a; }}
.doc p{{ margin: 0 0 1.05em 0; text-indent: 1.25em; }}
.doc p.lead{{ text-indent: 0; font-size: 1.06em; }}
.doc p.lead::first-letter{{ float:left; font-size:3.1em; line-height:.86; padding-right:.08em; font-weight:600; color:#2b59ff; }}
.doc h3{{
  font-size: .95em; font-weight:700; letter-spacing:.3px; margin: 1.2em 0 .4em;
  text-transform: uppercase; color:#394a76; border-left:3px solid #2b59ff; padding-left:.5em;
}}
@media print {{
  body{{ background:#fff }}
  .paper{{ box-shadow:none; border:none; padding: 0 }}
  .header, .brand, .logo{{ display:none }}
}}
</style>
</head>
<body>
  <div class="wrapper">
    <div class="header"><div class="logo"></div><div class="brand">{logo_name} · Transcription WOW</div></div>
    <div class="paper">
      <h1>{title}</h1>
      <p class="meta">{time.strftime("%d %b %Y · %H:%M:%S")}</p>
      <div class="doc">
        {body}
      </div>
    </div>
  </div>
</body>
</html>"""

# ---------- App ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")

# ---------- Security Headers ----------
@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable[..., Awaitable]):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "media-src 'self' blob:; "
        "frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "microphone=(self)"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

# ---------- Helpers testo ----------
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')

def to_sentences(s: str) -> List[str]:
    s = re.sub(r'\s+', ' ', (s or '').strip())
    if not s:
        return []
    parts = _SENT_SPLIT.split(s)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", p)
        if len(tokens) <= 2 and len(p) < 10 and out:
            out[-1] = (out[-1] + ' ' + p).strip()
        else:
            out.append(p)
    return [x for x in out if x]

def paragraphs_from_sentences(sents: List[str], max_sent_per_para=3) -> List[str]:
    paras, buf = [], []
    for s in sents:
        buf.append(s)
        if len(buf) >= max_sent_per_para or s.endswith(("?!", "!?")):
            paras.append(" ".join(buf)); buf = []
    if buf:
        paras.append(" ".join(buf))
    return paras

# Watermark/jolly
_BAD_WM = [
    re.compile(r"\bsottotitoli\s+(?:creati|a\s*cura|realizzati|forniti)\s+(?:da(?:lla|l)?\s*)?.*", re.I),
    re.compile(r"\bsottotitoli\s+(?:a\s*cura\s+di)\s*.*", re.I),
    re.compile(r"\bsottotitoli\s+.*", re.I),
    re.compile(r"\bsubtitles?\s+(?:by|created|provided)\b.*", re.I),
    re.compile(r"\bcaptions?\s+(?:by|created|provided)\b.*", re.I),
    re.compile(r"(?:comunit[àa].{0,20})?amara\.org", re.I),
]
_JOLLY_RX = [
    re.compile(r"al prossimo episodio\.?$", re.I),
    re.compile(r"alla prossima\.?$", re.I),
    re.compile(r"grazie per l'attenzione\.?$", re.I),
    re.compile(r"fine\.?$", re.I),
    re.compile(r"the end\.?$", re.I),
]

def sanitize_text(s: str) -> str:
    if not s:
        return ""
    t = s
    for rx in _BAD_WM:
        t = rx.sub(" ", t)
    lines = []
    for ln in re.split(r"[\r\n]+", t):
        if re.search(r"^\s*(?:-|\(|\[)?\s*sottotitoli\b", ln, re.I):
            continue
        lines.append(ln)
    t = "\n".join(lines)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([,.!?;:])", r"\1", t)
    t = t.strip()
    if t:
        t_norm = t.lower().strip()
        if len(t_norm.split()) <= 5:
            for rx in _JOLLY_RX:
                if rx.search(t_norm):
                    return ""
    return t

# ---------- httpx logging ----------
async def _log_request(req: httpx.Request):
    # Evita caratteri non ASCII per compatibilità con terminali non UTF-8
    try:
        print(f"[httpx] -> {req.method} {req.url}")
    except Exception:
        # Fallback ultra-conservativo
        try:
            m = getattr(req, "method", "?")
            u = getattr(req, "url", "?")
            print("[httpx] ->", m, u)
        except Exception:
            pass

async def _log_response(res: httpx.Response):
    # Evita caratteri non ASCII per compatibilità con terminali non UTF-8
    try:
        print(f"[httpx] <- {res.status_code} {res.request.url}")
    except Exception:
        try:
            sc = getattr(res, "status_code", "?")
            rq = getattr(res, "request", None)
            ru = getattr(rq, "url", "?") if rq is not None else "?"
            print("[httpx] <-", sc, ru)
        except Exception:
            pass

def new_httpx_client(timeout: int = 180) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        event_hooks={"request": [_log_request], "response": [_log_response]},
    )

# ---------- OpenAI helpers ----------
async def openai_transcribe(content: bytes, filename: str, content_type: str, *, model: str, preview: bool=False) -> dict:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {"file": (filename or "audio.wav", content, content_type or "application/octet-stream")}
    prompt = (
        "Trascrivi fedelmente in italiano. "
        "Se l'audio è silenzioso/rumoroso o non contiene parlato, restituisci stringa vuota."
    )
    if preview:
        prompt += " Rispondi telegrafico e non inserire punteggiatura incerta."

    data = {
        "model": model,
        # "language" accettato solo se a 2 lettere
        # verrà aggiunto sotto se valido
        "temperature": str(TEMPERATURE),
        "response_format": "json",
        "prompt": prompt,
    }
    if LANGUAGE:  # solo se passato il filtro a 2 lettere
        data["language"] = LANGUAGE

    async with new_httpx_client(timeout=60 if preview else 300) as client:
        r = await client.post(f"{OPENAI_API_BASE}/audio/transcriptions", headers=headers, files=files, data=data)
        r.raise_for_status()
        payload = r.json()
    text = (payload.get("text") or "").strip()
    return {"text": text}

async def openai_summarize_and_notes(text: str) -> Dict:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    sys = (
        "Sei un assistente che crea un riassunto conciso e note puntate da una trascrizione italiana. "
        "Stile chiaro e naturale. Non inventare contenuti. "
        'Restituisci SOLO JSON con chiavi: "summary" (3-6 frasi) e "notes" (5-10 voci brevi).'
    )
    body = {
        "model": OPENAI_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    try:
        async with new_httpx_client(timeout=120) as client:
            r = await client.post(f"{OPENAI_API_BASE}/chat/completions", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            obj = json.loads(data["choices"][0]["message"]["content"])
            summary = (obj.get("summary") or "").strip()
            notes = [n for n in (obj.get("notes") or []) if isinstance(n, str) and n.strip()]
            return {"summary": summary, "notes": notes[:10]}
    except Exception:
        sents = to_sentences(text)
        summary = " ".join(sents[:5])
        return {"summary": summary, "notes": sents[5:10]}

# ---------- Routes ----------
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "logo_name": LOGO_NAME, "live_draft": LIVE_DRAFT_ENABLED},
    )

@app.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    title: str = Form("Trascrizione"),
    sid: str = Form(None),
    part: int = Form(None),
):
    content = await file.read()
    if not content:
        return JSONResponse({"error": "File vuoto"}, status_code=400)
    if len(content) < 2048:
        return JSONResponse({"text": "", "formatted": ""})

    # Salvataggio automatico su Desktop
    name_ext = os.path.splitext(file.filename or "")[1].lower() or ".wav"
    ts = time.strftime("%Y%m%d_%H%M%S")
    if sid:
        base = _safe_name(sid)
        if part is not None:
            fname = f"{base}_part{int(part):03d}{name_ext}"
        else:
            fname = f"{base}_{ts}{name_ext}"
    else:
        fname = f"rec_{ts}{name_ext}"
    _save_bytes(content, sid, fname)

    # Transcribe
    try:
        result = await openai_transcribe(
            content,
            file.filename or "audio.wav",
            file.content_type or "audio/wav",
            model=OPENAI_TRANSCRIBE_MODEL,
            preview=False,
        )
    except httpx.HTTPStatusError as e:
        return JSONResponse({"error": "OpenAI error", "detail": e.response.text}, status_code=500)

    clean = sanitize_text(result.get("text") or "")
    if not clean:
        return JSONResponse({"text": "", "formatted": ""})

    sents = to_sentences(clean)
    paras = paragraphs_from_sentences(sents, max_sent_per_para=3)
    formatted = "\n\n".join(paras)

    # ---- Salva anche il testo formattato in HTML accanto all'audio (per la singola parte) ----
    try:
        if sid:
            base = _safe_name(sid)
            if part is not None:
                text_fname = f"{base}_part{int(part):03d}.html"
            else:
                text_fname = f"{base}_{ts}.html"
        else:
            text_fname = f"rec_{ts}.html"

        html_doc = _build_html_document(title or "Trascrizione", LOGO_NAME, formatted)
        _save_bytes(html_doc.encode("utf-8"), sid, text_fname)
    except Exception as _e:
        print("[warn] Salvataggio HTML part fallito:", _e)

    return JSONResponse({"text": clean, "formatted": formatted})

@app.post("/upload_preview")
async def upload_preview(file: UploadFile = File(...)):
    """Anteprima live: WAV 16k mono di ~5s, risposta telegrafica."""
    content = await file.read()
    print(f"[/upload_preview] recv name={file.filename} ct={file.content_type} size={len(content) if content else 0}")
    if not content or len(content) < 2048:
        return JSONResponse({"text": ""})
    try:
        result = await openai_transcribe(
            content,
            file.filename or "preview.wav",
            file.content_type or "audio/wav",
            model=PREVIEW_TRANSCRIBE_MODEL,
            preview=True,
        )
    except httpx.HTTPStatusError:
        return JSONResponse({"text": ""})
    clean = sanitize_text(result.get("text") or "")
    return JSONResponse({"text": clean[:200]})

@app.post("/save_audio")
async def save_audio(file: UploadFile = File(...), sid: str = Form(None)):
    """Salva un file audio così com'è (usato per il file completo allo stop)."""
    content = await file.read()
    if not content:
        return JSONResponse({"error": "File vuoto"}, status_code=400)
    name_ext = os.path.splitext(file.filename or "")[1].lower() or ".wav"
    ts = time.strftime("%Y%m%d_%H%M%S")
    if sid:
        base = _safe_name(sid)
        fname = f"{base}_full{name_ext}"
    else:
        fname = f"rec_{ts}_full{name_ext}"
    path = _save_bytes(content, sid, fname)
    return JSONResponse({"saved": True, "path": path})

@app.post("/summarize")
async def summarize(payload: Dict):
    text = (payload or {}).get("text") or ""
    if not text.strip():
        return JSONResponse({"summary": "", "notes": []})
    try:
        out = await openai_summarize_and_notes(text)
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse({"summary": "", "notes": [], "error": str(e)}, status_code=500)

@app.post("/save_text")
async def save_text(payload: Dict):
    """Salva il documento completo della sessione come HTML formattato su Desktop."""
    text = (payload or {}).get("text") or ""
    sid = (payload or {}).get("sid")
    title = ((payload or {}).get("title") or "Trascrizione completa").strip() or "Trascrizione completa"

    # Log utile per capire cosa arriva dal client
    print(f"[/save_text] sid={sid!r} title={title!r} chars={len(text)}")

    # Anche se il testo è vuoto, salviamo comunque un HTML per coerenza con il file audio full
    clean = sanitize_text(text)
    sents = to_sentences(clean)
    paras = paragraphs_from_sentences(sents, max_sent_per_para=3)
    formatted = "\n\n".join(paras) if paras else (clean if clean else "(documento vuoto)")

    ts = time.strftime("%Y%m%d_%H%M%S")
    if sid:
        base = _safe_name(sid)
        fname = f"{base}_full.html"
    else:
        fname = f"rec_{ts}_full.html"

    try:
        html_doc = _build_html_document(title, LOGO_NAME, formatted)
        path = _save_bytes(html_doc.encode("utf-8"), sid, fname)
        print(f"[/save_text] saved: {path}")
        return JSONResponse({"saved": True, "path": path})
    except Exception as e:
        print(f"[/save_text] error: {e}")
        return JSONResponse({"saved": False, "error": str(e)}, status_code=500)

# ---------- Run ----------
if __name__ == "__main__":
    import uvicorn, sys
    port = int(os.getenv("PORT", "8000"))
    print(f"==> Avvio su http://127.0.0.1:{port} (reload={'on' if RELOAD else 'off'})")
    if RELOAD:
        module_name = os.path.splitext(os.path.basename(__file__))[0]
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        uvicorn.run(f"{module_name}:app", host="127.0.0.1", port=port, reload=True, log_level="info")
    else:
        uvicorn.run(app, host="127.0.0.1", port=port, reload=False, log_level="info")
