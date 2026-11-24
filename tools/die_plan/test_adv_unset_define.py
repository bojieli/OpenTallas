"""pytest: ADV-UNSET-DEFINE / ADV-TREE-SWITCH on a throw-away git repo and tree."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tree_switch as TS  # noqa: E402
import adv_unset_define as U  # noqa: E402


def test_added_and_plan_switches():
    log = "@@C abc1234 2026-11-23 add\n+++ b/rtl/x/m.sv\n+`ifdef OT_NEW_A\n+ foo\n@@C def5678 2026-11-20 older\n+++ b/rtl/x/m.sv\n+`ifndef OT_NEW_A\n+`elsif OT_NEW_B\n"
    a = U.added_switches(log)
    assert a["OT_NEW_A"][0] == "def5678" and a["OT_NEW_B"][2] == "rtl/x/m.sv"
    raw = {"partition_types": {"t1": {"module": "m", "verilog_defines": ["OT_NEW_B=1"]}}, "note": "uses OT_OTHER"}
    assert set(U.plan_switches(raw)) == {"OT_NEW_B", "OT_OTHER"}


def _git(d, *a):
    subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def test_unset_and_tree_switch(tmp_path):
    repo, tree = tmp_path / "repo", tmp_path / "tree"
    (repo / "rtl").mkdir(parents=True)
    (tree / "rtl").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "rtl" / "m.sv").write_text("module mm;\n`ifdef OT_ON\n`endif\n`ifdef OT_OFF\n`endif\nendmodule\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add switches")
    (tree / "rtl" / "m.sv").write_text("module mm;\n`ifdef OT_ON\n`endif\nendmodule\n")
    raw = {"partition_types": {"t1": {"module": "mm", "verilog_defines": ["OT_ON", "OT_OFF", "OT_TYPO"]}}}
    gd = str(repo / ".git")
    ts = TS.findings(raw, "p", str(tree), main_repo=gd, main_ref="main")
    txt = "\n".join(ts)
    assert "OT_OFF: SWITCH-NOOP+DRIFT" in txt and "rtl/m.sv 4 lines vs 6 on main" in txt and "OT_TYPO: SWITCH-NOOP+UNDEFINED" in txt and "OT_ON:" not in txt
    assert "2 SWITCH-NOOP" in ts[-1]
    un = U.findings({"partition_types": {"t1": {"module": "mm", "verilog_defines": ["OT_ON"]}}}, "p", None, main_repo=gd, main_ref="main")
    assert any("OT_OFF: not set" in x and "targets 1 type(s)" in x for x in un) and "1 UNSET" in un[-1]
