import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pta", HERE / "pin_track_audit.py")
pta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pta)
sys.path.insert(0, str(HERE.parents[1] / "physical/die_plan/s81/cores/legacy"))


def test_lattice_is_the_schema_die_lattice():
    # S81-T51-PINFIX-2: the die / parent tracks, not the ORFS platform make_tracks (M7 was 16, M3-M6 axes swapped)
    assert pta.TRACKS["M7"] == ("x", 32, 64) and pta.TRACKS["M6"] == ("y", 32, 64)
    assert pta.TRACKS["M5"] == ("x", 24, 48) and pta.TRACKS["M4"] == ("y", 24, 48) and pta.TRACKS["M3"] == ("x", 9, 36)


def test_t51_native_e_source_root_is_20nm_off_in_plan_frame():
    # origin x 639.36 (0 mod 64 nm) + plan offset 0.108 + kit root pin x 23.328 -> 662.796: 12 mod 64, die track 32
    pins = [dict(name="clk_t19", layer="M7", x=23.328, y=338.592)]
    r = pta.audit_pins(pins, [639.36, 8.64], [0.108, 0.012], ["M7"])["M7"]
    assert r["offtrack"] == 1 and r["residue_nm"] == {44: 1} and r["shift_nm"] == 20


def test_plus4_snap_is_still_off_track():
    # the 11-12 02:29 +4 nm snap (local 36 mod 64) lands 16 nm off the die M7 track: the mutant must fail
    pins = [dict(name="clk_t19", layer="M7", x=23.332, y=338.592)]
    r = pta.audit_pins(pins, [639.36, 8.64], [0.108, 0.012], ["M7"])["M7"]
    assert r["offtrack"] == 1 and r["shift_nm"] == 16


def test_local_52_is_on_track_and_agrees_with_the_generator():
    pins = [dict(name="clk_t19", layer="M7", x=23.348, y=338.592)]          # 23348 nm = 52 mod 64
    assert pta.audit_pins(pins, [639.36, 8.64], [0.108, 0.012], ["M7"])["M7"]["offtrack"] == 0
    G = pytest.importorskip("gen_core_kit_legacy")
    hc = dict(module="m", pins_file="p.json", origin_um=[639.36, 8.64], outline_um=[794.88, 1209.6], orient="R0",
              track_offset_um=[0.108, 0.012])
    plan = {"partition_types": {"t": {"hard_cores": [hc]}}}
    assert G.native_m7_phase({"clk_t19": ["M7", 23.332, 338.2, 23.364, 338.968]}, hc, plan) == pytest.approx(0.052)


def test_on_track_pin_ok():
    r = pta.audit_pins([dict(name="a", layer="M7", x=0.032, y=0.0)], [0, 0], [0, 0], ["M7"])["M7"]
    assert r["offtrack"] == 0 and r["shift_nm"] is None


def test_shift_lands_on_track():
    p = dict(name="a", layer="M7", x=0.016, y=0.0)
    r = pta.audit_pins([p], [0, 0], [0, 0], ["M7"])["M7"]
    assert r["offtrack"] == 1 and r["shift_nm"] == 16
    p["x"] = round(p["x"] + r["shift_nm"] / 1000, 4)
    assert pta.audit_pins([p], [0, 0], [0, 0], ["M7"])["M7"]["offtrack"] == 0


def test_mirrored_axis_uses_outline_minus_centre():
    # MY core, outline 794.88: local x -> 794.88 - x in the plan frame (gen_core_kit_legacy.native_m7_phase)
    w = 794.88
    good = round(w - (0.032 - 0.108 - 639.36) % 0.064 - 0.064 * 100, 3)     # some local x on the die lattice
    g = 639360 + 108 + round(w * 1000) - round(good * 1000)
    assert (g - 32) % 64 == 0
    p = [dict(name="a", layer="M7", x=good, y=1.0)]
    assert pta.audit_pins(p, [639.36, 8.64], [0.108, 0.012], ["M7"], "MY", [w, 1209.6])["M7"]["offtrack"] == 0
    assert pta.audit_pins(p, [639.36, 8.64], [0.108, 0.012], ["M7"], "R0", [w, 1209.6])["M7"]["offtrack"] == 1
    with pytest.raises(ValueError):
        pta.audit_pins(p, [0, 0], [0, 0], ["M7"], "MY")
