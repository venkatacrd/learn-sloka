"""PyInstaller entry point for the standalone 'sanskrit-romanize' executable."""

from sanskrit_romanize.cli import app

if __name__ == "__main__":
    app(prog_name="sanskrit-romanize")
