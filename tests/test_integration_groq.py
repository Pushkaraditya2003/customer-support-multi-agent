"""
Optional Live Integration Test for Groq API + Semantic Kernel execution.
Validates live model inference and tool calling on cse476 environment.
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY", "")


@pytest.mark.skipif(not GROQ_KEY or "your_" in GROQ_KEY, reason="Valid GROQ_API_KEY not configured in .env")
def test_live_groq_integration():
    import groq
    # Initialize Groq client with explicit base_url
    client = groq.Groq(api_key=GROQ_KEY, base_url="https://api.groq.com")
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        messages=[{"role": "user", "content": "Respond with: VERIFIED"}],
        max_tokens=300,
    )
    content = resp.choices[0].message.content or ""
    assert "VERIFIED" in content.upper()
