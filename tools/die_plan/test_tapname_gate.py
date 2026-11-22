"""TAPNAME-1122 (FLOW-OPS-R2, COORD): density added tap names are checked against the bind's density base in seconds."""
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def plan(tmp_path, added, refs=()):
    ck = {"tap_mode": "density", "added_taps": [{"name": n, "xy": [1, 1]} for n in added],
          "landing_contract": {"pins": [{"source_clock_port": r} for r in refs]}}
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"partition_types": {"cbf_q00": {"clock": ck}, "other": {"clock": {"tap_mode": "explicit"}}}}))
    return str(p)


BASE = lambda P, raw, tn: 114  # noqa: E731


def test_wrong_added_name_refused_with_expected():
    import tempfile
    d = Path(tempfile.mkdtemp())
    f = G.check_tapname(plan(d, ["clk_t101", "clk_t102"]), base_fn=BASE)
    assert f == ["FAIL TAPNAME cbf_q00: density base gives 114 taps, so added_taps must be clk_t114..clk_t115; "
                 "clk_t101 should be clk_t114; clk_t102 should be clk_t115"]


def test_right_names_pass_and_stale_refs_need_retap(tmp_path):
    assert G.check_tapname(plan(tmp_path, ["clk_t114"], ["clk_t3", "clk_t114"]), base_fn=BASE) == []
    f = G.check_tapname(plan(tmp_path, ["clk_t114"], ["clk_t130", "clk_t3"]), base_fn=BASE)
    assert len(f) == 1 and f[0].startswith("FAIL TAPNAME-RETAP cbf_q00:") and "clk_t130" in f[0] and "clk_t3," not in f[0]


def test_solve_error_is_unchecked_fail(tmp_path):
    """TAPNAME-UNCHECKED-1122: an unsolved density base is a FAIL (UNCHECKED), never a WARN + PASS"""
    f = G.check_tapname(plan(tmp_path, ["clk_t114"]), base_fn=lambda *a: 1 / 0)
    assert f[0].startswith("FAIL TAPNAME-UNCHECKED cbf_q00: density base not solved")


def test_cli_missing_base_inputs_is_unchecked_nonzero(tmp_path, monkeypatch, capsys):
    """run from a bare dir with no plan inputs: rc != 0 and the verdict line says UNCHECKED, not PASS"""
    p = plan(tmp_path, ["clk_t114"])
    bare = tmp_path / "bare"
    bare.mkdir()
    monkeypatch.chdir(bare)
    rc = G.main(["check", "--tree", str(bare), "--plan", p, "--skip", "SCHEMA", "--skip", "INPUT", "--skip", "TOOLS", "--skip", "ROWS",
                 "--skip", "GEOM", "--skip", "KITFIT", "--skip", "FIXEDCYC", "--skip", "ROWSINK", "--skip", "MODULES", "--skip", "TOOLSTALE",
                 "--skip", "LANDREMAP", "--skip", "ABSPATH", "--skip", "ISTCYC", "--skip", "DEADIN", "--skip", "R8STALE",
                 "--skip", "RELAYSINK", "--skip", "EMITNAME"])
    out = capsys.readouterr().out
    assert rc != 0 and "PLAN-GATE-PRE UNCHECKED" in out and "PLAN-GATE-PRE PASS" not in out


def test_density_base_solved_inside_tree(tmp_path):
    """the default solver reads the plan's repo-relative inputs from --tree, not from the checker's own tool tree"""
    seen = []
    import taps as TP
    import schema
    orig, oplan = TP._density_base, schema.Plan
    try:
        TP._density_base = lambda P, tn: seen.append(TP._root()) or [0] * 114
        schema.Plan = lambda raw, path=None: object()
        f = G.check_tapname(plan(tmp_path, ["clk_t114"]), tree=str(tmp_path))
    finally:
        TP._density_base, schema.Plan = orig, oplan
    assert f == [] and seen and seen[0] == tmp_path.resolve() and TP._root() != tmp_path.resolve()


def test_only_types_changed_vs_base_are_solved(tmp_path):
    """TAPNAME-DELTA-1122: a type whose clock section equals the base's is not re-solved (the QC full-plan solve took ~1 h)"""
    calls = []
    fn = lambda P, raw, tn: calls.append(tn) or 114  # noqa: E731
    b = tmp_path / "b"
    b.mkdir()
    base = plan(b, ["clk_t114"])
    assert G.check_tapname(plan(tmp_path, ["clk_t114"]), base_fn=fn, base=base) == [
        f"WARN TAPNAME 1 density type(s) with a clock section identical to base {base} not re-solved (OT_TAPNAME_ALL=1 solves all)"]
    assert calls == []
    f = G.check_tapname(plan(tmp_path, ["clk_t115"]), base_fn=fn, base=base)     # changed vs base: solved and refused
    assert calls == ["cbf_q00"] and f[0].startswith("FAIL TAPNAME cbf_q00:")
    calls.clear()
    G.check_tapname(plan(tmp_path, ["clk_t114"]), base_fn=fn, base=base, solve_all=True)
    assert calls == ["cbf_q00"]


def test_kit_only_clock_keys_do_not_trigger_a_solve(tmp_path):
    """TAP-GRID-R5 set tap_balance_to / tap_slowest_max_ps on 108 QC types: kit-side keys, not density inputs"""
    calls = []
    fn = lambda P, raw, tn: calls.append(tn) or 114  # noqa: E731
    b = tmp_path / "b"
    b.mkdir()
    base = plan(b, ["clk_t114"])
    p = Path(plan(tmp_path, ["clk_t114"]))
    raw = json.loads(p.read_text())
    raw["partition_types"]["cbf_q00"]["clock"].update(tap_balance_to="slowest", tap_slowest_max_ps=265.0)
    p.write_text(json.dumps(raw))
    assert G.check_tapname(str(p), base_fn=fn, base=base)[0].startswith("WARN TAPNAME 1 density type(s)") and calls == []
