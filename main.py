import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui import start_ui

def main():
    try:
        asyncio.run(start_ui())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
