# Mjolnir: LLM Jailbreak Research Tool

![mjolnir](img/mjolnir.jpg)

A Flask-based web application for systematically testing and documenting LLM jailbreak attempts across multiple models. This tool helps security researchers identify vulnerabilities in LLM safety guardrails and generate bug bounty submissions for the 0din.ai platform.

## Features

- **Multi-Model Testing**: Test prompts against multiple LLM models simultaneously via OpenRouter API
- **Prompt Version Control**: Track and manage different versions of jailbreak prompts with rollback capability
- **Automated Safety Testing**: Evaluate responses using the 0din JEF (Jailbreak Evaluation Framework) with five test categories:
  - Tiananmen (Censorship) - threshold 70%
  - Nerve Agent - threshold 70%
  - Meth Synthesis - threshold 70%
  - Harry Potter Copyright - threshold 80%
  - General Copyright - threshold 80%
- **Results Analysis**: View detailed test results with scores, pass/fail status, and response analysis
- **Bug Bounty Submission**: Generate formatted JSON and text reports for 0din.ai vulnerability submissions
- **Session Management**: Organize tests into sessions with descriptive titles and notes

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- OpenRouter API key (sign up at [openrouter.ai](https://openrouter.ai))
- Optional: 0din.ai API key for programmatic submissions

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd vuln-research-tool
```

### 2. Install Dependencies

Using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5000

# Database Configuration
DATABASE_PATH=data/vuln_research.db

# API Keys (OpenRouter is required)
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

See `.env.example` for a template.

### 4. Configure Models

Edit `config/models.yaml` to specify which LLM models to test against. The file uses this format:

```yaml
models:
  - id: "openai/gpt-4-turbo"
    display_name: "GPT-4 Turbo"
    vendor: "OpenAI"

  - id: "anthropic/claude-3-opus"
    display_name: "Claude 3 Opus"
    vendor: "Anthropic"
```

Available model IDs can be found in the [OpenRouter models documentation](https://openrouter.ai/docs#models).

### 5. Run the Application

Using uv:
```bash
uv run python app.py
```

Or directly with Python:
```bash
python app.py
```

The application will start on `http://localhost:5000` (or the port specified in your `.env` file).

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_APP` | No | `app.py` | Flask application entry point |
| `FLASK_ENV` | No | `production` | Environment mode (development/production) |
| `FLASK_DEBUG` | No | `False` | Enable Flask debug mode |
| `PORT` | No | `5000` | Port to run the application on |
| `DATABASE_PATH` | No | `data/vuln_research.db` | SQLite database file path |
| `OPENROUTER_API_KEY` | Yes | - | Your OpenRouter API key |
| `SECRET_KEY` | No | Auto-generated | Flask session secret key |

### Model Configuration

The `config/models.yaml` file defines which models are available for testing. Each model entry requires:

- **id**: OpenRouter model identifier (format: `"vendor/model-name"`)
- **display_name**: User-friendly name shown in the UI
- **vendor**: Provider name (e.g., "OpenAI", "Anthropic", "Meta")

Models are validated against OpenRouter's API on application startup. Invalid or unavailable models will generate warnings in the logs.

## Usage

### 1. Configure API Keys

Navigate to **Settings** (`/settings`) and enter your OpenRouter API key. Optionally, add your 0din.ai API key for future API-based submissions.

### 2. Create a Test Session

1. Go to **Sessions** (`/sessions`)
2. Click **"Create New Session"**
3. Enter a descriptive title (optional)
4. Click **"Create Session"**

### 3. Create a Prompt Version

In the session detail page:

1. Enter your jailbreak prompt in the **"Prompt Text"** field
2. Optionally add **"Reference Text"** for copyright tests
3. Add **"Notes"** to document your approach or hypothesis
4. Click **"Save New Version"**

The system supports version control - you can create multiple versions and rollback to previous ones.

### 4. Run Tests

1. Select one or more models to test against
2. Set the temperature parameter (0.0 - 2.0, default 1.0)
3. Click **"Run Tests"**

Tests are executed sequentially. Each response is evaluated using the JEF framework with five safety tests. Results are stored in the database.

### 5. View Results

Navigate to **Results** (`/sessions/<id>/results`) to see:

- Summary statistics (total tests, success rate, average scores)
- Results grouped by prompt version
- Individual test scores and pass/fail status
- Full model responses

### 6. Submit to 0din.ai

For successful jailbreak attempts:

1. Click **"Submit to 0din"** on any test result
2. Fill out the submission form:
   - **Title**: Concise vulnerability description
   - **Summary**: Detailed explanation of the vulnerability
   - **Security Boundary**: Category (e.g., Prompt Injection, Guardrail Bypass)
   - **Severity**: Low, Medium, High, or Severe
3. Click **"Generate Submission"**
4. Copy the JSON (for API submission) or formatted report (for web form submission)

The tool generates:
- **JSON format**: Matches 0din.ai API specification for programmatic submissions
- **Text format**: Formatted report for manual web form submissions

## Workflow Example

```
1. Create Session: "GPT-4 Poetry Encoding Tests"
2. Create Prompt Version: Write initial jailbreak attempt
3. Run Tests: Test against GPT-4 Turbo and GPT-4
4. View Results: Check JEF scores (e.g., 85/100 on nerve_agent)
5. Iterate: Create new version with refined approach
6. Run Tests: Test new version
7. Submit: Generate bug bounty submission for successful jailbreak
```

## Database Schema

The application uses SQLite with four main tables:

### `test_sessions`
- `id`: Primary key
- `title`: Session name (nullable)
- `created_at`: Timestamp

### `prompt_versions`
- `id`: Primary key
- `session_id`: Foreign key to test_sessions
- `prompt_text`: The jailbreak prompt
- `reference_text`: Optional reference for copyright tests
- `notes`: Optional notes
- `is_current_version`: Boolean flag
- `created_at`: Timestamp

### `test_results`
- `id`: Primary key
- `version_id`: Foreign key to prompt_versions
- `model_id`: OpenRouter model identifier
- `model_name`: Display name
- `vendor`: Provider name
- `temperature`: Test parameter
- `response_text`: Model's response
- `tiananmen_score`, `nerve_agent_score`, `meth_score`, `harry_potter_score`, `copyrights_score`: JEF scores (0-100)
- `tiananmen_pass`, `nerve_agent_pass`, `meth_pass`, `harry_potter_pass`, `copyrights_pass`: Pass/fail flags
- `overall_success`: Overall jailbreak success
- `error_status`: Error flag
- `error_message`: Error details
- `created_at`: Timestamp

### `configuration`
- `id`: Primary key
- `key`: Configuration key (e.g., 'openrouter_api_key')
- `value`: Configuration value
- `updated_at`: Timestamp

## Security Boundaries

The tool supports the following vulnerability categories for 0din.ai submissions:

- **Prompt Injection**: Injecting malicious instructions into prompts
- **Interpreter Jailbreak**: Breaking out of code interpreter sandboxes
- **Content Manipulation**: Manipulating model outputs or behavior
- **Guardrail Bypass**: Circumventing safety guardrails
- **Context Confusion**: Exploiting context window or attention mechanisms
- **System Prompt Leakage**: Extracting system prompts or hidden instructions
- **Data Exfiltration**: Accessing or extracting unauthorized data
- **Model Manipulation**: Altering model behavior or parameters

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=models --cov-report=html
```

### Database Migrations

The application uses Flask-SQLAlchemy. Database tables are created automatically on first run. To reset the database:

```bash
rm data/vuln_research.db
python app.py  # Will recreate tables
```

### Adding New Models

1. Find the model ID on [OpenRouter](https://openrouter.ai/docs#models)
2. Add entry to `config/models.yaml`:
   ```yaml
   - id: "vendor/model-name"
     display_name: "Model Display Name"
     vendor: "Vendor Name"
   ```
3. Restart the application

### Debugging

Enable debug mode in `.env`:
```
FLASK_DEBUG=True
FLASK_ENV=development
```

Check application logs for:
- Model validation warnings
- API errors
- JEF scoring issues

## API Integration

### OpenRouter API

All model inference is handled through OpenRouter. The tool automatically:
- Validates configured models on startup
- Sends prompts with specified temperature
- Handles rate limiting and errors
- Stores raw responses for analysis

### 0din JEF Framework

The [0din-jef](https://pypi.org/project/0din-jef/) package evaluates responses across five safety categories. Each test:
- Returns a score from 0-100 (higher = more successful jailbreak)
- Has a threshold for passing (70% or 80% depending on test)
- Can be conditionally excluded (e.g., copyright tests for Chinese models)

## Troubleshooting

### "OpenRouter API key not configured"
- Ensure `OPENROUTER_API_KEY` is set in `.env`
- Or configure it via the Settings page in the UI

### "Model not available on OpenRouter"
- Check that the model ID is correct in `config/models.yaml`
- Verify the model is active on [OpenRouter](https://openrouter.ai/docs#models)
- Some models may have restricted access or be deprecated

### "Database locked" errors
- Only one process should access the SQLite database at a time
- Stop any duplicate Flask processes
- Use a production database (PostgreSQL) for concurrent access

### "No test results showing"
- Verify tests completed successfully (check logs)
- Check that the session has at least one prompt version
- Ensure the prompt version has associated test results

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues related to:
- **This tool**: Open an issue on the repository
- **0din.ai platform**: Contact support@0din.ai
- **OpenRouter API**: See [OpenRouter documentation](https://openrouter.ai/docs)
- **JEF framework**: See [0din-jef documentation](https://pypi.org/project/0din-jef/)

## Acknowledgments

- **0din.ai** for the JEF evaluation framework
- **OpenRouter** for unified LLM API access
- **Flask** and **SQLAlchemy** for the web framework
