"""OLDPLAN-NOREAP-1124 (COORD urgent, KV-ALLFIX hub b27c53f1): KV D29 kv3_hroot@1, launched 08:25 and past synthesis, was held SKIP-OLDPLAN at the route enqueue
(09:32) and the retire pass turned that hold into CANCELLED / SUPERSEDED, so REAP stopped it (09:33).  OWNER 11-19: an old-plan kit that can still sign is never cancelled by the wave."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

CFG = {"stops_off": True, "dies": {"qwen_kvsys": {"event": "KV-A5t3", "enabled": True, "plan": "p", "gen_host": "h"},
                "hbm": {"event": "E2", "enabled": True, "plan": "q", "gen_host": "h"}}}
ST = {"plans": {"h:p|KV-A5t3": {"blocks": {"kv3_hroot": "NEW"}}, "h:q|E2": {"blocks": {"hb": "NEW"}}}}


def row(die="qwen_kvsys", item="kv3_hroot", **k):
    return dict({"die": die, "item": item, "event": "KV-D29" if die == "qwen_kvsys" else "E1", "attempt": 1, "block_sha": "OLD", "status": "PASS", "stage": "place"}, **k)


def test_past_synthesis_old_plan_row_routes(monkeypatch):
    monkeypatch.setattr(KW, "_plan_current", lambda cfg, st, rec: False)    # its block really changed on the new event
    assert KW.enqueue_skip_reason(CFG, row(), ST) is None


def test_old_plan_route_hold_is_never_cancelled_and_routes_on_the_next_pass(monkeypatch):
    monkeypatch.setattr(KW, "_plan_current", lambda cfg, st, rec: False)
    r = row(status="ROUTE-HELD", route_hold="SKIP-OLDPLAN: attempt of plan event KV-D29, the die's current plan event is KV-A5t3")
    st = dict(ST, items={"k": r})
    KW.retire_superseded_rows(None, CFG, st, now=1.0)
    assert r["status"] == "ROUTE-HELD" and "retire" not in r


def test_parked_hbm_keeps_the_old_rule(monkeypatch):
    monkeypatch.setattr(KW, "_plan_current", lambda cfg, st, rec: False)
    assert KW.enqueue_skip_reason(CFG, row("hbm", "hb"), ST)[0] == "SKIP-OLDPLAN"
    r = row("hbm", "hb", status="ROUTE-HELD", route_hold="SKIP-OLDPLAN: x")
    KW.retire_superseded_rows(None, CFG, dict(ST, items={"k": r}), now=1.0)
    assert r["status"] == "CANCELLED"
