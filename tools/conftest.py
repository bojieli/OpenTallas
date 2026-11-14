"""tools/ pytest preconditions (PROFILE-1 2026-11-13).

The sign-off profile switch OT_SIGNOFF_PROFILE defaults to 'minimal' (R-MINIMAL, OWNER 11-13: only DRC 0, TT setup,
internal FF hold and bind/latency block).  The suites written before it assert the legacy gates (preflight, visual,
LEC, path gate, io_hold_parent, ...), so every test runs with the legacy profile unless it sets or deletes the variable
itself; tools/die_plan/test_signoff_profile.py covers the minimal profile and its legacy fallback."""
import pytest


@pytest.fixture(autouse=True)
def _legacy_signoff_profile_default(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")
