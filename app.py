"""
LLM Jailbreak Research Tool
Main Flask application for testing prompts against multiple LLM models.
"""

import os
from flask import Flask, render_template, request, redirect, url_for
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
from models.config import (
    load_models_config,
    get_api_key,
    set_api_key,
    validate_models_against_openrouter,
    mask_api_key
)

db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

    # Load and validate model configuration
    try:
        configured_models = load_models_config()
        app.config['CONFIGURED_MODELS'] = configured_models
        app.logger.info(f"Loaded {len(configured_models)} models from configuration")

        # Validate models against OpenRouter if API key is available
        openrouter_key = get_api_key('openrouter')
        if openrouter_key:
            unavailable_models, error = validate_models_against_openrouter(
                openrouter_key,
                configured_models
            )

            if error:
                app.logger.warning(f"OpenRouter validation failed: {error}")
            elif unavailable_models:
                app.logger.warning(
                    f"The following configured models are not available on OpenRouter: "
                    f"{', '.join(unavailable_models)}"
                )
            else:
                app.logger.info("All configured models validated successfully against OpenRouter")
        else:
            app.logger.info("OpenRouter API key not configured - skipping model validation")

    except FileNotFoundError:
        app.logger.error("models.yaml configuration file not found")
        app.config['CONFIGURED_MODELS'] = []
    except Exception as e:
        app.logger.error(f"Failed to load model configuration: {str(e)}")
        app.config['CONFIGURED_MODELS'] = []

# Root route - basic confirmation
@app.route('/')
def index():
    return render_template('index.html')


# Settings route - display and save API keys
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Handle API key configuration"""
    success_message = None
    error_message = None

    if request.method == 'POST':
        # Get form data
        openrouter_key = request.form.get('openrouter_key', '').strip()
        odin_key = request.form.get('odin_key', '').strip()

        # Validate input - only OpenRouter key is required
        if not openrouter_key:
            error_message = "OpenRouter API key is required"
        else:
            # Save API keys to database
            try:
                set_api_key('openrouter', openrouter_key)
                if odin_key:
                    set_api_key('0din_ai', odin_key)

                success_message = "API keys saved successfully"
            except Exception as e:
                error_message = f"Failed to save API keys: {str(e)}"

    # Retrieve existing API keys (masked for display)
    openrouter_key = get_api_key('openrouter')
    odin_key = get_api_key('0din_ai')

    # Mask keys for display
    masked_openrouter = mask_api_key(openrouter_key) if openrouter_key else None
    masked_odin = mask_api_key(odin_key) if odin_key else None

    # Get configured models for display
    configured_models = app.config.get('CONFIGURED_MODELS', [])

    return render_template(
        'settings.html',
        openrouter_key=masked_openrouter,
        odin_key=masked_odin,
        models=configured_models,
        model_count=len(configured_models),
        success_message=success_message,
        error_message=error_message
    )


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
