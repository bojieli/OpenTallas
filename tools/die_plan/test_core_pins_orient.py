"""CLOCK-KV-R12: core_pins_orient flip algebra, data-pin mirror (clock pins kept), collision slide, track snap."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core_pins_orient as O  # noqa: E402


def test_compose_is_flip_group():
    assert O.compose("MX", "MX") == "R0" and O.compose("MX", "MY") == "R180" and O.compose("R180", "MY") == "MX"
    assert O.compose("R0", "R180") == "R180"


def _pins(tmp, pins):
    f = tmp / "p.json"
    f.write_text(json.dumps(dict(faces={"N": {"pins": 1}, "E": {"pins": 1}}, pins=pins)))
    return f


def test_mirror_keeps_clock_and_swaps_faces(tmp_path):
    f = _pins(tmp_path, [dict(name="d[0]", layer="M5", x=10.0, y=215.904), dict(name="ck", layer="M5", x=20.0, y=0.096)])
    O.mirror_pins(f, tmp_path / "o.json", "MX", 216.0, 216.0)
    js = json.loads((tmp_path / "o.json").read_text())
    d, ck = js["pins"]
    assert abs(d["y"] - 0.096) < 1e-9 and d["x"] == 10.0
    assert ck["y"] == 0.096 and ck["x"] == 20.0
    assert set(js["faces"]) == {"S", "E"}


def test_collision_with_kept_clock_slides_along_face(tmp_path):
    f = _pins(tmp_path, [dict(name="d[0]", layer="M5", x=20.0, y=215.904), dict(name="ck", layer="M5", x=20.0, y=0.096)])
    O.mirror_pins(f, tmp_path / "o.json", "MX", 216.0, 216.0)
    d, ck = json.loads((tmp_path / "o.json").read_text())["pins"]
    assert abs(d["y"] - 0.096) < 1e-9 and abs(abs(d["x"] - 20.0) - 0.048) < 1e-9


def test_x_mirror_snaps_to_type_track(tmp_path):
    f = _pins(tmp_path, [dict(name="t[0]", layer="M3", x=1.009, y=0.096)])
    L = {"M3": dict(dir="V", pitch_um=0.036, offset_um=0.009)}
    hc = dict(orient="R0", origin_um=[0.0, 0.0])
    O.mirror_pins(f, tmp_path / "o.json", "MY", 10.0, 5.0, layers=L, hc=hc)
    x = json.loads((tmp_path / "o.json").read_text())["pins"][0]["x"]
    k = (x - 0.009) / 0.036
    assert abs(k - round(k)) < 1e-6 and abs(x - (10.0 - 1.009)) <= 0.018 + 1e-9
