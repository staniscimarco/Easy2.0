# 🚀 Guida al Deployment su Render

## Perché Render invece di Vercel?

- ✅ **Supporto nativo per Flask**: Render supporta direttamente applicazioni Python/Flask
- ✅ **HTTPS automatico**: Certificati SSL gratuiti e automatici
- ✅ **Deployment automatico**: Ogni push su GitHub attiva automaticamente un nuovo deployment
- ✅ **File system persistente**: I file JSON e uploads vengono salvati e persistono
- ✅ **Piano gratuito disponibile**: Perfetto per iniziare

## 📋 Passo-passo per il Deployment

### 1. Prepara il Repository GitHub

Se non hai ancora un repository GitHub:

```bash
# Inizializza git (se non l'hai già fatto)
git init

# Aggiungi tutti i file
git add .

# Fai il primo commit
git commit -m "Initial commit - Ready for deployment"

# Crea il repository su GitHub (vai su github.com e crea un nuovo repo)
# Poi collega il repository locale:
git remote add origin https://github.com/TUO_USERNAME/Easy2.0.git
git branch -M main
git push -u origin main
```

### 2. Crea Account su Render

1. Vai su [render.com](https://render.com)
2. Clicca su "Get Started for Free"
3. Registrati con GitHub (consigliato per deployment automatico)

### 3. Crea un Nuovo Web Service

1. Nel dashboard Render, clicca su **"New +"** → **"Web Service"**
2. Seleziona **"Connect GitHub"** e autorizza Render ad accedere ai tuoi repository
3. Seleziona il repository **Easy2.0**

### 4. Configura il Servizio

Compila i seguenti campi:

- **Name**: `easyloading` (o un nome a tua scelta)
- **Environment**: `Python 3`
- **Region**: Scegli la regione più vicina (es. Frankfurt per l'Europa)
- **Branch**: `main` (o il branch che vuoi usare)
- **Root Directory**: (lascia vuoto)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Plan**: 
  - **Free**: Gratuito, ma il servizio va in "sleep" dopo 15 minuti di inattività
  - **Starter ($7/mese)**: Sempre attivo, più veloce

### 5. Configura Variabili d'Ambiente (Opzionale ma Consigliato)

Nella sezione **"Environment"**, aggiungi:

- **Key**: `SECRET_KEY`
- **Value**: Genera una chiave segreta (usa questo comando Python):
  ```python
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

### 6. Deploy!

1. Clicca su **"Create Web Service"**
2. Render inizierà automaticamente:
   - Installazione delle dipendenze
   - Build dell'applicazione
   - Avvio del servizio
3. Attendi 2-5 minuti per il primo deployment
4. Il tuo sito sarà disponibile su: `https://easyloading.onrender.com` (o il nome che hai scelto)

## 🔄 Deployment Automatico

Dopo il primo deployment, ogni volta che fai un push su GitHub:

```bash
git add .
git commit -m "Descrizione delle modifiche"
git push
```

Render rileverà automaticamente le modifiche e:
1. Farà un nuovo build
2. Testerà l'applicazione
3. Se tutto va bene, farà il deploy della nuova versione

Puoi vedere lo stato del deployment nel dashboard Render.

## 🔒 HTTPS

Render fornisce **automaticamente HTTPS** per tutti i servizi. Non serve configurazione aggiuntiva!

Il tuo sito sarà disponibile su:
- `https://easyloading.onrender.com` (HTTPS automatico)

## 📊 Monitoraggio

Nel dashboard Render puoi:
- Vedere i log in tempo reale
- Monitorare l'uso delle risorse
- Vedere lo stato del servizio
- Configurare alert via email

## 🛠️ Troubleshooting

### Il servizio non si avvia
- Controlla i log nel dashboard Render
- Verifica che `requirements.txt` contenga tutte le dipendenze
- Assicurati che `gunicorn` sia nella lista delle dipendenze

### Errori 500
- Controlla i log per vedere l'errore specifico
- Verifica che tutti i file necessari siano nel repository
- Assicurati che le variabili d'ambiente siano configurate correttamente

### Il servizio va in "sleep"
- Sui piani gratuiti, Render mette in sleep i servizi dopo 15 minuti di inattività
- Il primo accesso dopo il sleep può richiedere 30-60 secondi per "svegliare" il servizio
- Per evitare il sleep, considera il piano Starter ($7/mese)

## 💡 Consigli

1. **Backup**: I file JSON vengono salvati nel filesystem di Render. Considera di fare backup periodici
2. **Monitoraggio**: Controlla regolarmente i log per identificare problemi
3. **Performance**: Se il servizio è lento, considera di passare al piano Starter
4. **Sicurezza**: Usa sempre una `SECRET_KEY` forte in produzione

## 📞 Supporto

- [Documentazione Render](https://render.com/docs)
- [Community Render](https://community.render.com)

