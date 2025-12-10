# Phase 1 Context: Project Foundation & Database Schema

## Initial Orientation

This is Phase 1 of an 8-phase implementation plan for the **LLM Jailbreak Research Tool**, a local web application for security researchers to test prompts against multiple LLM models and detect jailbreaks using the 0din-JEF library.

**Key Files:**
- **Spec**: `/docs/dev-sessions/2025-12-10-1003-planning/spec.md`
- **Plan**: `/docs/dev-sessions/2025-12-10-1003-planning/plan.md`

**Critical Facts to Remember:**
- Single-user local Flask application with SQLite database
- Use **uv** package manager for all Python dependency management
- 0din-JEF library integration for jailbreak detection (5 tests: tiananmen, nerve_agent, meth, harry_potter, copyrights)
- Scoring thresholds: 70% for substances/censorship, 80% for copyright
- Model exclusions: Grok, Mistral, Command R (excluded from substance/copyright scoring)
- Sequential testing with 5-second delays between API calls
- Manual prompt versioning (user explicitly saves versions)
- Temperature is constant across all models in a session

## Work Completed in Phase 1

### 1. Project Initialization
- Initialized git repository
- Created directory structure: `static/`, `templates/`, `models/`, `config/`
- Initialized uv package manager with `uv init --app`
- Created `.env` file for environment configuration
- Created `.gitignore` to exclude virtual environment, database, and IDE files

### 2. Dependency Management
Used **uv** to add all required dependencies:
- Flask (3.1.2)
- Flask-SQLAlchemy (3.1.1)
- requests (2.32.5)
- PyYAML (6.0.3)
- python-dotenv (1.2.1)
- 0din-jef (0.1.6)

Dependencies are tracked in `pyproject.toml` and `uv.lock`.

### 3. Flask Application Setup
Created `app.py` as the main Flask application with:
- Environment variable loading from `.env`
- Database configuration with absolute path resolution
- SQLAlchemy initialization using the factory pattern (db created in models/database.py, then initialized with app)
- Automatic database table creation on startup
- Basic index route serving `templates/index.html`
- Debug mode enabled for development

### 4. Database Models
Created comprehensive SQLAlchemy models in `models/database.py`:

**TestSession**:
- id (PK), title (nullable), created_at
- Relationship to PromptVersion with cascade delete

**PromptVersion**:
- id (PK), session_id (FK), prompt_text (TEXT), reference_text (TEXT, nullable)
- notes (nullable), is_current_version (boolean), created_at
- Relationship to TestResult with cascade delete

**TestResult**:
- id (PK), version_id (FK), model_id, model_name, vendor, temperature
- response_text (TEXT, nullable)
- Five score fields: tiananmen_score, nerve_agent_score, meth_score, harry_potter_score, copyrights_score (all nullable floats)
- Five pass fields: tiananmen_pass, nerve_agent_pass, meth_pass, harry_potter_pass, copyrights_pass (all nullable booleans)
- overall_success (boolean), error_status (boolean), error_message (TEXT, nullable)
- created_at

**Configuration**:
- id (PK), key (unique), value (TEXT), updated_at
- For storing API keys and other configuration

### 5. Database Testing
- Successfully created database file at `data/vuln_research.db`
- Verified all four tables created with correct schema
- Confirmed foreign key relationships are properly defined
- Tested data insertion and querying via SQLite CLI
- Verified Flask app runs successfully on localhost:5000

### 6. Basic UI Template
Created `templates/index.html` with:
- Welcome message confirming app is running
- Navigation links to Settings (Phase 2) and Sessions (Phase 3)

## Problems Encountered & Solutions

### Problem 1: Circular Import
**Issue**: Initial code had circular import - app.py imported models, models imported db from app.

**Solution**: Refactored to use Flask-SQLAlchemy factory pattern:
- Created `db = SQLAlchemy()` in `models/database.py`
- In `app.py`, imported db and called `db.init_app(app)`
- This allows models to use db without importing from app

### Problem 2: Database File Path
**Issue**: SQLite couldn't open database file with relative path.

**Solution**: Modified `app.py` to convert relative paths to absolute:
```python
if not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
```

### Problem 3: uv vs pip
**Issue**: Initially created requirements.txt manually, but user requested uv package manager.

**Solution**: Used `uv init --app` and `uv add` commands to manage dependencies through `pyproject.toml` instead of `requirements.txt`.

## Current State

### Working
✅ Flask application runs successfully
✅ Database schema fully implemented with all tables and relationships
✅ All dependencies installed and managed via uv
✅ Basic index page accessible at http://127.0.0.1:5000
✅ Git repository initialized

### Not Yet Implemented
- Settings page for API key configuration (Phase 2)
- Session and version management UI (Phase 3)
- OpenRouter integration (Phase 4)
- JEF scoring integration (Phase 5)
- Results display (Phase 6)
- Submission generation (Phase 7)
- End-to-end testing (Phase 8)

### Known Issues
- SQLite foreign key constraints not enforced by default (need `PRAGMA foreign_keys = ON`), but SQLAlchemy handles this correctly when using the ORM
- No model configuration YAML file yet (will be created in Phase 2)

## Success Criteria Met

All Phase 1 success criteria have been met:
- ✅ Flask application runs and serves a basic page on localhost
- ✅ Database file created with all four tables
- ✅ All foreign key relationships properly defined
- ✅ Can manually insert and query data using SQLite CLI
- ✅ Dependencies managed via uv in pyproject.toml

## Next Phase

**Phase 2: Configuration & Settings Management**

Focus areas:
- Create settings page for API key entry (OpenRouter, 0din.ai)
- Create `config/models.yaml` with initial model list
- Implement configuration loading and API key storage/retrieval
- Add OpenRouter model validation on startup
- Store validated models in app context

Ready to proceed when user approves Phase 1.
