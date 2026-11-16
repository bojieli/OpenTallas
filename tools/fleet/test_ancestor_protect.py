"""KIT-OPS-6 11-14 (COORD r32 (2), qct13/views deleted): a directory that CONTAINS a protected path must never be deleted.
ot-autoclean: PathSet.hit reports 'holds <path>' for an ancestor; wt-reaper: protected() refuses a worktree that contains a listed
source path.  (ot-reaper / ot_orphan_reaper kills processes, it deletes no directory.)"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, fname):
    spec = importlib.util.spec_from_file_location(name, HERE / fname)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def test_autoclean_ancestor_holds_the_protected_child():
    A = load("ot_autoclean_mod", "ot-autoclean.py")
    ps = A.PathSet([("/srv/opentallas-scratch2/claude/qct13/views/qfd_dv_s8x_btab", "kit_wave prov view")])
    for anc in ("/srv/opentallas-scratch2/claude/qct13/views", "/srv/opentallas-scratch2/claude/qct13"):
        hit = ps.hit(anc)
        assert hit and hit.startswith("holds /srv/opentallas-scratch2/claude/qct13/views/qfd_dv_s8x_btab"), (anc, hit)
    assert ps.hit("/srv/opentallas-scratch2/claude/qct12") is None


def test_wt_reaper_refuses_a_tree_that_contains_a_listed_source(tmp_path):
    W = load("wt_reaper_mod", "wt-reaper.py")
    wt = tmp_path / "qct13"
    (wt / "views" / "m").mkdir(parents=True)
    why = W.protected(str(wt), str(tmp_path / "admin"), str(tmp_path / "common"),
                      listed=[(str(wt / "views" / "m"), "kit_wave.json prov_view_sources")])
    assert why and "listed source" in why
    assert W.protected(str(wt), str(tmp_path / "admin"), str(tmp_path / "common"), listed=[]) is None


def test_autoclean_reads_protect_d(tmp_path):
    """KIT-OPS-6 11-15: ot-autoclean's protection also comes from protect.d/*.txt (one live source of truth with wt-reaper)"""
    A = load("ot_autoclean_mod2", "ot-autoclean.py")
    (tmp_path / "hub-kit-wave-live.txt").write_text("/srv/opentallas-scratch2/claude/qct13/views/m\n# c\n\nnot a path\n")
    (tmp_path / "other.json").write_text("/srv/x\n")
    rows = A.read_protect_d(str(tmp_path))
    assert rows == [("/srv/opentallas-scratch2/claude/qct13/views/m", "protect.d/hub-kit-wave-live.txt")]
    assert A.read_protect_d(str(tmp_path / "none")) == []
    ps = A.PathSet(rows)
    assert ps.hit("/srv/opentallas-scratch2/claude/qct13") .startswith("holds ")
    src = (HERE / "ot-autoclean.py").read_text()
    assert "rows = list(rows) + read_protect_d()" in src
