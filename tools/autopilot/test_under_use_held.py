"""FABLE-FLOW-0230 U1: SKIP-HELD / WAIT-FORM rows split by hold key with owner, eta and age; ownerless / overdue / old no-eta keys flagged."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import under_use as UU      # noqa: E402

NOW = time.mktime(time.strptime("2026-11-22 03:00", "%Y-%m-%d %H:%M"))
CFG = {"dies": {"s81": {"lane": "FIX-SYNC-S81", "event": "J8", "hold_items": {
    "hd_*": "plan event J8 pending owner=S81-PLAN eta=2026-11-22 01:00",
    "col_*": "KV-PLAN-R6 hold 11-21 19:1x"}}}}


def rows():
    r = {}
    for i in range(3):
        r[f"a{i}"] = {"die": "s81", "item": f"hd_x{i}", "status": "ENQUEUED", "event": "J8", "updated": NOW - 5 * 3600}
    r["b"] = {"die": "s81", "item": "col_t1", "status": "ROUTE-HELD", "event": "J8", "updated": NOW - 30 * 3600,
              "route_hold": "SKIP-HELD: item held (col_*): KV-PLAN-R6 hold 11-21 19:1x"}
    r["c"] = {"die": "s81", "item": "slice_t2", "status": "ROUTE-HELD", "event": "J8", "updated": NOW - 2 * 3600,
              "route_hold": "WAIT-FORM: visual verdict BAD for this attempt"}
    r["old"] = {"die": "s81", "item": "hd_y", "status": "ENQUEUED", "event": "J7", "updated": NOW}     # superseded event: not held
    return r


def test_held_detail_keys_owner_age_flags():
    d = {(x["bucket"], x["key"]): x for x in UU.held_detail(rows(), CFG, now=NOW)}
    hd = d[("SKIP-HELD", "hd_*")]
    assert hd["n"] == 3 and hd["owner"] == "S81-PLAN" and hd["age_h"] == 5.0 and hd["flags"] == ["OVERDUE"]
    col = d[("SKIP-HELD", "col_*")]
    assert col["n"] == 1 and col["flags"] == ["NO-OWNER", "NO-ETA>24h"]
    wf = [x for x in d.values() if x["bucket"] == "WAIT-FORM"][0]
    assert wf["n"] == 1 and "FIX-SYNC-S81" in wf["owner"] and wf["flags"] == []


def test_held_line_prints_each_key():
    ln = UU.held_line(UU.held_detail(rows(), CFG, now=NOW))
    assert ln.startswith("UNDER-USE HELD SKIP-HELD 4: ") and "s81/hd_* 3 [owner S81-PLAN, 5.0 h" in ln and "FLAGGED OVERDUE" in ln
    assert "WAIT-FORM 1:" in ln and ln.endswith("flagged keys 2")
    assert UU.held_line([]) == "UNDER-USE HELD none"
