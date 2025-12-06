# 🚀 Configurazione MongoDB su Vercel

## Connection String Completa

⚠️ **IMPORTANTE**: Le credenziali MongoDB devono essere configurate come variabili d'ambiente su Vercel, NON hardcoded nel codice!

Usa questa connection string su Vercel (sostituisci con le TUE credenziali):

```
mongodb+srv://<USERNAME>:<PASSWORD>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

## 📋 Passi per Configurare su Vercel

### 1. Vai su Vercel Dashboard
1. Apri [Vercel Dashboard](https://vercel.com/dashboard)
2. Seleziona il progetto **Easy2.0**

### 2. Aggiungi Environment Variables
1. Vai su **Settings** → **Environment Variables**
2. Aggiungi queste due variabili:

#### Variabile 1: MONGODB_URI
- **Name**: `MONGODB_URI`
- **Value**: `mongodb+srv://<USERNAME>:<PASSWORD>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
  - ⚠️ **Sostituisci** `<USERNAME>` e `<PASSWORD>` con le tue credenziali MongoDB
  - ⚠️ **Sostituisci** `xxxxx` con il nome del tuo cluster
- **Environment**: Seleziona tutte (Production, Preview, Development)

#### Variabile 2: MONGODB_DB_NAME
- **Name**: `MONGODB_DB_NAME`
- **Value**: `easyloading`
- **Environment**: Seleziona tutte (Production, Preview, Development)

3. Clicca su **Save** per ogni variabile

### 3. Abilita Accesso da Vercel (IMPORTANTE!)
1. Vai su [MongoDB Atlas Dashboard](https://cloud.mongodb.com/)
2. Vai su **Network Access** (menu laterale)
3. Clicca su **Add IP Address**
4. Seleziona **Allow Access from Anywhere**
   - Questo aggiungerà `0.0.0.0/0` alla whitelist
5. Clicca su **Confirm**

⚠️ **Nota**: In produzione, è meglio limitare gli IP, ma per iniziare va bene così.

### 4. Riavvia il Deploy
1. Vai su **Deployments** nel progetto Vercel
2. Clicca sui tre puntini (...) sull'ultimo deploy
3. Seleziona **Redeploy**
4. Oppure fai un nuovo commit e push

### 5. Verifica i Log
Dopo il deploy, controlla i log su Vercel. Dovresti vedere:
```
✅ Connesso a MongoDB: easyloading
```

Se vedi errori di connessione, verifica:
- Le variabili d'ambiente sono state salvate correttamente
- L'accesso di rete è configurato (0.0.0.0/0)
- La password nella connection string è corretta

## ✅ Test
Dopo il deploy:
1. Vai sulla tua applicazione
2. Carica un'anagrafica o fai un'estrazione
3. I dati ora sono salvati in MongoDB e **non verranno persi** ad ogni deploy! 🎉

## 🔒 Sicurezza
- Le password sono salvate come variabili d'ambiente (non nel codice)
- MongoDB Atlas usa SSL/TLS di default
- Puoi limitare gli IP in Network Access per maggiore sicurezza

