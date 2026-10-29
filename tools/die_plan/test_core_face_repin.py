"""DIE-HBM-15: core_face_repin face algebra + placement (on the table's lattice, face edge depth, interior pins ignored)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_face_repin as F  # noqa: E402

L = {"M4": dict(dir="H", pitch_um=0.048, offset_um=0.024), "M5": dict(dir="V", pitch_um=0.048, offset_um=0.024)}


def test_type_face_and_dir_follow_orient():
    assert F.type_face("R0", "N") == "N" and F.type_face("MX", "N") == "S" and F.type_face("MY", "E") == "W"
    assert F.type_face("R180", "S") == "N" and F.type_face("MX", "E") == "E"
    assert F.core_dir("MX", 0.0, 1.0) == (0.0, -1.0) and F.core_dir("MY", 1.0, 0.0) == (-1.0, 0.0)


def test_score_face_prefers_partner_side():
    recs = [dict(orient="R0", dirs=[("p", 0.0, 1.0)]), dict(orient="MX", dirs=[("p", 0.0, -1.0)])]
    # both partners are on the core-frame N side once the MX instance is unflipped
    assert min("NSEW", key=lambda f: F.score_face(recs, f)[0]) == "N"
    assert F.score_face(recs, "S")[0][0] == 2


def test_place_on_face_lattice_and_depth_ignores_interior_pins():
    cw, ch = 50.0, 40.0
    pins = [dict(name="ck", layer="M5", x=24.984, y=20.0),                 # interior clock pin: never a face pin
            dict(name="a[0]", layer="M5", x=10.008, y=39.904),             # existing N face pin (lattice + depth)
            dict(name="d[0]", layer="M4", x=49.904, y=5.0), dict(name="d[1]", layer="M4", x=49.904, y=5.096)]
    moved = pins[2:]
    lay, step, _ = F.place(pins, moved, "N", cw, ch, L, 0.0, dict(origin_um=[0, 0]))
    assert lay == "M5" and step == 2
    for p in moved:
        assert p["layer"] == "M5" and abs(p["y"] - 39.904) < 1e-9
        k = (p["x"] - 10.008) / 0.048
        assert abs(k - round(k)) < 1e-6 and p["x"] != 10.008
    assert abs(moved[1]["x"] - moved[0]["x"]) >= 0.096 - 1e-9 and moved[0]["x"] < moved[1]["x"]


def test_place_w_face_never_uses_interior_depth():
    cw, ch = 50.0, 40.0
    pins = [dict(name="ck", layer="M4", x=20.0, y=20.016),                 # interior, nearest face W
            dict(name="d[0]", layer="M4", x=49.904, y=5.016)]
    F.place(pins, pins[1:], "W", cw, ch, L, 0.0, dict(origin_um=[0, 0]))
    assert pins[1]["x"] <= F.EDGE
