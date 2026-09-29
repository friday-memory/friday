"""Allow running Friday CLI via python -m friday."""

import sys
from friday.cli import main

if __name__ == "__main__":
    sys.exit(main())
