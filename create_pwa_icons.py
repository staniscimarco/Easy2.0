#!/usr/bin/env python3
"""
Script per creare le icone PWA dal logo principale
Genera icone per iPhone e Android in diverse dimensioni
"""

from PIL import Image
import os

def create_pwa_icons():
    """Crea le icone PWA dal logo.png"""
    
    # Percorso del logo originale
    logo_path = 'static/logo.png'
    
    if not os.path.exists(logo_path):
        print(f"Errore: {logo_path} non trovato!")
        return
    
    # Carica il logo
    logo = Image.open(logo_path)
    print(f"Logo originale: {logo.size}, mode: {logo.mode}")
    
    # Dimensioni richieste per PWA
    sizes = [
        (180, 180, 'icon-180.png'),  # iPhone apple-touch-icon
        (192, 192, 'icon-192.png'),  # Android/Chrome
        (512, 512, 'icon-512.png'),  # Android/Chrome grande
    ]
    
    # Crea le icone
    for width, height, filename in sizes:
        # Crea un'immagine quadrata con sfondo bianco
        icon = Image.new('RGBA', (width, height), (255, 255, 255, 255))
        
        # Calcola le dimensioni per mantenere le proporzioni
        logo_width, logo_height = logo.size
        aspect_ratio = logo_width / logo_height
        
        if aspect_ratio > 1:
            # Logo più largo che alto
            new_width = int(width * 0.9)  # 90% della dimensione per lasciare margine
            new_height = int(new_width / aspect_ratio)
        else:
            # Logo più alto che largo
            new_height = int(height * 0.9)  # 90% della dimensione per lasciare margine
            new_width = int(new_height * aspect_ratio)
        
        # Ridimensiona il logo mantenendo le proporzioni
        logo_resized = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Calcola la posizione per centrare il logo
        x_offset = (width - new_width) // 2
        y_offset = (height - new_height) // 2
        
        # Incolla il logo centrato sull'icona
        if logo_resized.mode == 'RGBA':
            icon.paste(logo_resized, (x_offset, y_offset), logo_resized)
        else:
            icon.paste(logo_resized, (x_offset, y_offset))
        
        # Salva l'icona
        output_path = os.path.join('static', filename)
        icon.save(output_path, 'PNG', optimize=True)
        print(f"Creata: {output_path} ({width}x{height})")
    
    print("\n✅ Tutte le icone PWA sono state create con successo!")

if __name__ == '__main__':
    create_pwa_icons()

