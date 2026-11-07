#!/usr/bin/env python3
"""Compatibility wrapper: same as `holdbackcalc verify-sources`."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from holdbackcalc.verify import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
