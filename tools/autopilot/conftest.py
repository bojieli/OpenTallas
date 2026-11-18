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
