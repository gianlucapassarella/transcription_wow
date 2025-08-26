# 📖 Guida all’uso

## 🌐 Apri nel browser
- Avvia il server e apri:  
  [http://127.0.0.1:8000](http://127.0.0.1:8000)

💡 **Suggerimento:** per la registrazione dal microfono usa **HTTPS** oppure `http://localhost`.

---

## 🖥️ Dall’interfaccia web
- **🎙️ Record** → avvia una sessione di registrazione  
- **⏸ Pausa / ▶ Riprendi** → gestisci una registrazione in corso  
- **⏹ Stop & Transcribe** → interrompe e trascrive l’ultimo blocco, salvando anche il file completo  
- **⬆ Upload** → carica un file audio già presente sul disco  
- **🤖 AI Insights** → genera e aggiorna un riassunto + punti elenco dal testo cumulativo  

👉 Tutti i file vengono salvati automaticamente in:  
`Desktop/Transcription WOW/<sessione>/`

---

## 🔒 Sicurezza
- Middleware configurato con **CSP**, **Referrer-Policy** e **X-Content-Type-Options**  
- CORS attualmente aperto (`allow_origins=["*"]`) per semplicità  
- ⚠ Per l’uso in produzione: restringere CORS e rimuovere `'unsafe-inline'` quando JS e CSS saranno separati  

---

## 🛠 Risoluzione dei problemi
- **403 / microfono negato** → usa HTTPS o `http://localhost`  
- **Errore: `python-multipart` mancante** → esegui `pip install python-multipart`  
- **Nessun file salvato** → controlla la cartella Desktop e i permessi di scrittura  
- **Errori API** → verifica `OPENAI_API_KEY` e i nomi dei modelli nel file `.env`  

---

## 🗺 Roadmap
- Miglioramento del **VAD** (Voice Activity Detection) con avvio/arresto automatici intelligenti  
- **Riconoscimento automatico della lingua**  
- **Diarizzazione parlanti** (etichette dei parlatori con timestamp)  
- **Download ZIP** dell’intera sessione  
- Test di base (**unit test**) + pipeline CI  

---

## 📜 Licenza
Scegli una licenza (es. **MIT**) e aggiungi un file `LICENSE` al repository.
