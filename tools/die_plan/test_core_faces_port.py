"""check.py core_faces: a core_conns destination 'core:<inst>.<port>' (bind / netlist form) names the partner core."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "autopilot"))
import check as C  # noqa: E402


class _P:
    def __init__(self, t):
        self.types = {"t": t}
        self.raw = {}


def test_core_dest_with_port_counts_for_face_rule(tmp_path):
    pins = [{"name": f"d[{i}]", "layer": "M4", "xy": [40.0, 10.0 + i]} for i in range(4)]
    hc = [dict(inst="u_h.u_a", origin_um=[10, 10], outline_um=[40, 40], orient="R0", pins=pins),
          dict(inst="u_h.u_b", origin_um=[200, 10], outline_um=[40, 40], orient="R0", pins=pins)]
    t = {"outline_um": [300, 100], "hard_cores": hc}
    (tmp_path / "core_conns.json").write_text(json.dumps({"t": {"u_h.u_a": {"d": ["core:u_h.u_b.d"]}}}))
    R = C.Report(True)
    o = C.check_core_faces(_P(t), R, tmp_path)
    assert o["groups"] == 1 and o["cores_unchecked"] == 1
