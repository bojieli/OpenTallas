"""ADV-PAD-LAUNCH: station chain priced from the core leaf but really launched by a pad-stage register."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_pad_launch as A  # noqa: E402


def plan(relay=None, straps=None, rep=450):
    st = {"conn": "bus:x_su_c_p1_o", "launch": "u_ctl", "from_um": [900, 593], "leaf_um": [900, 593], "regs_um": [[1055, 490], [1100, 300]]}
    t = {"internal_stations": [st], "relay_sites": relay or {}, "count_straps": straps or []}
    return {"die": {"rep_um": rep}, "partition_types": {"sle_ctl": t}}


def test_measured_pad_flagged_with_distances():
    r = A.hits(plan(), measured={"sle_ctl": {"bus:x_su_c_p1_o": [630, 640]}})
    assert len(r) == 1 and r[0]["basis"] == "MEASURED" and r[0]["priced_hop"] < 300 < r[0]["real_hop"] and r[0]["gap"] > 250


def test_face_launched_chain_is_not_judged_by_receive_pads():
    p = plan(relay={"u_lpad_x_su_c_p1_o.q[0]": [600, 650]}, straps=[{"name": "strap_r8pad_l", "sites_um": [[630, 640]]}])
    p["partition_types"]["sle_ctl"]["internal_stations"][0]["launch"] = "face x"
    assert A.hits(p) == []


def test_r8pad_strap_proxy_needs_plausible_pad_and_is_labelled():
    s = [{"name": "strap_r8pad_lane_x", "sites_um": [[630, 640]]}]
    assert A.hits(plan(straps=s))[0]["basis"] == "R8PAD-PROXY"
    far = [{"name": "strap_r8pad_lane_x", "sites_um": [[10, 2000]]}]
    assert A.hits(plan(straps=far)) == []


def test_pad_at_the_leaf_is_quiet_and_other_straps_ignored():
    assert A.hits(plan(), measured={"sle_ctl": {"bus:x_su_c_p1_o": [900, 600]}}) == []
    assert A.hits(plan(straps=[{"name": "strap_ca_pad", "sites_um": [[630, 640]]}])) == []


def test_findings_are_warn_lines_and_never_raise():
    out = A.findings(plan(), "p.json", measured={"sle_ctl": {"bus:x_su_c_p1_o": [630, 640]}})
    assert out[0].startswith("WARN ADV-PAD-LAUNCH sle_ctl bus:x_su_c_p1_o") and "summary" in out[-1]
    assert A.findings({"partition_types": 3}, "p.json")[0].startswith("WARN ADV-PAD-LAUNCH not checked")
