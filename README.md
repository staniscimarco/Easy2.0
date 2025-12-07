# Easy 2.0 - Sistema di Gestione CSV e Estrazione Dati

Applicazione Flask per la trasformazione di file CSV e l'estrazione di dati da OData.

## 🚀 Deployment su Vercel

L'applicazione è configurata per il deployment automatico su Vercel.

### Primo Deployment

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard) e crea un account
2. Clicca su "New Project" → "Import Git Repository"
3. Seleziona il repository `Easy2.0`
4. Vercel rileverà automaticamente Python e installerà le dipendenze
5. Configura le variabili d'ambiente (vedi sotto)

### Variabili d'Ambiente su Vercel

Vai su **Settings** → **Environment Variables** e aggiungi:

**Obbligatorie:**
- `MONGODB_URI`: La tua connection string MongoDB (es: `mongodb+srv://user:pass@cluster.mongodb.net/`)
- `MONGODB_DB_NAME`: Nome del database (default: `easyloading`)
- `SECRET_KEY`: Chiave segreta per Flask (genera una stringa casuale)

**Per file > 4.5MB (AWS S3):**
- `S3_ACCESS_KEY_ID`: La tua AWS Access Key ID
- `S3_SECRET_ACCESS_KEY`: La tua AWS Secret Access Key
- `S3_BUCKET_NAME`: Nome del bucket S3 (default: `chatpdfgpt`)
- `AWS_REGION`: Regione AWS (default: `eu-west-1`)

**Nota**: `PORT` viene impostato automaticamente da Vercel, non modificare.

### Deployment Automatico

Vercel esegue automaticamente il deployment ogni volta che fai un push su GitHub:
```bash
git add .
git commit -m "Descrizione delle modifiche"
git push
```

Vercel rileverà automaticamente le modifiche e farà il redeploy.

### HTTPS

Vercel fornisce automaticamente HTTPS gratuito per tutti i servizi. Non è necessaria alcuna configurazione aggiuntiva.

## 📁 Struttura del Progetto

```
Easy2.0/
├── app.py                 # Applicazione Flask principale
├── storage.py             # Modulo per storage persistente (MongoDB)
├── s3_storage.py          # Modulo per upload su AWS S3 (file > 4.5MB)
├── requirements.txt       # Dipendenze Python
├── vercel.json            # Configurazione Vercel
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
- **File <= 4.5MB**: Upload diretto in MongoDB
- **File > 4.5MB**: Upload su **AWS S3** (bypass limite Vercel)
- La cartella `uploads/` viene creata automaticamente solo per file temporanei
- Assicurati di non committare file sensibili (credenziali, ecc.)
- Le credenziali MongoDB e AWS devono essere configurate come variabili d'ambiente su Vercel

## 🔗 Link Utili

- [Vercel Dashboard](https://vercel.com/dashboard)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [AWS S3 Console](https://console.aws.amazon.com/s3/)
- [Documentazione Vercel](https://vercel.com/docs)
