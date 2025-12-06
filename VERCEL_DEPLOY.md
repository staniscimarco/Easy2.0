# Deploy su Vercel

## Prerequisiti

1. Account Vercel (gratuito): https://vercel.com
2. Repository GitHub connesso

## Deploy Automatico da GitHub

1. Vai su https://vercel.com e accedi con GitHub
2. Clicca su "Add New Project"
3. Seleziona il repository `Easy2.0`
4. Vercel rileverà automaticamente che è un progetto Python
5. Configurazione:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (root del progetto)
   - **Build Command**: (lascia vuoto o `pip install -r requirements.txt`)
   - **Output Directory**: (lascia vuoto)
6. Aggiungi variabili d'ambiente (se necessario):
   - `SECRET_KEY`: una chiave segreta per Flask
   - `FLASK_ENV`: `production`
7. Clicca "Deploy"

## Deploy Manuale con Vercel CLI

```bash
# Installa Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel

# Deploy in produzione
vercel --prod
```

## Note Importanti

- **File System**: Su Vercel (serverless), il filesystem è read-only tranne `/tmp`
- I file JSON vengono salvati in `/tmp/uploads` su Vercel
- I file in `/tmp` sono temporanei e vengono eliminati dopo ogni invocazione
- Per dati persistenti, considera di usare un database (es. Vercel Postgres, Supabase, etc.)

## Limitazioni Vercel Free Tier

- 100GB bandwidth/mese
- Funzioni serverless con timeout di 10 secondi (Hobby) o 60 secondi (Pro)
- Deploy illimitati
- HTTPS automatico

## Miglioramenti Consigliati

Per dati persistenti, considera:
1. **Vercel Postgres** (database integrato)
2. **Supabase** (database PostgreSQL gratuito)
3. **Upstash Redis** (cache/key-value store)
4. **Cloudflare R2** (storage S3-compatible)

