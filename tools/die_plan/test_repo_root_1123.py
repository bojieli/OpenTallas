"""REPO-ROOT-1123: $OT_REPO_ROOT names the tree whose repository-relative data the bind / taps / remap read."""
import importlib
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _fresh(mod, env):
    code = f"import sys; sys.path.insert(0, {str(HERE)!r}); import {mod} as M; print(M.REPO if hasattr(M, 'REPO') else M._root())"
    return subprocess.run([sys.executable, "-I", "-c", code], env=env, capture_output=True, text=True, check=True).stdout.strip()


def test_env_root_wins_for_bind_elab_and_taps(tmp_path):
    env = dict(os.environ, OT_REPO_ROOT=str(tmp_path))
    assert _fresh("bind_elab", env) == str(tmp_path.resolve())
    assert _fresh("taps", env) == str(tmp_path.resolve())


def test_unset_or_missing_keeps_tool_checkout(tmp_path):
    tool_root = str(HERE.parents[1])
    env = {k: v for k, v in os.environ.items() if k != "OT_REPO_ROOT"}
    assert _fresh("bind_elab", env) == tool_root
    env["OT_REPO_ROOT"] = str(tmp_path / "absent")
    assert _fresh("taps", env) == tool_root


def test_input_path_resolves_under_env_root(tmp_path, monkeypatch):
    import taps
    (tmp_path / "physical").mkdir()
    (tmp_path / "physical" / "x.json").write_text("{}")
    monkeypatch.setenv("OT_REPO_ROOT", str(tmp_path))
    assert taps.input_path("physical/x.json") == tmp_path.resolve() / "physical" / "x.json"
