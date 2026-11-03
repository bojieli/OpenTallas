import head_xing_table as X

PLAN = dict(partitions=[dict(name="a", type="TA"), dict(name="b", type="TB"), dict(name="s", type="TS")],
            ports=[dict(id="p0", src=dict(part="a"), dst=dict(part="b"), width=8, kind="data"),
                   dict(id="p1", src=dict(part="a"), dst=dict(part="s"), width=4, kind="data")],
            lanes=[dict(id="L0", ports=["p1", "p0"])],
            latency=dict(lanes=dict(L0=dict(cycles=5, clock_landing=3))))
CA = {c: {"p0": dict(margin_lo_ps=200.0, margin_hi_ps=600.0)} for c in ("TT", "FF")}


def test_forms_and_cycles():
    t = X.build(PLAN, CA, {"p0": 3}, dict(lanes=dict(L0=dict(cycles=1, reason="split")), ports=dict(p0=dict(cycles=2, reason="face"))))
    f = {p["port"]: p["form"] for p in t["ports"]}
    assert f == {"p0": "landed_ca", "p1": "seam_latch"}
    assert t["lanes"]["L0"]["total_cycles"] == 8 and t["lanes"]["L0"]["added_cycles"] == 3
    assert t["summary"]["by_form"]["landed_ca"] == dict(ports=1, bits=8)
    assert t["summary"]["ca_worst_lo_ps"]["TT"] == 200.0


def test_no_added_keeps_plan_cycles():
    t = X.build(PLAN, CA, {}, None)
    assert t["lanes"]["L0"]["total_cycles"] == 5 and t["summary"]["added_cycles_total"] == 0
