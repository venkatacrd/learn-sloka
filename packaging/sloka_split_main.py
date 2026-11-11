"""PyInstaller entry point for the standalone 'sloka-split' executable."""

from sloka_split.cli import app

if __name__ == "__main__":
    app(prog_name="sloka-split")
