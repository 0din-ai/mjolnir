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

# Root route - redirect to sessions
@app.route('/')
def index():
    return redirect(url_for('sessions'))


# Session list route
@app.route('/sessions')
def sessions():
    """Display list of all test sessions"""
    # Query all sessions ordered by most recent first
    all_sessions = TestSession.query.order_by(TestSession.created_at.desc()).all()

    # Add version count to each session
    sessions_with_counts = []
    for session in all_sessions:
        sessions_with_counts.append({
            'id': session.id,
            'title': session.title,
            'created_at': session.created_at,
            'version_count': len(session.prompt_versions)
        })

    return render_template('sessions.html', sessions=sessions_with_counts)


# New session form route
@app.route('/sessions/new')
def new_session():
    """Display form to create a new test session"""
    return render_template('new_session.html')


# Create session route
@app.route('/sessions', methods=['POST'])
def create_session():
    """Create a new test session"""
    title = request.form.get('title', '').strip()

    # Create new session (title can be NULL if empty)
    new_session = TestSession(
        title=title if title else None
    )
    db.session.add(new_session)
    db.session.commit()

    # Redirect to session detail page
    return redirect(url_for('session_detail', session_id=new_session.id))


# Session detail route
@app.route('/sessions/<int:session_id>')
def session_detail(session_id):
    """Display session detail with prompt editing and version history"""
    # Get session or 404
    session = TestSession.query.get_or_404(session_id)

    # Get all versions for this session, ordered by creation date (newest first)
    versions = PromptVersion.query.filter_by(session_id=session_id)\
        .order_by(PromptVersion.created_at.desc()).all()

    # Find current version
    current_version = next((v for v in versions if v.is_current_version), None)

    # Extract current prompt and reference text if exists
    current_prompt = current_version.prompt_text if current_version else None
    current_reference = current_version.reference_text if current_version else None

    # Get success/error messages from query params (for redirects)
    success_message = request.args.get('success')
    error_message = request.args.get('error')

    # Get configured models for test execution UI
    configured_models = app.config.get('CONFIGURED_MODELS', [])

    return render_template(
        'session_detail.html',
        session=session,
        versions=versions,
        current_prompt=current_prompt,
        current_reference=current_reference,
        success_message=success_message,
        error_message=error_message,
        models=configured_models
    )


# Save new version route
@app.route('/sessions/<int:session_id>/versions', methods=['POST'])
def save_version(session_id):
    """Save a new prompt version for this session"""
    # Verify session exists
    session = TestSession.query.get_or_404(session_id)

    # Get form data
    prompt_text = request.form.get('prompt_text', '').strip()
    reference_text = request.form.get('reference_text', '').strip()
    notes = request.form.get('notes', '').strip()

    # Validate required field
    if not prompt_text:
        return redirect(url_for('session_detail',
                                session_id=session_id,
                                error='Prompt text is required'))

    # Set all existing versions to not current
    PromptVersion.query.filter_by(session_id=session_id)\
        .update({'is_current_version': False})

    # Create new version as current
    new_version = PromptVersion(
        session_id=session_id,
        prompt_text=prompt_text,
        reference_text=reference_text if reference_text else None,
        notes=notes if notes else None,
        is_current_version=True
    )
    db.session.add(new_version)
    db.session.commit()

    return redirect(url_for('session_detail',
                            session_id=session_id,
                            success='New version saved successfully'))


# Rollback to previous version route
@app.route('/sessions/<int:session_id>/versions/<int:version_id>/rollback', methods=['POST'])
def rollback_version(session_id, version_id):
    """Rollback to a previous version by creating a new version with the old content"""
    # Verify session exists
    session = TestSession.query.get_or_404(session_id)

    # Get the old version to rollback to
    old_version = PromptVersion.query.filter_by(
        id=version_id,
        session_id=session_id
    ).first_or_404()

    # Set all existing versions to not current
    PromptVersion.query.filter_by(session_id=session_id)\
        .update({'is_current_version': False})

    # Create new version with old content
    rollback_version = PromptVersion(
        session_id=session_id,
        prompt_text=old_version.prompt_text,
        reference_text=old_version.reference_text,
        notes=f"Rolled back from version #{version_id}",
        is_current_version=True
    )
    db.session.add(rollback_version)
    db.session.commit()

    return redirect(url_for('session_detail',
                            session_id=session_id,
                            success=f'Rolled back to version #{version_id}'))


# Run tests route
@app.route('/sessions/<int:session_id>/run-tests', methods=['POST'])
def run_tests(session_id):
    """Run tests against selected models using the current prompt version"""
    from models.test_runner import run_tests_sequential

    # Verify session exists
    session = TestSession.query.get_or_404(session_id)

    # Get form data
    model_ids = request.form.getlist('model_ids')
    temperature = request.form.get('temperature', type=float)

    # Validate model selection
    if not model_ids:
        return redirect(url_for('session_detail',
                                session_id=session_id,
                                error='Please select at least one model to test'))

    # Validate temperature
    if temperature is None or temperature < 0 or temperature > 2:
        return redirect(url_for('session_detail',
                                session_id=session_id,
                                error='Temperature must be between 0 and 2'))

    # Get current version
    current_version = PromptVersion.query.filter_by(
        session_id=session_id,
        is_current_version=True
    ).first()

    if not current_version:
        return redirect(url_for('session_detail',
                                session_id=session_id,
                                error='Please save a prompt version before running tests'))

    # Get OpenRouter API key
    openrouter_key = get_api_key('openrouter')
    if not openrouter_key:
        return redirect(url_for('session_detail',
                                session_id=session_id,
                                error='Please configure OpenRouter API key in settings'))

    # Run tests sequentially
    try:
        result_ids = run_tests_sequential(
            version_id=current_version.id,
            model_ids=model_ids,
            temperature=temperature,
            api_key=openrouter_key,
            prompt_text=current_version.prompt_text
        )

        # Success message
        model_count = len(result_ids)
        success_msg = f'Tests completed. {model_count} model{"s" if model_count != 1 else ""} tested.'

        return redirect(url_for('session_detail',
                                session_id=session_id,
                                success=success_msg))

    except Exception as e:
        app.logger.error(f"Error running tests: {str(e)}")
        return redirect(url_for('session_detail',
                                session_id=session_id,
                                error=f'Error running tests: {str(e)}'))


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
