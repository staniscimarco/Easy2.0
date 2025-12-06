# 🔧 Risoluzione Problema Deploy Automatico Vercel

## Problema
GitHub non invia automaticamente il deploy su Vercel quando fai push al repository.

## ✅ Soluzione Passo-Passo

### 1. Verifica il Collegamento del Repository su Vercel

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Seleziona il progetto **easy2-0** (o il nome del tuo progetto)
3. Vai su **Settings** → **Git**
4. Verifica che il repository sia collegato:
   - Dovresti vedere: `staniscimarco/Easy2.0`
   - Se non c'è o è disconnesso, procedi al passo 2

### 2. Riconnetti il Repository (Se Necessario)

1. Su Vercel, vai su **Settings** → **Git**
2. Se il repository non è collegato:
   - Clicca su **Connect Git Repository**
   - Seleziona **GitHub**
   - Autorizza Vercel se richiesto
   - Seleziona il repository `staniscimarco/Easy2.0`
3. Se il repository è già collegato ma non funziona:
   - Clicca su **Disconnect** accanto al repository
   - Attendi qualche secondo
   - Clicca su **Connect Git Repository** di nuovo
   - Seleziona `staniscimarco/Easy2.0`
   - Autorizza tutti i permessi richiesti

### 3. Verifica i Permessi dell'App GitHub su Vercel

1. Su Vercel, vai su **Settings** → **Git** → **GitHub App**
2. Verifica che l'app GitHub abbia i permessi necessari:
   - ✅ **Repository access**: Deve avere accesso al repository `Easy2.0`
   - ✅ **Webhooks**: Devono essere abilitati
3. Se i permessi non sono corretti:
   - Clicca su **Configure GitHub App**
   - Autorizza l'app a accedere al repository `Easy2.0`
   - Abilita i webhook per il repository
   - Salva le modifiche

### 4. Verifica i Webhook su GitHub

1. Vai su https://github.com/staniscimarco/Easy2.0
2. Vai su **Settings** → **Webhooks**
3. Cerca webhook di Vercel (dovrebbero essere 2):
   - `https://api.vercel.com/v1/integrations/deploy/...`
   - `https://api.vercel.com/v1/integrations/events/...`
4. Verifica che siano:
   - ✅ **Active** (verde)
   - ✅ Hanno eventi selezionati: `push`, `pull_request`
   - ✅ Ultima delivery recente (non più di qualche minuto fa se hai appena fatto push)
5. Se non ci sono webhook:
   - Vai su Vercel → Settings → Git
   - Disconnetti e riconnetti il repository
   - Questo creerà automaticamente i webhook

### 5. Verifica le Impostazioni del Progetto Vercel

1. Su Vercel, vai su **Settings** → **General**
2. Verifica:
   - **Production Branch**: `main` (deve corrispondere al tuo branch principale)
   - **Auto-deploy**: Deve essere **Enabled** ✅
3. Se **Auto-deploy** è disabilitato:
   - Abilitalo
   - Salva le modifiche

### 6. Testa il Deploy Automatico

Dopo aver verificato tutto, fai un test:

```bash
# Fai una piccola modifica
echo "<!-- Test deploy -->" >> templates/base.html
git add templates/base.html
git commit -m "Test deploy automatico Vercel"
git push
```

1. Vai su Vercel → **Deployments**
2. Dovresti vedere un nuovo deployment che parte automaticamente entro 1-2 minuti
3. Se non parte, controlla i log su GitHub (Settings → Webhooks → Recent Deliveries)

### 7. Verifica i Log di Vercel

1. Su Vercel, vai su **Deployments**
2. Clicca sull'ultimo deployment
3. Vai su **Logs** per vedere se ci sono errori
4. Controlla se il deployment è partito automaticamente o manualmente

### 8. Verifica i Permessi GitHub

1. Vai su https://github.com/settings/applications
2. Cerca **Vercel** nell'elenco delle app autorizzate
3. Clicca su **Vercel** e verifica:
   - ✅ Ha accesso al repository `Easy2.0`
   - ✅ I permessi includono: `repo`, `admin:repo_hook`
4. Se i permessi non sono corretti:
   - Clicca su **Revoke**
   - Poi riconnetti da Vercel (Settings → Git → Connect Git Repository)

## 🔍 Troubleshooting Avanzato

### Se i Webhook Non Funzionano

1. Su GitHub, vai su **Settings** → **Webhooks**
2. Clicca sul webhook di Vercel
3. Scorri in basso e clicca su **Recent Deliveries**
4. Verifica se ci sono errori nelle richieste:
   - Se vedi errori **401/403**: I permessi non sono corretti
   - Se vedi errori **404**: Il progetto Vercel non esiste o è stato eliminato
   - Se vedi errori **500**: Problema temporaneo di Vercel, riprova più tardi
5. Se ci sono errori, clicca su **Redeliver** per riprovare

### Se il Deploy Non Parte Automaticamente

1. Su Vercel, vai su **Deployments**
2. Clicca su **Redeploy** per forzare un nuovo deploy
3. Se funziona manualmente ma non automaticamente, il problema è nei webhook
4. Riconnetti il repository (passo 2)

### Reinstallazione Completa dell'Integrazione

Se nulla funziona, prova una reinstallazione completa:

1. **Su Vercel**:
   - Settings → Git → Disconnect il repository
   - Attendi 30 secondi

2. **Su GitHub**:
   - Settings → Applications → Authorized OAuth Apps
   - Trova **Vercel** e clicca su **Revoke**

3. **Su Vercel** (di nuovo):
   - Settings → Git → Connect Git Repository
   - Seleziona GitHub
   - Autorizza tutti i permessi
   - Seleziona il repository `staniscimarco/Easy2.0`
   - Configura il progetto (se richiesto)

4. **Testa**:
   ```bash
   git commit --allow-empty -m "Test deploy dopo riconnessione"
   git push
   ```

## ✅ Checklist Finale

Prima di considerare risolto il problema, verifica:

- [ ] Repository collegato su Vercel (Settings → Git)
- [ ] Auto-deploy abilitato (Settings → General)
- [ ] Webhook attivi su GitHub (Settings → Webhooks)
- [ ] Permessi GitHub corretti (Settings → Applications)
- [ ] Production branch corretto (`main`)
- [ ] Test deploy funziona (push → deploy automatico)

## 🆘 Se Nulla Funziona

1. **Controlla lo stato di Vercel**: https://www.vercel-status.com/
2. **Controlla i log di Vercel**: Deployments → Logs
3. **Contatta il supporto Vercel**: https://vercel.com/support
4. **Verifica la documentazione**: https://vercel.com/docs/concepts/git

## 📝 Note Importanti

- I webhook di Vercel possono impiegare 1-2 minuti per attivarsi dopo un push
- Se fai molti push rapidi, Vercel potrebbe raggrupparli in un unico deploy
- I deploy automatici funzionano solo per il branch configurato come "Production Branch"
- I deploy manuali (Redeploy) funzionano sempre, anche se i webhook non funzionano

