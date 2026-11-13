"""R-REACH-1 die-level relays: START provider relay stages (count-aligned PAD) and monitor-bundle relays."""
import copy
from types import SimpleNamespace

import pytest

import landing_contract as LC
import reach_relay_plan as RP
import start_provider_plan as SP


def _pv():
    """root b0 (clock node at 0,0) -> child b1 460 um east on a straight trunk; b1 drives partition q's START input"""
    def node(i, x, parent, root):
        return dict(id=i, region=f"st:{i}", rect_um=[x - 5.4, -1.3, x, 1.3], clock_node=i, clock_node_xy_um=[x + 0.5, 0.0],
                    clock_port=f"t_st_{i}__clk", module="ot_dp_landing_origin", flops=3, parent=parent, root=root)
    a, b = node("b0", 0.0, None, True), node("b1", 460.0, "st:b0", False)
    e = dict(max_hop_um=405, source_registered=True, capture_registered=True)
    return dict(form="emitted_start_stage_rows", nodes=[a, b],
                edges=[dict(e, src_stage="b0", dst_stage="b1", src_rect_um=a["rect_um"], dst_rect_um=b["rect_um"]),
                       dict(e, src_stage="b1", part="q", pin="cland_tstart_in", net="pst_b1", src_rect_um=b["rect_um"],
                            dst_rect_um=[470.0, 0.0, 470.0, 0.0])])


def _P():
    pin = dict(name="cland_tstart_in", xy_um=[470.0, 0.0])
    return SimpleNamespace(ptype=lambda n: dict(clock=dict(landing_contract=dict(pins=[pin]))), to_die=lambda n, q: q,
                           clock=dict(landing_network=dict(start_tree=dict(uses=[dict(part="q", pin="cland_tstart_in",
                                                                                     net="pst_b1")]))))


def test_start_relay_inserted_on_trunk_and_padded():
    pv = _pv()
    P = _P()
    assert SP.check(P, pv)["errors"]                       # 460 um parent edge fails the 405 gate
    regions = {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}
    rows = RP.start_relays(P, pv, regions)
    r = SP.check(P, pv)
    assert not r["errors"] and r["relays"] == 1 and r["max_hop_um"] <= RP.SITE_MAX
    assert regions["st:b1"]["pad"] == 1 and rows[0]["relays"] == 1        # the bind prices the boot cycle (K)
    rl = [n for n in pv["nodes"] if n.get("kind") == "relay"][0]
    assert rl["clock_node_xy_um"][1] == 0.0 and 0 < rl["clock_node_xy_um"][0] < 460.5   # on the b0 -> b1 trunk
    st = RP.depth_stats(pv)
    assert st["max_depth"] == 3 and st["max_relays_on_path"] == 1
    again = copy.deepcopy(pv)                              # a second pass is a no-op (idempotent)
    assert RP.start_relays(P, again, regions) == [] and again == pv and regions["st:b1"]["pad"] == 1


def test_short_edges_untouched():
    pv = _pv()
    for n in pv["nodes"][1:]:
        n["rect_um"] = [200 - 5.4, -1.3, 200, 1.3]
        n["clock_node_xy_um"] = [200.5, 0.0]
    pv["edges"][0]["dst_rect_um"] = pv["nodes"][1]["rect_um"]
    before = copy.deepcopy(pv)
    regions = {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}
    assert RP.start_relays(_P(), pv, regions) == [] and pv == before and regions["st:b1"]["pad"] == 0


def _lc_plan(relays=None, group=True, clk_relay_xy=None):
    pins = {"s": [dict(name="cland_up_ready", dir="out", kind="ctl", epoch=False, layer="M4", xy_um=[0.0, 0.0]),
                  dict(name="fclk_out_cland_up", dir="out", kind="clock", epoch=False, layer="M4", xy_um=[0.0, 2.0])],
            "d": [dict(name="cland_dn_ready_0", dir="in", kind="ctl", epoch=False, layer="M4", xy_um=[0.0, 460.0]),
                  dict(name="fclk_in_cland_dn_0", dir="in", kind="clock", epoch=False, layer="M4", xy_um=[0.0, 462.0])]}
    types = {tn: dict(outline_um=[10.0, 500.0], clock=dict(landing_contract=dict(pins=ps),
                                                            edge_clocks=[dict(port="fclk_in_cland_dn_0")]))
             for tn, ps in pins.items()}
    e = dict(width=1, epoch=False, max_hop_um=405)
    edges = [dict(e, id="cland_mon_ready__s", src=dict(part="s", bus="cland_up_ready"), dst=dict(part="d", bus="cland_dn_ready_0"),
                  kind="ctl", source_registered=True, capture_registered=True),
             dict(e, id="cland_mon_clk__s", src=dict(part="s", bus="fclk_out_cland_up"), dst=dict(part="d", bus="fclk_in_cland_dn_0"),
                  kind="clock", source_registered=False, capture_registered=False)]
    if relays is not None:
        for ed in edges:
            xy = clk_relay_xy if (clk_relay_xy and ed["kind"] == "clock") else relays
            ed["relays"] = [dict(id="rl_s_1", kind="fwd_clock_relay", xy_um=list(xy))]
            if group:
                ed["relay_group"] = "cland_mon__s"
    net = dict(edges=edges, root_observer=dict(part="s", module="m", fault_port="f", ready_port="r"))
    return SimpleNamespace(types=types, parts={"s": dict(type="s"), "d": dict(type="d")}, layers={"M4": {}},
                           clock=dict(landing_network=net), to_die=lambda pn, xy: (xy[0], xy[1]))


def test_monitor_bundle_relay_segments_checked():
    assert any("exceeds405" in e for e in LC.check(_lc_plan())["errors"])
    r = LC.check(_lc_plan(relays=[0.0, 231.0]))
    assert not r["errors"] and r["max_hop_um"] <= 405


@pytest.mark.parametrize("bad", ["no_group", "split_sites", "far_site"])
def test_monitor_relay_mutants_fail(bad):
    P = {"no_group": lambda: _lc_plan(relays=[0.0, 231.0], group=False),
         "split_sites": lambda: _lc_plan(relays=[0.0, 231.0], clk_relay_xy=[0.0, 240.0]),
         "far_site": lambda: _lc_plan(relays=[0.0, 30.0])}[bad]()
    assert LC.check(P)["errors"]


def test_monitor_relay_second_pass_is_noop():
    P = _lc_plan(relays=[0.0, 231.0])
    P.ptype = lambda pn: P.types[P.parts[pn]["type"]]
    before = copy.deepcopy(P.clock)
    assert RP.mon_relays(P, P.clock["landing_network"], [], RP.Grid()) == [] and P.clock == before


def _trunks(region_b0="R0", detour=False, extra_other=False):
    """built clock: b0/b1 sit on built nodes c0 (2, 3) / c1 (455, 3); the built leg c0 -> c1 runs y = 3 in region R0"""
    legs = [dict(a="c0", a_xy_um=[2.0, 3.0], b="c1", b_xy_um=[455.0, 3.0], net="n0", region="R0", region_kind="local",
                 **({"detour_um": 40.0} if detour else {}))]
    if extra_other:     # a nearer leg of another region (y = 0.5) must be rejected
        legs.append(dict(a="x0", a_xy_um=[0.0, 0.5], b="x1", b_xy_um=[460.0, 0.5], net="nx", region="R9", region_kind="feed"))
    return dict(schema="opentallas.qc_trunk_nodes.v1", clock_build="t", plan_sha256="p", legs=legs,
                stages={"b0": dict(clock_node="c0", clock_net="n0", clock_node_xy_um=[2.0, 3.0], region=region_b0,
                                   region_kind="local", old_clock_node="b0"),
                        "b1": dict(clock_node="c1", clock_net="n1", clock_node_xy_um=[455.0, 3.0], region="R0",
                                   region_kind="local", old_clock_node="b1")})


def test_built_trunk_rewrites_provider_and_seats_relays_on_built_legs_of_the_source_region():
    pv, P = _pv(), _P()
    st, segs, meta = RP.load_trunks(_trunks(extra_other=True))
    rw = RP.rewrite_provider(pv, st)
    assert rw["nodes"] == 2 and pv["nodes"][0]["clock_node"] == "c0" and pv["nodes"][0]["clock_region"] == "R0"
    regions = {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}
    rej = set()
    rows = RP.start_relays(P, pv, regions, (segs, meta, RP.by_region(segs, meta)), rej)
    rl = [n for n in pv["nodes"] if n.get("kind") == "relay"][0]
    assert rows[0]["relays"] == 1 and rl["clock_node_xy_um"][1] == 3.0 and rl["site_net"] == "n0"
    assert rl["clock_node"] == "c0" and rl["clock_region"] == "R0" and not SP.check(P, pv)["errors"]
    assert not rej                              # placed on R0 (the nearer R9 leg is never offered)


def test_built_trunk_guards():
    pv = _pv()
    st, *_ = RP.load_trunks(_trunks())
    del st["b1"]
    with pytest.raises(RP.RelayError):          # a provider node without a built node: no fallback
        RP.rewrite_provider(pv, st)
    with pytest.raises(RP.RelayError):
        RP.load_trunks(dict(schema="other", legs=[], stages={}))
    pv = _pv()
    st, segs, meta = RP.load_trunks(_trunks(detour=True))
    assert segs == []                           # detoured legs carry no relay
    RP.rewrite_provider(pv, st)
    with pytest.raises(RP.RelayError):
        RP.start_relays(_P(), pv, {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}, (segs, meta, RP.by_region(segs, meta)), set())
    pv = _pv()                                  # only the FED stage's region has a leg: destination-side relay
    st, segs, meta = RP.load_trunks(_trunks(region_b0="R5"))
    RP.rewrite_provider(pv, st)
    RP.start_relays(_P(), pv, {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}, (segs, meta, RP.by_region(segs, meta)), set())
    rl = [n for n in pv["nodes"] if n.get("kind") == "relay"][0]
    assert rl["clock_side"] == "dst" and rl["clock_node"] == "c1" and rl["clock_region"] == "R0" and rl["flops"] == 4
    pv = _pv()                                  # a third region only: rejected, no site
    tk = _trunks(region_b0="R5")
    tk["stages"]["b1"]["region"] = "R6"
    st, segs, meta = RP.load_trunks(tk)
    RP.rewrite_provider(pv, st)
    rej = set()
    with pytest.raises(RP.RelayError):
        RP.start_relays(_P(), pv, {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}, (segs, meta, RP.by_region(segs, meta)), rej)
    assert rej and all(r[2] == "R0" for r in rej)
