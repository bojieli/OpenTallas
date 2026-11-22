"""DEADIN-1122 (FLOW-OPS-R2, COORD): the bind's dead-input proof validation runs in plan_gate_pre, before the elab."""
import json
import os
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def setup(tmp_path, proofs):
    src = tmp_path / "src"; (src / "results").mkdir(parents=True)
    (src / "results" / "p.json").write_text(json.dumps({"schema": "opentallas.dead_inputs.v1", "verdict": "PASS",
                                                        "defines": [], "dependency_modules": [], "declarations": []}))
    tree = tmp_path / "launch"; tree.mkdir()
    os.symlink(src / "results", tree / "results")                          # rt launch tree: results/ is a link
    plan = tree / "plan.json"; plan.write_text(json.dumps({"partition_types": {"t": {}}}))
    ab = tree / "ab.json"; ab.write_text(json.dumps({"dead_input_proofs": proofs}))
    return str(tree), str(plan), str(ab), src


def test_symlinked_results_proof_passes(tmp_path):
    tree, plan, ab, _ = setup(tmp_path, ["results/p.json"])
    assert G.check_deadin(tree, plan, ab) == []


def test_absolute_or_bad_proof_refused_before_elab(tmp_path):
    tree, plan, ab, src = setup(tmp_path, [str(tmp_path / "src" / "results" / "p.json")])
    f = G.check_deadin(tree, plan, ab)
    assert len(f) == 1 and f[0].startswith("FAIL DEADIN dead-input proof must be repository-relative")
    (src / "results" / "p.json").write_text(json.dumps({"schema": "x"}))
    tree, plan, ab, _ = setup(tmp_path / "b", ["results/p.json"])
    assert G.check_deadin(tree, plan, ab) == []                                # fresh valid tree
    assert G.check_deadin(tree, plan, None) == []
