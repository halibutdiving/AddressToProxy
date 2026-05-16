from typer.testing import CliRunner

from address_to_proxy import __version__
from address_to_proxy.cli import app


def test_package_exposes_version():
    assert __version__


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "resolve" in result.stdout
