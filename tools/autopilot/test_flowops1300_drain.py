"""FLOW-OPS-1300 (FABLE-FLOW-1240 d): a wave unit's drain read is re-taken after DRAIN_TTL_S (was once per run: slice_station__t45 a9 failed 40 min after an undrain),
and an all-draining refusal waits with fresh reads, then ends INFRA DRAIN-WAIT (not a FLOW fail counted in the caps)."""
import inspect
import kit_wave as KW


def test_drain_ttl_and_fresh_reread_before_refusal():
    assert KW.DRAIN_TTL_S <= 60 and KW.DRAIN_WAIT_N >= 1
    src = inspect.getsource(KW)
    assert 'time.time() - _drc.get("t", 0) > DRAIN_TTL_S' in src and "read once per run\"\"\"" not in src
    assert "_dr = stage_drain(fresh=True)" in src


def test_drain_wait_refusal_is_infra():
    cls = KW.classify("place", "RuntimeError: INFRA DRAIN-WAIT: heavy stage refused: every target host is draining (epyc7, epyc9, intel1) after 3 fresh re-reads 10 min apart")
    assert cls[0] == "INFRA", cls
