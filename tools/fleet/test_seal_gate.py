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
    monkeypatch.setattr(SG, "SEAL_BLOCK_AFTER", 1_800_000_000)
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


def test_walk_budget_is_advisory_in_block_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(SG, "findings", lambda *a: [f"{SG.WALK_CUT}60 s)"])
    assert SG.gate(tmp_path, "bind", env={"OT_SEAL_GATE": "block"}) == 0
    assert "walk cut" in capsys.readouterr().err


def test_default_is_report_only_and_own_fork_links_are_allowed_others_blocked(tmp_path, monkeypatch):
    """FLEET-OPS 11-25: KV-PV-ESTRIP launch tree (309 links) into its own private ot-tree-fork was refused"""
    import json
    monkeypatch.setattr(SG, "SCRATCH_TREE_RE", re.compile("^" + str(tmp_path) + "/claude/"))
    assert SG.mode(now=1_900_000_000, env={}) == "report"                      # default: report-only for now
    own = tmp_path / "claude/kv-pv-estrip"
    fork = tmp_path / "claude/kv-fork-elsewhere/forkA"       # a recorded fork of THIS lane living in another dir
    other = tmp_path / "claude/other-lane/tree"
    sealed = tmp_path / "claude/kw45/src_x"
    for d in (own / "tree_fork", fork, other, sealed):
        d.mkdir(parents=True)
        (d / "plan.json").write_text("p")
    tree = own / "launch12"
    (tree / "physical/die_plan").mkdir(parents=True)
    os.symlink(str(own / "tree_fork/plan.json"), tree / "physical/die_plan/a.json")      # own lane dir
    os.symlink(str(fork / "plan.json"), tree / "physical/die_plan/b.json")               # recorded fork of this lane
    os.symlink(str(other / "plan.json"), tree / "physical/die_plan/c.json")              # another lane: blocked
    os.symlink(str(sealed / "plan.json"), tree / "physical/die_plan/d.json")             # sealed tree: blocked
    ff = tmp_path / "forks.jsonl"
    ff.write_text(json.dumps({"dst": str(fork), "lane": "kv-pv-estrip"}) + "\n")
    f = SG.findings(str(tree), forks_file=str(ff), env={"OT_LANE": "kv-pv-estrip"})
    names = " ".join(f)
    assert "c.json" in names and "d.json" in names and "a.json" not in names and "b.json" not in names
    f2 = SG.findings(str(tree), forks_file=str(ff), env={"OT_LANE": "someone-else"})
    assert "b.json" in " ".join(f2) and "a.json" not in " ".join(f2)
