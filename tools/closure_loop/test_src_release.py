"""SRC-RELEASE (ROOT 2026-10-15): terminal jobs lose src/ + bench_src*/ snapshots soon after the verdict."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as cl  # noqa: E402

C = "a" * 40


def _run(tmp, refs):
    env = dict(os.environ, OT_DR=json.dumps(dict(run=str(tmp), mode="src", src_commit=C, refs=refs)))
    return subprocess.run([sys.executable, "-"], input=cl.DEEP_RELEASE_PY, text=True, env=env, capture_output=True)


def test_src_mode_cuts_only_snapshots_and_keeps_receipt_paths(tmp_path):
    for d in ("src", "bench_src_a1", "bench_src_a2"):
        (tmp_path / d / "physical/x").mkdir(parents=True)
        (tmp_path / d / "SOURCE_COMMIT").write_text(C + "\n")
        (tmp_path / d / "physical/x/big.json").write_bytes(b"0" * 100000)
        (tmp_path / d / "physical/x/sig.sdc").write_text("x")
    (tmp_path / "bench_src_a2/SOURCE_COMMIT").write_text("b" * 40 + "\n")     # another commit: kept whole
    (tmp_path / "routes/r").mkdir(parents=True)
    (tmp_path / "routes/r/6_final.odb").write_bytes(b"1" * 1000)
    keep = str(tmp_path / "src/physical/x/sig.sdc")
    r = _run(tmp_path, [keep])
    assert r.returncode == 0 and "DEEP_FREED" in r.stdout, r.stderr
    assert (tmp_path / "src/physical/x/sig.sdc").exists() and not (tmp_path / "src/physical/x/big.json").exists()
    assert (tmp_path / "src/SOURCE_COMMIT").exists() and (tmp_path / "src/TRIMMED_SOURCE_SNAPSHOT").exists()
    assert not (tmp_path / "bench_src_a1/physical").exists()
    assert (tmp_path / "bench_src_a2/physical/x/big.json").exists()
    assert (tmp_path / "routes/r/6_final.odb").exists()


def test_keep_marker_and_candidates(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/SOURCE_COMMIT").write_text(C)
    (tmp_path / "src/f").write_text("x")
    (tmp_path / ".keep").write_text("")
    assert "DEEP_FREED 0" in _run(tmp_path, []).stdout and (tmp_path / "src/f").exists()
    old = "2026-10-01T00:00:00-07:00"
    base = dict(host="h", run="/r/a", updated=old, events=[], spec={"block": "b"})
    jobs = [dict(base, name="a", status="CLOSED"),
            dict(base, name="b", status="EARLY_FAIL_HOLD", run="/r/b"),
            dict(base, name="c", status="CLOSED", run="/r/c", near_miss_retained=True),
            dict(base, name="d", status="CLOSED", run="/r/d"), dict(base, name="d2", status="RUNNING", run="/r/d"),
            dict(base, name="e", status="CLOSED", run="/r/e", src_released={"at": old})]
    with patch.object(cl, "hosts_table", lambda: [{"name": "h"}]), patch.object(cl, "closed_blocks", lambda j: set()), \
            patch.object(cl, "near_miss", lambda j, c=None: False), patch.object(cl, "bf_exempt", lambda j, now=None: False), \
            patch.object(cl, "helper_provenance_retained", lambda j: False), \
            patch.object(cl, "collect_crash_after_closed_verdict", lambda j: False), \
            patch.object(cl, "viz_elem_running", lambda j: False), patch.object(cl, "STATE", tmp_path):
        assert [x["name"] for x in cl.src_release_candidates(jobs)] == ["a"]
