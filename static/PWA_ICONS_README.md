# Icone PWA

Per completare la configurazione PWA, devi creare due icone:

1. **icon-192.png** - 192x192 pixel
2. **icon-512.png** - 512x512 pixel

## Come creare le icone

Puoi usare il logo esistente (`logo.png`) come base:

1. Apri `logo.png` in un editor di immagini (Photoshop, GIMP, o online come https://www.iloveimg.com/resize-image)
2. Ridimensiona l'immagine a 192x192 pixel e salva come `icon-192.png`
3. Ridimensiona l'immagine a 512x512 pixel e salva come `icon-512.png`
4. Posiziona entrambi i file nella cartella `static/`

## Note

- Le icone devono essere in formato PNG
- Le dimensioni devono essere esatte (192x192 e 512x512)
- Le icone dovrebbero avere uno sfondo trasparente o colorato
- Per ora, puoi anche copiare `logo.png` come placeholder temporaneo

## Comandi rapidi (se hai ImageMagick installato)

```bash
# Crea icon-192.png
convert static/logo.png -resize 192x192 static/icon-192.png

# Crea icon-512.png
convert static/logo.png -resize 512x512 static/icon-512.png
```

