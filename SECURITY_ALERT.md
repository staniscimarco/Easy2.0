# ⚠️ AVVISO DI SICUREZZA - Credenziali MongoDB Esposte

## 🚨 Problema Rilevato

GitHub Secret Scanning ha rilevato che le credenziali MongoDB sono state esposte pubblicamente nei file di documentazione.

## ✅ Azioni Immediate Richieste

### 1. Rigenera le Credenziali MongoDB (URGENTE!)

Le credenziali esposte devono essere **immediatamente revocate**:

1. Vai su [MongoDB Atlas Dashboard](https://cloud.mongodb.com/)
2. Vai su **Database Access** (menu laterale)
3. Trova l'utente `staniscimarco_db_user` (o quello esposto)
4. Clicca sui **tre puntini** → **Edit** o **Delete**
5. **CAMBIA LA PASSWORD** o **ELIMINA** l'utente e creane uno nuovo
6. Se crei un nuovo utente, salva le nuove credenziali in un posto sicuro

### 2. Aggiorna le Variabili d'Ambiente su Vercel

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Seleziona il progetto **Easy2-0**
3. Vai su **Settings** → **Environment Variables**
4. Trova `MONGODB_URI`
5. **Aggiorna** con le nuove credenziali:
   ```
   mongodb+srv://<NUOVO_USERNAME>:<NUOVA_PASSWORD>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
6. Clicca su **Save**

### 3. Verifica che Non Ci Siano Altre Credenziali Esposte

I file di documentazione sono stati aggiornati per rimuovere le credenziali hardcoded. Verifica che:
- ✅ Nessun file `.env` sia stato committato
- ✅ Nessuna credenziale sia nel codice sorgente
- ✅ Tutte le credenziali siano solo in variabili d'ambiente

### 4. Chiudi gli Alert su GitHub

1. Vai su https://github.com/staniscimarco/Easy2.0/security/secret-scanning
2. Per ogni alert:
   - Clicca sull'alert
   - Clicca su **Mark as resolved** o **Revoke secret**
   - Seleziona "I rotated the secret" o "I revoked the secret"

## 🔒 Best Practices per il Futuro

1. **MAI** committare credenziali nel codice o nella documentazione
2. **SEMPRE** usare variabili d'ambiente per credenziali sensibili
3. Usa `.gitignore` per escludere file `.env` e file con credenziali
4. Usa placeholder nei file di documentazione (es. `<USERNAME>`, `<PASSWORD>`)
5. Considera l'uso di servizi di gestione segreti (es. Vercel Environment Variables, AWS Secrets Manager)

## 📋 Checklist Post-Sicurezza

- [ ] Credenziali MongoDB rigenerate su MongoDB Atlas
- [ ] Variabili d'ambiente aggiornate su Vercel
- [ ] Alert GitHub chiusi/risolti
- [ ] Verificato che non ci siano altre credenziali esposte
- [ ] Testato che l'applicazione funzioni con le nuove credenziali

## 🆘 Supporto

Se hai bisogno di aiuto:
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)

