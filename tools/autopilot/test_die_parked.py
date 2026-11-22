"""F4 (FLOW-OPS-R2 11-22, FABLE-FLOW-0000): dies.<die>.parked is honoured by the wave gate, TOOLS-LAG and the adopt guard."""
import json, subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent))
import kit_wave as KW  # noqa: E402
import tools_lag as TL  # noqa: E402

PK = {"owner": "COORD", "since": "2026-11-21", "reason": "HBM parked (separate target)"}


def test_gate_says_parked_and_unpark_rearms():
    cfg = {"dies": {"hbm": {"enabled": True, "coord_enable": True, "event": "x", "parked": PK}}}
    ok, why = KW.gate(cfg, "hbm")
    assert not ok and why.startswith("DIE-PARKED owner COORD since 2026-11-21")
    cfg["dies"]["hbm"].pop("parked")
    assert not KW.gate(cfg, "hbm")[1].startswith("DIE-PARKED")


def test_tools_lag_skips_parked(monkeypatch):
    seen = []
    monkeypatch.setattr(TL, "lag", lambda repo, pin, ref, rulings=None: seen.append(pin) or {"n_commits": 0})
    monkeypatch.setattr(TL, "pin_of", lambda d: d["src"])
    out = TL.measure({"dies": {"hbm": {"enabled": True, "src": "a", "parked": PK}, "s81": {"enabled": True, "src": "b"}}})
    assert list(out) == ["s81"] and seen == ["b"]


def test_adopt_guard_plan_only_skips_parked(tmp_path):
    cfg = tmp_path / "kw.json"
    cfg.write_text(json.dumps({"dies": {"hbm": {"enabled": True, "plan": "/nonexistent/die_plan.json", "plan_sha256": "ab" * 32, "parked": PK}}}))
    r = subprocess.run([sys.executable, "-I", str(H / "adopt_guard.py"), "hbm", "--config", str(cfg), "--plan-only"], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "DIE-PARKED hbm" in r.stdout and "PLAN_MISSING" not in r.stdout + r.stderr
