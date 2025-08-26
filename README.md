# 🎤 Transcription WOW ➡️ ✍️  

### Trascrizione e riassunto automatico di audio con l’AI  
*(Prototipo didattico realizzato in Python + FastAPI + OpenAI)*

---

## 🔎 Cos’è
**Transcription WOW** è una piccola **web-app locale** che:
- registra l’audio dal microfono,
- lo invia all’AI di OpenAI,
- restituisce una **trascrizione testuale** e un **riassunto automatico**.

👉 È nata come **prototipo didattico**: mostra come integrare Python, un backend web moderno (FastAPI) e un frontend HTML+JS con servizi di AI.

---

## 🎯 Obiettivo del progetto
Non è un prodotto “pronto per tutti”, ma un esempio pratico.  
Serve a dimostrare:
- come si costruisce un prototipo funzionante da zero,
- come usare **FastAPI** per creare un servizio web,
- come integrare le **API di OpenAI** in un’applicazione reale,
- come un docente può guidare dall’idea al prototipo completo.

---

## 🚀 Come provarla (guida rapida)

### 1. Requisiti
- **Python 3.11+**
- Un account [OpenAI](https://platform.openai.com/) con **API key attiva**

### 2. Clona e installa

```bash

git clone https://github.com/gianlucapassarella/transcription_wow.git

cd transcription_wow

python -m venv .venv

source .venv/bin/activate   # su Windows: .venv\Scripts\activate

pip install -r requirements.txt

```

### 3. Configura la tua API key

Crea un file .env nella cartella principale con dentro:

```bash

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
OPENAI_TRANSCRIBE_MODEL=gpt-4o-transcribe   # or whisper-1, gpt-4o-mini-transcribe
OPENAI_TEXT_MODEL=gpt-4o-mini
LOGO_NAME=YourName
RELOAD=false
LIVE_DRAFT_ENABLED=true
LANGUAGE=it          # optional, 2-letter code (en, it, fr...)
TEMPERATURE=0
PORT=8000

```
### 4. Avvia il server
```bash

uvicorn transcription_wow:app --reload

```

Vai su 👉 http://127.0.0.1:8000
Ti troverai davanti l’interfaccia web per registrare e trascrivere.

## 🖼️ Screenshot

![Transcription WOW UI](assets/screenshot.jpg)

## 🎥 Demo

[![Watch the demo](https://img.youtube.com/vi/pChOhweECEY/0.jpg)](https://youtu.be/pChOhweECEY)




## ⚠️ Nota importante
È un prototipo didattico, non un prodotto commerciale.

Ogni utente deve usare la propria API key (non sono inclusi crediti).

L’app salva i file in locale sulla macchina dove gira il server.

## 📚 Tecnologie usate
Python 3.11
FastAPI
HTML + JavaScript
OpenAI API


## 📜 Licenza
Distribuito sotto licenza MIT – libero uso, modifica e condivisione.

#### 🏫 Progetto realizzato da Gianluca Passarella come esempio di laboratorio e dimostrazione didattica.