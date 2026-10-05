"""Gates D3 and D4 read the ``design`` block tools/run_abi3_physical.py writes.

These tests pin the evaluator's refusals: a candidate that did not close, one
at another view, one without declared per-MAC figures, and a declared lane
count the netlist does not confirm must all FAIL; only a closed routed result
at the baseline's view that improves both per-MAC figures passes.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_redesign_gates", ROOT / "tools/check_redesign_gates.py"
)
gates = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gates)


def _baseline() -> dict:
    # The shape of results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json
    # as far as the evaluator reads it: 8,348.44 um2 at 18 ns, closed.
    return {
        "status": "pass",
        "view": {"name": "asap7"},
        "place_and_route": {
            "clock_period_ns": 18.0,
            "metrics": {"standard_cell_area_um2": 8348.44},
        },
    }


def _candidate(**over) -> dict:
    body = {
        "status": "pass",
        "view": {"name": "asap7"},
        "place_and_route": {"clock_period_ns": 5.0, "metrics": {}},
        "design": {
            "lanes": 8,
            "lanes_verified_in_netlist": True,
            "mac_per_cycle": 8.0,
            "closed": True,
            "per_mac_area_um2": 700.0,
            "per_mac_period_ns": 0.625,
        },
    }
    for key, value in over.items():
        node = body
        parts = key.split("__")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return body


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(gates, "REPO", tmp_path)
    base = tmp_path / "results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json"
    base.parent.mkdir(parents=True)
    base.write_text(json.dumps(_baseline()))
    return tmp_path


def _write(repo: Path, rel: str, body: dict) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


D4 = {
    "type": "per_mac_improvement",
    "baseline": "results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json",
    "glob": "results/physical_abi3/*/*lane*/pnr.json",
    "baseline_mac_per_cycle": 0.17294,
}
D3 = {
    "type": "artifact_threshold",
    "glob": "results/physical_abi3/*/*array*/pnr.json",
    "field": "design.lanes",
    "min": 2,
    "also_require": {"field": "design.lanes_verified_in_netlist", "equals": True},
}


def test_d4_derives_the_baseline_figures_and_passes_a_closed_improvement(repo):
    _write(repo, "results/physical_abi3/asap7/a3_lane_pipelined/pnr.json", _candidate())
    out = gates.evaluate({"evaluator": D4})
    assert out["status"] == "pass", out
    assert "48,274 um2" in out["why"] and "104.1 ns" in out["why"]


def test_d4_fails_when_the_candidate_did_not_close(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_lane_pipelined/pnr.json",
        _candidate(status="not_met", design__closed=False),
    )
    out = gates.evaluate({"evaluator": D4})
    assert out["status"] == "fail"
    assert "not closed" in out["why"]


def test_d4_fails_when_either_per_mac_figure_regresses(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_lane_pipelined/pnr.json",
        _candidate(design__per_mac_period_ns=120.0),
    )
    out = gates.evaluate({"evaluator": D4})
    assert out["status"] == "fail"
    assert "period regresses" in out["why"]


def test_d4_refuses_a_candidate_at_another_view(repo):
    _write(
        repo,
        "results/physical_abi3/sky130hd/a3_lane_pipelined/pnr.json",
        _candidate(view__name="sky130hd"),
    )
    out = gates.evaluate({"evaluator": D4})
    assert out["status"] == "fail"
    assert "not the baseline's asap7" in out["why"]


def test_d4_refuses_a_candidate_without_declared_figures(repo):
    body = _candidate()
    del body["design"]["per_mac_area_um2"]
    _write(repo, "results/physical_abi3/asap7/a3_lane_pipelined/pnr.json", body)
    out = gates.evaluate({"evaluator": D4})
    assert out["status"] == "fail"
    assert "declares no per-MAC figures" in out["why"]


def test_d3_requires_the_netlist_to_confirm_the_declared_lanes(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_lq8_array/pnr.json",
        _candidate(design__lanes_verified_in_netlist=False),
    )
    out = gates.evaluate({"evaluator": D3})
    assert out["status"] == "fail"
    assert "lanes_verified_in_netlist" in out["why"]
    _write(repo, "results/physical_abi3/asap7/a3_lq8_array/pnr.json", _candidate())
    out = gates.evaluate({"evaluator": D3})
    assert out["status"] == "pass", out
