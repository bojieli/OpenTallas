"""A native multiPORT pin is checked against actual emitted metal, not trusted metadata."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import kit_contract as K

RECTS=[["M3",276.444,395.242,276.462,395.28],["M3",276.444,394.445,276.462,395.261]]

def fixture(tmp_path):
    row=dict(bus="cfg_v",bit=None,layer="M3",x=276.453,y=394.853,face="N",native_rects=RECTS)
    (tmp_path/"pins.json").write_text(json.dumps([row]))
    lines=["set ot_mp_bt [[ord::get_db_block] findBTerm {cfg_v}]"]
    for layer,*box in RECTS:
        v=" ".join(f"[expr {{int(round({x:.6f}*$ot_mp_u))}}]" for x in box)
        lines.append(f"odb::dbBox_create $ot_mp_bp [[ord::get_db_tech] findLayer {layer}] {v}")
    (tmp_path/"io.tcl").write_text("\n".join(lines)+"\n")
    declared=dict(pins=[dict(name="cfg_v",layer="M3",x=row["x"],y=row["y"])])
    (tmp_path/"freeze.json").write_text(json.dumps(dict(outline_um=[311.04,395.28],pins_canon_sha256=K._canon(declared,[311.04,395.28]))))
    return row

def test_actual_multiport_logical_center_passes(tmp_path):
    fixture(tmp_path)
    errors,_=K.pins_canonical(tmp_path)
    assert errors==[]

def test_shifted_actual_box_refuses_unchanged_metadata(tmp_path):
    fixture(tmp_path)
    p=tmp_path/"io.tcl";p.write_text(p.read_text().replace("394.445000","394.455000"))
    errors,_=K.pins_canonical(tmp_path)
    assert any("kit placed pins" in e for e in errors)

def test_missing_actual_box_refuses_unchanged_metadata(tmp_path):
    fixture(tmp_path)
    p=tmp_path/"io.tcl";p.write_text("\n".join(p.read_text().splitlines()[:-1])+"\n")
    assert K.pins_canonical(tmp_path)[0]

def test_forged_logical_point_refuses_actual_metal(tmp_path):
    row=fixture(tmp_path);row["y"]+=.001
    (tmp_path/"pins.json").write_text(json.dumps([row]))
    assert K.pins_canonical(tmp_path)[0]
