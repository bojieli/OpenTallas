"""WF-1 11-14: item@N releases exactly once when attempt N is the latest and ended, whatever the key's first-seen age."""
import kit_wave as K


def rec(item, n, started, status="FAIL", q=None, die="s81"):
    return {"die": die, "item": item, "attempt": n, "started": started, "status": status, "q_status": q}


def run(retry, items, seen=None):
    cfg = {"dies": {"s81": {"event": "ev", "retry": list(retry)}}}
    st = {"items": {f"k{i}": r for i, r in enumerate(items)}, "retry_seen": dict(seen or {})}
    logs = []
    dropped = K.prune_stale_retries(cfg, st, log=logs.append, now=1000.0)
    return cfg["dies"]["s81"]["retry"], dropped, logs, st


def test_old_first_seen_does_not_drop_a_key_for_an_ended_latest_attempt():
    # attempt 2 launched (t=500) AFTER the key was first seen (t=100): the old rule dropped it
    kept, dropped, logs, _ = run(["lepe@2"], [rec("lepe", 1, 10), rec("lepe", 2, 500)], seen={"s81|ev|lepe@2": 100.0})
    assert kept == ["lepe@2"] and not dropped
    assert any("RETRY-RELEASE s81/lepe@2" in m for m in logs)


def test_consumed_once_the_relaunch_exists():
    kept, dropped, logs, _ = run(["lepe@2"], [rec("lepe", 2, 500), rec("lepe", 3, 900, status="RUNNING")])
    assert kept == [] and dropped == {"s81": ["lepe@2"]}
    assert any("RETRY-IGNORED s81/lepe@2" in m and "consumed" in m for m in logs)


def test_running_latest_attempt_keeps_the_key_without_a_release_line():
    kept, _, logs, _ = run(["bk_sel@4"], [rec("bk_sel", 4, 500, status="RUNNING")])
    assert kept == ["bk_sel@4"] and not logs


def test_future_attempt_key_is_kept():
    kept, _, _, _ = run(["x@5"], [rec("x", 2, 500)])
    assert kept == ["x@5"]


def test_cancelled_and_enqueued_queue_fail_count_as_ended():
    assert run(["a@1"], [rec("a", 1, 5, status="CANCELLED")])[0] == ["a@1"]
    assert run(["b@1"], [rec("b", 1, 5, status="ENQUEUED", q="FAIL")])[0] == ["b@1"]
    assert run(["c@1"], [rec("c", 1, 5, status="ENQUEUED", q="RUNNING")])[2] == []


def test_release_is_logged_once_per_item_and_attempt():
    cfg = {"dies": {"s81": {"event": "ev", "retry": ["lepe@2"]}}}
    st = {"items": {"k": rec("lepe", 2, 500)}}
    logs = []
    K.prune_stale_retries(cfg, st, log=logs.append, now=1.0)
    cfg["dies"]["s81"]["retry"] = ["lepe@2"]
    K.prune_stale_retries(cfg, st, log=logs.append, now=2.0)
    assert sum("RETRY-RELEASE" in m for m in logs) == 1
