"""
Pytest configuration: add the pipeline bin/ directory to sys.path so that
pk_impact.py, pk_impact_models.py, etc. can be imported directly in tests.
"""

import sys
from pathlib import Path

# Resolve the bin/ directory relative to this conftest.py file:
# tests/pytest/ → ../../bin/
_BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if str(_BIN_DIR) not in sys.path:
    sys.path.insert(0, str(_BIN_DIR))
