"""The clock CLI must start under isolated Python from an unrelated directory."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent


@pytest.mark.parametrize("command, expected", [
    ([], "native-source"),
    (["native-source"], "--target"),
    (["local-entry"], "--out"),
])
def test_isolated_cli_help_imports_its_adjacent_helpers(tmp_path, command, expected):
    # Neither the current directory nor PYTHONPATH may supply these dependencies.
    for name in ("native_clock_source", "local_entry"):
        (tmp_path / (name + ".py")).write_text("raise RuntimeError('untrusted helper must not load')\n")
    r = subprocess.run([sys.executable, "-I", str(HERE / "ot_clk.py"), *command, "--help"],
                       cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(tmp_path)),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "usage:" in r.stdout and expected in r.stdout
    assert "ModuleNotFoundError" not in r.stderr
