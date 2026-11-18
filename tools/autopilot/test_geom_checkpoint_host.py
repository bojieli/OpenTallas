"""A missing old source tree cannot move geometry checks away from their placed DB."""
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


def tool_root(tmp_path):
    root = tmp_path / "qualified_tools"
    root.mkdir()
    for name in K.GEOM_TOOL_FILES:
        (root / name).write_text("# qualified " + name + "\n")
    return root


def runner(calls, bad_copy=False):
    def run(stage, argv, **kwargs):
        calls.append((stage, argv))
        argv = list(argv)
        if argv[0] == "rsync":
            assert argv[-1].startswith("epyc7:")
            argv[-1] = argv[-1].split(":", 1)[1]
            if bad_copy:
                return 23, "transfer failed"
        else:
            assert argv[5] == "epyc7"  # actual DB host, not gen host epyc10
            argv = shlex.split(argv[6])
        p = subprocess.run(argv, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr
    return run


def test_missing_old_source_stages_complete_tools_at_checkpoint_host(tmp_path):
    source = tool_root(tmp_path)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    actual_db = tmp_path / "actual_kit" / "3_place.odb"
    actual_db.parent.mkdir()
    actual_db.write_bytes(b"placed DB must stay on epyc7")
    calls = []
    staged = Path(K.stage_geom_tools(attempt, str(tmp_path / "geom"), "epyc7", "intel2", runner(calls), source))
    assert {p.name for p in staged.iterdir()} == set(K.GEOM_TOOL_FILES)
    for name in K.GEOM_TOOL_FILES:
        assert (staged / name).read_bytes() == (source / name).read_bytes()
    assert actual_db.read_bytes() == b"placed DB must stay on epyc7"
    assert all("epyc10" not in " ".join(argv) for _, argv in calls)
    body = Path(K.__file__).read_text().split("    def after_place(K, rc, txt):", 1)[1].split("    svc_file =", 1)[0]
    assert "[kh], roam=False" in body
    assert "_gh = G" not in body


def test_transfer_failure_is_infra_without_missing_checkpoint_claim(tmp_path):
    source = tool_root(tmp_path)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    with pytest.raises(OSError, match="KW_GEOM_TOOLS epyc7: copy failed") as e:
        K.stage_geom_tools(attempt, str(tmp_path / "geom"), "epyc7", "intel2", runner([], bad_copy=True), source)
    cls, reason = K.classify("geom_tools", str(e.value))
    assert cls == "INFRA"
    assert "checkpoint missing" not in reason


def test_missing_bundle_member_never_runs_geometry(tmp_path):
    source = tool_root(tmp_path)
    (source / "geom_memory.py").unlink()
    calls = []
    with pytest.raises(OSError):
        K.stage_geom_tools(tmp_path, str(tmp_path / "geom"), "epyc7", "intel2", runner(calls), source)
    assert calls == []
