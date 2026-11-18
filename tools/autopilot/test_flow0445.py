"""FLOW-HEALTH-1 11-16 (FABLE-FLOW-0445 #3 #5 + config-key reader check)"""
import time

import kit_wave as KW

MISS = "FLOW: no RTL header for blackbox @gen: ValueError: header /srv/x/src/rtl/hdr_a.svh missing for blackbox y"


def cfg(overlay="o1"):
    return {"dies": {"qwen_kvsys": {"src_sha": "s", "_src_overlay": overlay, "_plan_sha": "p", "event": "e", "enabled": True, "gen_host": "h"}}}


def rec(item="kv3_pv_v1"):
    return {"die": "qwen_kvsys", "item": item, "block_sha": "b", "stage": "gen"}


def test_3_overlay_change_that_does_not_touch_the_read_files_is_no_release(monkeypatch):
    sha = {"/srv/x/src/rtl/hdr_a.svh": "aaa"}
    monkeypatch.setattr(KW, "file_sha", lambda c, d, p, **k: sha.get(p, ""))
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "FLOW", MISS)
    assert st["fail_keys"]["qwen_kvsys|kv3_pv_v1"]["read_sha"] == {"/srv/x/src/rtl/hdr_a.svh": "aaa"}
    bl, why, chg = KW.fail_key_gate(cfg(overlay="o2"), st, "qwen_kvsys", "kv3_pv_v1", "b")      # another lane edited something else in the overlay
    assert bl and chg == []
    sha["/srv/x/src/rtl/hdr_a.svh"] = "bbb"                                                       # the file the stage read changed
    assert KW.fail_key_gate(cfg(overlay="o2"), st, "qwen_kvsys", "kv3_pv_v1", "b")[2] == ["read-file"]


def test_3_no_file_named_keeps_the_overlay_rule(monkeypatch):
    monkeypatch.setattr(KW, "file_sha", lambda *a, **k: "")
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "INFRA", "INFRA: tool or source skew @gen: AttributeError: module x has no attribute y")
    assert KW.fail_key_gate(cfg(overlay="o2"), st, "qwen_kvsys", "kv3_pv_v1", "b")[2] == ["overlay"]


class AP:
    def __init__(self):
        self.logs, self.q = [], []

    def log(self, m):
        self.logs.append(m)

    def coord_append(self, rel, line):
        self.q.append(line)


def test_5_dedup_release_is_logged_once_and_the_member_waits_for_its_owner(monkeypatch, tmp_path):
    ap = AP()
    ap.AP_DIR, ap.DRY = tmp_path, False
    st = {"items": {"d|own|e|b": {"die": "d", "item": "col_a__t1__clx__pv11111111", "status": "FAIL", "class": "FLOW", "q_status": None, "updated": 5, "attempt": 3},
                    "d|mem|e|b": {"die": "d", "item": "col_a__t1__cly__pv22222222", "status": "DEDUP", "dedup_owner": "col_a__t1__clx__pv11111111"}}}
    monkeypatch.setattr(KW, "fail_key_gate", lambda *a, **k: (False, "", []))
    c = {"dies": {"d": {"enabled": True, "event": "e", "kit_dedup": ["col_*"]}}}     # S81-COL-FLOW-1118: dedup is opt-in now
    for _ in range(3):                                   # the member is re-created as DEDUP each tick (it relaunches into the same identity)
        st["items"]["d|mem|e|b"] = {"die": "d", "item": "col_a__t1__cly__pv22222222", "status": "DEDUP", "dedup_owner": "col_a__t1__clx__pv11111111"}
        KW.dedup_step(ap, c, st, {}, str(tmp_path))
    assert len([m for m in ap.logs if "DEDUP RELEASE" in m]) == 1
    # the launch gate holds the member while the owner's state is unchanged
    monkeypatch.setattr(KW, "scheduler_current", lambda a: True)
    monkeypatch.setattr(KW, "tool_skew_refuse", lambda *a, **k: False, raising=False)
    assert KW.launch(ap, c, st, "d", {"item": "col_a__t1__cly__pv22222222", "block_sha": "b"}, "hub") is None
    assert len([m for m in ap.logs if "LAUNCH-HELD" in m and "DEDUP terminal" in m]) == 1
    KW.launch(ap, c, st, "d", {"item": "col_a__t1__cly__pv22222222", "block_sha": "b"}, "hub")
    assert len([m for m in ap.logs if "DEDUP terminal" in m]) == 1                       # logged once
    st["items"]["d|own|e|b"]["attempt"] = 4                                              # the owner moved on: the hold ends
    assert "d|col_a__t1__cly__pv22222222" in st["dedup_released"]
    try:
        KW.launch(ap, c, st, "d", {"item": "col_a__t1__cly__pv22222222", "block_sha": "b"}, "hub")
    except Exception:
        pass                                                                             # launch proceeds past the gate (needs a real hub); the ledger entry is gone
    assert "d|col_a__t1__cly__pv22222222" not in st.get("dedup_released", {})


def test_5_retry_infra_rows_get_a_name():
    ap = AP()
    now = 100000.0
    c = {"dies": {"s81": {"event": "e2", "enabled": True}}}
    st = {"items": {"a": {"die": "s81", "item": "old", "status": "RETRY-INFRA", "event": "e1", "updated": now - 9999},
                    "b": {"die": "s81", "item": "nohost", "status": "RETRY-INFRA", "event": "e2", "updated": now - 9999, "no_host_at": 5},
                    "c": {"die": "s81", "item": "young", "status": "RETRY-INFRA", "event": "e2", "updated": now - 10},
                    "d": {"die": "s81", "item": "plain", "status": "RETRY-INFRA", "event": "e2", "updated": now - 9999}}}
    out = KW.name_stuck_retry_infra(ap, c, st, now=now)
    assert st["items"]["a"]["status"] == "CANCELLED" and st["items"]["a"]["retry_stop"] == "SUPERSEDED"
    assert st["items"]["b"]["retry_stop"] == "NO-HOST" and "retry_stop" not in st["items"]["c"] and st["items"]["d"]["retry_stop"] == "UNEXPLAINED"
    assert out == {"SUPERSEDED": 1, "NO-HOST": 1, "UNEXPLAINED": 1}
    n = len(ap.logs)
    KW.name_stuck_retry_infra(ap, c, st, now=now + 600)
    assert len(ap.logs) == n                                                          # named once, no repeat line


def test_config_key_with_no_reader_is_found_and_posted_once():
    c = {"dies": {"s81": {"enabled": True, "src": "/x", "gen_host": "h", "flow_guard_budget_s": 25, "grt_halving_off_zzz": 1, "note_x": "n"}}}
    assert KW.unread_config_keys(c) == {"s81": ["grt_halving_off_zzz"]}
    ap, st = AP(), {}
    KW.config_key_check(ap, c, st)
    KW.config_key_check(ap, c, st)
    assert len(ap.q) == 1 and "grt_halving_off_zzz" in ap.q[0] and len([m for m in ap.logs if "CONFIG-KEY-UNREAD" in m]) == 1
