"""
Database models for LLM Jailbreak Research Tool
Defines SQLAlchemy ORM models for test sessions, prompt versions, test results, and configuration.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy (will be bound to app in app.py)
db = SQLAlchemy()


class TestSession(db.Model):
    """
    Represents a test session containing multiple prompt versions and test results.
    """
    __tablename__ = 'test_sessions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    prompt_versions = db.relationship('PromptVersion', backref='session', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TestSession {self.id}: {self.title or "Untitled"}>'


class PromptVersion(db.Model):
    """
    Represents a version of a prompt within a test session.
    Supports versioning with rollback capability.
    """
    __tablename__ = 'prompt_versions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('test_sessions.id'), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    reference_text = db.Column(db.Text, nullable=True)  # For copyright tests
    notes = db.Column(db.Text, nullable=True)
    is_current_version = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    test_results = db.relationship('TestResult', backref='prompt_version', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PromptVersion {self.id} (Session {self.session_id}, Current: {self.is_current_version})>'


class TestResult(db.Model):
    """
    Represents the result of testing a prompt against a specific model.
    Stores raw response, JEF scores, and pass/fail status.
    """
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('prompt_versions.id'), nullable=False)

    # Model information
    model_id = db.Column(db.String(255), nullable=False)  # OpenRouter format like "openai/gpt-4"
    model_name = db.Column(db.String(255), nullable=False)
    vendor = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, nullable=False)

    # Response
    response_text = db.Column(db.Text, nullable=True)

    # JEF Test Scores (0-100, nullable for excluded models or conditional tests)
    tiananmen_score = db.Column(db.Float, nullable=True)
    nerve_agent_score = db.Column(db.Float, nullable=True)
    meth_score = db.Column(db.Float, nullable=True)
    harry_potter_score = db.Column(db.Float, nullable=True)
    copyrights_score = db.Column(db.Float, nullable=True)

    # Pass/Fail Status (nullable for skipped tests)
    tiananmen_pass = db.Column(db.Boolean, nullable=True, default=False)
    nerve_agent_pass = db.Column(db.Boolean, nullable=True, default=False)
    meth_pass = db.Column(db.Boolean, nullable=True, default=False)
    harry_potter_pass = db.Column(db.Boolean, nullable=True, default=False)
    copyrights_pass = db.Column(db.Boolean, nullable=True, default=False)

    # Overall result
    overall_success = db.Column(db.Boolean, default=False, nullable=False)
    error_status = db.Column(db.Boolean, default=False, nullable=False)
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<TestResult {self.id}: {self.model_name} (Success: {self.overall_success})>'


class Configuration(db.Model):
    """
    Key-value store for application configuration, primarily API keys.
    """
    __tablename__ = 'configuration'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Configuration {self.key}>'
