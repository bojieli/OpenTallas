"""DIE-HBM KITGEN (COORD 10-27 20:21 ruling c): gen_core_kit_hbm.py records freeze.json pins_canon_sha256 with the
shared kit_contract canonicalisation, so kit_preflight pins_canonical finds the recorded hash equal to the plan pin
table's canonical hash (no forked formula)."""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import kit_contract as KC  # noqa: E402
import die_sta_related as DSR  # noqa: E402

spec = importlib.util.spec_from_file_location("coregen_pins_canon", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)

W, H = 20.0, 10.0
PINS = [dict(name="clk", layer="M5", x=4.824, y=0.019, dir="input"),
        dict(name="a[0]", layer="M4", x=0.019, y=2.424, dir="input"),
        dict(name="y[0]", layer="M4", x=19.981, y=3.384, dir="output")]


def _kit(kd, pins, extra_fz=None):
    """minimal kit as the generator writes it: io.tcl from the plan pins, freeze.json pin provenance."""
    io, _ = coregen.io_tcl(pins, W, H, "t")
    (kd / "io.tcl").write_text(io)
    (kd / "plan").mkdir()
    body = json.dumps(pins)
    (kd / "plan" / "cores_t.json").write_text(body)
    import hashlib
    fz = dict(outline_um=[W, H], pins_file="cores_t.json", pins_sha256=hashlib.sha256(body.encode()).hexdigest(),
              pins_canon_sha256=coregen.plan_pins_canon_sha256(pins, [W, H]))
    fz.update(extra_fz or {})
    (kd / "freeze.json").write_text(json.dumps(fz))
    return fz


def test_recorded_equals_shared_canon_and_die_sta(tmp_path):
    rec = coregen.plan_pins_canon_sha256(PINS, [W, H])
    assert rec == KC._canon(PINS, [W, H])
    # die STA pins_relation compares the recorded hash with canon_pins of the plan table: same value
    assert rec == DSR.canon_sha256(DSR.canon_pins(dict(pins=PINS), [W, H]))
    assert coregen.plan_pins_canon_sha256(PINS[:2], [W, H]) != rec


def test_preflight_finds_recorded_hash(tmp_path):
    fz = _kit(tmp_path, PINS)
    errors, info = KC.pins_canonical(tmp_path, tmp_path / "plan")
    assert not any("no pins_canon_sha256" in e for e in errors), errors
    assert not any("!= recorded" in e for e in errors), errors
    assert info["recorded"] == fz["pins_canon_sha256"] == info["plan_canon"]


def test_preflight_flags_missing_hash(tmp_path):
    _kit(tmp_path, PINS, dict(pins_canon_sha256=None))
    errors, _ = KC.pins_canonical(tmp_path, tmp_path / "plan")
    assert any("no pins_canon_sha256" in e for e in errors), errors
