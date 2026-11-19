"""kit_flow_refresh: a kit's verbatim copy of an older main flow script is replaced by the rt version; generated files never."""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_flow_refresh as K


def setup(tmp):
    rt = Path(tmp) / "rt" / "aaaaaaaaaaaa"
    (rt / "tools/die_plan").mkdir(parents=True)
    (rt / "physical/common_flow").mkdir(parents=True)
    old, new = b"puts old\n", b"puts fixed\n"
    (rt / "tools/die_plan/vclk_measured_hold.tcl").write_bytes(new)
    (rt / "physical/common_flow/grt183_make.sh").write_bytes(b"echo same\n")
    idx = {"blobs": {"tools/die_plan/vclk_measured_hold.tcl": sorted({K.blob_id(old), K.blob_id(new)}),
                     "physical/common_flow/grt183_make.sh": [K.blob_id(b"echo same\n")],
                     "tools/die_plan/gen_lint.tcl": [K.blob_id(b"stock\n")]}}
    (rt / "tools/.flow_blobs.json").write_text(json.dumps(idx))
    Path(str(rt) + ".manifest.json").write_text(json.dumps({"sha": "a" * 40}))
    kit = Path(tmp) / "kit"
    kit.mkdir()
    (kit / "vclk_measured_hold.tcl").write_bytes(old)
    (kit / "grt183_make.sh").write_bytes(b"echo same\n")
    (kit / "gen_lint.tcl").write_bytes(b"generated for this kit\n")
    (kit / "run_kit.sh").write_bytes(b"#!/bin/bash\n")
    return rt, kit


def test_replaces_only_verbatim_old_copies():
    rt, kit = setup(tempfile.mkdtemp())
    assert K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)]) == 0
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts fixed\n"
    assert (kit / "gen_lint.tcl").read_bytes() == b"generated for this kit\n"
    rec = json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])
    assert rec["sha"] == "a" * 40 and rec["stage"] == "route" and [r["file"] for r in rec["replaced"]] == ["vclk_measured_hold.tcl"]
    K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])          # idempotent: nothing more to replace
    assert json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])["replaced"] == []


def test_no_index_and_opt_out_touch_nothing(monkeypatch):
    rt, kit = setup(tempfile.mkdtemp())
    (rt / "tools/.flow_blobs.json").unlink()
    K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts old\n"
    (rt / "tools/.flow_blobs.json").write_text(json.dumps({"blobs": {"tools/die_plan/vclk_measured_hold.tcl": [K.blob_id(b"puts old\n")]}}))
    monkeypatch.setenv("OT_FLOW_REFRESH", "0")
    K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts old\n"


def test_blob_id_matches_git():
    import subprocess
    d = tempfile.mkdtemp()
    p = Path(d) / "f"
    p.write_bytes(b"hello\n")
    assert K.blob_id(b"hello\n") == subprocess.run(["git", "hash-object", str(p)], capture_output=True, text=True).stdout.strip()


def test_bundle_layout_from_signoff_chain(capsys):
    """FABLE-FLOW-1000 A: inside the sealed job the chain runs from the admission bundle: refresher + index + scripts are there"""
    import shutil, subprocess
    tmp = Path(tempfile.mkdtemp())
    rt, kit = setup(tmp)
    b = tmp / "bundle"
    (b / "die_plan/__flow__/common_flow").mkdir(parents=True)
    shutil.copy(rt / "tools/die_plan/vclk_measured_hold.tcl", b / "die_plan/vclk_measured_hold.tcl")
    shutil.copy(rt / "tools/.flow_blobs.json", b / "die_plan/__flow__/flow_blobs.json")
    shutil.copy(Path(K.__file__), b / "die_plan/__flow__/kit_flow_refresh.py")
    import signoff_chain as SC
    SC.flow_refresh(kit, "route", script="/nonexistent", bundle=b)
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts fixed\n"
    assert json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])["stage"] == "route"


def test_skip_is_loud(capsys):
    import signoff_chain as SC
    tmp = Path(tempfile.mkdtemp())
    SC.flow_refresh(tmp, "route", script="/nonexistent", bundle=tmp)
    assert "KIT_FLOW_REFRESH SKIPPED" in capsys.readouterr().out


def die_setup(tmp):
    """TOOLS-DECOUPLE-2: a die tree with an OLD gate copy, rt with the fixed one, a kit that took the die tree's copy"""
    rt = Path(tmp) / "rt" / "bbbbbbbbbbbb"
    (rt / "tools/autopilot").mkdir(parents=True)
    (rt / "tools/die_plan").mkdir(parents=True)
    (rt / "tools/autopilot/gp_noconverge.py").write_bytes(b"fixed gate\n")
    (rt / "tools/die_plan/gp_noconverge_gate.tcl").write_bytes(b"same tcl\n")
    (rt / "tools/die_plan/only_rt.tcl").write_bytes(b"rt only\n")
    Path(str(rt) + ".manifest.json").write_text(json.dumps({"sha": "b" * 40}))
    die = Path(tmp) / "src_die"
    (die / "tools/autopilot").mkdir(parents=True)
    (die / "tools/die_plan").mkdir(parents=True)
    (die / "tools/autopilot/gp_noconverge.py").write_bytes(b"old gate\n")
    (die / "tools/die_plan/gp_noconverge_gate.tcl").write_bytes(b"same tcl\n")
    (die / "tools/die_plan/die_only.tcl").write_bytes(b"only the die has this\n")
    kit = Path(tmp) / "kit"
    kit.mkdir()
    (kit / "gp_noconverge.py").write_bytes(b"old gate\n")
    (kit / "gp_noconverge_gate.tcl").write_bytes(b"same tcl\n")
    (kit / "die_only.tcl").write_bytes(b"only the die has this\n")
    (kit / "config.mk").write_bytes(b"generated\n")
    (kit / "gen_made.tcl").write_bytes(b"generated, in neither tree\n")
    return rt, die, kit


def test_die_tree_copy_replaced_by_rt_and_tools_rev_written():
    rt, die, kit = die_setup(tempfile.mkdtemp())
    assert K.main(["--kit", str(kit), "--stage", "gen", "--rt", str(rt), "--die-src", str(die)]) == 0
    assert (kit / "gp_noconverge.py").read_bytes() == (rt / "tools/autopilot/gp_noconverge.py").read_bytes()
    assert (kit / "gen_made.tcl").read_bytes() == b"generated, in neither tree\n"
    assert (kit / "die_only.tcl").read_bytes() == b"only the die has this\n"
    rev = json.loads((kit / "tools_rev.json").read_text())
    assert rev["tools_sha"] == "b" * 40 and rev["stage"] == "gen"
    assert rev["die_tree_copies_replaced"] == ["gp_noconverge.py"]
    assert rev["rt_files"] == {"gp_noconverge.py": "tools/autopilot/gp_noconverge.py", "gp_noconverge_gate.tcl": "tools/die_plan/gp_noconverge_gate.tcl"}
    assert rev["die_tree_only"] == ["die_only.tcl"]
    K.main(["--kit", str(kit), "--stage", "place", "--rt", str(rt), "--die-src", str(die)])       # idempotent
    assert json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])["replaced"] == []


def test_composed_launch_tree_fill_counts_as_die_only():
    """--rt may be the composed launch tree: a file listed in .rt_launch_filled is the die tree's, not rt's"""
    tmp = tempfile.mkdtemp()
    rt, die, kit = die_setup(tmp)
    (rt / "tools/die_plan/die_only.tcl").write_bytes(b"only the die has this\n")      # hardlinked in by the fill step
    (rt / ".rt_launch_filled").write_text("tools/die_plan/die_only.tcl\n")
    K.main(["--kit", str(kit), "--stage", "gen", "--rt", str(rt), "--die-src", str(die)])
    rev = json.loads((kit / "tools_rev.json").read_text())
    assert rev["die_tree_only"] == ["die_only.tcl"] and "die_only.tcl" not in rev["rt_files"]


def test_without_die_src_nothing_new_is_written():
    rt, die, kit = die_setup(tempfile.mkdtemp())
    K.main(["--kit", str(kit), "--stage", "gen", "--rt", str(rt)])
    assert not (kit / "tools_rev.json").exists() and (kit / "gp_noconverge.py").read_bytes() == b"old gate\n"
