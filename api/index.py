"""
Handler per Vercel serverless functions.
Vercel rileva automaticamente Flask da questo file.
"""
import sys
import os

# Aggiungi la directory root al path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Cambia la directory di lavoro alla root
os.chdir(root_dir)

# Importa l'app Flask - Vercel rileva automaticamente l'app Flask
from app import app
