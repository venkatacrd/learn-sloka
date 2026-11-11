from typer.testing import CliRunner

from sanskrit_extract import __version__
from sanskrit_extract.cli import app


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
