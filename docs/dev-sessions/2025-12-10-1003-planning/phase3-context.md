# Phase 3 Context: Session & Prompt Version Management

## Initial Orientation

This is Phase 3 of an 8-phase implementation plan for the **LLM Jailbreak Research Tool**, a local web application for security researchers to test prompts against multiple LLM models and detect jailbreaks using the 0din-JEF library.

**Key Files:**
- **Spec**: `/docs/dev-sessions/2025-12-10-1003-planning/spec.md`
- **Plan**: `/docs/dev-sessions/2025-12-10-1003-planning/plan.md`
- **Phase 1 Context**: `/docs/dev-sessions/2025-12-10-1003-planning/phase1-context.md`
- **Phase 2 Context**: `/docs/dev-sessions/2025-12-10-1003-planning/phase2-context.md`

**Critical Facts to Remember:**
- Single-user local Flask application with SQLite database
- Use **uv** package manager for all Python dependency management
- 0din-JEF library integration for jailbreak detection (5 tests: tiananmen, nerve_agent, meth, harry_potter, copyrights)
- Scoring thresholds: 70% for substances/censorship, 80% for copyright
- Model exclusions: Grok, Mistral, Command R (excluded from substance/copyright scoring)
- Sequential testing with 5-second delays between API calls
- **Manual prompt versioning** - user explicitly saves versions
- Temperature is constant across all models in a session
- **OpenRouter API key is required**, 0din.ai API key is optional
- **is_current_version flag** - only one version per session can be current
- **Rollback creates new version** - maintains full audit trail

## Work Completed in Phase 3

### 1. Session List Page (`templates/sessions.html`)
Created comprehensive session list page with:

**Features**:
- Table displaying all test sessions ordered by most recent first
- Columns: Session title/ID, Created date, Version count
- "New Session" button in header
- Clickable session rows that link to session detail
- Empty state message when no sessions exist
- Navigation links to Home and Settings

**Styling**:
- Clean table layout with hover effects
- Mobile-responsive design
- Consistent styling with settings page
- Empty state with call-to-action button

### 2. Session Routes in `app.py`

**Root Route (Modified)**:
```python
@app.route('/')
def index():
    return redirect(url_for('sessions'))
```
- Changed from static page to redirect to sessions list
- Sessions list is now the main landing page

**Session List Route**:
```python
@app.route('/sessions')
def sessions():
```
- Queries all TestSession records ordered by `created_at DESC`
- Calculates version count for each session using `session.prompt_versions` relationship
- Returns sessions with counts to template
- **Bug Fix**: Changed from `session.versions` to `session.prompt_versions` to match database model

**New Session Form Route**:
```python
@app.route('/sessions/new')
def new_session():
```
- Displays form for creating new session
- Simple GET route rendering `new_session.html`

**Create Session Route**:
```python
@app.route('/sessions', methods=['POST'])
def create_session():
```
- Accepts title from form (optional field)
- Creates new TestSession with title or NULL
- Redirects to session detail page after creation
- Returns session ID for routing

### 3. New Session Form (`templates/new_session.html`)
Created simple session creation form with:

**Form Fields**:
- Optional text input for session title
- Submit button

**User Experience**:
- Help text explaining purpose of title field
- Default label: "Untitled Session" if left blank
- Navigation back to sessions list
- Clean, minimal design focusing on quick session creation

### 4. Session Detail Page (`templates/session_detail.html`)
Created comprehensive session detail page - the main working area of the application:

**Header Section**:
- Session title or "Untitled Session"
- Session ID and creation date
- Navigation to sessions list and settings

**Current Prompt Section**:
- Form to save new version
- Prompt text textarea (required, 10 rows, monospace)
- Reference text textarea (optional, 5 rows, for copyright tests)
- Version notes textarea (optional, 3 rows)
- "Save New Version" button
- Help text explaining each field

**Version History Section**:
- Lists all versions in reverse chronological order
- Each version shows:
  - Version number (calculated as loop.revindex)
  - "CURRENT" badge for current version
  - Creation date/time
  - Notes preview (if present)
  - Prompt text preview (first 100 characters)
- Click to expand/collapse full version details
- Expanded view shows:
  - Full prompt text
  - Full reference text (if present)
  - Full notes (if present)
  - "Rollback to This Version" button (for non-current versions only)

**Visual Design**:
- Current version highlighted with green background
- Clickable headers with hover effects
- JavaScript toggle for expand/collapse
- Monospace font for prompt text
- Clear visual hierarchy

### 5. Session Detail Route

**Implementation**:
```python
@app.route('/sessions/<int:session_id>')
def session_detail(session_id):
```

**Functionality**:
- Uses `get_or_404` to retrieve session
- Queries all PromptVersion records for session, ordered by `created_at DESC`
- Finds current version using `next((v for v in versions if v.is_current_version), None)`
- Extracts current prompt and reference text if current version exists
- Retrieves success/error messages from query params (for redirect messages)
- Passes all data to template

**Error Handling**:
- Returns 404 if session doesn't exist
- Handles case where no current version exists (empty form)

### 6. Save Version Functionality

**Implementation**:
```python
@app.route('/sessions/<int:session_id>/versions', methods=['POST'])
def save_version(session_id):
```

**Critical Logic**:
1. Verifies session exists (404 if not)
2. Retrieves form data: `prompt_text`, `reference_text`, `notes`
3. Validates `prompt_text` is not empty (required field)
4. **Sets all existing versions to `is_current_version=False`** using bulk update
5. Creates new PromptVersion with `is_current_version=True`
6. Commits transaction
7. Redirects to session detail with success message

**Key Implementation Detail**:
```python
PromptVersion.query.filter_by(session_id=session_id)\
    .update({'is_current_version': False})
```
This ensures **only one version is current at a time** - critical requirement from spec.

**Validation**:
- Prompt text is required
- Reference text and notes are optional (NULL if empty)
- Returns error message if prompt text is missing

### 7. Rollback Functionality

**Implementation**:
```python
@app.route('/sessions/<int:session_id>/versions/<int:version_id>/rollback', methods=['POST'])
def rollback_version(session_id, version_id):
```

**Rollback Strategy** (maintains audit trail):
1. Verifies session and old version exist (404 if not)
2. Retrieves old version by ID and session_id (ensures version belongs to session)
3. Sets all existing versions to `is_current_version=False`
4. **Creates NEW version** with:
   - Same `prompt_text` as old version
   - Same `reference_text` as old version
   - Notes: "Rolled back from version #{version_id}"
   - `is_current_version=True`
5. Commits and redirects with success message

**Why Create New Version?**:
- Maintains complete audit trail
- Can see all rollback operations in history
- Never deletes or modifies historical data
- Complies with spec requirement

### 8. Testing & Validation
User performed comprehensive manual testing and confirmed all features working correctly:

**Tested Workflows**:
- ✅ Session list page displays correctly
- ✅ Can create new sessions with titles
- ✅ Can create sessions without titles ("Untitled Session")
- ✅ Session detail page loads with all sections
- ✅ Can save prompt versions with all fields
- ✅ Version history displays correctly
- ✅ Current version badge shows correctly
- ✅ Expand/collapse works for version details
- ✅ Rollback creates new version correctly
- ✅ is_current_version flag properly maintained

**Database Validation**:
- ✅ Only one version has `is_current_version=True` per session
- ✅ Foreign key relationship works (session_id references test_sessions)
- ✅ Version count calculates correctly using relationship
- ✅ Rollback creates new record instead of modifying existing

## Problems Encountered & Solutions

### Problem 1: AttributeError on session.versions
**Issue**: When implementing session list route, got error:
```
AttributeError: 'TestSession' object has no attribute 'versions'
```

**Root Cause**: The SQLAlchemy relationship in `TestSession` model is named `prompt_versions`, not `versions`:
```python
prompt_versions = db.relationship('PromptVersion', backref='session', lazy=True, cascade='all, delete-orphan')
```

**Solution**: Changed app.py line 97 from:
```python
'version_count': len(session.versions)
```
to:
```python
'version_count': len(session.prompt_versions)
```

**Lesson**: Always verify exact relationship names in database models before using them in routes.

### Problem 2: User Stopped Testing Early
**Issue**: Started manual curl testing but user indicated they tested features themselves.

**Solution**: User confirmed all features work correctly through browser testing. Moved on to documentation as requested.

## Current State

### Working
✅ Session list page showing all sessions with version counts
✅ Create new session with optional title
✅ Session detail page with full version management
✅ Save new prompt versions with prompt, reference, and notes
✅ Version history displays all versions chronologically
✅ Current version badge and highlighting
✅ Expand/collapse version details with JavaScript
✅ Rollback to previous versions (creates new version)
✅ is_current_version flag properly maintained
✅ Success/error messages via redirect query params
✅ Navigation between all session pages
✅ Root route redirects to sessions list

### Not Yet Implemented
- OpenRouter integration and test execution (Phase 4)
- Model selection UI (Phase 4)
- Temperature configuration (Phase 4)
- Sequential test runner (Phase 4)
- JEF scoring integration (Phase 5)
- Results display (Phase 6)
- Submission generation (Phase 7)
- End-to-end testing (Phase 8)

### Known Issues
None at this time. All Phase 3 functionality is working as expected.

## Success Criteria Met

All Phase 3 success criteria have been met:
- ✅ Can create new test session with optional title
- ✅ Session list page shows all sessions with creation dates
- ✅ Can view individual session with current prompt and version history
- ✅ Can save new prompt version with optional notes
- ✅ Version history displays all versions chronologically
- ✅ Rollback loads previous version as current prompt (creates new version, doesn't delete)
- ✅ Foreign key relationship between sessions and versions works correctly
- ✅ "is_current_version" flag is properly maintained (only one current version per session)

## File Changes Summary

### New Files Created:
1. `templates/sessions.html` - Session list page (75 lines)
2. `templates/new_session.html` - New session form (68 lines)
3. `templates/session_detail.html` - Session detail with version management (225 lines)

### Modified Files:
1. `app.py` - Added 4 new routes:
   - Modified `/` to redirect to sessions
   - Added `GET /sessions` - session list
   - Added `GET /sessions/new` - new session form
   - Added `POST /sessions` - create session
   - Added `GET /sessions/<id>` - session detail
   - Added `POST /sessions/<id>/versions` - save version
   - Added `POST /sessions/<id>/versions/<version_id>/rollback` - rollback

### Database Schema:
No changes to database schema. Used existing tables:
- `test_sessions` - stores sessions
- `prompt_versions` - stores versions with is_current_version flag

## Code Highlights

### Session List with Version Counts
```python
all_sessions = TestSession.query.order_by(TestSession.created_at.desc()).all()
sessions_with_counts = []
for session in all_sessions:
    sessions_with_counts.append({
        'id': session.id,
        'title': session.title,
        'created_at': session.created_at,
        'version_count': len(session.prompt_versions)
    })
```

### Maintaining is_current_version Flag
```python
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
```

### Rollback Creating New Version
```python
# Create new version with old content
rollback_version = PromptVersion(
    session_id=session_id,
    prompt_text=old_version.prompt_text,
    reference_text=old_version.reference_text,
    notes=f"Rolled back from version #{version_id}",
    is_current_version=True
)
```

### JavaScript Version Toggle
```javascript
function toggleVersion(versionId) {
    const body = document.getElementById('version-body-' + versionId);
    body.classList.toggle('expanded');
}
```

## Next Phase

**Phase 4: OpenRouter Integration & Test Execution**

Focus areas:
- Create OpenRouter client module for API calls
- Add model selection UI to session detail page
- Add temperature configuration input
- Implement sequential test runner with 5-second delays
- Handle API errors and timeouts
- Store raw responses in test_results table
- Add basic progress indication

Ready to proceed when user approves Phase 3.
