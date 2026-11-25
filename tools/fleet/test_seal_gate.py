"""FLEET-OPS 11-25 F-06 hook: seal_gate reports for an hour, then blocks; same rule as ot-tree-fork --seal-check"""
import os
import sys
import re
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seal_gate as SG  # noqa: E402


def mk(tmp):
    other = tmp / "claude/paused"
    other.mkdir(parents=True)
    (other / "x").write_text("x")
    tree = tmp / "claude/lane/tree"
    (tree / "physical/die_plan").mkdir(parents=True)
    os.symlink(str(other / "x"), tree / "physical/die_plan/plan.json")
    (tree / "run").mkdir()
    os.symlink(str(other / "x"), tree / "run/ignored")
    return tree


def test_outside_link_found_only_under_the_checked_subtree_and_agrees_with_ot_tree_fork(tmp_path, monkeypatch):
    rx = re.compile("^" + str(tmp_path) + "/claude/")
    monkeypatch.setattr(SG, "SCRATCH_TREE_RE", rx)
    tree = mk(tmp_path)
    f = SG.findings(str(tree))
    assert len(f) == 1 and "physical/die_plan/plan.json" in f[0]
    TF = SourceFileLoader("ot_tree_fork_sg", str(HERE / "ot-tree-fork")).load_module()
    monkeypatch.setattr(TF, "SCRATCH_TREE_RE", rx)
    assert any("physical/die_plan/plan.json" in b for b in TF.seal_check(str(tree)))


def test_report_only_first_then_blocking_and_switches(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(SG, "SCRATCH_TREE_RE", re.compile("^" + str(tmp_path) + "/claude/"))
    tree = mk(tmp_path)
    before, after = SG.SEAL_BLOCK_AFTER - 10, SG.SEAL_BLOCK_AFTER + 10
    assert SG.gate(str(tree), "bind", now=before, env={}) == 0
    assert "REPORT-ONLY" in capsys.readouterr().err
    assert SG.gate(str(tree), "bind", now=after, env={}) == 4
    assert "BLOCK" in capsys.readouterr().err
    assert SG.gate(str(tree), "bind", now=after, env={"OT_SEAL_GATE": "0"}) == 0
    assert SG.gate(str(tree), "bind", now=after, env={"OT_SEAL_GATE": "report"}) == 0
    assert SG.gate(str(tree), "bind", now=before, env={"OT_SEAL_GATE": "block"}) == 4
    clean = tmp_path / "claude/lane/clean"; (clean / "physical").mkdir(parents=True)
    assert SG.gate(str(clean), "bind", now=after, env={}) == 0


def test_bind_and_run_kit_call_it():
    assert "_seal_gate(\"bind\")" in (HERE.parent / "die_plan/bind.py").read_text()
    gp = (HERE.parent / "die_plan/gen_phys.py").read_text()
    assert "seal_gate.py\" \"$K\" run_kit" in gp.replace("\\", "") or 'seal_gate.py" "$K" run_kit' in gp
    assert '"fleet" / "seal_gate.py"' in gp
