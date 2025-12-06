# Easy 2.0 - Sistema di Gestione CSV e Estrazione Dati

Applicazione Flask per la trasformazione di file CSV e l'estrazione di dati da OData.

## 🚀 Deployment su Vercel

L'applicazione è configurata per il deployment automatico su Vercel. Per maggiori dettagli, consulta:
- [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md) - Guida completa al deployment
- [VERCEL_MONGODB_SETUP.md](VERCEL_MONGODB_SETUP.md) - Configurazione MongoDB su Vercel

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
- La cartella `uploads/` viene creata automaticamente
- Assicurati di non committare file sensibili (credenziali, ecc.)
- Le credenziali MongoDB devono essere configurate come variabili d'ambiente su Vercel

