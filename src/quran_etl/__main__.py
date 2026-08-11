"""Allow `python -m quran_etl`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
