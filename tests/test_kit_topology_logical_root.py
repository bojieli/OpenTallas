"""WAVE-PREPNR-1115: kit_rtl recorded through a symlinked work root (epyc2 kw43-wave-1109 -> scratch3) names a path that
the roam host lacks; kit_topology.localize_bound must map it back onto the local kit dir."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "die_plan"))
import kit_topology as KT


def _kit(tmp_path, recorded_root):
    base = tmp_path / "s2" / "claude" / "kw43-wave-1109"
    local = base / "runs" / "qwen_kvsys" / "kit-wave" / "ev" / "items" / "t" / "attempt_19" / "rtl"
    local.mkdir(parents=True)
    (local / "t_bound.sv").write_text("module t_bound; endmodule\n")
    (local / "t_top.sv").write_text("module t_top; endmodule\n")
    rec = recorded_root / local.relative_to(base)
    files = [str(rec / "t_top.sv"), str(rec / "t_bound.sv")]
    (local / "kit_rtl.json").write_text(json.dumps({"files": files, "bound_module": "t_bound"}))
    (local / "kit_rtl.f").write_text("\n".join(files) + "\n")
    return local, rec


def test_remap_stale_realpath_spelling(tmp_path):
    local, rec = _kit(tmp_path, tmp_path / "s3" / "claude" / "kw43-wave-1109")
    assert not (rec / "t_bound.sv").exists()
    assert KT.remap_under_root(rec / "t_bound.sv", local) == local / "t_bound.sv"
    assert KT.remap_under_root(local / "t_bound.sv", local) == local / "t_bound.sv"
    other = tmp_path / "elsewhere" / "x.sv"
    assert KT.remap_under_root(other, local) == other


def test_localize_bound_no_filenotfound(tmp_path):
    local, rec = _kit(tmp_path, tmp_path / "s3" / "claude" / "kw43-wave-1109")
    KT.localize_bound(local)
    man = json.loads((local / "kit_rtl.json").read_text())
    assert all(Path(f).is_file() and Path(f).parent == local for f in man["files"])
    assert all(Path(x).is_file() for x in (local / "kit_rtl.f").read_text().split())


def test_logical_path_kept_not_resolved(tmp_path):
    real = tmp_path / "s3" / "w"
    real.mkdir(parents=True)
    (tmp_path / "s2").mkdir()
    os.symlink(real, tmp_path / "s2" / "w")
    logical = tmp_path / "s2" / "w" / "rtl"
    assert os.path.abspath(logical) == str(logical) and str(logical.resolve()) != str(logical)
