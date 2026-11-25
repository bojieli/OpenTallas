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



def test_lane_own_rule_refuses_other_lane_dir_without_symlink(monkeypatch):
    other = "/srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r6/launch27f/physical/die_plan/x/plan.json"
    own = "/srv/opentallas-scratch2/claude/FLOW-OPS-R2/tmp/x.json"
    monkeypatch.delenv("OT_TREE_WRITE_ANY_LANE", raising=False)
    w = TWG.lane_refusal(other, lane="FLOW-OPS-R2")
    assert "belongs to lane opus-fix-kv-hgi-r6" in w and "writer lane FLOW-OPS-R2" in w
    assert TWG.lane_refusal(other, lane="OPUS-FIX-KV-HGI-R6") == ""                # own lane, case-insensitive
    assert TWG.lane_refusal(own, lane="FLOW-OPS-R2") == ""
    assert TWG.lane_refusal("/srv/opentallas-scratch2/claude/kw45/snap/x.json", lane="FLOW-OPS-R2") == ""   # shared container
    assert TWG.lane_refusal("/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/x", lane="FLOW-OPS-R2") == ""
    assert TWG.lane_refusal(other, lane="") == ""                                   # no lane named: rule 3 off
    monkeypatch.setenv("OT_TREE_WRITE_ANY_LANE", "1")
    assert TWG.lane_refusal(other, lane="FLOW-OPS-R2") == ""


def test_fork_json_names_the_owner(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_TREE_WRITE_ANY_LANE", raising=False)
    root = tmp_path / "trees" / "t1"
    (root / "physical").mkdir(parents=True)
    (root / ".fork.json").write_text(json.dumps({"lane": "KV-WAITBIND-R1"}))
    assert "belongs to lane KV-WAITBIND-R1" in TWG.refusal(root / "physical" / "p.json", lane="FLOW-OPS-R2")
    assert TWG.refusal(root / "physical" / "p.json", lane="kv_waitbind_r1") == ""


def _fake_derive(monkeypatch, seen):
    class R:
        returncode, stdout, stderr = 0, "LAND_R8 DERIVED\n", ""

    def run(cmd, **k):
        seen.append(cmd)
        return R()
    monkeypatch.setattr(RR.subprocess, "run", run)


def test_r8_refresh_symlinked_launch_view_inside_root_allowed(tmp_path, monkeypatch, capsys):
    """QC-R8-SYMLINK 11-24: a table reached through a symlinked launch view whose target is inside the real tree --root is written"""
    monkeypatch.delenv("OT_LANE", raising=False)
    S, P = trees(tmp_path)
    V = tmp_path / "lane/view"; os.symlink(S, V)                        # whole launch view is a symlink to the real tree
    ab = S / "ab.json"; ab.write_text(json.dumps({"land_r8_extra": []}))
    for table in (P / REL, V / REL):
        assert TWG.root_for(table, str(S)) == str(S)
        assert TWG.refusal(table, TWG.root_for(table, str(S))) == ""
        seen = []; _fake_derive(monkeypatch, seen)
        assert RR.main(["plan.json", "bg.json", str(table), "--asbuilt", str(ab), "--root", str(S)]) == 0, capsys.readouterr().out
        cmd = seen[0]
        assert cmd[cmd.index("--root") + 1] == str(S)                    # the derive's --out guard gets the same root
    assert TWG.root_for(V / REL, str(V)) == str(V)                       # root given as the view itself: also inside


def test_r8_refresh_symlink_escaping_root_refused(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OT_LANE", raising=False)
    S, P = trees(tmp_path)
    own = tmp_path / "lane/own"; (own / "r8").mkdir(parents=True); (own / ".fork.json").write_text("{}")
    os.symlink(S / "physical", own / "r8/esc")                           # a link inside --root that leaves it
    t = own / "r8/esc/die_plan/qwen_compute/qc_start_1106/runtime/zz_r8.json"
    before = t.read_bytes()
    assert TWG.root_for(t, str(own)) == str(own)                         # lexically under --root ...
    assert "through symlink" in TWG.refusal(t, TWG.root_for(t, str(own)))   # ... but its real path is outside: refused
    ab = own / "ab.json"; ab.write_text(json.dumps({"land_r8_extra": []}))
    seen = []; _fake_derive(monkeypatch, seen)
    assert RR.main(["plan.json", "bg.json", str(t), "--asbuilt", str(ab), "--root", str(own)]) == 3
    assert "R8_REFRESH REFUSED" in capsys.readouterr().out and not seen and t.read_bytes() == before
    assert RR.main(["plan.json", "bg.json", str(P / REL), "--asbuilt", str(ab), "--root", str(own)]) == 3   # unrelated root: marker root P


def test_r8_refresh_plain_path_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_LANE", raising=False)
    own = tmp_path / "lane/own"; (own / "r8").mkdir(parents=True); (own / ".fork.json").write_text("{}")
    t = own / "r8/t.json"; t.write_text(json.dumps({"members": []}))
    ab = own / "ab.json"; ab.write_text(json.dumps({"land_r8_extra": []}))
    assert TWG.root_for(t, str(own)) == str(own) and TWG.root_for(t, None) is None
    assert TWG.root_for(t, str(tmp_path / "elsewhere")) is None
    for extra in ([], ["--root", str(own)]):
        seen = []; _fake_derive(monkeypatch, seen)
        assert RR.main(["plan.json", "bg.json", str(t), "--asbuilt", str(ab)] + extra) == 0
        assert ("--root" in seen[0]) == bool(extra)


def test_r8_refresh_relative_table_through_symlinked_launch_view(tmp_path, monkeypatch, capsys):
    """COORD 11-24 (QC-STA-PROBE): cwd = the launch view, table and --root given relative; the table resolves through the view's
    symlinked physical/die_plan into the real tree named by --root -> written; the same table with --root . (the view) stays refused"""
    monkeypatch.delenv("OT_LANE", raising=False)
    S, P = trees(tmp_path)
    ab = P / "ab.json"; ab.write_text(json.dumps({"land_r8_extra": []}))
    monkeypatch.chdir(P)
    rel_root = os.path.relpath(S, P)
    seen = []; _fake_derive(monkeypatch, seen)
    assert RR.main(["plan.json", "bg.json", REL, "--asbuilt", "ab.json", "--root", rel_root]) == 0, capsys.readouterr().out
    assert os.path.realpath(seen[0][seen[0].index("--root") + 1]) == os.path.realpath(S)
    seen.clear()
    assert RR.main(["plan.json", "bg.json", REL, "--asbuilt", "ab.json", "--root", "."]) == 3   # the shared tree is not the view's
    assert not seen
