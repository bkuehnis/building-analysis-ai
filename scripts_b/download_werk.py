#!/usr/bin/env python3
"""
Download building data from werk-material.crb.ch

Usage:
    python scripts/download_werk.py --login       # Interactive login
    python scripts/download_werk.py               # Download data (requires prior login)
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipelines.werk.download import main

if __name__ == "__main__":
    main()
