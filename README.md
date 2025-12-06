# Easyloading - Sistema di Gestione CSV e Estrazione Dati

Applicazione Flask per la trasformazione di file CSV e l'estrazione di dati da OData.

## 🚀 Deployment su Render

### Prerequisiti
1. Account su [Render.com](https://render.com) (gratuito)
2. Repository GitHub del progetto

### Passaggi per il Deployment

1. **Prepara il repository GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/TUO_USERNAME/Easy2.0.git
   git push -u origin main
   ```

2. **Crea un nuovo servizio su Render**
   - Vai su [Render Dashboard](https://dashboard.render.com)
   - Clicca su "New +" → "Web Service"
   - Connetti il tuo repository GitHub
   - Seleziona il repository `Easy2.0`

3. **Configura il servizio**
   - **Name**: `easyloading` (o un nome a tua scelta)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (o Starter per più risorse)

4. **Variabili d'Ambiente (opzionali)**
   - `SECRET_KEY`: Genera una chiave segreta per Flask (puoi usare: `python -c "import secrets; print(secrets.token_hex(32))"`)

5. **Deploy**
   - Clicca su "Create Web Service"
   - Render inizierà automaticamente il build e il deployment
   - Il tuo sito sarà disponibile su `https://easyloading.onrender.com` (o il nome che hai scelto)

### Deployment Automatico

Render esegue automaticamente il deployment ogni volta che fai un push su GitHub:
```bash
git add .
git commit -m "Descrizione delle modifiche"
git push
```

Render rileverà automaticamente le modifiche e farà il redeploy.

### HTTPS

Render fornisce automaticamente HTTPS gratuito per tutti i servizi. Non è necessaria alcuna configurazione aggiuntiva.

## 📁 Struttura del Progetto

```
Easy2.0/
├── app.py                 # Applicazione Flask principale
├── requirements.txt       # Dipendenze Python
├── Procfile              # Comando di avvio per Render
├── render.yaml           # Configurazione Render (opzionale)
├── templates/            # Template HTML
├── static/              # File statici (CSS, JS, immagini)
├── uploads/             # File caricati (creato automaticamente)
├── anagrafica.json      # Dati anagrafica
├── odata_config.json    # Configurazione OData
└── odata_cache.json     # Cache estrazioni OData
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

- I file JSON (`anagrafica.json`, `odata_cache.json`) vengono salvati nel filesystem e persistono tra i deployment su Render
- La cartella `uploads/` viene creata automaticamente
- Assicurati di non committare file sensibili (credenziali, ecc.)

