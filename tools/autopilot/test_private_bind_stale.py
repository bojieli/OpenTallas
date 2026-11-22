"""KIT-TOPO-STALE-1122 (FLOW-OPS-R2, COORD): private-spec refuses in seconds a plan paired with a bind made from another plan."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

SP = {"kind": "type", "src": "/t", "plan": "/t/plan.json", "gen_host": "epyc9", "gen_env": {"OT_NATIVE_RESET_SCOPE": "selected"},
      "kit_rtl": {"mode": "bind", "bind_out": "/t/bind", "asbuilt": "/t/ab.json"}}


def test_stale_refused_with_reason():
    seen = []
    rpy = lambda h, code, g, timeout: seen.append((h, g)) or {"stale": ["kv3_pc_v3"]}  # noqa: E731
    v, why = KW.private_bind_stale(SP, "kv3_pc_v3", rpy)
    assert v == "STALE" and "made from another plan" in why and "--bind-out" in why
    assert seen[0][0] == "epyc9" and seen[0][1]["types"] == ["kv3_pc_v3"] and seen[0][1]["scope"] == "selected"


def test_relay_stale_names_rows_and_green_passes_and_unknown():
    v, why = KW.private_bind_stale(SP, "x", lambda *a, **k: {"stale": ["x"], "relay": {"x": "relay_depth row r3"}})
    assert v == "STALE" and "relay_depth row r3" in why
    assert KW.private_bind_stale(SP, "x", lambda *a, **k: {"stale": []}) == ("", "")
    assert KW.private_bind_stale(SP, "x", lambda *a, **k: {"error": "ssh"})[0] == "UNKNOWN"


def test_not_bind_mode_not_probed():
    boom = lambda *a, **k: 1 / 0  # noqa: E731
    assert KW.private_bind_stale(dict(SP, kit_rtl={"mode": "script"}), "x", boom) == ("", "")
    assert KW.private_bind_stale(dict(SP, kind="core"), "x", boom) == ("", "")
