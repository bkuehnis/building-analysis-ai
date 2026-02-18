#!/usr/bin/env python3
"""
Extract structured fields from Werk-material building data using OpenAI.

Usage:
    python scripts/extract_fields.py --id 57403
    python scripts/extract_fields.py --all
    python scripts/extract_fields.py --all --dry-run
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.werk.extractor import main

if __name__ == "__main__":
    main()
