"""Pytest global configuration and fixtures for Friday test suite."""

import os
import tempfile
from pathlib import Path

# Setup stable test environment before any module loads
_TMP_FACTS = str(Path(tempfile.gettempdir()) / "friday_pytest_facts.json")
os.environ["FACTS_PATH"] = _TMP_FACTS
os.environ["FRIDAY_API_KEY"] = "test_key"
os.environ["BRAIN_API_KEY"] = "test_key"
