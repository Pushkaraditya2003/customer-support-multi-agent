"""
Configuration and Environment Settings for CA2 Customer Support Desk.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent
KB_DIR = PROJECT_ROOT / "knowledge_base"
DATA_DIR = PROJECT_ROOT / "data"

# Load .env file
load_dotenv(PROJECT_ROOT / ".env")

# LLM / Groq Configuration
PROVIDER: str = os.getenv("PROVIDER", "groq")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# Operational Thresholds
MAX_REVISION_ATTEMPTS: int = int(os.getenv("MAX_REVISION_ATTEMPTS", "3"))
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))

# Supported Categories
CATEGORIES = ["billing", "technical", "account", "other"]
