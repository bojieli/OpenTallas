"""DIE-HEAD-12: opt-in band spread reaches landing_placement.tcl as a ring tag suffix; default plans unchanged."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_place as LP  # noqa: E402


class _P:
    def __init__(self, bands):
        self.types = {"t": {"clock": {"landing_contract": {"monitor": "dataflow", "bands": bands, "pins": []}}}}


def test_spread_suffix_only_when_band_has_spread():
    plain = LP.tcl(_P({"i": {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i"}}), "t")
    assert "{u_cland_i {1.00000 2.00000 3.00000 4.00000} ring:i}" in plain
    sp = LP.tcl(_P({"i": {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i", "spread": 1.8037}}), "t")
    assert "{u_cland_i {1.00000 2.00000 3.00000 4.00000} ring:i@1.8037}" in sp


def test_placement_tcl_widens_reserve_by_spread():
    tcl = (Path(__file__).resolve().parent / "landing_placement.tcl").read_text()
    assert "regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp" in tcl
    assert "/0.4*$sp/$ff_sw" in tcl
