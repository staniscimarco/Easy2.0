"""
Handler per Vercel serverless functions.
Questo file wrappa l'app Flask per Vercel usando WSGI.
"""
import sys
import os

# Aggiungi la directory root al path per permettere l'importazione di app.py
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Cambia la directory di lavoro alla root del progetto
os.chdir(root_dir)

# Importa l'app Flask
try:
    from app import app as flask_app
    # Vercel richiede un'app WSGI, esportiamo direttamente l'app Flask
    # che è già un'applicazione WSGI
    app = flask_app
except Exception as e:
    # Se c'è un errore nell'importazione, crea un'app di fallback
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        import traceback
        error_msg = f"Error initializing app: {str(e)}\n\n{traceback.format_exc()}"
        return error_msg, 500
