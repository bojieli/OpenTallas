"""RESETPUB-SOLVE-DEFAULT-1125: QC plans solve RESETPUB by default; OT_RESETPUB_SOLVE=0/1 overrides for any die."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as PGP  # noqa: E402

QC = "/t/physical/die_plan/qwen_compute/plan_of_record/p.json"
KV = "/t/physical/die_plan/qwen_kvsys/plan_of_record/p.json"


def test_qc_default_on():
    assert PGP.resetpub_solve(QC, {}) is True


def test_other_die_default_off():
    assert PGP.resetpub_solve(KV, {}) is False


def test_env_overrides():
    assert PGP.resetpub_solve(QC, {"OT_RESETPUB_SOLVE": "0"}) is False
    assert PGP.resetpub_solve(KV, {"OT_RESETPUB_SOLVE": "1"}) is True


def test_die_key_fallback(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text('{"die": "qwen_compute"}')
    assert PGP.plan_die(p) == "qwen_compute"
    assert PGP.resetpub_solve(p, {}) is True


def test_reset_solve_types_uses_default(monkeypatch):
    monkeypatch.setattr(PGP, "resetpub_todo", lambda raw, braw, solve, max_list=4: [("t_a", {}, ["rst"])] if solve else [])
    sel = PGP.reset_solve_types("/t", QC, {"partition_types": {}}, skip={"LANDREMAP", "STARTSETTLE", "ANCHORDRY", "RSTREACH", "DERIVEDNAME"}, env={})
    assert sel["plan"].get("t_a") == ["RESETPUB"]
    sel = PGP.reset_solve_types("/t", QC, {"partition_types": {}}, skip={"LANDREMAP", "STARTSETTLE", "ANCHORDRY", "RSTREACH", "DERIVEDNAME"}, env={"OT_RESETPUB_SOLVE": "0"})
    assert "t_a" not in sel["plan"]
