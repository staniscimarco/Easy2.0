# Risoluzione Problema Integrazione GitHub-Vercel

## Problema
GitHub non invia automaticamente il deploy su Vercel quando fai push al repository.

## Soluzione Passo-Passo

### 1. Verifica il Collegamento del Repository su Vercel

1. Vai su https://vercel.com e accedi al tuo account
2. Seleziona il progetto **easy2-0**
3. Vai su **Settings** → **Git**
4. Verifica che il repository sia collegato:
   - Dovresti vedere: `staniscimarco/Easy2.0`
   - Se non c'è, clicca su **Connect Git Repository** e seleziona il repository

### 2. Verifica i Permessi dell'App GitHub su Vercel

1. Vai su **Settings** → **Git** → **GitHub App**
2. Verifica che l'app GitHub abbia i permessi necessari:
   - ✅ **Repository access**: Deve avere accesso al repository `Easy2.0`
   - ✅ **Webhooks**: Devono essere abilitati
3. Se i permessi non sono corretti:
   - Clicca su **Configure GitHub App**
   - Autorizza l'app a accedere al repository `Easy2.0`
   - Abilita i webhook per il repository

### 3. Verifica i Webhook su GitHub

1. Vai su https://github.com/staniscimarco/Easy2.0
2. Vai su **Settings** → **Webhooks**
3. Cerca webhook di Vercel (dovrebbero essere 2):
   - `https://api.vercel.com/v1/integrations/deploy/...`
   - `https://api.vercel.com/v1/integrations/events/...`
4. Verifica che siano:
   - ✅ **Active** (verde)
   - ✅ Hanno eventi selezionati: `push`, `pull_request`
5. Se non ci sono webhook:
   - Vai su Vercel → Settings → Git
   - Disconnetti e riconnetti il repository
   - Questo creerà automaticamente i webhook

### 4. Riconnetti il Repository (Se Necessario)

1. Su Vercel, vai su **Settings** → **Git**
2. Clicca su **Disconnect** accanto al repository
3. Clicca su **Connect Git Repository**
4. Seleziona **GitHub** e poi il repository `staniscimarco/Easy2.0`
5. Autorizza l'app GitHub se richiesto
6. Vercel creerà automaticamente i webhook necessari

### 5. Testa il Deploy Automatico

1. Fai una piccola modifica al file `README.md`:
   ```bash
   echo "# Test deploy" >> README.md
   git add README.md
   git commit -m "Test deploy automatico"
   git push
   ```
2. Vai su Vercel → **Deployments**
3. Dovresti vedere un nuovo deployment che parte automaticamente entro 1-2 minuti

### 6. Verifica i Log di Vercel

1. Su Vercel, vai su **Deployments**
2. Clicca sull'ultimo deployment
3. Vai su **Logs** per vedere se ci sono errori
4. Controlla se il deployment è partito automaticamente o manualmente

### 7. Verifica le Impostazioni del Progetto

1. Su Vercel, vai su **Settings** → **General**
2. Verifica:
   - **Production Branch**: `main` (o `master`)
   - **Auto-deploy**: Deve essere **Enabled**
3. Se **Auto-deploy** è disabilitato, abilitalo

### 8. Verifica i Permessi GitHub

1. Vai su https://github.com/settings/applications
2. Cerca **Vercel** nell'elenco delle app autorizzate
3. Clicca su **Vercel** e verifica:
   - ✅ Ha accesso al repository `Easy2.0`
   - ✅ I permessi includono: `repo`, `admin:repo_hook`
4. Se i permessi non sono corretti:
   - Clicca su **Revoke** e poi riconnetti da Vercel

## Troubleshooting Avanzato

### Se i Webhook Non Funzionano

1. Su GitHub, vai su **Settings** → **Webhooks**
2. Clicca sul webhook di Vercel
3. Scorri in basso e clicca su **Recent Deliveries**
4. Verifica se ci sono errori nelle richieste
5. Se ci sono errori 401/403, i permessi non sono corretti

### Se il Deploy Non Parte Automaticamente

1. Su Vercel, vai su **Deployments**
2. Clicca su **Redeploy** per forzare un nuovo deploy
3. Se funziona manualmente ma non automaticamente, il problema è nei webhook

### Reinstallazione Completa dell'Integrazione

1. Su Vercel → **Settings** → **Git** → **Disconnect** il repository
2. Su GitHub → **Settings** → **Applications** → **Authorized OAuth Apps** → Revoca Vercel
3. Su Vercel, riconnetti il repository da zero
4. Autorizza tutti i permessi richiesti

## Verifica Finale

Dopo aver seguito questi passaggi, fai un test:

```bash
# Fai un piccolo cambiamento
echo "<!-- Test -->" >> templates/base.html
git add templates/base.html
git commit -m "Test deploy automatico Vercel"
git push
```

Entro 1-2 minuti dovresti vedere un nuovo deployment su Vercel che parte automaticamente.

## Contatti Supporto

Se il problema persiste:
- **Vercel Support**: https://vercel.com/support
- **GitHub Support**: https://support.github.com

