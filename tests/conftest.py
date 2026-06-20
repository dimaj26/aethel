import os
import sys

# Ensure the repository root is importable when tests run without an editable install.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
