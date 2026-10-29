"""DIE-HEAD-21: gen phys --clock-landing emits kit land_slots.json for count-aligned landing rings (face_guard form
hold_mux, D = ring DEPTH; dataflow status pins ride the same slots).  Opt-in: kits without it stay byte-identical.
python3 -m pytest -q tools/die_plan/test_land_slots_emit.py"""
import copy
import filecmp
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import face_guard  # noqa: E402
import gen_phys  # noqa: E402
import schema  # noqa: E402
from clock_landings import LAND_SLOTS_SCHEMA, Landings  # noqa: E402
from test_clock_landings import ca_vehicle, vehicle  # noqa: E402
from test_g2 import PAIR  # noqa: E402


def test_count_aligned_ring_declares_hold_mux_slots_of_its_depth():
    for depth in (4, 8):
        p, t = ca_vehicle(depth=depth)
        c = Landings(p, t)
        got = c.land_slots("B")
        assert got == {"schema": LAND_SLOTS_SCHEMA, "buses": {"y": {"D": depth, "form": "hold_mux"},
                                                             "cland_fstart_in_y": {"form": "ring_start", "ring": "y"}}}
        # face_guard accepts every emitted spec: the enable-mux slot form + the ring START of that ring
        assert {b: face_guard.land_spec(v) for b, v in got["buses"].items()} == {"y": (depth, "hold_mux"),
                                                                                 "cland_fstart_in_y": (0, "ring_start")}
        assert face_guard.ring_spec(got["buses"]["cland_fstart_in_y"]) == ["y"]
        assert c.land_slots("A") is None          # sender only: no landed input, no file


def test_dataflow_status_pins_ride_the_same_slots():
    p, t = ca_vehicle(depth=4)
    c = Landings(p, t)
    c.dataflow = True                             # ring d = {cland_dn_fault_y, cland_dn_ready_y, y}
    assert c.land_slots("B")["buses"] == {**{n: {"D": 4, "form": "hold_mux"}
                                             for n in ("y", "cland_dn_ready_y", "cland_dn_fault_y")},
                                          "cland_fstart_in_y": {"form": "ring_start", "ring": "y"}}


def test_default_ring_form_declares_nothing():
    p, t = vehicle()
    assert Landings(p, t).land_slots("B") is None and Landings(p, t).land_slots("A") is None


def _same_tree(a, b):
    c = filecmp.dircmp(a, b)
    assert not c.left_only and not c.right_only and not c.diff_files, (c.left_only, c.right_only, c.diff_files)
    for s in c.common_dirs:
        _same_tree(Path(a) / s, Path(b) / s)


def test_kit_byte_identical_without_land_slots_and_one_file_with_it():
    spec = {"schema": LAND_SLOTS_SCHEMA, "buses": {"i": {"D": 4, "form": "hold_mux"}}}
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b, tempfile.TemporaryDirectory() as c:
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", a, [])
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", b, [], land_slots=None)
        _same_tree(Path(a) / "fa", Path(b) / "fa")
        assert not (Path(a) / "fa" / "land_slots.json").exists()
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", c, [], land_slots=spec)
        k0, k1 = Path(a) / "fa", Path(c) / "fa"
        d = filecmp.dircmp(k0, k1)
        assert d.right_only == ["land_slots.json"] and not d.left_only and not d.diff_files
        # beside pins.json, where run_kit's face_guard --pins /work/pins.json looks for it
        assert face_guard.kit_land(k1 / "land_slots.json") == spec["buses"]
