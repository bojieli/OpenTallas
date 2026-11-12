"""KW-FIX-45 11-11: removing a retry entry forgets its first-seen time, so re-adding it is a fresh release."""
import kit_wave as KW


def cfg(retry):
    return {"dies": {"qwen_compute": {"event": "hcut1111", "retry": list(retry)}}}


def state(started):
    return {"items": {"k": {"die": "qwen_compute", "item": "x", "attempt": 2, "started": started}}}


def test_entry_first_seen_before_the_attempt_started_is_stale():
    st = state(1000.0)
    st["retry_seen"] = {"qwen_compute|hcut1111|x@2": 500.0}
    c = cfg(["x@2"])
    assert KW.prune_stale_retries(c, st, now=2000.0) == {"qwen_compute": ["x@2"]} and c["dies"]["qwen_compute"]["retry"] == []


def test_remove_then_readd_across_a_pass_releases_again():
    st = state(1000.0)
    st["retry_seen"] = {"qwen_compute|hcut1111|x@2": 500.0}
    KW.prune_stale_retries(cfg(["y@1"]), st, now=2000.0)                      # pass without the entry: first-seen forgotten
    assert "qwen_compute|hcut1111|x@2" not in st["retry_seen"]
    c = cfg(["x@2", "y@1"])
    assert KW.prune_stale_retries(c, st, now=3000.0) == {} and "x@2" in c["dies"]["qwen_compute"]["retry"]
    assert st["retry_seen"]["qwen_compute|hcut1111|x@2"] == 3000.0


def test_die_without_a_retry_list_wipes_nothing():
    st = state(1000.0)
    st["retry_seen"] = {"qwen_compute|hcut1111|x@2": 500.0}
    KW.prune_stale_retries(cfg([]), st, now=2000.0)
    assert st["retry_seen"] == {"qwen_compute|hcut1111|x@2": 500.0}
