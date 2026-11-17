"""PGCAP dependencies follow the generated configuration, not the caller shell."""
import ast
import os
from pathlib import Path
import re
import shutil
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def installer():
    source = HERE / "gen_phys.py"
    tree = ast.parse(source.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "pgcap_install")
    hook = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PGCAP_HOOK" for t in n.targets))
    ns = dict(os=os, re=re, shutil=shutil, Path=Path, __file__=str(source))
    exec(compile(ast.Module(body=[hook, fn], type_ignores=[]), str(source), "exec"), ns)
    return ns["pgcap_install"], ns["PGCAP_HOOK"]


def test_captured_enabled_without_generator_env_and_idempotence(tmp_path):
    install, hook = installer()
    (tmp_path / "config.mk").write_text("export OT_PGCAP = 1\n")
    (tmp_path / "grt_pre.tcl").write_text("# PG truth retained\n")
    with patch.dict(os.environ, {}, clear=True):
        assert install(tmp_path)
        assert (tmp_path / "pg_pair_cap.tcl").read_bytes() == (HERE / "pg_pair_cap.tcl").read_bytes()
        first = (tmp_path / "grt_pre.tcl").read_text()
        assert first.endswith(hook)
        assert install(tmp_path)
        assert (tmp_path / "grt_pre.tcl").read_text() == first


def test_effective_off_overrides_stale_env_and_previous_assignment(tmp_path):
    install, _ = installer()
    (tmp_path / "config.mk").write_text("export OT_PGCAP = 1\noverride export OT_PGCAP := 0\n")
    (tmp_path / "grt_pre.tcl").write_bytes(b"# unchanged\n")
    with patch.dict(os.environ, {"OT_PGCAP": "1"}, clear=True):
        assert not install(tmp_path)
    assert not (tmp_path / "pg_pair_cap.tcl").exists()
    assert (tmp_path / "grt_pre.tcl").read_bytes() == b"# unchanged\n"


def test_unset_config_stays_byte_identical(tmp_path):
    install, _ = installer()
    (tmp_path / "config.mk").write_text("export OT_PG_TRACK_TRUTH = 1\n")
    (tmp_path / "grt_pre.tcl").write_bytes(b"# unchanged\n")
    with patch.dict(os.environ, {}, clear=True):
        assert not install(tmp_path)
    assert not (tmp_path / "pg_pair_cap.tcl").exists()
    assert (tmp_path / "grt_pre.tcl").read_bytes() == b"# unchanged\n"
