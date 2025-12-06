"""
Vercel serverless function wrapper for Flask app
Vercel Python supports Flask directly - just export the app
"""
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects the Flask app to be exported as 'app' or 'application'
# This works directly with @vercel/python
application = app
