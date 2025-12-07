# 🔍 Verifica e Risoluzione Deploy Automatico

## ⚠️ Problema: Deploy non parte automaticamente

## ✅ Soluzione Passo-Passo

### STEP 1: Verifica Repository Collegato su Vercel

1. Vai su https://vercel.com/dashboard
2. Seleziona il progetto **easy2-0**
3. Vai su **Settings** → **Git**
4. **Cosa devi vedere:**
   - Repository: `staniscimarco/Easy2.0`
   - Branch: `main`
   - Status: Collegato ✅

**Se NON è collegato o è disconnesso:**
- Clicca su **Connect Git Repository**
- Seleziona **GitHub**
- Autorizza Vercel (se richiesto)
- Seleziona `staniscimarco/Easy2.0`
- Salva

### STEP 2: Verifica Auto-Deploy Abilitato

1. Su Vercel: **Settings** → **General**
2. Scorri fino a **Production Branch**
3. Verifica:
   - ✅ **Production Branch**: `main`
   - ✅ **Auto-deploy**: **Enabled** (deve essere verde/attivo)

**Se Auto-deploy è Disabled:**
- Clicca sul toggle per abilitarlo
- Salva

### STEP 3: Verifica Webhook su GitHub

1. Vai su https://github.com/staniscimarco/Easy2.0/settings/hooks
2. **Cosa devi vedere:**
   - 2 webhook di Vercel
   - Status: **Active** (verde) ✅
   - Eventi: `push`, `pull_request` ✅

**Se NON ci sono webhook:**
- Vai su Vercel → Settings → Git
- Disconnetti il repository
- Riconnettilo (questo creerà i webhook)

**Se i webhook sono disabilitati (rossi):**
- Clicca sul webhook
- Verifica gli errori in "Recent Deliveries"
- Se ci sono errori 401/403: problema permessi
- Se ci sono errori 404: progetto Vercel non trovato

### STEP 4: Verifica Alert di Sicurezza

1. Vai su https://github.com/staniscimarco/Easy2.0/security/secret-scanning
2. **Cosa devi vedere:**
   - **Open**: 0 (zero alert aperti) ✅
   - **Closed**: Tutti gli alert risolti

**Se ci sono alert aperti:**
- Gli alert bloccano i webhook!
- Risolvili seguendo `DEPLOY_AUTOMATICO.md`
- Rigenera le credenziali MongoDB
- Chiudi gli alert su GitHub

### STEP 5: Verifica Permessi App GitHub

1. Vai su https://github.com/settings/applications
2. Cerca **Vercel** nelle app autorizzate
3. Clicca su **Vercel**
4. Verifica:
   - ✅ Repository access: `Easy2.0` è nella lista
   - ✅ Permessi: `repo`, `admin:repo_hook`

**Se NON c'è accesso:**
- Clicca su **Configure**
- Autorizza accesso a `Easy2.0`
- Salva

### STEP 6: Test Manuale

Dopo aver verificato tutto, fai un test:

```bash
# Fai un piccolo cambiamento
echo "<!-- Test deploy " >> templates/base.html
git add templates/base.html
git commit -m "Test deploy automatico"
git push
```

**Poi:**
1. Vai su Vercel → Deployments
2. Dovresti vedere un nuovo deployment partire entro 1-2 minuti
3. Se non parte, controlla i log su GitHub (Settings → Webhooks → Recent Deliveries)

### STEP 7: Riconnessione Completa (Se Nulla Funziona)

Se dopo tutti i passaggi non funziona ancora:

1. **Su Vercel:**
   - Settings → Git → **Disconnect** repository
   - Attendi 1 minuto

2. **Su GitHub:**
   - Settings → Applications → **Revoke** Vercel
   - Attendi 30 secondi

3. **Su Vercel (di nuovo):**
   - Settings → Git → **Connect Git Repository**
   - Seleziona **GitHub**
   - Autorizza TUTTI i permessi richiesti
   - Seleziona `staniscimarco/Easy2.0`
   - Configura il progetto (se richiesto)

4. **Test:**
   ```bash
   git commit --allow-empty -m "Test dopo riconnessione completa"
   git push
   ```

## 🔍 Debug Avanzato

### Verifica Log Webhook

1. GitHub → Settings → Webhooks
2. Clicca sul webhook di Vercel
3. Scorri in basso → **Recent Deliveries**
4. Clicca sull'ultima delivery
5. Verifica:
   - **Status**: 200 OK ✅
   - **Request**: Dovrebbe mostrare il payload
   - **Response**: Dovrebbe mostrare la risposta di Vercel

**Se vedi errori:**
- **401/403**: Problema permessi → Riconnetti repository
- **404**: Progetto Vercel non trovato → Verifica nome progetto
- **500**: Errore Vercel → Riprova più tardi

### Verifica Log Vercel

1. Vercel → Deployments
2. Clicca sull'ultimo deployment
3. Vai su **Logs**
4. Verifica se ci sono errori durante il build

## 📋 Checklist Finale

Prima di considerare risolto, verifica:

- [ ] Repository collegato su Vercel (Settings → Git)
- [ ] Auto-deploy abilitato (Settings → General)
- [ ] Production branch = `main`
- [ ] 2 webhook attivi su GitHub (Settings → Webhooks)
- [ ] 0 alert di sicurezza aperti (Security → Secret scanning)
- [ ] App Vercel ha accesso al repository (Settings → Applications)
- [ ] Test deploy funziona (push → deploy automatico)

## 🆘 Se Ancora Non Funziona

1. **Controlla lo stato di Vercel**: https://www.vercel-status.com/
2. **Controlla i log**: Vercel → Deployments → Logs
3. **Contatta supporto**: https://vercel.com/support

