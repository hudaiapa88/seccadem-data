#!/usr/bin/env python3
"""
Orchestrator — fetches all prayer times data from all sources.
Usage: python fetch_all.py [year]
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else datetime.now().year

    print(f"\n{'#'*60}")
    print(f"#  Seccadem Data — Full Fetch for {year}")
    print(f"{'#'*60}")

    # 1. Diyanet (TR + CY)
    print(f"\n[1/2] Fetching Diyanet data (TR + CY)...")
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "fetch_diyanet.py"), str(year)])

    # 2. Aladhan (63 countries)
    print(f"\n[2/2] Fetching Aladhan data (63 countries)...")
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "fetch_aladhan.py"), str(year)])

    print(f"\n{'#'*60}")
    print(f"#  All done! Review data in v1/ directory")
    print(f"{'#'*60}")


if __name__ == "__main__":
    main()
