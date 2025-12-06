# 🚀 Deploy su Vercel - Guida Completa

## ✅ Deploy Automatico

Vercel fa il **deploy automatico** ogni volta che fai push su GitHub. Se hai già collegato il repository, il deploy dovrebbe essere già in corso!

## 📋 Verifica Deploy

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Seleziona il progetto **Easy2.0**
3. Vai su **Deployments**
4. Dovresti vedere l'ultimo deploy in corso o completato

## 🔄 Deploy Manuale (se necessario)

Se il deploy automatico non funziona:

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Seleziona il progetto **Easy2.0**
3. Vai su **Deployments**
4. Clicca sui **tre puntini** sull'ultimo deploy
5. Seleziona **Redeploy**

## 🔗 Collegare Repository (se non ancora fatto)

Se non hai ancora collegato il repository:

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Clicca su **Add New...** → **Project**
3. Seleziona **Import Git Repository**
4. Scegli **GitHub** e autorizza Vercel
5. Seleziona il repository **Easy2.0**
6. Vercel rileverà automaticamente:
   - **Framework Preset**: Other
   - **Build Command**: (lasciare vuoto o `pip install -r requirements.txt`)
   - **Output Directory**: (lasciare vuoto)
   - **Install Command**: (lasciare vuoto)
7. Clicca su **Deploy**

## ⚙️ Configurazione Progetto

Assicurati che queste variabili d'ambiente siano configurate:

1. Vai su **Settings** → **Environment Variables**
2. Aggiungi:
   - `MONGODB_URI`: `mongodb+srv://staniscimarco_db_user:wRVnY9xafcVFWdLH@cluster0.dznab1r.mongodb.net/?retryWrites=true&w=majority`
   - `MONGODB_DB_NAME`: `easyloading`
   - `FLASK_ENV`: `production`
   - `VERCEL`: `1`

## 📊 Verifica Deploy Completato

Dopo il deploy:

1. Vai su **Deployments**
2. Clicca sull'ultimo deploy
3. Controlla i **Logs** per eventuali errori
4. Se tutto è OK, vedrai: `✅ Build successful`

## 🌐 URL dell'Applicazione

L'applicazione sarà disponibile su:
- **Production**: `https://easy2-0.vercel.app` (o il tuo dominio personalizzato)
- **Preview**: Ogni branch ha il suo URL preview

## 🔍 Troubleshooting

### Deploy fallisce
- Controlla i **Logs** su Vercel
- Verifica che `requirements.txt` sia corretto
- Assicurati che `vercel.json` sia presente

### Errore 413 Payload Too Large
- Limite Vercel: 4.5MB (non modificabile)
- Dividi file più grandi in parti più piccole

### MongoDB non si connette
- Verifica `MONGODB_URI` nelle variabili d'ambiente
- Controlla Network Access su MongoDB Atlas (deve essere 0.0.0.0/0)

## ✅ Checklist Pre-Deploy

- [ ] Tutti i file sono stati pushati su GitHub
- [ ] `vercel.json` è presente e corretto
- [ ] `requirements.txt` contiene tutte le dipendenze
- [ ] Variabili d'ambiente sono configurate su Vercel
- [ ] MongoDB Network Access è configurato (0.0.0.0/0)

## 🎯 Dopo il Deploy

1. Testa l'applicazione: `https://easy2-0.vercel.app`
2. Testa MongoDB: `https://easy2-0.vercel.app/api/test_mongodb`
3. Verifica che tutto funzioni correttamente

