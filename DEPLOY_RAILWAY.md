# Guida al Deployment su Railway

Questa guida ti aiuterà a deployare Easy 2.0 su Railway.

## Prerequisiti

- Account GitHub
- Account Railway (gratuito)
- Account MongoDB Atlas (gratuito)

## Step 1: Setup MongoDB Atlas

1. Vai su [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Crea un cluster gratuito (M0)
3. Crea un utente database (username e password)
4. Aggiungi il tuo IP (o `0.0.0.0/0` per permettere tutti gli IP)
5. Copia la connection string (es: `mongodb+srv://user:pass@cluster.mongodb.net/`)

## Step 2: Deploy su Railway

### Opzione A: Deploy da GitHub (Consigliato)

1. Vai su [Railway Dashboard](https://railway.app/dashboard)
2. Clicca su **"New Project"**
3. Seleziona **"Deploy from GitHub repo"**
4. Autorizza Railway ad accedere al tuo GitHub
5. Seleziona il repository `Easy2.0`
6. Railway rileverà automaticamente Python e inizierà il build

### Opzione B: Deploy da CLI

```bash
# Installa Railway CLI
npm i -g @railway/cli

# Login
railway login

# Inizializza progetto
railway init

# Deploy
railway up
```

## Step 3: Configura Variabili d'Ambiente

1. Vai su Railway Dashboard → Il tuo progetto
2. Clicca su **Settings** → **Variables**
3. Aggiungi le seguenti variabili:

| Variabile | Valore | Descrizione |
|-----------|--------|-------------|
| `MONGODB_URI` | `mongodb+srv://...` | Connection string MongoDB |
| `MONGODB_DB_NAME` | `easyloading` | Nome database (opzionale) |
| `SECRET_KEY` | `una-chiave-segreta-casuale` | Chiave segreta Flask |

**Nota**: `PORT` viene impostato automaticamente da Railway, non aggiungerlo.

## Step 4: Verifica il Deploy

1. Vai su **Settings** → **Networking**
2. Clicca su **"Generate Domain"** per ottenere un URL pubblico
3. Apri l'URL nel browser
4. Dovresti vedere la homepage di Easy 2.0

## Step 5: Test MongoDB

1. Vai su `https://tuo-dominio.railway.app/api/test_mongodb`
2. Dovresti vedere un messaggio di successo se MongoDB è configurato correttamente

## Deployment Automatico

Railway esegue automaticamente il deployment ogni volta che fai un push su GitHub:

```bash
git add .
git commit -m "Descrizione modifiche"
git push
```

Railway rileverà le modifiche e farà il redeploy automaticamente.

## Troubleshooting

### Build Fallisce

- Verifica che `requirements.txt` sia presente e corretto
- Controlla i log su Railway Dashboard → **Deployments** → **View Logs**

### MongoDB Non Connette

- Verifica che `MONGODB_URI` sia corretto
- Verifica che l'IP di Railway sia whitelistato su MongoDB Atlas
- Controlla i log dell'applicazione

### Porta Non Trovata

- Railway imposta automaticamente `PORT`, non modificarlo
- Verifica che `Procfile` sia presente e corretto

### File Upload Non Funziona

- Railway supporta file fino a 100MB
- Verifica che MongoDB sia configurato correttamente
- Controlla i log per errori specifici

## Limitazioni Railway

- **Piano Gratuito**: 500 ore/mese, 512MB RAM, 1GB storage
- **Piano Pro**: $20/mese, risorse illimitate
- **File Upload**: Fino a 100MB (molto più di Vercel!)

## Supporto

- [Railway Docs](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [MongoDB Atlas Docs](https://docs.atlas.mongodb.com)

