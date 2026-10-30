"""Declared pin provenance must not turn an undeclared placement into a plan."""
import hashlib
import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_legacy as G
sys.path.insert(0, str(G.TOOL))
import kit_contract as K


def test_declared_and_placed_hashes_remain_distinct(tmp_path):
    declared = dict(pins=[dict(name="data", layer="M3", x=0.042, y=1.0)])
    pf = tmp_path / "plan_pins.json"
    pf.write_text(json.dumps(declared))
    (tmp_path / "io.tcl").write_text("place_pin -pin_name {data} -layer M3 -location {0.042 2.0}\n")
    hashes = G._pin_freeze_hashes(tmp_path, pf, [10, 10])
    assert hashes["pins_canon_sha256"] == K._canon(declared, [10, 10])
    assert hashes["pins_placed_canon_sha256"] != hashes["pins_canon_sha256"]
    freeze = dict(outline_um=[10, 10], pins_file=pf.name,
                  pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(), **hashes)
    (tmp_path / "freeze.json").write_text(json.dumps(freeze))
    errors, _ = K.pins_canonical(tmp_path)
    assert any("kit placed pins" in e for e in errors)
    assert not any("!= recorded" in e for e in errors)
    (tmp_path / "io.tcl").write_text("place_pin -pin_name {data} -layer M3 -location {0.042 1.0}\n")
    errors, _ = K.pins_canonical(tmp_path)
    assert errors == []


def test_inline_lef_contract_uses_declared_pins(tmp_path):
    # Hard children declare pin rows inline; pins_file is their source LEF,
    # which must never be parsed as JSON or replaced by the kit placement.
    lef = tmp_path / "child.lef"
    lef.write_text("MACRO child\nEND child\n")
    declared = [dict(name="data", layer="M3", x=0.042, y=1.0)]
    (tmp_path / "io.tcl").write_text("place_pin -pin_name {data} -layer M3 -location {0.042 2.0}\n")
    hashes = G._pin_freeze_hashes(tmp_path, lef, [10,10], declared_pins=declared)
    assert hashes["pins_canon_sha256"] == K._canon(declared, [10,10])
    assert hashes["pins_placed_canon_sha256"] != hashes["pins_canon_sha256"]


def test_lef_without_declared_inline_rows_does_not_fallback(tmp_path):
    lef = tmp_path / "child.lef"
    lef.write_text("MACRO child\nEND child\n")
    (tmp_path / "io.tcl").write_text("place_pin -pin_name {data} -layer M3 -location {0.042 2.0}\n")
    with pytest.raises(json.JSONDecodeError):
        G._pin_freeze_hashes(tmp_path, lef, [10,10])


@pytest.mark.parametrize('kind',['json','lef'])
def test_external_declared_contract_is_staged_self_contained(tmp_path,kind):
    src=tmp_path/'source';src.mkdir();kd=tmp_path/'kit';kd.mkdir()
    rows=[dict(name='data',layer='M3',x=.042,y=1.042)]
    text=json.dumps(dict(pins=rows)) if kind=='json' else 'MACRO child\n SIZE 10 BY 10 ;\n PIN data\n PORT\n LAYER M3 ;\n RECT 0 1 .084 1.084 ;\n END\n END data\nEND child\n'
    pf=src/('child_pins.'+kind);pf.write_text(text)
    (kd/'io.tcl').write_text('place_pin -pin_name {data} -layer M3 -location {0.042 1.042}\n')
    (kd/'master_slice.json').write_text('{}')
    hashes=G._pin_freeze_hashes(kd,pf,[10,10],declared_pins=rows if kind=='lef' else None)
    assert (kd/pf.name).read_bytes()==pf.read_bytes()
    freeze=dict(module='child',outline_um=[10,10],pins_file='external/'+pf.name,
                pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),**hashes)
    (kd/'freeze.json').write_text(json.dumps(freeze));pf.unlink()
    errors,info=K.pins_canonical(kd)
    assert not errors and info['plan_file']==str(kd/pf.name)


def test_declared_contract_basename_collision_is_not_overwritten(tmp_path):
    src=tmp_path/'source';src.mkdir();kd=tmp_path/'kit';kd.mkdir()
    pf=src/'child_pins.json';pf.write_text(json.dumps(dict(pins=[])))
    old=kd/pf.name;old.write_text('owned unrelated kit material')
    with pytest.raises(ValueError,match='basename collision'):G._pin_freeze_hashes(kd,pf,[10,10])
    assert old.read_text()=='owned unrelated kit material'


@pytest.mark.parametrize('mutation',['path','hash'])
def test_staged_contract_manifest_cannot_redirect_or_change_hash(tmp_path,mutation):
    pf=tmp_path/'child_pins.json';pf.write_text(json.dumps(dict(pins=[])))
    (tmp_path/'io.tcl').write_text('')
    hashes=G._pin_freeze_hashes(tmp_path,pf,[10,10]);hashes['pins_staged_file' if mutation=='path' else 'pins_staged_sha256']='../elsewhere.json' if mutation=='path' else 'bad'
    (tmp_path/'freeze.json').write_text(json.dumps(dict(outline_um=[10,10],pins_file=pf.name,pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),**hashes)))
    with pytest.raises(ValueError,match='manifest'):K.pins_canonical(tmp_path)
