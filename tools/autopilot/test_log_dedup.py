"""FLOW-HEALTH-1 11-15 (FABLE-FLOW-1000 class 10): repeated autopilot log lines are suppressed"""
import autopilot as AP


def test_repeat_suppressed_then_counted():
    AP._LOG_SEEN.clear()
    assert AP.log_dedup("x", now=0) == "x"
    assert AP.log_dedup("x", now=10) is None
    assert AP.log_dedup("x", now=20) is None
    assert AP.log_dedup("y", now=30) == "y"
    assert AP.log_dedup("x", now=AP.LOG_DEDUP_S + 1) == "x (+2 identical suppressed)"
    assert AP.log_dedup("x", now=AP.LOG_DEDUP_S + 2) is None


def test_off_by_env_value_zero():
    AP._LOG_SEEN.clear()
    old, AP.LOG_DEDUP_S = AP.LOG_DEDUP_S, 0
    try:
        assert AP.log_dedup("x", now=0) == "x" and AP.log_dedup("x", now=1) == "x"
    finally:
        AP.LOG_DEDUP_S = old
