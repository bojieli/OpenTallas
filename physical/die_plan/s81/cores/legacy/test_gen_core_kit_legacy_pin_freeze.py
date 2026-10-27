"""Declared pin provenance must not turn an undeclared placement into a plan."""
import hashlib
import json
import sys
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
