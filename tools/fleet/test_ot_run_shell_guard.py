"""Never execute the live launcher or its historical shell-active docstring."""
import ast
import hashlib
from pathlib import Path
import shlex
import subprocess
import sys
import os
import json
import shutil
import pytest

SOURCE = Path(__file__).with_name("ot-run").read_text()
PREFIX = SOURCE.split("__doc__ = ", 1)[0]


def test_python_source_and_original_help_are_preserved():
    tree = ast.parse(SOURCE)
    help_text = next(n.value.value for n in tree.body
                     if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__doc__" for t in n.targets))
    assert hashlib.sha256(help_text.encode()).hexdigest() == "69e92f684df53bb95f66a922f1b0bcf7cf94f987bd10f8192bf2c6abc293f95d"
    assert "pkill -f" in help_text  # inert text under Python; never evaluate it


@pytest.mark.parametrize("interpreter", [["bash"], ["sh"], [sys.executable], [sys.executable, "-I"], []])
def test_shell_handoff_never_evaluates_documentation(tmp_path, interpreter):
    marker = tmp_path / "shell_doc_was_executed"
    fixture = tmp_path / "harmless_launcher.py"
    # Even if the guard regresses this fixture can only create its own marker.
    doc = "safe documentation `touch " + shlex.quote(str(marker)) + "`"
    fixture.write_text(PREFIX + "from __future__ import annotations\n__doc__ = " + json.dumps(doc) + "\nimport sys,json\nprint(json.dumps([__doc__,sys.argv[1:]]))\n")
    fixture.chmod(0o755)
    r = subprocess.run([*interpreter, str(fixture), "--harmless-fixture", "argument with spaces"],
                       text=True, capture_output=True, timeout=10)
    assert r.returncode == 0, r.stderr
    assert not marker.exists(), "documentation executed as shell commands"
    assert json.loads(r.stdout) == [doc, ["--harmless-fixture", "argument with spaces"]]


@pytest.mark.parametrize("shell", ["bash", "sh"])
def test_failed_python_exec_stops_before_documentation(tmp_path, shell):
    marker = tmp_path / "must_not_execute"
    fixture = tmp_path / "no_python.py"
    doc = "safe marker `printf x > " + shlex.quote(str(marker)) + "`"
    fixture.write_text(PREFIX + "__doc__ = " + json.dumps(doc) + "\n")
    env = dict(os.environ, PATH=str(tmp_path))
    r = subprocess.run([shutil.which(shell), str(fixture)], env=env, text=True, capture_output=True)
    assert r.returncode == 127
    assert not marker.exists()


def test_benign_control_demonstrates_unguarded_shell_substitution(tmp_path):
    marker = tmp_path / "benign_control_executed"
    fixture = tmp_path / "unguarded_control.py"
    fixture.write_text('__doc__ = "safe `touch ' + shlex.quote(str(marker)) + '`"\n')
    r = subprocess.run(["bash", str(fixture)], text=True, capture_output=True)
    assert r.returncode != 0
    assert marker.exists()
