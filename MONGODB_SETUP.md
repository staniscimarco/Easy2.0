# 🗄️ Configurazione MongoDB per Storage Persistente

Per evitare di perdere i dati JSON ad ogni deploy su Vercel, abbiamo implementato un sistema di storage persistente usando **MongoDB Atlas** (gratuito).

## 📋 Prerequisiti

1. Account MongoDB Atlas (gratuito): https://www.mongodb.com/cloud/atlas/register
2. Cluster MongoDB Atlas creato (piano gratuito M0)

## 🚀 Setup MongoDB Atlas

### 1. Crea un Cluster Gratuito

1. Vai su [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Clicca su "Try Free" o accedi al tuo account
3. Crea un nuovo cluster (scegli il piano **M0 FREE**)
4. Seleziona una regione vicina a te (es. `eu-west-1` per l'Europa)
5. Clicca su "Create Cluster"

### 2. Configura Network Access

1. Nel menu laterale, vai su **Network Access**
2. Clicca su **Add IP Address**
3. Per sviluppo locale: clicca su **Add Current IP Address**
4. Per Vercel: clicca su **Allow Access from Anywhere** (0.0.0.0/0)
   - ⚠️ **Nota**: In produzione, è meglio limitare gli IP, ma per iniziare va bene
5. Clicca su **Confirm**

### 3. Crea un Database User

1. Nel menu laterale, vai su **Database Access**
2. Clicca su **Add New Database User**
3. Scegli **Password** come metodo di autenticazione
4. Inserisci:
   - **Username**: `easyloading` (o quello che preferisci)
   - **Password**: Genera una password sicura (salvala!)
5. Assegna il ruolo: **Atlas admin** (o **Read and write to any database**)
6. Clicca su **Add User**

### 4. Ottieni la Connection String

1. Nel menu laterale, vai su **Database**
2. Clicca su **Connect** sul tuo cluster
3. Scegli **Connect your application**
4. Seleziona **Python** come driver
5. Copia la **Connection String** (sarà qualcosa come):
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
6. Sostituisci `<username>` e `<password>` con le credenziali che hai creato

### 5. Configura Vercel

1. Vai sul tuo progetto su [Vercel Dashboard](https://vercel.com/dashboard)
2. Vai su **Settings** → **Environment Variables**
3. Aggiungi queste variabili:

   | Name | Value |
   |------|-------|
   | `MONGODB_URI` | `mongodb+srv://easyloading:TUAPASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority` |
   | `MONGODB_DB_NAME` | `easyloading` |

4. Clicca su **Save**

### 6. Configura Locale (Opzionale)

Se vuoi testare MongoDB anche in locale, crea un file `.env` nella root del progetto:

```env
MONGODB_URI=mongodb+srv://easyloading:TUAPASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=easyloading
```

E installa `python-dotenv`:

```bash
pip install python-dotenv
```

Poi modifica `app.py` per caricare le variabili da `.env`:

```python
from dotenv import load_dotenv
load_dotenv()
```

## ✅ Verifica

Dopo il deploy su Vercel:

1. Vai sulla tua applicazione
2. Carica un'anagrafica o fai un'estrazione
3. Controlla i log su Vercel: dovresti vedere `✅ Connesso a MongoDB`
4. I dati ora sono persistenti! 🎉

## 🔄 Come Funziona

- **Su Vercel**: Se `MONGODB_URI` è configurato, i dati vengono salvati in MongoDB
- **In Locale**: Se `MONGODB_URI` non è configurato, usa il file system locale
- **Fallback Automatico**: Se MongoDB non è disponibile, usa automaticamente il file system

## 📊 Struttura Database

Il database `easyloading` contiene queste collezioni:

- **`anagrafica`**: Anagrafica articoli
- **`config`**: Configurazione OData
- **`extractions`**: Estrazioni JSON salvate

## 🆓 Limiti Piano Gratuito

- **512 MB** di storage (più che sufficiente per migliaia di estrazioni)
- **Shared RAM/CPU** (performance adeguate per uso normale)
- **Nessun limite** sul numero di documenti

## 🔒 Sicurezza

- Le password sono salvate come variabili d'ambiente (non nel codice)
- MongoDB Atlas usa SSL/TLS di default
- Puoi limitare gli IP che possono accedere al database

## 🆘 Troubleshooting

### Errore: "Connection refused"
- Verifica che l'IP sia autorizzato in **Network Access**

### Errore: "Authentication failed"
- Verifica username e password in `MONGODB_URI`
- Assicurati di aver sostituito `<username>` e `<password>` nella connection string

### I dati non vengono salvati
- Controlla i log su Vercel per vedere se MongoDB è connesso
- Verifica che `MONGODB_URI` sia configurato correttamente

## 📚 Risorse

- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)

