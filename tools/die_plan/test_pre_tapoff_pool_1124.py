"""TAPOFF-POOL-1124: check_tapoff's per-type port solve in a fork pool gives exactly the serial findings."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_gate_pre as G  # noqa: E402
import schema  # noqa: E402


def test_pool_equals_serial(tmp_path, monkeypatch):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    tns = sorted(raw["partition_types"])
    grid = {tn: [("clk", 0.0, 0.0), ("clk_t1", 100.0 + i, 0.0), ("clk_t2", 200.0, 10.0 * i)] for i, tn in enumerate(tns)}
    raw.setdefault("clock", {})["tap_offset"] = {"per_port_ps": {tn: {"clk": {"TT": 1, "FF": 1, "tol": 5}} for tn in tns}}
    for tn in tns[1:]:
        raw["clock"]["tap_offset"]["per_port_ps"][tn]["clk_t1"] = {"TT": 1, "FF": 1, "tol": 5}

    def tap_grid(P, tn):
        if tn == tns[-1]:
            raise ValueError("unsolvable")
        return grid[tn]
    monkeypatch.setattr(schema, "tap_grid", tap_grid)
    monkeypatch.setattr(schema, "core_taps", lambda P, tn: [])
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(raw))
    monkeypatch.setenv("OT_RESET_POOL_J", "1")
    serial = G.check_tapoff(str(p))
    monkeypatch.setenv("OT_RESET_POOL_J", "3")
    pooled = G.check_tapoff(str(p))
    assert pooled == serial and any(x.startswith("FAIL TAPOFF-MISSING") for x in serial), serial


def test_fork_map_serial_and_pool_agree():
    sq = lambda x: x * x  # noqa: E731
    assert G.fork_map(sq, range(7), jobs=1) == G.fork_map(sq, range(7), jobs=3) == {i: i * i for i in range(7)}
