"""
Vercel serverless function wrapper for Flask app
Vercel uses serverless functions, so we need to wrap Flask in a handler
"""
from app import app

# Vercel expects a handler function
# For Flask, we use the WSGI adapter
def handler(request, response):
    # Import the WSGI adapter from vercel
    from vercel import wsgi
    
    # Return the WSGI application wrapped for Vercel
    return wsgi(app)(request, response)
