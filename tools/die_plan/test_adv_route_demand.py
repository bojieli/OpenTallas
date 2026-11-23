"""ADV-ROUTE-DEMAND (LEAF-ROUTE-CBC): static routing-demand advisory; a WARN names the hot region and the core channel."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_route_demand as R  # noqa: E402
import plan_advisory as PA  # noqa: E402


def _type(gap, bits=1024):
    # two M5-obs cores side by side with a `gap` um channel; a wide bus crosses from the W core's E face through the gap
    a = {"inst": "u_lf.u_vp.g_ln[0].u_l", "origin_um": [100.0, 100.0], "outline_um": [114.48, 114.48], "obs_max": "M5"}
    b = {"inst": "u_lf.u_vp.g_ln[1].u_l", "origin_um": [214.48 + gap, 100.0], "outline_um": [114.48, 114.48], "obs_max": "M5"}
    st = [{"bits": bits, "launch": "core:u_lf.u_vn.u_a.hw_d", "capture": "u_lf.u_vp.g_ln[1].u_l",
           "from_um": [214.48 + gap / 2, 20.0], "regs_um": [[214.48 + gap / 2, 160.0]], "to_um": [214.48 + gap / 2, 300.0]}
          for _ in range(4)]
    return {"outline_um": [500.0, 400.0], "hard_cores": [a, b], "internal_stations": st, "ft_slots": []}


def test_narrow_channel_is_named():
    out = R.findings({"partition_types": {"leaf_x": _type(8.64)}})
    assert len(out) == 1 and out[0].startswith("WARN ADV-ROUTE-DEMAND leaf_x:")
    assert "channel 8.64 um x" in out[0] and "hw_d" in out[0]


def test_light_load_is_quiet():
    assert R.findings({"partition_types": {"leaf_y": _type(60.0, bits=8)}}) == []


def test_wider_channel_lowers_peak():
    narrow = max(max(r) for r in R.grid(_type(8.64))["util"])
    wide = max(max(r) for r in R.grid(_type(100.0))["util"])
    assert wide < narrow


def test_bad_rows_never_raise():
    t = {"outline_um": [100, 100], "hard_cores": [{"inst": "x"}], "internal_stations": [{"bits": "q"}], "ft_slots": [{}]}
    out = R.findings({"partition_types": {"bad": t, "nolegs": {"outline_um": [10, 10]}}})
    assert all(x.startswith("WARN ADV-ROUTE-DEMAND") for x in out)


def test_registered_last_in_plan_advisory():
    assert ("ROUTE-DEMAND", "adv_route_demand") in PA.CHECKS
