# 🔒 Risoluzione Alert di Sicurezza GitHub che Bloccano Deploy

## 🚨 Problema

GitHub Secret Scanning ha rilevato credenziali esposte e ha creato degli alert di sicurezza. Questi alert possono **bloccare i webhook** e impedire il deploy automatico su Vercel.

## ✅ Soluzione Passo-Passo

### 1. Verifica gli Alert di Sicurezza

1. Vai su https://github.com/staniscimarco/Easy2.0
2. Clicca su **Security** (nella barra di navigazione)
3. Clicca su **Secret scanning** nel menu laterale
4. Verifica quanti alert sono **aperti** (Open)

### 2. Risolvi gli Alert MongoDB

Per ogni alert MongoDB Atlas Database URI:

1. **Clicca sull'alert** per vedere i dettagli
2. **Rigenera le credenziali su MongoDB Atlas** (IMPORTANTE!):
   - Vai su [MongoDB Atlas Dashboard](https://cloud.mongodb.com/)
   - Vai su **Database Access**
   - Trova l'utente esposto (es. `staniscimarco_db_user`)
   - Clicca sui **tre puntini** → **Edit**
   - **CAMBIA LA PASSWORD** o elimina e crea un nuovo utente
   - Salva le nuove credenziali in un posto sicuro

3. **Aggiorna le variabili d'ambiente su Vercel**:
   - Vai su [Vercel Dashboard](https://vercel.com/dashboard)
   - Settings → Environment Variables
   - Trova `MONGODB_URI`
   - Aggiorna con le nuove credenziali
   - Salva

4. **Chiudi l'alert su GitHub**:
   - Torna su GitHub → Security → Secret scanning
   - Clicca sull'alert
   - Clicca su **Mark as resolved** o **Revoke secret**
   - Seleziona **"I rotated the secret"** (ho rigenerato il secret)
   - Clicca su **Mark as resolved**

### 3. Verifica che Non Ci Siano Altri Alert

1. Su GitHub → Security → Secret scanning
2. Verifica che tutti gli alert siano **chiusi** (Closed)
3. Se ci sono altri alert aperti, risolvili seguendo lo stesso processo

### 4. Verifica i Webhook

Dopo aver risolto tutti gli alert:

1. Vai su GitHub → Settings → Webhooks
2. Verifica che i webhook di Vercel siano **attivi** (verde)
3. Se un webhook è disabilitato:
   - Clicca sul webhook
   - Clicca su **Redeliver** per testarlo
   - Se continua a fallire, riconnetti il repository su Vercel

### 5. Riconnetti il Repository su Vercel (Se Necessario)

Se i webhook non funzionano ancora:

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Settings → Git
3. Clicca su **Disconnect** accanto al repository
4. Attendi 30 secondi
5. Clicca su **Connect Git Repository**
6. Seleziona GitHub → autorizza → seleziona `staniscimarco/Easy2.0`
7. Questo ricreerà i webhook

### 6. Testa il Deploy Automatico

Dopo aver risolto gli alert e riconnesso il repository:

```bash
# Fai un piccolo cambiamento
echo "<!-- Test dopo risoluzione alert -->" >> templates/base.html
git add templates/base.html
git commit -m "Test deploy dopo risoluzione alert sicurezza"
git push
```

1. Vai su Vercel → Deployments
2. Dovresti vedere un nuovo deployment che parte automaticamente entro 1-2 minuti

## 🔍 Verifica Stato Alert

Per verificare rapidamente lo stato degli alert:

1. Vai su https://github.com/staniscimarco/Easy2.0/security/secret-scanning
2. Controlla:
   - **Open**: Numero di alert aperti (dovrebbe essere 0)
   - **Closed**: Numero di alert risolti

## ⚠️ Importante

- **NON** chiudere gli alert senza rigenerare le credenziali
- Le credenziali esposte sono state compromesse e devono essere cambiate
- Dopo aver rigenerato le credenziali, aggiorna sempre Vercel
- Gli alert bloccano i webhook finché non vengono risolti

## 🆘 Se Non Riesci a Risolvere

1. **Verifica i log dei webhook**:
   - GitHub → Settings → Webhooks
   - Clicca sul webhook di Vercel
   - Scorri in basso → Recent Deliveries
   - Verifica se ci sono errori

2. **Contatta il supporto**:
   - GitHub Support: https://support.github.com
   - Vercel Support: https://vercel.com/support

## 📋 Checklist

Prima di considerare risolto:

- [ ] Tutti gli alert di sicurezza sono chiusi su GitHub
- [ ] Credenziali MongoDB rigenerate su MongoDB Atlas
- [ ] Variabili d'ambiente aggiornate su Vercel
- [ ] Webhook attivi su GitHub
- [ ] Test deploy automatico funziona

