"""PRE-ELAB-RACE-1122 (TAP-GRID-R5, KV D29 gate 3): the in-bind plan_gate_pre must not read OUT/asbuilt.json while the elab writes it."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def test_beside_child_never_reads_the_elab(monkeypatch, tmp_path):
    monkeypatch.setattr(bind, "_PG_BESIDE", [True])
    for cmd in ("bind", "elab", "all"):
        assert bind._pg_elab_dir(NS(cmd=cmd, out=str(tmp_path))) is None


def test_serial_only_bind_after_its_own_elab(monkeypatch, tmp_path):
    monkeypatch.setattr(bind, "_PG_BESIDE", [False])
    assert bind._pg_elab_dir(NS(cmd="bind", out=str(tmp_path))) == str(tmp_path)
    assert bind._pg_elab_dir(NS(cmd="elab", out=str(tmp_path))) is None      # a previous run's elab, maybe another plan
    assert bind._pg_elab_dir(NS(cmd="all", out=str(tmp_path))) is None


def test_gate_passes_the_guarded_dir(monkeypatch, tmp_path):
    seen = {}

    class G:
        @staticmethod
        def check(repo, plan, **kw):
            seen.update(kw)
            return []
    monkeypatch.setitem(sys.modules, "plan_gate_pre", G)
    monkeypatch.setenv("OT_PLAN_GATE_SKIP", "LANDREMAP")
    monkeypatch.delenv("OT_PLAN_GATE_BASELINE", raising=False)
    monkeypatch.delenv("OT_PLAN_GATE_PRE", raising=False)
    monkeypatch.setattr(bind, "_PG_BESIDE", [True])
    p = tmp_path / "p.json"
    p.write_text("{}")
    a = NS(plan=str(p), out=str(tmp_path / "o"), asbuilt=None, cmd="all")
    assert bind._plan_gate_pre(a) == 0
    assert seen.get("elab_dir") is None
