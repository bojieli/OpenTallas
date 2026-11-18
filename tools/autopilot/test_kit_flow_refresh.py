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
