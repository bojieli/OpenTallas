import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ext_source_check as E  # noqa: E402


def test_internal_and_bind_paths_pass_external_fail(tmp_path):
    tree = tmp_path / "srv" / "tree"
    bind = tmp_path / "srv" / "bind"
    tree.mkdir(parents=True)
    bind.mkdir(parents=True)
    ok = bind / "bind.f"
    ok.write_text(f"/srv/x\n")
    assert E.main(["--allow", "/srv/x", str(bind)]) == 0
    ok.write_text("/srv/x/rtl/a.sv\n/srv/old/wt/qc-s29-tree2/rtl/b.sv\n")
    (bind / "m.json").write_text(json.dumps({"files": ["/srv/old/wt/qc-s29-tree2/rtl/c.sv"]}))
    cnt, ex, missing = E.scan(["/srv/x"], [str(bind)])
    assert sum(cnt.values()) == 2 and len(missing) == 2
    assert E.main(["--allow", "/srv/x", str(bind)]) == 1
    assert E.main(["--allow", "/srv/x", "--allow", "/srv/old/wt/qc-s29-tree2", str(bind)]) == 0


def test_prefix_is_a_path_boundary(tmp_path):
    (tmp_path / "a.f").write_text("/srv/tree2/rtl/a.sv\n")
    assert E.main(["--allow", "/srv/tree", str(tmp_path)]) == 1


def test_config_refuses_lane_folders_but_not_published_trees():
    ok = "/srv/opentallas-scratch2/claude/kw45/src_s81_pin_eb1e73448bd0"
    assert E.lane_folder(ok + "/physical/x.json") == ""
    assert E.lane_folder("/srv/opentallas-scratch2/claude/kw45/kvbind_pin_eb1e73448bd0/out_h1") == ""
    assert E.lane_folder("/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gG3b/src") == "s81-b3-clk"
    assert E.lane_folder("/srv/opentallas-scratch2/claude/kw45/src_head_rp21z_pgcaplec_c327") == "kw45"      # unpublished tree
    assert E.lane_folder("/srv/opentallas-scratch2/claude/die-qc-103/treeA/p.json", ("/srv/opentallas-scratch2/claude/die-qc-103/",)) == ""
    cfg = {"dies": {"s81": {"enabled": True, "src": "/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gG3b/src", "plan": ok + "/p.json",
                            "kit_rtl": {"bind_out": ok + "/o", "asbuilt": "/srv/opentallas-scratch2/claude/s81-b3-clk/x.json"},
                            "gen_args": ["--clock-landing", "/srv/opentallas-scratch2/claude/s81-b3-clk/run/sc.json"]},
                    "hbm": {"enabled": False, "src": "/srv/opentallas-scratch2/claude/lane/x"}}}
    p = E.check_config(cfg)
    assert [x.split(" = ")[0] for x in p] == ["LANE-FOLDER s81.src", "LANE-FOLDER s81.kit_rtl.asbuilt", "LANE-FOLDER s81.gen_args"]
    cfg["dies"]["s81"].update(src=ok, gen_args=[], kit_rtl={"bind_out": ok})
    assert E.check_config(cfg) == []
