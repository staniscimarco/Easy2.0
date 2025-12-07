"""
Handler per Vercel serverless functions.
Questo file wrappa l'app Flask per Vercel.
"""
import sys
import os

# Aggiungi la directory root al path per permettere l'importazione di app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa l'app Flask
from app import app

# Vercel richiede che l'handler sia esportato come 'handler'
handler = app

