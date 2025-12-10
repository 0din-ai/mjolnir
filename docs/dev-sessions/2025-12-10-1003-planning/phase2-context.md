# Phase 2 Context: Configuration & Settings Management

## Initial Orientation

This is Phase 2 of an 8-phase implementation plan for the **LLM Jailbreak Research Tool**, a local web application for security researchers to test prompts against multiple LLM models and detect jailbreaks using the 0din-JEF library.

**Key Files:**
- **Spec**: `/docs/dev-sessions/2025-12-10-1003-planning/spec.md`
- **Plan**: `/docs/dev-sessions/2025-12-10-1003-planning/plan.md`
- **Phase 1 Context**: `/docs/dev-sessions/2025-12-10-1003-planning/phase1-context.md`

**Critical Facts to Remember:**
- Single-user local Flask application with SQLite database
- Use **uv** package manager for all Python dependency management
- 0din-JEF library integration for jailbreak detection (5 tests: tiananmen, nerve_agent, meth, harry_potter, copyrights)
- Scoring thresholds: 70% for substances/censorship, 80% for copyright
- Model exclusions: Grok, Mistral, Command R (excluded from substance/copyright scoring)
- Sequential testing with 5-second delays between API calls
- Manual prompt versioning (user explicitly saves versions)
- Temperature is constant across all models in a session
- **OpenRouter API key is required**, 0din.ai API key is optional

## Work Completed in Phase 2

### 1. Model Configuration YAML File
Created `config/models.yaml` with 15 initial models across 6 vendors:
- **OpenAI**: GPT-4 Turbo, GPT-4, GPT-3.5 Turbo
- **Anthropic**: Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku
- **Google**: Gemini Pro, Gemini Pro 1.5
- **Meta**: Llama 3 70B Instruct, Llama 3 8B Instruct
- **Mistral**: Mistral Large, Mistral Medium
- **Cohere**: Command R+, Command R
- **xAI**: Grok Beta

Each model entry includes:
- `id`: OpenRouter model identifier (e.g., "openai/gpt-4-turbo")
- `display_name`: User-friendly name for the UI
- `vendor`: Provider name

The file includes comments explaining the format for future editing.

### 2. Configuration Module (`models/config.py`)
Implemented comprehensive configuration management functions:

**`load_models_config()`**:
- Reads and parses `config/models.yaml`
- Returns list of model dictionaries
- Handles FileNotFoundError and YAML parsing errors

**`get_api_key(key_name)`**:
- Retrieves API keys from Configuration table
- Returns None if key doesn't exist
- Used for both 'openrouter' and '0din_ai' keys

**`set_api_key(key_name, value)`**:
- Inserts new API keys or updates existing ones
- Uses upsert pattern (checks if exists, then updates or inserts)
- Commits changes to database

**`validate_models_against_openrouter(api_key, configured_models)`**:
- Queries OpenRouter `/api/v1/models` endpoint
- Compares configured models against available models
- Returns tuple: (list of unavailable models, error message)
- Handles network errors, authentication failures, and parsing errors
- 10-second timeout for API requests

**`mask_api_key(api_key)`**:
- Masks API keys for secure display in UI
- Shows first 3 characters + "***" + last 3 characters
- Example: "sk-test-1234567890" → "sk-***890"

### 3. Application Startup Integration
Modified `app.py` to load and validate models on startup:

**Startup Routine** (in app context):
1. Loads models from `config/models.yaml`
2. Stores models in `app.config['CONFIGURED_MODELS']`
3. Retrieves OpenRouter API key from database
4. If API key exists, validates configured models against OpenRouter
5. Logs appropriate info/warning messages:
   - Info: Number of models loaded
   - Info: Models validated successfully OR API key not configured
   - Warning: Specific models unavailable
   - Warning: OpenRouter API validation failed (with error details)

**Error Handling**:
- FileNotFoundError: Logs error and sets CONFIGURED_MODELS to empty list
- Other exceptions: Logs error and sets CONFIGURED_MODELS to empty list
- Application continues to run even if model loading fails

### 4. Settings Page Template
Created `templates/settings.html` with:

**Form Fields**:
- OpenRouter API key input (password field, marked as required with *)
- 0din.ai API key input (password field, marked as optional)
- Submit button

**User Experience**:
- Success message display (green, shown after successful save)
- Error message display (red, shown for validation errors)
- Help text for each field with links to get API keys
- Navigation link back to home page

**Model Display Section**:
- Shows count of loaded models
- Lists all configured models with display name, vendor, and model ID
- Useful for verifying configuration loaded correctly

**Styling**:
- Clean, modern form design with proper spacing
- Color-coded messages (green for success, red for errors)
- Mobile-responsive layout
- Accessible form labels and inputs

### 5. Settings Routes Implementation
Added `/settings` route with GET and POST handlers in `app.py`:

**GET Handler**:
- Retrieves existing API keys from database
- Masks keys for secure display (e.g., "sk-***999")
- Passes masked keys, model list, and model count to template
- Shows empty form if no keys configured yet

**POST Handler**:
- Receives form data (openrouter_key, odin_key)
- Validates that OpenRouter key is provided (required)
- Saves keys to database using `set_api_key()`
- 0din.ai key is optional - only saved if provided
- Displays success or error message
- Re-renders form with masked keys after save

**Security Considerations**:
- Keys stored in plaintext (prototype requirement per spec)
- Keys masked when displayed in form
- No client-side key exposure in HTML source
- Form uses POST to prevent key leakage in URLs/logs

### 6. Testing & Validation
Comprehensive testing performed:

**Configuration Functions**:
- ✅ `set_api_key()` successfully inserts new keys
- ✅ `get_api_key()` retrieves stored keys
- ✅ Keys persist correctly in database
- ✅ Updating existing keys works (no duplicates created)
- ✅ `mask_api_key()` correctly masks keys for display

**Settings Page**:
- ✅ GET request renders form correctly
- ✅ Shows "15 models loaded from configuration"
- ✅ POST request saves keys to database
- ✅ Success message displays after save
- ✅ Keys are masked in form after save (e.g., "sk-***999")
- ✅ Both OpenRouter and 0din.ai keys work correctly

**Startup Validation**:
- ✅ Models load from YAML on startup
- ✅ Logs show "Loaded 15 models from configuration"
- ✅ When no API key configured: "OpenRouter API key not configured - skipping model validation"
- ✅ Application continues running even without API keys

## Problems Encountered & Solutions

### Problem 1: Determining Required vs Optional API Keys
**Issue**: Initial implementation treated both API keys as required, but needed clarification on which keys were mandatory.

**Solution**: User confirmed that only the OpenRouter API key is required, while the 0din.ai API key is optional. Updated:
- Validation logic to only require OpenRouter key
- Template to mark OpenRouter field with `*` and add `required` attribute
- Template to mark 0din.ai field as "(optional)"
- POST handler to only validate OpenRouter key presence

### Problem 2: Port Conflict During Testing
**Issue**: When restarting Flask app for testing, got "Address already in use" error on port 5000.

**Solution**: Used `lsof -ti:5000 | xargs kill -9` to kill existing processes before restarting. Multiple Flask instances were running in background from previous test runs.

## Current State

### Working
✅ 15 models loaded from `config/models.yaml` on startup
✅ Configuration module with all required functions implemented
✅ Settings page displays form for API keys
✅ API keys can be saved and updated via settings page
✅ Keys are masked when displayed (security)
✅ Success message shows after save
✅ OpenRouter validation function ready (will be tested with real API key in Phase 4)
✅ Model list displays on settings page
✅ Application startup logs model loading status

### Not Yet Implemented
- Session and version management UI (Phase 3)
- Actual OpenRouter API calls for testing prompts (Phase 4)
- JEF scoring integration (Phase 5)
- Results display (Phase 6)
- Submission generation (Phase 7)
- End-to-end testing (Phase 8)

### Known Issues
None at this time. All Phase 2 functionality is working as expected.

### Testing Notes
- OpenRouter model validation has been tested with the function implementation but not with a real API key
- When a valid OpenRouter API key is added via settings, the app will need to be restarted to trigger startup validation
- No validation performed on API key format (they're treated as opaque strings)

## Success Criteria Met

All Phase 2 success criteria have been met:
- ✅ Settings page displays form for entering OpenRouter and 0din.ai API keys
- ✅ API keys can be saved and updated in the database
- ✅ Visual confirmation shown after successful save
- ✅ YAML file at `config/models.yaml` is loaded on application startup
- ✅ Application validates configured models against OpenRouter /models endpoint (function ready)
- ✅ Startup warnings displayed if configured models are unavailable (logging implemented)
- ✅ Can retrieve API keys programmatically for use in later phases

## Next Phase

**Phase 3: Session & Prompt Version Management**

Focus areas:
- Create session list page showing all test sessions
- Implement session creation form
- Build session detail page with current prompt display
- Add prompt version saving functionality
- Display version history
- Implement rollback to previous versions
- Ensure proper management of `is_current_version` flag

Ready to proceed when user approves Phase 2.
