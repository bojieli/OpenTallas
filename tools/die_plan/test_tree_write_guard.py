"""FLOW-FLEET-R1 11-22 (COORD class fix, FABLE-FIX-QC-COLL-R2 incident): plan-tree writers refuse a path that resolves through a symlink outside
the caller's tree root; ot-tree-fork and private-spec refuse (or materialise) a symlinked physical/die_plan."""
import json
import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tree_write_guard as TWG  # noqa: E402
import r8_refresh as RR  # noqa: E402
import land_r8_derive as LD  # noqa: E402

REL = "physical/die_plan/qwen_compute/qc_start_1106/runtime/zz_r8.json"


def trees(tmp_path):
    """shared tree S (marker .src-manifest.json) and a launch-tree-style private copy P whose physical/die_plan links into S"""
    S, P = tmp_path / "kw45/snap/famqc", tmp_path / "lane/launch"
    (S / REL).parent.mkdir(parents=True)
    (S / REL).write_text('{"members": [{"id": "a", "bound": 3, "landed": 3}]}')
    (S / ".src-manifest.json").write_text("{}")
    (P / "physical").mkdir(parents=True)
    (P / ".rt_launch_ok").write_text("{}")
    os.symlink(S / "physical/die_plan", P / "physical/die_plan")
    return S, P


def test_guard_refuses_symlink_out_of_tree_allows_own(tmp_path):
    S, P = trees(tmp_path)
    w = TWG.refusal(P / REL)
    assert "TREE-WRITE REFUSED" in w and "through symlink" in w and str(P / "physical/die_plan") in w
    assert TWG.refusal(S / REL) == ""                                   # the tree's own file, by its real path
    (tmp_path / "lane/own/physical").mkdir(parents=True)
    (tmp_path / "lane/own/.fork.json").write_text("{}")
    assert TWG.refusal(tmp_path / "lane/own/physical/t.json") == ""    # a real private tree
    assert TWG.refusal(P / REL, root=str(S)) == ""                      # explicit root = the shared tree owner
    os.symlink(S / REL, tmp_path / "lane/own/physical/link.json")       # a file symlink leaving the tree
    assert "REFUSED" in TWG.refusal(tmp_path / "lane/own/physical/link.json")


def test_guard_nlink_only_for_inplace(tmp_path):
    (tmp_path / "t/physical").mkdir(parents=True)
    (tmp_path / "t/.fork.json").write_text("{}")
    f = tmp_path / "t/physical/a.json"; f.write_text("1")
    os.link(f, tmp_path / "other.json")
    assert TWG.refusal(f) == ""                                          # tmp + rename: a new inode, the other link keeps its bytes
    assert "nlink 2" in TWG.refusal(f, inplace=True)


def test_r8_refresh_refuses_before_writing(tmp_path, capsys):
    S, P = trees(tmp_path)
    before = (S / REL).read_bytes()
    ab = P / "ab.json"; ab.write_text(json.dumps({"land_r8_extra": []}))
    assert RR.main(["plan.json", "bg.json", str(P / REL), "--asbuilt", str(ab)]) == 3
    assert "R8_REFRESH REFUSED" in capsys.readouterr().out
    assert (S / REL).read_bytes() == before
    ab.write_text(json.dumps({"land_r8_extra": [REL]}))                 # an extra table through the link, relative to --root P
    own = tmp_path / "lane/own"; (own / "r8").mkdir(parents=True); (own / ".fork.json").write_text("{}")
    assert RR.main(["plan.json", "bg.json", str(own / "r8/t.json"), "--asbuilt", str(ab), "--root", str(P)]) == 3


def test_land_r8_derive_refuses_out_through_link(tmp_path, capsys):
    S, P = trees(tmp_path)
    assert LD.main(["derive", "plan.json", "bg.json", "--like", str(S / REL), "--out", str(P / REL)]) == 3
    assert "LAND_R8 REFUSED" in capsys.readouterr().out


def test_ot_tree_fork_refuses_or_materializes_plan_link(tmp_path, monkeypatch):
    TF = SourceFileLoader("ot_tree_fork", str(HERE.parent / "fleet/ot-tree-fork")).load_module()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(TF, "LOG", str(tmp_path / "home/fl.jsonl"))
    monkeypatch.setenv("OT_TREE_FORK_FLOOR_GB", "0")
    monkeypatch.delenv("OT_EVENT_TREE_ROOTS", raising=False)
    shared = tmp_path / "wave/src"                                      # writable, not an event tree
    (shared / REL).parent.mkdir(parents=True); (shared / REL).write_text("{}")
    src = tmp_path / "lane/l1"; (src / "physical").mkdir(parents=True); (src / "rtl.txt").write_text("r")
    os.symlink(shared / "physical/die_plan", src / "physical/die_plan")
    with pytest.raises(TF.Refused, match="plan dir"):
        TF.fork(str(src), str(tmp_path / "lane/f1"), out=lambda *_: None)
    TF.fork(str(src), str(tmp_path / "lane/f2"), materialize=True, out=lambda *_: None)
    d = tmp_path / "lane/f2/physical/die_plan"
    assert d.is_dir() and not d.is_symlink() and (tmp_path / "lane/f2" / REL).is_file()
    os.symlink(shared / "physical/die_plan", tmp_path / "lane/v_die_plan")
    (tmp_path / "lane/v/physical").mkdir(parents=True)
    os.symlink(shared / "physical/die_plan", tmp_path / "lane/v/physical/die_plan")
    assert any(e.startswith("PLAN-LINK physical/die_plan") for e in TF.verify(str(tmp_path / "lane/v")))


def test_private_spec_refuses_symlinked_die_plan(tmp_path):
    sys.path.insert(0, str(HERE.parent / "autopilot"))
    import kit_wave as KW
    S, P = trees(tmp_path)
    assert "physical/die_plan is a symlink" in KW.private_tree_plan_link_refusal(str(P), "qwen_compute")
    assert KW.private_tree_plan_link_refusal(str(S), "qwen_compute") == ""
