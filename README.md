# Easy 2.0 - Sistema di Gestione CSV e Estrazione Dati

Applicazione Flask per la trasformazione di file CSV e l'estrazione di dati da OData.

## 🚀 Deployment su Railway

L'applicazione è configurata per il deployment automatico su Railway. Railway supporta file fino a **100MB** (molto più di Vercel che aveva solo 4.5MB).

### Primo Deployment

1. Vai su [Railway](https://railway.app) e crea un account
2. Clicca su "New Project" → "Deploy from GitHub repo"
3. Seleziona il repository `Easy2.0`
4. Railway rileverà automaticamente Python e installerà le dipendenze
5. Configura le variabili d'ambiente (vedi sotto)

### Variabili d'Ambiente su Railway

Vai su **Settings** → **Variables** e aggiungi:

- `MONGODB_URI`: La tua connection string MongoDB (es: `mongodb+srv://user:pass@cluster.mongodb.net/`)
- `MONGODB_DB_NAME`: Nome del database (default: `easyloading`)
- `SECRET_KEY`: Chiave segreta per Flask (genera una stringa casuale)
- `PORT`: Railway lo imposta automaticamente, non modificare

### Deployment Automatico

Railway esegue automaticamente il deployment ogni volta che fai un push su GitHub:
```bash
git add .
git commit -m "Descrizione delle modifiche"
git push
```

Railway rileverà automaticamente le modifiche e farà il redeploy.

### HTTPS

Railway fornisce automaticamente HTTPS gratuito per tutti i servizi. Non è necessaria alcuna configurazione aggiuntiva.

## 📁 Struttura del Progetto

```
Easy2.0/
├── app.py                 # Applicazione Flask principale
├── storage.py             # Modulo per storage persistente (MongoDB)
├── requirements.txt       # Dipendenze Python
├── railway.json           # Configurazione Railway
├── Procfile               # Comando di avvio per Railway
├── templates/            # Template HTML
├── static/              # File statici (CSS, JS, immagini)
├── uploads/             # File caricati (creato automaticamente)
└── odata_config.json    # Configurazione OData
```

## 🔧 Configurazione Locale

Per testare localmente:

```bash
# Installa le dipendenze
pip install -r requirements.txt

# Avvia il server
python app.py
```

L'applicazione sarà disponibile su `http://localhost:5004`

## 📝 Note

- I dati vengono salvati in **MongoDB Atlas** per persistenza tra i deployment
- Gli upload CSV vengono salvati direttamente in MongoDB
- File fino a 20MB: upload diretto in MongoDB
- File più grandi: upload in chunk automatico (1.5MB per chunk, Base64)
- La cartella `uploads/` viene creata automaticamente solo per file temporanei
- Assicurati di non committare file sensibili (credenziali, ecc.)
- Le credenziali MongoDB devono essere configurate come variabili d'ambiente su Railway

## 🔗 Link Utili

- [Railway Dashboard](https://railway.app/dashboard)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [Documentazione Railway](https://docs.railway.app)
