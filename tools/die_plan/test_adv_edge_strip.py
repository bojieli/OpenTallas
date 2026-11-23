"""ADV-EDGE-STRIP: a 1104-bit window with a core 34.56 um behind it is flagged (svc u_c form); the same core at 69.12 um,
a core beside the window span, a narrow window and a mirrored partner are handled."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("adv_edge_strip", HERE / "adv_edge_strip.py")
ES = importlib.util.module_from_spec(_spec)
sys.modules["adv_edge_strip"] = ES
_spec.loader.exec_module(ES)


def _plan(core_y=34.56, core_x=100.0, width=1104, orient_b="R0"):
    ta = {"outline_um": [1000.0, 1000.0],
          "hard_cores": [{"inst": "u_c", "origin_um": [core_x, core_y], "outline_um": [150.0, 250.0]}]}
    tb = {"outline_um": [1000.0, 1000.0], "hard_cores": []}
    return {"partition_types": {"svc": ta, "lf": tb},
            "partitions": [{"name": "a", "type": "svc", "origin_um": [0.0, 1000.0], "orient": "R0"},
                           {"name": "b", "type": "lf", "origin_um": [0.0, 0.0], "orient": orient_b}],
            "ports": [{"id": "p0", "src": {"part": "b", "bus": "x_o"}, "dst": {"part": "a", "bus": "x_i"},
                       "width": width, "face": "N", "window_um": [120.0, 240.0], "layers": ["M7", "M5"]}]}


def test_flags_core_behind_window():
    out = ES.findings(_plan(), "p.json")
    assert any("svc: 1 window" in x and "strip 34.56" in x for x in out), out


def test_clear_at_threshold():
    out = ES.findings(_plan(core_y=69.12), "p.json")
    assert out[-1].endswith("s") and "0 type(s)" in out[-1], out


def test_core_beside_window_not_flagged():
    out = ES.findings(_plan(core_x=400.0), "p.json")
    assert "0 type(s)" in out[-1], out


def test_narrow_window_not_flagged():
    out = ES.findings(_plan(width=128), "p.json")
    assert "0 type(s)" in out[-1], out


def test_mirrored_partner_maps_face():
    rows = ES.strips(_plan(orient_b="MX"))
    assert rows and rows[0][0] == "svc" and rows[0][2] == "S", rows
