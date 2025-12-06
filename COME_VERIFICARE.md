# ✅ Come Verificare che MongoDB Funzioni

## 🔍 Metodo 1: Test Endpoint (Rapido)

1. **Vai sull'endpoint di test**:
   ```
   https://TUO-DOMINIO-VERCEL.vercel.app/api/test_mongodb
   ```
   
   Sostituisci `TUO-DOMINIO-VERCEL` con il tuo dominio Vercel.

2. **Risposta attesa**:
   ```json
   {
     "success": true,
     "message": "✅ MongoDB connesso e funzionante!",
     "database": "easyloading",
     "collections": ["anagrafica", "config", "extractions", "test"],
     "test_write_read": "OK",
     "using_mongodb": true,
     "using_filesystem": false
   }
   ```

3. **Se vedi questo**, MongoDB funziona! 🎉

## 🔍 Metodo 2: Verifica Log Vercel

1. Vai su [Vercel Dashboard](https://vercel.com/dashboard)
2. Seleziona il progetto **Easy2.0**
3. Vai su **Deployments** → clicca sull'ultimo deploy
4. Vai su **Logs**
5. Cerca questi messaggi:
   ```
   ✅ Connesso a MongoDB: easyloading
   ✅ Anagrafica salvata in MongoDB
   ✅ Estrazione salvata in MongoDB
   ```

## 🔍 Metodo 3: Test Pratico

### Test 1: Carica un'Anagrafica
1. Vai sulla home page della tua app
2. Carica un file CSV anagrafica
3. Dovresti vedere: `✅ Anagrafica salvata in MongoDB` nei log

### Test 2: Fai un'Estrazione
1. Vai su "Calendario Estrazione"
2. Clicca su un giorno
3. Dovresti vedere: `✅ Estrazione salvata in MongoDB` nei log

### Test 3: Verifica Persistenza
1. Fai un nuovo deploy su Vercel (o aspetta un auto-deploy)
2. Ricarica la pagina
3. I dati dovrebbero essere ancora presenti! 🎉

## 🔍 Metodo 4: Verifica su MongoDB Atlas

1. Vai su [MongoDB Atlas Dashboard](https://cloud.mongodb.com/)
2. Clicca su **Browse Collections**
3. Seleziona il database **easyloading**
4. Dovresti vedere queste collezioni:
   - `anagrafica` - contiene l'anagrafica articoli
   - `config` - contiene la configurazione OData
   - `extractions` - contiene le estrazioni JSON

## ❌ Se Non Funziona

### Errore: "MongoDB non configurato"
- Verifica che `MONGODB_URI` sia configurato su Vercel
- Controlla che la connection string sia corretta

### Errore: "Connection refused"
- Vai su MongoDB Atlas → **Network Access**
- Assicurati che `0.0.0.0/0` sia nella whitelist

### Errore: "Authentication failed"
- Verifica username e password nella connection string
- Controlla che l'utente database esista su MongoDB Atlas

### I dati non persistono
- Controlla i log su Vercel per vedere se MongoDB è usato
- Verifica che `using_mongodb: true` nell'endpoint di test

## 📊 Checklist Completa

- [ ] Variabile `MONGODB_URI` configurata su Vercel
- [ ] Variabile `MONGODB_DB_NAME` configurata su Vercel
- [ ] Network Access configurato (0.0.0.0/0)
- [ ] Endpoint `/api/test_mongodb` restituisce `success: true`
- [ ] Log Vercel mostrano "✅ Connesso a MongoDB"
- [ ] Dati persistono dopo un deploy

## 🎯 Test Rapido

Apri questo URL nel browser (sostituisci con il tuo dominio):
```
https://TUO-DOMINIO.vercel.app/api/test_mongodb
```

Se vedi `"success": true`, tutto funziona! ✅

