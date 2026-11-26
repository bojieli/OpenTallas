"""RESETPUB-SOLVE-DEFAULT-1125: publish_gate mirrors the PRE default and forwards only an explicit caller value."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_gate as PG  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
import plan_gate_pre as PGP  # noqa: E402

QC = "/t/physical/die_plan/qwen_compute/plan_of_record/p.json"
S81 = "/t/physical/die_plan/s81/plan_of_record/p.json"


def test_mirror_matches_pre():
    for plan in (QC, S81):
        for env in ({}, {"OT_RESETPUB_SOLVE": "0"}, {"OT_RESETPUB_SOLVE": "1"}):
            assert PG.resetpub_solve_default(plan, env) == PGP.resetpub_solve(plan, env)
    assert PG.RESETPUB_SOLVE_DIES == PGP.RESETPUB_SOLVE_DIES


def _cmd(monkeypatch, env):
    for k in ("OT_RESETPUB_SOLVE",):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "", ""

    def runner(argv, **kw):
        seen["cmd"] = argv[-1]
        return R()
    PG.static_remote("localhost", "/tmp/w", "/t", QC, "", "0" * 64, runner=runner)
    return seen["cmd"]


def test_forward_explicit_only(monkeypatch):
    assert "&& nice -n 10" in _cmd(monkeypatch, {})
    assert "&& OT_RESETPUB_SOLVE=1 nice" in _cmd(monkeypatch, {"OT_RESETPUB_SOLVE": "1"})
    assert "&& OT_RESETPUB_SOLVE=0 nice" in _cmd(monkeypatch, {"OT_RESETPUB_SOLVE": "0"})
