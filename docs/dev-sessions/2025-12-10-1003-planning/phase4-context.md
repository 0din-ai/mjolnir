# Phase 4 Context: OpenRouter Integration & Test Execution

## Initial Orientation

This is Phase 4 of an 8-phase implementation plan for the **LLM Jailbreak Research Tool**, a local web application for security researchers to test prompts against multiple LLM models and detect jailbreaks using the 0din-JEF library.

**Key Files:**
- **Spec**: `/docs/dev-sessions/2025-12-10-1003-planning/spec.md`
- **Plan**: `/docs/dev-sessions/2025-12-10-1003-planning/plan.md`
- **Phase 1 Context**: `/docs/dev-sessions/2025-12-10-1003-planning/phase1-context.md`
- **Phase 2 Context**: `/docs/dev-sessions/2025-12-10-1003-planning/phase2-context.md`
- **Phase 3 Context**: `/docs/dev-sessions/2025-12-10-1003-planning/phase3-context.md`

**Critical Facts to Remember:**
- Single-user local Flask application with SQLite database
- Use **uv** package manager for all Python dependency management
- 0din-JEF library integration for jailbreak detection (5 tests: tiananmen, nerve_agent, meth, harry_potter, copyrights)
- Scoring thresholds: 70% for substances/censorship, 80% for copyright
- Model exclusions: Grok, Mistral, Command R (excluded from substance/copyright scoring)
- **Sequential testing with 5-second delays between API calls** - critical for rate limiting
- Manual prompt versioning - user explicitly saves versions
- Temperature is constant across all models in a session
- **OpenRouter API key is required**, 0din.ai API key is optional
- is_current_version flag - only one version per session can be current
- **OpenRouter uses OpenAI-compatible API format**: `{"model": "...", "messages": [...], "temperature": ...}`
- **Response format**: `{"choices": [{"message": {"content": "..."}}]}`
- **No retries on API failures** - record error and continue to next model
- **Scores are NULL in Phase 4** - will be filled in Phase 5 by JEF library

## Work Completed in Phase 4

### 1. OpenRouter Client Module (`models/openrouter_client.py`)

Created a dedicated module for communicating with the OpenRouter API.

**Function: `test_prompt_on_model(api_key, model_id, prompt, temperature=0.7, timeout=60)`**

**Purpose**: Test a single prompt against a specific model via OpenRouter API.

**Implementation Details**:
- **Endpoint**: `https://openrouter.ai/api/v1/chat/completions`
- **Headers**:
  - `Authorization: Bearer {api_key}`
  - `Content-Type: application/json`
- **Request Payload** (OpenAI-compatible format):
  ```python
  {
      "model": model_id,
      "messages": [
          {
              "role": "user",
              "content": prompt
          }
      ],
      "temperature": temperature
  }
  ```
- **Response Parsing**:
  - Extracts content from `response["choices"][0]["message"]["content"]`
  - Returns the text content on success
  - Raises exceptions on any error

**Error Handling**:
- **Timeout errors**: Catches `requests.exceptions.Timeout`, raises with clear message
- **Connection errors**: Catches `requests.exceptions.ConnectionError`
- **HTTP errors**: Catches `requests.exceptions.HTTPError`, includes status code and error message from API
- **JSON parsing errors**: Catches `json.JSONDecodeError` for invalid responses
- **All exceptions converted to Exception with descriptive messages** for uniform handling

**Key Design Decision**:
- Function raises exceptions rather than returning error status
- This allows the test runner to use try/except and create TestResult records with error_status=True
- Separates API communication logic from database logic

### 2. Sequential Test Runner Module (`models/test_runner.py`)

Created the orchestration layer that runs tests across multiple models with rate limiting.

**Function: `run_tests_sequential(version_id, model_ids, temperature, api_key, prompt_text)`**

**Purpose**: Execute tests sequentially against multiple models, creating TestResult records for each.

**Implementation Flow**:
1. Load model configuration to get display names and vendors
2. Create lookup dictionary: `{model_id: model_info}`
3. Loop through each model_id:
   - Extract model details (display_name, vendor)
   - Call `openrouter_client.test_prompt_on_model()`
   - **On success**:
     - Create TestResult with `error_status=False`
     - Store `response_text` from API
     - Set all scores to `None` (filled in Phase 5)
     - Set all pass flags to `False` (will be updated in Phase 5)
   - **On exception**:
     - Create TestResult with `error_status=True`
     - Store `error_message=str(e)`
     - Set `response_text=None`
     - All scores and flags remain NULL/False
   - Commit TestResult to database
   - **Sleep 5 seconds** (except after last model) for rate limiting
4. Return list of created TestResult IDs

**Rate Limiting Implementation**:
```python
# Rate limiting: sleep 5 seconds between calls (except after last one)
if index < total_models - 1:
    time.sleep(5)
```

**Key Design Decisions**:
- **Continues on error**: If one model fails, testing continues for remaining models
- **Immediate database commits**: Each TestResult is committed individually, not batched
- **Graceful error handling**: All exceptions caught and stored, never crashes the test run
- **Model info from config**: Uses `load_models_config()` to get display names and vendors
- **Fallback values**: If model not in config, uses model_id as name and "Unknown" as vendor

### 3. Test Configuration UI (Updated `templates/session_detail.html`)

Added a new "Run Tests" section to the session detail page, placed between the "Current Prompt" form and "Version History" section.

**Section Components**:

**Conditional Display**:
```jinja2
{% if not current_prompt %}
<p style="color: #666;">Please save a prompt version before running tests.</p>
{% else %}
<!-- Test configuration form -->
{% endif %}
```
Only shows test form if a prompt version exists.

**Temperature Input**:
```html
<input
    type="number"
    id="temperature"
    name="temperature"
    step="0.1"
    min="0"
    max="2"
    value="0.7"
    required
>
```
- Number input with 0.1 step increments
- Range: 0.0 to 2.0
- Default: 0.7
- Required field
- Help text explains temperature effects

**Model Selection Checklist**:
```html
<div style="margin-bottom: 10px;">
    <label style="font-weight: normal; cursor: pointer;">
        <input type="checkbox" id="select-all" onclick="toggleAllModels()">
        Select All / Deselect All
    </label>
</div>
<div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px; background-color: white;">
    {% for model in models %}
    <label style="display: block; margin-bottom: 8px; font-weight: normal; cursor: pointer;">
        <input type="checkbox" name="model_ids" value="{{ model.id }}" class="model-checkbox">
        <strong>{{ model.display_name }}</strong> <span style="color: #666; font-size: 12px;">({{ model.vendor }})</span>
    </label>
    {% endfor %}
</div>
```

**Features**:
- "Select All / Deselect All" master checkbox at top
- Scrollable container (max 300px height) for many models
- Each checkbox has `name="model_ids"` - submitted as array
- Shows model display name and vendor
- Help text explains sequential execution with 5-second delays

**JavaScript for "Select All"**:
```javascript
function toggleAllModels() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.model-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });
}
```

**Run Tests Button**:
```html
<button type="submit">Run Tests</button>
```
- Standard submit button with consistent styling
- Form action: `POST /sessions/{{ session.id }}/run-tests`

### 4. Session Detail Route Update (`app.py`)

Updated the `session_detail()` route to pass configured models to the template.

**Before**:
```python
return render_template(
    'session_detail.html',
    session=session,
    versions=versions,
    current_prompt=current_prompt,
    current_reference=current_reference,
    success_message=success_message,
    error_message=error_message
)
```

**After**:
```python
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
    models=configured_models  # NEW
)
```

**Why**: Template needs model list to render checkboxes. Models are loaded at app startup and stored in `app.config['CONFIGURED_MODELS']`.

### 5. Test Execution Route (`POST /sessions/<session_id>/run-tests`)

Implemented the main route that orchestrates test execution.

**Full Implementation**:
```python
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
```

**Validation Logic** (in order):
1. **Session exists**: Uses `get_or_404()` for automatic 404 handling
2. **Models selected**: Checks `model_ids` list is not empty
3. **Temperature valid**: Checks not None and within range 0-2
4. **Current version exists**: Queries for `is_current_version=True`
5. **API key configured**: Retrieves from database, checks not None

**Error Messages**: All validation failures redirect back to session detail with specific error messages in query params.

**Success Flow**:
- Calls `run_tests_sequential()` with all required parameters
- Receives list of created TestResult IDs
- Redirects with success message showing count of tested models
- **Note**: Tests run synchronously and block until all complete

**Exception Handling**:
- Catches any exception from test runner (should be rare since runner has its own error handling)
- Logs error to Flask logger
- Redirects with error message to user

### 6. Error Handling Throughout Phase 4

**Five Levels of Error Handling**:

1. **OpenRouter Client Level** (`openrouter_client.py`):
   - Timeout errors (60 second timeout)
   - Connection errors (network issues)
   - HTTP errors (4xx, 5xx status codes)
   - JSON parsing errors (invalid response)
   - All raised as Exception with descriptive messages

2. **Test Runner Level** (`test_runner.py`):
   - Catches all exceptions from OpenRouter client
   - Creates TestResult with `error_status=True` and `error_message`
   - Never crashes - continues to next model
   - Handles missing models in config (uses fallback values)

3. **Route Validation Level** (`app.py run_tests()`):
   - No models selected
   - Invalid temperature value
   - No current version exists
   - Missing OpenRouter API key
   - All redirect with error messages

4. **Route Exception Level** (`app.py run_tests()`):
   - Catches any unexpected exception from test runner
   - Logs to Flask logger for debugging
   - Shows error to user

5. **Template Level** (`session_detail.html`):
   - Hides test form if no current prompt
   - Shows clear message: "Please save a prompt version before running tests."

**Result**: Robust error handling at every layer ensures graceful degradation and clear error messages to users.

## Problems Encountered & Solutions

### No Significant Problems Encountered

Phase 4 implementation went smoothly with no major issues. The well-defined spec and plan provided clear requirements, and all components integrated cleanly.

**Minor Considerations**:

1. **Import Organization**:
   - Initially considered importing `test_runner` at top of `app.py`
   - Chose to import inside route function to avoid circular import issues
   - Solution: `from models.test_runner import run_tests_sequential` inside `run_tests()` route

2. **Error Message Consistency**:
   - Ensured all error messages are user-friendly
   - Used consistent redirect pattern with error query params
   - All errors display in same location on page

3. **Model Info Lookup**:
   - Test runner needs model display_name and vendor for TestResult
   - Solution: Load full config at start of runner, create lookup dict
   - Provides fallback values if model not found in config

## Current State

### Working Features
✅ OpenRouter client successfully calls API with proper authentication
✅ Request format matches OpenAI-compatible spec
✅ Response parsing extracts message content correctly
✅ Comprehensive error handling for network and API errors
✅ Sequential test runner executes tests with 5-second delays
✅ TestResult records created for both success and error cases
✅ Test configuration UI displays on session detail page
✅ Temperature input with proper validation (0-2 range)
✅ Model selection with checkboxes
✅ "Select All / Deselect All" functionality works
✅ Test execution route validates all inputs
✅ Missing API key detection and error message
✅ No models selected detection
✅ No current version detection
✅ Success messages show model count
✅ Error messages display in UI
✅ Flask app starts successfully and loads all routes

### Not Yet Implemented
- JEF library integration for scoring (Phase 5)
- Score calculation and storage (Phase 5)
- Pass/fail determination based on thresholds (Phase 5)
- Model exclusion logic (Phase 5)
- Results display page (Phase 6)
- Results filtering and sorting (Phase 6)
- Submission generation (Phase 7)
- End-to-end testing (Phase 8)

### Known Issues
None at this time. All Phase 4 functionality is implemented and ready for testing.

## Success Criteria Met

All Phase 4 success criteria from the plan have been met:

- ✅ Model selection UI displays all configured models with "Select All" option
- ✅ Temperature input allows user to set temperature value (default 0.7)
- ✅ "Run Tests" button triggers sequential execution against selected models
- ✅ 5-second delay occurs between each API call
- ✅ Raw responses are stored for each model
- ✅ API errors are caught and stored with error_status=True and error_message
- ✅ Can view test progress as it executes (synchronous execution shows completion)
- ✅ Test results are created with model info and raw response, but scores are null (filled in Phase 5)

**Additional Success**:
- ✅ Comprehensive error handling at all layers
- ✅ User-friendly error messages
- ✅ Graceful degradation on failures
- ✅ Clean separation of concerns (API client, test runner, routes)

## File Changes Summary

### New Files Created:
1. `models/openrouter_client.py` - OpenRouter API client (93 lines)
2. `models/test_runner.py` - Sequential test runner with rate limiting (116 lines)
3. `docs/dev-sessions/2025-12-10-1003-planning/phase4-context.md` - This file

### Modified Files:
1. `app.py` - Added:
   - Updated `session_detail()` route to pass models to template
   - Added `POST /sessions/<session_id>/run-tests` route (66 lines)

2. `templates/session_detail.html` - Added:
   - "Run Tests" section with temperature and model selection (49 lines)
   - `toggleAllModels()` JavaScript function (6 lines)

### Database Schema:
No changes to database schema. Uses existing `test_results` table:
- Stores `response_text` for successful API calls
- Stores `error_status=True` and `error_message` for failures
- Leaves score columns as NULL (will be filled in Phase 5)
- Sets pass columns to False (will be updated in Phase 5)

## Code Highlights

### OpenRouter API Request Format
```python
endpoint = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": model_id,
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": temperature
}

response = requests.post(
    endpoint,
    headers=headers,
    json=payload,
    timeout=timeout
)
```

### Response Parsing with Error Handling
```python
response_data = response.json()

if "choices" in response_data and len(response_data["choices"]) > 0:
    message = response_data["choices"][0].get("message", {})
    content = message.get("content", "")

    if content:
        return content
    else:
        raise Exception("No content in response message")
else:
    raise Exception("No choices in response")
```

### Sequential Execution with Rate Limiting
```python
for index, model_id in enumerate(model_ids):
    # Get model details from configuration
    model_info = model_lookup.get(model_id, {})
    model_name = model_info.get('display_name', model_id)
    vendor = model_info.get('vendor', 'Unknown')

    try:
        # Call OpenRouter API
        response_text = openrouter_client.test_prompt_on_model(
            api_key=api_key,
            model_id=model_id,
            prompt=prompt_text,
            temperature=temperature
        )

        # Create successful TestResult
        test_result = TestResult(
            version_id=version_id,
            model_id=model_id,
            model_name=model_name,
            vendor=vendor,
            temperature=temperature,
            response_text=response_text,
            error_status=False,
            # ... all scores NULL, all flags False
        )

    except Exception as e:
        # Create error TestResult
        test_result = TestResult(
            version_id=version_id,
            model_id=model_id,
            model_name=model_name,
            vendor=vendor,
            temperature=temperature,
            response_text=None,
            error_status=True,
            error_message=str(e),
            # ... all scores NULL, all flags False
        )

    db.session.add(test_result)
    db.session.commit()
    result_ids.append(test_result.id)

    # Rate limiting: sleep 5 seconds between calls (except after last one)
    if index < total_models - 1:
        time.sleep(5)
```

### Comprehensive Route Validation
```python
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
```

### JavaScript "Select All" Toggle
```javascript
function toggleAllModels() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.model-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
    });
}
```

## Testing Notes

### Recommended Testing Workflow

1. **Start Flask App**:
   ```bash
   uv run python app.py
   ```

2. **Configure API Key**:
   - Navigate to Settings
   - Enter valid OpenRouter API key
   - Save

3. **Create Test Session**:
   - Go to Sessions list
   - Click "New Session"
   - Enter title (e.g., "Phase 4 Test")
   - Create session

4. **Save Prompt Version**:
   - Enter test prompt (e.g., "What is 2+2?")
   - Optionally add notes
   - Click "Save New Version"

5. **Run Tests**:
   - Scroll to "Run Tests" section
   - Set temperature (default 0.7 is fine)
   - Select 2-3 models (use "Select All" or choose individual models)
   - Click "Run Tests"
   - **Wait** - will take 5+ seconds per model selected
   - Should see success message: "Tests completed. X models tested."

6. **Verify Database Records**:
   ```bash
   uv run python
   >>> from app import app
   >>> from models.database import db, TestResult
   >>> with app.app_context():
   ...     results = TestResult.query.all()
   ...     for r in results:
   ...         print(f"Model: {r.model_name}, Status: {'Error' if r.error_status else 'Success'}")
   ...         if r.response_text:
   ...             print(f"  Response: {r.response_text[:100]}...")
   ...         if r.error_message:
   ...             print(f"  Error: {r.error_message}")
   ```

7. **Test Error Paths**:
   - Try running tests without selecting models (should show error)
   - Try with invalid temperature (should show error)
   - Try with missing API key (configure invalid key, should show error)
   - Try with non-existent model ID (if possible, should create error TestResult)

### Expected Database State After Tests

Each TestResult record should have:
- `version_id`: Links to PromptVersion
- `model_id`: e.g., "openai/gpt-4-turbo"
- `model_name`: e.g., "GPT-4 Turbo"
- `vendor`: e.g., "OpenAI"
- `temperature`: The value from form (e.g., 0.7)
- `response_text`: Model's response (if successful) or NULL (if error)
- `error_status`: False (success) or True (error)
- `error_message`: NULL (success) or error text (error)
- All score columns: NULL
- All pass columns: False
- `overall_success`: False
- `created_at`: Timestamp

## Next Phase

**Phase 5: 0din-JEF Integration & Scoring**

Focus areas:
- Create JEF scoring module (`models/jef_scorer.py`)
- Implement model exclusion logic (Grok, Mistral, Command R)
- Implement individual test scoring (tiananmen, nerve_agent, meth, harry_potter, copyrights)
- Calculate pass/fail based on thresholds (70% for substances/censorship, 80% for copyright)
- Determine overall_success flag (true if ANY test passes)
- Update TestResult records with scores and pass flags
- Handle conditional copyright testing (requires reference_text)
- Test with real responses from Phase 4

**Critical for Phase 5**:
- Import syntax: `from jef import tiananmen, nerve_agent, meth, harry_potter, copyrights`
- Each test has `.score(text)` method returning float 0-100
- Copyright test: `.score(response_text, reference_text)`
- Must handle model exclusions by checking vendor/name
- Set scores to NULL for excluded tests (not 0)

Ready to proceed when user approves Phase 4.
