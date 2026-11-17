"""A wider signal grant must not move or weaken physical clock obligations."""
import json
import re
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import gen_phys as GP
import kit_contract as KC
from test_pad_clock import plan, guard, NET

def kit(tmp_path, monkeypatch):
    p=plan()
    p.types["mid"]["face_layers"]={"E":["M8","M6","M4"]}
    monkeypatch.setenv("OT_CONS_KIT","1")
    monkeypatch.setenv("OT_CONS_MAX_LAYER","M8")
    GP.write_type_kit(p,"mid",str(tmp_path),[])
    return tmp_path/"mid"

def test_generated_m7_clock_m8_signals_keep_physical_layer(tmp_path,monkeypatch):
    kd=kit(tmp_path,monkeypatch)
    b=json.loads((kd/"budget.json").read_text())
    assert b["signal_max"]=="M8"
    assert b["clock"]["pin_layer"]=="M7"
    assert KC.clock_pin_geometry(kd)[0]==[]

@pytest.mark.parametrize("mutant",["pad-layer","core-layer","xy","role"])
def test_expanded_route_limit_keeps_actual_clock_checks(tmp_path,monkeypatch,mutant):
    kd=kit(tmp_path,monkeypatch)
    f=kd/"io.tcl";s=f.read_text()
    if mutant in ("pad-layer","core-layer"):
        name="{pma_rck[0]}" if mutant=="pad-layer" else "{clk}"
        lines=s.splitlines()
        for i,line in enumerate(lines):
            if re.search(r"place_pin -pin_name \{?"+re.escape(name.strip("{}"))+r"\}? ", line):
                lines[i]=line.replace("-layer M7","-layer M6")
                break
        else:raise AssertionError("clock placement not found")
        f.write_text("\n".join(lines)+"\n")
    elif mutant=="xy":
        f.write_text(s.replace("{10.0160 10.0000}","{10.0480 10.0000}"))
    else:
        j=json.loads((kd/"pad_clock.json").read_text())
        j["pins"][0]["dir"]="data"
        (kd/"pad_clock.json").write_text(json.dumps(j))
    assert KC.clock_pin_geometry(kd)[0]

def test_real_pad_clock_roles_still_require_clock_loads():
    assert guard()["verdict"]=="PASS"
    assert guard(NET.replace(".D(a)",".D(pma_rck[0])"))["fail_counts"].get("pad_clock")
