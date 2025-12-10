"""
LLM Jailbreak Research Tool
Main Flask application for testing prompts against multiple LLM models.
"""

import os
from flask import Flask, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure database
db_path = os.getenv('DATABASE_PATH', 'data/vuln_research.db')
# Convert to absolute path
if not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
# Create data directory if it doesn't exist
os.makedirs(os.path.dirname(db_path), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Import db and initialize with app
from models.database import db, TestSession, PromptVersion, TestResult, Configuration
db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Root route - basic confirmation
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
