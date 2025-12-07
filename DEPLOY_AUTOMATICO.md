# 🚀 Deploy Automatico GitHub → Vercel

## ✅ Verifica Rapida

1. **Vai su Vercel Dashboard**: https://vercel.com/dashboard
2. **Seleziona il progetto** `easy2-0`
3. **Vai su Settings → Git**
4. Verifica che il repository `staniscimarco/Easy2.0` sia collegato

## 🔧 Se il Deploy Automatico Non Funziona

### 1. Riconnetti il Repository

1. Su Vercel: **Settings → Git**
2. Clicca su **Disconnect** accanto al repository
3. Attendi 30 secondi
4. Clicca su **Connect Git Repository**
5. Seleziona **GitHub** → autorizza → seleziona `staniscimarco/Easy2.0`

### 2. Verifica Auto-Deploy

1. Su Vercel: **Settings → General**
2. Verifica che **Auto-deploy** sia **Enabled** ✅
3. Verifica che **Production Branch** sia `main`

### 3. Verifica Webhook su GitHub

1. Vai su https://github.com/staniscimarco/Easy2.0/settings/hooks
2. Dovresti vedere 2 webhook di Vercel attivi (verde)
3. Se non ci sono, riconnetti il repository (passo 1)

### 4. Risolvi Alert di Sicurezza (Se Presenti)

1. Vai su https://github.com/staniscimarco/Easy2.0/security/secret-scanning
2. Se ci sono alert aperti, chiudili:
   - Rigenera le credenziali su MongoDB Atlas
   - Aggiorna le variabili d'ambiente su Vercel
   - Chiudi gli alert su GitHub

## 🧪 Test

Dopo aver verificato tutto:

```bash
echo "<!-- Test deploy -->" >> templates/base.html
git add templates/base.html
git commit -m "Test deploy automatico"
git push
```

Entro 1-2 minuti dovresti vedere un nuovo deployment su Vercel.

## 📝 Note

- I webhook possono impiegare 1-2 minuti per attivarsi
- Se fai molti push rapidi, Vercel potrebbe raggrupparli
- I deploy manuali (Redeploy) funzionano sempre

