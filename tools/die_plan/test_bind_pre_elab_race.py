"""PRE-ELAB-RACE-1122 / PRE-ORDER-1123 (TAP-GRID-R5, KV D29 gate 3; COORD 11-23): the in-bind plan_gate_pre reads OUT/asbuilt.json only
after this run's elab finished; the order lives in main(), not in an env."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def test_before_own_elab_never_reads_the_elab(monkeypatch, tmp_path):
    monkeypatch.setattr(bind, "_PG_ELAB_DONE", [False])
    for cmd in ("elab", "all"):
        assert bind._pg_elab_dir(NS(cmd=cmd, out=str(tmp_path))) is None
    assert bind._pg_elab_dir(NS(cmd="bind", out=str(tmp_path))) == str(tmp_path)     # bind reads, never writes, the elab


def test_after_own_elab_reads_it(monkeypatch, tmp_path):
    monkeypatch.setattr(bind, "_PG_ELAB_DONE", [True])
    for cmd in ("elab", "all", "bind"):
        assert bind._pg_elab_dir(NS(cmd=cmd, out=str(tmp_path))) == str(tmp_path)


def test_main_orders_the_gate_after_elab():
    src = (Path(__file__).resolve().parent / "bind.py").read_text()
    m = src[src.index("def _main(argv=None):"):]
    assert 'if a.cmd == "bind":            # PRE-ORDER-1123' in m
    allb = m[m.index('if a.cmd == "all":'):]
    assert allb.index("cmd_elab(a)") < allb.index("_PG_ELAB_DONE[0] = True") < allb.index("_pg_run(a)") < allb.index("cmd_bind(a)")
    el = m[m.index('if a.cmd == "elab":'):]
    assert el.index("cmd_elab(a)") < el.index("_pg_run(a)")


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
    monkeypatch.setattr(bind, "_PG_ELAB_DONE", [False])
    p = tmp_path / "p.json"
    p.write_text("{}")
    a = NS(plan=str(p), out=str(tmp_path / "o"), asbuilt=None, cmd="all")
    assert bind._plan_gate_pre(a) == 0
    assert seen.get("elab_dir") is None
    seen.clear()
    monkeypatch.setattr(bind, "_PG_ELAB_DONE", [True])
    (tmp_path / "o" / "plan_gate_pre.json").unlink(missing_ok=True)
    assert bind._plan_gate_pre(a) == 0
    assert seen.get("elab_dir") in (None, str(tmp_path / "o"))
