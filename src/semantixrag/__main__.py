"""Allow semantixrag to be executed as a module: python -m semantixrag"""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
