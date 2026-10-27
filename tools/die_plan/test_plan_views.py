"""COORD ruling KV-CORES-R6: derived plan dirs carry REAL view copies + views.sha256; no write through shared symlinks."""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_views as PV  # noqa: E402


def _shared(tmp_path):
    """shared/ = another plan's real views; plan/ = a plan dir whose cores/ and plan json are symlinks (the R5 case)."""
    sh = tmp_path / "shared"
    (sh / "cores").mkdir(parents=True)
    (sh / "cores/a_pins.json").write_text('{"pins": [1]}\n')
    (sh / "cores/b_pins_fMX.json").write_text('{"pins": [2]}\n')
    plan = dict(partition_types={"t": {"hard_cores": [{"inst": "u0", "module": "a", "pins_file": "cores/a_pins.json"}]}})
    (sh / "hm.json").write_text(json.dumps(plan))
    pd = tmp_path / "plan"
    pd.mkdir()
    os.symlink(sh / "cores", pd / "cores")
    os.symlink(sh / "hm.json", pd / "hm.json")
    return sh, pd


def _snap(sh):
    return {p.relative_to(sh).as_posix(): p.read_bytes() for p in sorted(sh.rglob("*")) if p.is_file()}


def test_snapshot_real_copies_and_sha_list(tmp_path):
    sh, pd = _shared(tmp_path)
    before = _snap(sh)
    out = tmp_path / "out"
    n = PV.snapshot(pd, out)
    assert n == 2
    assert not (out / "cores").is_symlink() and (out / "cores").is_dir()
    assert all(not p.is_symlink() for p in (out / "cores").iterdir())
    assert PV.verify(out) == []
    PV.safe_write(out, "cores/a_pins.json", '{"pins": [9]}\n')          # derived view
    PV.safe_write(out, "hm.json", json.dumps({"x": 1}))                  # plan json was a symlink: replaced, not written through
    assert not (out / "hm.json").is_symlink()
    assert _snap(sh) == before                                           # the other plan's views are untouched
    assert PV.verify(out) == []                                          # sha list refreshed on the view write
    lst = (out / PV.SHA_LIST).read_text()
    assert "cores/a_pins.json" in lst and "cores/b_pins_fMX.json" in lst


def test_refuses_write_through_symlinked_view_dir(tmp_path):
    sh, pd = _shared(tmp_path)
    before = _snap(sh)
    with pytest.raises(PV.PlanViewError, match="symlink"):
        PV.safe_write(pd, "cores/a_pins.json", "{}\n")
    with pytest.raises(PV.PlanViewError):
        PV.safe_write(pd, "../shared/cores/a_pins.json", "{}\n")
    assert _snap(sh) == before


def test_verify_flags_symlink_hardlink_and_drift(tmp_path):
    sh, pd = _shared(tmp_path)
    out = tmp_path / "out"
    PV.snapshot(pd, out)
    (out / "cores/a_pins.json").write_text('{"pins": [7]}\n')           # edit outside safe_write -> drift
    assert any("sha" in b for b in PV.verify(out))
    PV.write_sha_list(out)
    (out / "cores/b_pins_fMX.json").unlink()
    os.symlink(sh / "cores/b_pins_fMX.json", out / "cores/b_pins_fMX.json")
    assert any("symlink" in b for b in PV.verify(out))
    (out / "cores/b_pins_fMX.json").unlink()
    os.link(sh / "cores/b_pins_fMX.json", out / "cores/b_pins_fMX.json")
    assert any("hard link" in b for b in PV.verify(out))


def test_snapshot_breaks_hard_links(tmp_path):
    sh, pd = _shared(tmp_path)
    pd2 = tmp_path / "plan2"
    shutil.copytree(sh, pd2, copy_function=os.link)                    # hbm-style hard-link copy
    out = tmp_path / "out"
    PV.snapshot(pd2, out)
    assert (out / "cores/a_pins.json").stat().st_nlink == 1
    PV.safe_write(out, "cores/a_pins.json", "{}\n")
    assert (sh / "cores/a_pins.json").read_text() == '{"pins": [1]}\n'


def test_kv_core_slice_uses_plan_views():
    src = (HERE / "kv_core_slice.py").read_text()
    assert "PV.snapshot(pd, pdo" in src
    assert "copytree(pd, pdo" not in src
    assert ".write_text(" not in src.split("pdo = out", 1)[1].split("meta = dict", 1)[0]
