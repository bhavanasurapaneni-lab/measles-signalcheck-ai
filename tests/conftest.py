import os
import sys
from pathlib import Path

# Tests never create a real Anthropic client (no network, no cost), even if a .env exists.
os.environ["SIGNALCHECK_OFFLINE"] = "1"

# Make the src/ layout importable without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # for the evals/ package
