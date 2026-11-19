"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 D): the r576 cell limit is enforced at kit preflight, enqueue and native_cell_cap.tcl unless a ruling id waives it."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import cap_estimate as CE
import cell_cap

TCL = HERE.parent / "die_plan" / "native_cell_cap.tcl"


def kit(tmp_path, cells, waiver=None):
    k = tmp_path / "kit"
    k.mkdir(exist_ok=True)
    (k / "budget.json").write_text(json.dumps({"outline_um": [800, 800], "pins": 100}))
    (k / "cap_budget.json").write_text(json.dumps({"cells": cells, "macros": 0}))
    if waiver is not None:
        (k / "CELL_WAIVER").write_text(waiver + "\n")
    return k


def test_one_number_everywhere():
    assert CE.SPLIT_CELLS == cell_cap.SPLIT_CELLS == 400_000
    assert f"set ot_cap_split {cell_cap.SPLIT_CELLS}" in TCL.read_text()


def test_kit_preflight_refuses_over_the_limit_unless_a_ruling_waives(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_CELL_WAIVER", raising=False)
    err, est = CE.check_kit(kit(tmp_path, 5_690_000))
    assert err == [] and est["split_needed"]                                            # WAVE-PILOT-FIX 11-19: the refusal is deleted; the estimate stays
    assert CE.check_kit(kit(tmp_path, 399_000))[0] == []
    assert CE.check_kit(kit(tmp_path, 5_690_000, "r590"))[1]["cell_waiver"] == "r590"    # ruling id in KIT/CELL_WAIVER is still recorded
    assert "cell_waiver" not in CE.check_kit(kit(tmp_path, 5_690_000, "because"))[1]      # not a ruling id: no waiver
    monkeypatch.setenv("OT_CELL_WAIVER", "r591")
    assert CE.check_kit(kit(tmp_path, 5_690_000))[1]["cell_waiver"] == "r591"


def run_tcl(n_std, env=None, waiver_file=None, tmp=None):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("no tclsh")
    work = Path(tmp)
    harness = f"""
namespace eval ord {{ proc get_db_block {{}} {{ return blk }} }}
proc blk {{m args}} {{ switch $m {{ getInsts {{ return [lmap i [lrange [lseq 0 {n_std}] 0 end-1] {{ return -level 0 inst$i }}] }} getBTerms {{ return {{}} }} getDieArea {{ return die }} }} }}
for {{set i 0}} {{$i < {n_std}}} {{incr i}} {{ proc inst$i {{m}} {{ return mstr }} }}
proc mstr {{m}} {{ return 0 }}
"""
    harness = f"""
namespace eval ord {{ proc get_db_block {{}} {{ return blk }} }}
proc blk {{m args}} {{ if {{$m eq "getInsts"}} {{ set l {{}}; for {{set i 0}} {{$i < {n_std}}} {{incr i}} {{ lappend l i }}; return $l }}; return {{}} }}
proc i {{m}} {{ return mstr }}
proc mstr {{m}} {{ return 0 }}
set path [file join {work} native_cell_cap.tcl]
file mkdir /work
"""
    # the script writes /work/native_cell_count.json: run it against a rewritten copy that writes under the temp dir
    src = TCL.read_text().replace("/work/", f"{work}/")
    (work / "native_cell_cap.tcl").write_text(src)
    (work / "h.tcl").write_text(harness.replace("file mkdir /work\n", "") + f"source {work}/native_cell_cap.tcl\nputs DONE_OK\n")
    if waiver_file:
        (work / "CELL_WAIVER").write_text(waiver_file + "\n")
    e = dict(env or {})
    e["PATH"] = "/usr/bin:/bin"
    return subprocess.run([tclsh, str(work / "h.tcl")], capture_output=True, text=True, env=e)


def test_native_cell_cap_tcl_stops_over_the_limit_and_honours_a_waiver(tmp_path):
    ok = run_tcl(399_999, tmp=tmp_path)
    assert "DONE_OK" in ok.stdout and ok.returncode == 0, ok.stderr
    bad = run_tcl(400_001, tmp=tmp_path)
    assert bad.returncode == 0 and "DONE_OK" in bad.stdout and "cell cap removed" in bad.stdout   # KV-HUBPV-1118: report only
    w = run_tcl(400_001, env={"OT_CELL_WAIVER": "r590"}, tmp=tmp_path)
    assert "DONE_OK" in w.stdout
    assert run_tcl(400_001, env={"OT_CELL_WAIVER": "please"}, tmp=tmp_path).returncode == 0


def test_enqueue_refuses_over_the_limit_unless_waived(monkeypatch):
    import autopilot as AP
    monkeypatch.setattr(AP, "read_coord", lambda rel: "qwen_kvsys\tkv3_x\tr590\ns81\tother\tnotaruling\n")
    assert AP.cell_waiver_for("qwen_kvsys", "kv3_x") == "r590"
    assert AP.cell_waiver_for("s81", "other") == "" and AP.cell_waiver_for("s81", "none") == ""
    assert AP.SPLIT_CELLS == cell_cap.SPLIT_CELLS
