"""FABLE-FLOW-0000 F7: signed-but-uncounted rows alert after 2 h, naming the missing gate."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uncounted_signed as US  # noqa: E402

REVOKED = ("# header\n"
           "head\thd_turn_a\tsha256:c7\tmeasured real-parent FAIL\t2026-11-03 23:2x PST\n"
           "s81\tslice_station__t52\tsha256:69\tPENDING-LEC: signed 11-21 by the R-MINIMAL chain, routed LEC never run\t2026-11-21 PST\n")
CACHE = {"plans": {"qwen_compute/plan_of_record/p.json": {"die": "qwen_compute", "pending_archive_types": {
    "sle_hc0__cl92": ["epyc7:/srv/x/signoff/signoff.json SIGNED-NO-TAG"],
    "slw_hc3__clccfc3e6b__pvcca9ff41": ["epyc2:/srv/x/signoff_eco_1795305239091771775/signoff.json src eb1e flow f"]}}}}


def test_revoked_pending_rows_name_the_gate():
    rows = US.rows_from_revoked(REVOKED)
    assert [(r["name"], r["gate"]) for r in rows] == [("slice_station__t52", "LEC")]       # a real revocation is not "pending"
    assert rows[0]["t"] == time.mktime(time.strptime("2026-11-21 00:00", "%Y-%m-%d %H:%M"))


def test_cache_pending_archive_rows():
    rows = {r["name"]: r for r in US.rows_from_cache(CACHE)}
    assert rows["sle_hc0__cl92"]["gate"].startswith("flow tag")
    assert rows["slw_hc3__clccfc3e6b__pvcca9ff41"]["gate"].startswith("archive key")
    assert abs(rows["slw_hc3__clccfc3e6b__pvcca9ff41"]["t"] - 1795305239.09) < 1


def test_spool_set_aside_skips_canaries(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"die": "qwen_kvsys", "name": "hub_x"}))
    (tmp_path / "a.json.reason").write_text(json.dumps({"reason": "rtx-pro export error: no space"}))
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "b.json.reason").write_text(json.dumps({"reason": "canary / test run, not a sign-off of record: /x"}))
    rows = US.rows_from_spool(tmp_path)
    assert [(r["die"], r["name"], r["gate"]) for r in rows] == [("qwen_kvsys", "hub_x", "export")]


def test_credited_replacement_and_done_export_are_not_alerted(tmp_path):
    rev = REVOKED + "qwen_compute\tsle_st_b_v2__cl14\tsha256:bf\tPENDING-LEC: never run\t2026-11-21 PST\n"
    cache = {"credited": [{"die": "qwen_compute", "name": "sle_st_b_v2__cl14", "ruling": "replaces revoked c7ce"}]}
    assert [r["name"] for r in US.rows_from_revoked(rev)] == ["slice_station__t52", "sle_st_b_v2__cl14"]
    assert [r["name"] for r in US.rows_from_revoked(rev, US.credited_names(cache))] == ["slice_station__t52"]
    (tmp_path / "a.json").write_text(json.dumps({"die": "qwen_kvsys", "name": "dp_kv3_hroot", "record": "935f"}))
    (tmp_path / "a.json.reason").write_text(json.dumps({"reason": "exported, rtx-pro has not verified it (spool age 2.2 h): /x"}))
    (tmp_path / "b.json").write_text(json.dumps({"die": "qwen_kvsys", "name": "hub_x", "record": "77aa"}))
    (tmp_path / "b.json.reason").write_text(json.dumps({"reason": "rtx-pro export error: no space"}))
    ledger = {"units": {"h:/a.odb": {"record": "935f", "state": "done"}, "h:/b.odb": {"record": "77aa", "state": "meta"}}}
    assert [r["name"] for r in US.rows_from_spool(tmp_path)] == ["dp_kv3_hroot", "hub_x"]
    assert [r["name"] for r in US.rows_from_spool(tmp_path, US.done_records(ledger))] == ["hub_x"]


def test_judge_alerts_once_after_two_hours_and_rearms():
    st = {}
    rows = [dict(die="s81", name="t52", gate="LEC", evidence="e", t=None)]
    due, new = US.judge(rows, st, 1000.0)
    assert due == [] and new == []                                   # first sight, no time named: clock starts now
    due, new = US.judge(rows, st, 1000.0 + 2.1 * 3600)
    assert [d["name"] for d in due] == ["t52"] and len(new) == 1 and due[0]["age_h"] == 2.1
    due, new = US.judge(rows, st, 1000.0 + 3 * 3600)
    assert len(due) == 1 and new == []                                # alerted once
    US.judge([], st, 1000.0 + 4 * 3600)                               # counted: state cleared
    assert st["alerted"] == {} and st["seen"] == {}
    due, new = US.judge([dict(rows[0], t=0.5)], st, 1000.0 + 5 * 3600)   # a named old time counts at once
    assert len(new) == 1


def test_render():
    out = US.render([dict(die="s81", name="t52", gate="LEC", age_h=20.7, evidence="PENDING-LEC")], 0)
    assert "| s81 | t52 | LEC | 20.7 h |" in out
