#!/usr/bin/env python3
import sys
try:
    from aethel.linter import main
except ImportError:
    print("Error: 'aethel' package not found in Python path.")
    sys.exit(1)

if __name__ == "__main__":
    main()
