"""FLEET-WATCH-R5 11-21 (COORD): a pending visual verdict and stale-for-review are advisory (route proceeds) on every die except parked hbm."""
import kit_wave as K


def cfg(die):
    return {"dies": {die: {"event": "J", "review_before_route": {"event": "J", "all_items": True}}}, "visual_gate": "route", "stops_off": False}


def row(die):
    return {"die": die, "event": "J", "item": "t1", "attempt": 1, "kit": "epyc9:/k", "status": "PASS", "kind": "type"}


def test_pending_verdict_is_advisory_except_hbm(monkeypatch):
    monkeypatch.setattr(K, "exact_kit_visual_verdict", lambda rec: None)
    monkeypatch.setattr(K, "visual_verdicts", lambda: {})
    r = row("s81")
    assert K.route_hold_reason(cfg("s81"), r) is None and r["visual_pending"].startswith("WAIT-VISUAL (advisory)")
    h = row("hbm")
    assert K.route_hold_reason(cfg("hbm"), h).startswith("WAIT-VISUAL") and "visual_pending" not in h


def test_stale_for_review_is_advisory_except_hbm(monkeypatch):
    monkeypatch.setattr(K, "stale_visual_why", lambda cfg, rec, t0: "built on plan X")
    monkeypatch.setattr(K, "visual_gate_t0", lambda cfg: 0)
    monkeypatch.setattr(K.subprocess, "run", lambda *a, **k: None)
    s = dict(row("s81"), status="ROUTE-HELD", route_hold="WAIT-VISUAL: x")
    h = dict(row("hbm"), status="ROUTE-HELD", route_hold="WAIT-VISUAL: x")
    K.visual_queue_publish({"dies": {}, "visual_gate": "route"}, {"items": {"s": s, "h": h}})
    assert s["route_hold"] == "WAIT-VISUAL: x" and s["visual_pending"].startswith("WAIT-VISUAL (advisory): stale for review")
    assert h["route_hold"].startswith("WAIT-FORM: stale for review")
