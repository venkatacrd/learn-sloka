"""PyInstaller entry point for the standalone 'sanskrit-extract' executable."""

from sanskrit_extract.cli import app

if __name__ == "__main__":
    app(prog_name="sanskrit-extract")
