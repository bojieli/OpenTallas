"""WAVE-PILOT-FIX 11-18: the code default is stops_off ON (flow_guard.STOPS_OFF_DEFAULT = True).  The existing wave tests build configs without the key and exercise the
legacy hold / breaker / pilot / dedupe / probe paths (still live for hbm and for stops_off false), so they run with the default OFF; test_stops_default.py checks the
real default."""
import pytest

import flow_guard


@pytest.fixture(autouse=True)
def _legacy_stops_default(monkeypatch, request):
    if request.module.__name__ in ("test_stops_default",):
        return
    monkeypatch.setattr(flow_guard, "STOPS_OFF_DEFAULT", False)


@pytest.fixture(autouse=True)
def _no_real_host_verify(monkeypatch, request):
    """SNAP-RO-1119 (c): apply_marker proves the tree on every gen host over ssh; the existing apply tests use fake hosts.  test_snap_ro_1119.py exercises the real function with a fake runner."""
    import apply_reviewed_tree_marker as _A
    if request.module.__name__ == "test_snap_ro_1119":
        return
    monkeypatch.setattr(_A, "verify_tree_on_all_hosts", lambda *a, **k: ({}, {}))


@pytest.fixture(autouse=True)
def _no_bind_stamp_ssh(monkeypatch):
    """T1 (WAVE-OPS-R1): rt_tools_fields reads the bind's stamp over ssh; a test never does (tests inject BIND_STAMP_LOADER)"""
    import kit_wave as _KW
    monkeypatch.setattr(_KW, "BIND_STAMP_LOADER", lambda cfg, die, bind_out: None)
