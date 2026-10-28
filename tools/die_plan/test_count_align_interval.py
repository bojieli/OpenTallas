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
        (tmp_path / f"tap_arrivals_{c}.json").write_text(json.dumps(dict(corner=c, cppr_node_range_ps=rng, taps=taps, clock_cell="buf")))
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
    # FLOW-ONEMODEL-1: the per-port interval (the gate's function) with the MEASURED fall arrival (50 % duty here)
    ftaps = [dict(t, fall_late_ps=t["late_ps"], fall_early_ps=t["early_ps"]) for t in taps]
    ports, pr = CAP.row_ports([_row()])
    sta = D.sta_port_intervals(_proof(tmp_path, ftaps, rng), plan, ("TT", "FF"), ports, pr, fall=True)
    assert sta["TT"]["rise"]["ab"] == (50.0, 300.0) and sta["TT"]["fall"]["ab"] == (50.0, 300.0)
    # one interval model: hull -> rise is ambiguous on [50, 300] +- ap, fall is clean and keeps >= ap on STA numbers
    rows = [_row()]
    info = CAP.sta_hull(rows, sta)
    assert info["widened"] == 1 and info["missing"] == 0 and rows[0]["p_dn_ps"] == 210.0 and rows[0]["p_up_ps"] == 40.0
    regs, st = _sta_start_row(rows, ftaps, rng)
    assert regs[1]["start_from"]["edge"] == "fall" and regs[1]["start_from"]["sync_values"] == 1
    assert st["ok"] and st["sta_sync_dist_ps"] >= AP
    # rise-only proof: the planner may not assume fall = rise + T/2 -> rise (ambiguous), and the gate fails a fall
    # sample closed; plan and gate agree that this start edge is not clean
    rows = [_row()]
    CAP.sta_hull(rows, D.sta_port_intervals(_proof(tmp_path, taps, rng), plan, ("TT", "FF"), ports, pr, fall=True))
    assert rows[0]["fall_lo"] is None
    regs, st = _sta_start_row(rows, taps, rng)
    assert regs[1]["start_from"]["edge"] == "rise" and regs[1]["start_from"]["sync_values"] > 1


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
