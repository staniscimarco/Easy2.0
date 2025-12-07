"""
Handler per Vercel serverless functions.
Wrapper WSGI per Flask su Vercel.
"""
import sys
import os

# Aggiungi la directory root al path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Cambia la directory di lavoro alla root
os.chdir(root_dir)

# Importa l'app Flask
try:
    from app import app as flask_app
    
    # Crea un wrapper WSGI che Vercel può riconoscere
    def handler(request, response):
        """Handler WSGI per Vercel"""
        return flask_app(request.environ, lambda status, headers: None)
    
    # Esporta sia app che handler per compatibilità
    app = flask_app
    
except Exception as e:
    # Fallback in caso di errore
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        import traceback
        return f"Error: {str(e)}\n\n{traceback.format_exc()}", 500
