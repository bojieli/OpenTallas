import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("pta", Path(__file__).with_name("pin_track_audit.py"))
pta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pta)


def test_t51_native_e_root_pin_is_4nm_off_in_plan_frame():
    # origin x 639.36 (0 mod 64 nm) + plan offset 0.108 + kit root pin x 23.328 -> 662.796: 12 mod 64, track is 16
    pins = [dict(name="clk_t19", layer="M7", x=23.328, y=338.592)]
    r = pta.audit_pins(pins, [639.36, 8.64], [0.108, 0.012], ["M7"])["M7"]
    assert r["offtrack"] == 1 and r["residue_nm"] == {60: 1} and r["shift_nm"] == 4


def test_on_track_pin_ok():
    r = pta.audit_pins([dict(name="a", layer="M7", x=0.016, y=0.0)], [0, 0], [0, 0], ["M7"])["M7"]
    assert r["offtrack"] == 0 and r["shift_nm"] is None


def test_shift_lands_on_track():
    p = dict(name="a", layer="M7", x=0.032, y=0.0)
    r = pta.audit_pins([p], [0, 0], [0, 0], ["M7"])["M7"]
    assert r["offtrack"] == 1 and r["shift_nm"] == -16
    p["x"] = round(p["x"] + r["shift_nm"] / 1000, 4)
    assert pta.audit_pins([p], [0, 0], [0, 0], ["M7"])["M7"]["offtrack"] == 0
