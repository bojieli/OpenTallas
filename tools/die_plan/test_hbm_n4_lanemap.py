"""Unit tests for hbm_n4_lanemap.py (HBM-MU-QUAD-3 n4 lane-map assertion)."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_n4_lanemap as M  # noqa: E402


def _hub_type():
    hc = [dict(inst=f"u_mu_fused_{L}", module="hnx_fused_lane") for L in range(16)]
    st = []
    # golden pairwise tree over 16 lanes: level nodes named n<lvl>_<idx>, top = u_mu_fused_n4
    cur = [f"u_mu_fused_{L}" for L in range(16)]
    lvl = 1
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur), 2):
            p = "u_mu_fused_n4" if len(cur) == 2 else f"u_mu_fused_t{lvl}_{i // 2}"
            hc.append(dict(inst=p, module="ot_hnx_fused_tnode"))
            for ch, sl in ((cur[i], "ua"), (cur[i + 1], "ub")):
                st.append(dict(conn=f"mu_tree:{ch}.uo|{p}", launch=f"{ch}.uo", capture=f"{p}.{sl}"))
            nxt.append(p)
        cur = nxt
        lvl += 1
    st.append(dict(conn="mu_tree_root:n4:up", launch="u_mu_fused_n4.uo", capture="face root.up"))
    return dict(hard_cores=hc, internal_stations=st)


def _plan():
    t = _hub_type()
    return dict(partition_types=dict(q_hub_nw=t, q_hub_ne=copy.deepcopy(t), root={}),
                partitions=[dict(name="NW_hub", type="q_hub_nw", origin_um=[5000.0, 0.0]),
                            dict(name="root", type="root", origin_um=[13000.0, 0.0]),
                            dict(name="NE_hub", type="q_hub_ne", origin_um=[15000.0, 0.0])],
                ports=[])


def _lane(P, tn, L):
    return next(h for h in P["partition_types"][tn]["hard_cores"] if h["inst"] == f"u_mu_fused_{L}")


def test_inactive_without_n4():
    P = dict(partition_types=dict(a={}), partitions=[dict(name="a", type="a", origin_um=[0, 0])], ports=[])
    r = M.check(P)
    assert not r["active"] and not r["errors"]


def test_golden_plan_passes_and_derives_map():
    r = M.check(_plan())
    assert r["verdict"] == "PASS", r["errors"]
    assert r["required_lid"]["NW_hub.u_mu_fused_0"] == 0 and r["required_lid"]["NW_hub.u_mu_fused_15"] == 15
    assert r["required_lid"]["NE_hub.u_mu_fused_0"] == 16 and r["required_lid"]["NE_hub.u_mu_fused_15"] == 31


def test_strict_fails_on_undeclared_and_passes_when_declared():
    P = _plan()
    assert M.check(P, strict=True)["verdict"] == "FAIL"
    for tn, base in (("q_hub_nw", 0), ("q_hub_ne", 16)):
        for L in range(16):
            _lane(P, tn, L)["parent_id_straps"] = {"lane_lane_id": {"width": 5, "value": base + L}}
        st = next(s for s in P["partition_types"][tn]["internal_stations"] if s["conn"].startswith("mu_tree_root"))
        st["capture"] = "face root.up:" + ("a" if base == 0 else "b")
    r = M.check(P, strict=True)
    assert r["verdict"] == "PASS", r["errors"]


def test_swapped_hub_map_fails():
    P = _plan()
    for L in range(16):     # NW lanes declared as 16..31 (hubs swapped)
        _lane(P, "q_hub_nw", L)["parent_id_straps"] = {"lane_lane_id": {"width": 5, "value": 16 + L}}
    r = M.check(P)
    assert r["verdict"] == "FAIL" and any("!= 0" in e or "!= 1" in e for e in r["errors"])


def test_root_side_swapped_fails():
    P = _plan()
    st = next(s for s in P["partition_types"]["q_hub_nw"]["internal_stations"] if s["conn"].startswith("mu_tree_root"))
    st["capture"] = "face root.up:b"
    assert M.check(P)["verdict"] == "FAIL"


def test_permuted_tree_fails():
    P = _plan()
    st = P["partition_types"]["q_hub_ne"]["internal_stations"]
    for s in st:     # lanes 2 and 4 swap tree positions (RTL MUT 8)
        for k in ("launch", "conn"):
            s[k] = s[k].replace("u_mu_fused_2.", "@@").replace("u_mu_fused_4.", "u_mu_fused_2.").replace("@@", "u_mu_fused_4.")
    r = M.check(P)
    assert r["verdict"] == "FAIL" and any("golden" in e for e in r["errors"])


def test_west_east_order_and_names():
    P = _plan()
    P["partitions"][0]["origin_um"] = [20000.0, 0.0]
    assert M.check(P)["verdict"] == "FAIL"
    P = _plan()
    P["partitions"][2]["name"] = "XX_hub"
    assert M.check(P)["verdict"] == "FAIL"
