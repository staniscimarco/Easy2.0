# ⚠️ Limitazioni Vercel per File Grandi

## Problema

Vercel ha un **limite hardcoded di 4.5MB** per il payload delle funzioni serverless. Questo limite **non può essere aumentato** facilmente.

## Soluzioni Alternative

### Opzione 1: Dividere il File CSV (Consigliato)

Se hai file CSV più grandi di 4.5MB:

1. **Dividi il file in parti più piccole** (es. 3-4MB ciascuna)
2. **Processa ogni parte separatamente**
3. **Unisci i risultati** manualmente o con uno script

**Strumenti per dividere CSV:**
- Excel: Salva ogni parte separatamente
- Python script: Usa `pandas` per dividere il file
- Online tools: Cerca "CSV splitter" su Google

### Opzione 2: Processare in Locale

Per file molto grandi:

1. **Scarica l'applicazione in locale**
2. **Processa il file localmente** (nessun limite)
3. **Carica solo il risultato** se necessario

### Opzione 3: Usare un Servizio Esterno (Futuro)

Potremmo implementare:
- Upload su AWS S3 / Google Cloud Storage
- Processare il file sul servizio esterno
- Scaricare il risultato

Questo richiederebbe configurazione aggiuntiva.

## Limiti Attuali

- **Vercel Serverless Functions**: 4.5MB (hardcoded, non modificabile)
- **Flask MAX_CONTENT_LENGTH**: 20MB (ma Vercel blocca prima)
- **Timeout**: 300 secondi (5 minuti)
- **Memoria**: 3008MB

## Raccomandazione

Per file più grandi di 4.5MB, **dividi il file in parti più piccole** prima di processarlo.

