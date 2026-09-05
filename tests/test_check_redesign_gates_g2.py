"""Gate G2 must not pass on a block name.

G2 says one routed netlist contains the datapath array, the memory system AND
the microsequencer, at one named PDK, DRC 0 and antenna 0.  Its first
evaluator passed when any routed block's directory was named after the
microsequencer, so routing the front-end block alone
(results/physical_abi3/asap7/a3_microsequencer) would have turned a terminal
gate green on a third of its statement.  These tests pin the refusals: the
front-end block alone fails and says what it lacks; a record whose sources
cover every component but places no memory macro fails; a dirty route fails;
only one clean record holding all three passes.
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

G2 = {
    "type": "routed_netlist_contains",
    "glob": "results/physical_abi3/*/*/pnr.json",
    "require_sources_matching": {
        "microsequencer": ["*microsequencer*"],
        "datapath array": ["*tile64*", "*lq8*"],
    },
    "require_macro_count_min": 1,
}

FRONT_END_SOURCES = [
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
]


def _record(sources: list[str], *, macros: int, drc: int = 0, antenna: int = 0, routed: bool = True) -> dict:
    body = {
        "status": "pass" if drc == 0 and antenna == 0 else "not_met",
        "flow_completed": routed,
        "view": {"name": "asap7"},
        "design": {"sources": [{"path": s} for s in sources]},
    }
    if routed:
        body["place_and_route"] = {
            "metrics": {
                "macro_count": macros,
                "drc_errors": drc,
                "antenna_violating_nets": antenna,
                "antenna_violating_pins": antenna,
            }
        }
    return body


def _write(repo: Path, rel: str, body: dict) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(gates, "REPO", tmp_path)
    return tmp_path


def _evaluate() -> dict:
    return gates.evaluate({"id": "G2", "evaluator": G2})


def test_front_end_block_alone_fails_and_names_what_it_lacks(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_microsequencer/pnr.json",
        _record(FRONT_END_SOURCES, macros=0),
    )
    got = _evaluate()
    assert got["status"] == "fail"
    assert "a3_microsequencer" in got["why"]
    assert "no datapath array" in got["why"]
    assert "no memory system" in got["why"]


def test_no_routed_block_at_all_fails(repo):
    assert _evaluate()["status"] == "fail"


def test_all_components_without_placed_macros_fails(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_g2_top/pnr.json",
        _record(FRONT_END_SOURCES + ["rtl/abi3/ot_a3_tile64.sv"], macros=0),
    )
    got = _evaluate()
    assert got["status"] == "fail"
    assert "no memory system" in got["why"]
    assert "no datapath array" not in got["why"]


def test_dirty_route_fails(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_g2_top/pnr.json",
        _record(FRONT_END_SOURCES + ["rtl/abi3/ot_a3_lq8.sv"], macros=4, drc=3),
    )
    got = _evaluate()
    assert got["status"] == "fail"
    assert "not clean" in got["why"]


def test_synthesis_only_record_fails(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_g2_top/pnr.json",
        _record(FRONT_END_SOURCES + ["rtl/abi3/ot_a3_lq8.sv"], macros=4, routed=False),
    )
    got = _evaluate()
    assert got["status"] == "fail"
    assert "no completed place-and-route" in got["why"]


def test_one_clean_netlist_holding_all_three_passes(repo):
    _write(
        repo,
        "results/physical_abi3/asap7/a3_microsequencer/pnr.json",
        _record(FRONT_END_SOURCES, macros=0),
    )
    _write(
        repo,
        "results/physical_abi3/sky130hd/a3_g2_top/pnr.json",
        _record(FRONT_END_SOURCES + ["rtl/abi3/ot_a3_tile64.sv"], macros=12),
    )
    got = _evaluate()
    assert got["status"] == "pass"
    assert "a3_g2_top" in got["why"]


def test_the_committed_gate_spec_uses_the_per_record_evaluator():
    spec = json.loads((ROOT / "configs/gates/redesign_gates.json").read_text())
    g2 = next(g for g in spec["gates"] if g["id"] == "G2")
    assert g2["evaluator"]["type"] == "routed_netlist_contains"
    assert "microsequencer" in g2["evaluator"]["require_sources_matching"]
    assert "datapath array" in g2["evaluator"]["require_sources_matching"]
    assert g2["evaluator"]["require_macro_count_min"] >= 1
