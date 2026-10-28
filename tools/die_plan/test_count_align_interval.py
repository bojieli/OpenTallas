"""DIE-HEAD-5 (COORD 00:22 follow-up): ONE d-interval model for count_align_plan and die_sta_related --count-align.
The planner hulls its derated rows with die_sta_related.count_align_d_intervals (sta_d_intervals on the same proof), so
a sample edge the planner keeps >= ap from the boundary (incl. start skew) is also >= ap on the STA's own numbers."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_bind as CB  # noqa: E402
import count_align_plan as CAP  # noqa: E402
import die_sta_related as D  # noqa: E402

T = 833.0
AP = T / 8
REG = dict(clkq_max_wire_ps=60.0, clkq_min_nowire_ps=50.0)
SKEW = (50.0, 60.0)


def _proof(tmp_path, taps, rng):
    for c in ("TT", "FF"):
        (tmp_path / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(corner=c, cppr_node_range_ps=rng, taps=taps)))
    return tmp_path


def _row():
    # landed_phase_ocv row: d 260, derated [240, 280] -> both sample edges clean; the static order picks rise (240 > 136.5)
    return dict(port="ab", src="a", dst="b", d_ps=260.0, p_up_ps=20.0, p_dn_ps=20.0, unshared_a_ps=0.0, unshared_b_ps=0.0,
                margin_ps=0.0)


def _sta_start_row(rows, taps, rng):
    s, out, regs = CAP.plan(rows, T, AP, 0.0, 26.5, 0, None, SKEW)
    s.update(period_ps=T, aperture_ps=AP, sync_aperture_ps=26.5, pad=0)
    b = CB.bind(CB.plan_doc(s, out, regs))
    ca = D.count_align_landed([("pa", "pb", "a->b")], {t["port"]: t for t in taps}, b, T, REG, cppr_range=rng)
    return regs, ca["start_skew"]["rows"][0]


def test_planner_uses_sta_interval_start_edge_clears_ap_on_sta_numbers(tmp_path):
    # capture tap b has a wide late-early (the STA interval [Eb - La, Lb - Ea] = [50, 300] is wider than the plan row)
    taps = [dict(port="pa", part="a", late_ps=1000.0, early_ps=960.0, cppr_node="ra", slew_ps=10.0),
            dict(port="pb", part="b", late_ps=1260.0, early_ps=1050.0, cppr_node="rb", slew_ps=10.0)]
    rng = {"h": 0.0}
    plan = dict(ports=[dict(id="ab", src=dict(part="a"), dst=dict(part="b"), width=1)])
    sta = D.sta_d_intervals(_proof(tmp_path, taps, rng), plan, ("TT", "FF"), "none", False)
    assert sta["TT"]["a->b"] == (50.0, 300.0)
    # old planner (own rows only): rise, and the STA's skewed interval [-10, 250] crosses the rise boundary -> start FAIL
    regs, st = _sta_start_row([_row()], taps, rng)
    assert regs[1]["start_from"]["edge"] == "rise" and st["sta_sync_dist_ps"] < AP and not st["ok"]
    # one interval model: hull -> rise is ambiguous on [50, 300] +- ap, fall is clean and keeps >= ap on STA numbers
    rows = [_row()]
    info = CAP.sta_hull(rows, sta)
    assert info["widened"] == 1 and info["missing"] == 0 and rows[0]["p_dn_ps"] == 210.0 and rows[0]["p_up_ps"] == 40.0
    regs, st = _sta_start_row(rows, taps, rng)
    assert regs[1]["start_from"]["edge"] == "fall" and regs[1]["start_from"]["sync_values"] == 1
    assert st["ok"] and st["sta_sync_dist_ps"] >= AP


def test_count_align_interval_takes_cppr_at_last_common_node():
    # 12.4b: the common path's late-early cancels in d; with --cppr-lca + tree_path the credit is the LCA range
    taps = {"pa": dict(late_ps=1000.0, early_ps=900.0, cppr_node="ra", tree_path="hAB"),
            "pb": dict(late_ps=1300.0, early_ps=1200.0, cppr_node="rb", tree_path="hAC")}
    rng = {"h": 0.5, "hA": 80.0}
    old = D.CPPR_LCA
    try:
        D.CPPR_LCA = False
        assert D.count_align_d_intervals([("pa", "pb", "a->b")], taps) == {"a->b": (200.0, 400.0)}
        assert D.count_align_d_intervals([("pa", "pb", "a->b")], taps, rng) == {"a->b": (200.5, 399.5)}
        D.CPPR_LCA = True
        assert D.count_align_d_intervals([("pa", "pb", "a->b")], taps, rng) == {"a->b": (280.0, 320.0)}
    finally:
        D.CPPR_LCA = old


def _region_bind(named=True):
    """region R1 = {a, a2}, R2 = {b, b2}; two rings: a->b (K planned on a->b) and a2->b2 (a later-phase pair)."""
    mk = lambda s, d, dlo: dict(src="R1", dst="R2", depth=4, K=1, L_lo_ps=600.0, L_hi_ps=1000.0, d_lo_ps=dlo,
                                d_hi_ps=dlo + 100.0, **(dict(src_part=s, dst_part=d) if named else {}))
    return dict(ports={"p_ab": mk("a", "b", 200.0), "p_a2b2": mk("a2", "b2", 150.0)},
                parts={p: dict(region=r) for p, r in (("a", "R1"), ("a2", "R1"), ("b", "R2"), ("b2", "R2"))})


def _region_taps():
    t = lambda p, part, late, early: dict(port=p, part=part, late_ps=late, early_ps=early, cppr_node="r" + part,
                                          slew_ps=10.0)
    return {x["port"]: x for x in (t("pa", "a", 1000.0, 1000.0), t("pb", "b", 1200.0, 1200.0),
                                   t("pa2", "a2", 1000.0, 1000.0), t("pb2", "b2", 1150.0, 1150.0))}


def test_region_key_times_a_partition_named_port_on_its_own_pair_as_the_planner():
    """FLOW-GEN-1 10-28 (DIE-KV-11 phy edge columns): plan (sta_hull on src_part->dst_part) and gate agree per port."""
    taps, landed = _region_taps(), [("pa", "pb", "a->b"), ("pa2", "pb2", "a2->b2")]
    sta = {"FF": D.count_align_d_intervals(landed, taps)}
    rows = [dict(port=p, src="R1", dst="R2", src_part=s, dst_part=d, d_ps=dlo, p_up_ps=0.0, p_dn_ps=0.0)
            for p, s, d, dlo in (("p_ab", "a", "b", 200.0), ("p_a2b2", "a2", "b2", 150.0))]
    CAP.sta_hull(rows, sta)
    plan_lo = {r["port"]: r["d_ps"] - r["p_dn_ps"] for r in rows}
    ca = D.count_align_landed(landed, taps, _region_bind(), T, REG, key="region")
    gate = {r["port"]: r["L_lo_ps"] - 600.0 + _region_bind()["ports"][r["port"]]["d_lo_ps"] for r in ca["rows"]}
    assert plan_lo == gate == {"p_ab": 200.0, "p_a2b2": 150.0}
    assert all(r["interval_key"] == "part" for r in ca["rows"]) and ca["unbound"] == 0
    # control: a bind naming no partition pair keeps the pooled region interval (min over both pairs, unchanged)
    pooled = D.count_align_landed(landed, taps, _region_bind(named=False), T, REG, key="region")
    assert {r["port"]: r["L_lo_ps"] for r in pooled["rows"]} == {"p_ab": 550.0, "p_a2b2": 600.0}


def test_region_key_unnamed_landed_partition_pair_fails_closed():
    taps = _region_taps()
    landed = [("pa", "pb", "a->b"), ("pa2", "pb2", "a2->b2"), ("pa", "pb2", "a->b2")]   # a->b2 has no ring
    ca = D.count_align_landed(landed, taps, _region_bind(), T, REG, key="region")
    assert ca["unbound_tags"] == ["a->b2"] and ca["verdict"] == "FAIL"
