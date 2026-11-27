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


def packed_plan():
    return {
        "die": {"reach_um": 600},
        "partitions": [{"type": "frame"}],
        "partition_types": {"frame": {
            "buses": [{"name": "frame_i", "dir": "in", "width": 2}],
            "internal_stations": [{
                "conn": "bus:frame_i", "launch": "face flop",
                "regs_um": [[3, 3], [4, 4], [5, 5]],
            }],
            "relay_sites": {
                "u_bin_frame_i.q[0]": [0, 0],
                "u_lpad_frame_i.r[0][0]": [400, 7],
                "u_lpad_frame_i/r[1][0]": [800, 16],
                # This last 405 um leg is legal at the stock cap.
                "u_lpad_frame_i.r[2][0]": [1200, 21],
            },
        }},
    }


def test_packed_point_override_checks_first_and_consecutive_real_ranks():
    p = packed_plan()
    rows = A.packed_override_hits(p, "p.json")
    assert [(r["stage"], r["bit"], r["distance"], r["reach"]) for r in rows] == [
        (1, 0, 409, 405), (0, 0, 407, 405),
    ]
    warnings = A.findings(p, "p.json")
    assert len(warnings) == 2
    assert "1 first leg(s) and 1 consecutive rank leg(s)" in warnings[0]
    assert "2 over-reach packed legs in 1 chain(s)" in warnings[1]


def test_rank_line_and_conflicting_aliases_do_not_price_stale_point():
    p = packed_plan()
    t = p["partition_types"]["frame"]
    t["relay_rank_sites"] = {"u_lpad_frame_i.r[0]": {"line_um": [[10, 20], [20, 30]]}}
    assert A.packed_override_hits(p, "p.json") == []
    del t["relay_rank_sites"]
    t["relay_sites"]["u_bound.u_lpad_frame_i/r[0][0]"] = [10, 10]
    assert A.packed_override_hits(p, "p.json") == []


def test_exact_bank_can_complete_a_leg_but_nominal_site_cannot():
    p = packed_plan()
    t = p["partition_types"]["frame"]
    del t["relay_sites"]["u_lpad_frame_i/r[1][0]"]
    assert [r["stage"] for r in A.packed_override_hits(p, "p.json")] == [0]
    t["internal_stations"][0]["bit_sites_um"] = [
        [[30, 30], [31, 30], [32, 30]],
        [[800, 12], [801, 12], [802, 12]],
        [[1200, 21], [1201, 21], [1202, 21]],
    ]
    assert [(r["stage"], r["distance"]) for r in A.packed_override_hits(p, "p.json")] == [
        (2, 409), (0, 407),
    ]
