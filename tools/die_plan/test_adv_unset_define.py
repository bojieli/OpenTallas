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
    raw = {"partition_types": {"t1": {"module": "m", "verilog_defines": ["OT_NEW_B=1"]}}, "note": "uses OT_OTHER", "defines": ["OT_DIE_WIDE"]}
    assert set(U.plan_switches(raw)) == {"OT_NEW_B", "OT_DIE_WIDE"}      # free text is not a setting


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


def test_sibling_set_ranks_first(tmp_path):
    repo = tmp_path / "r"
    (repo / "rtl").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "rtl" / "m.sv").write_text("module mm;\n`ifdef OT_FAM_NEW\n`endif\n`ifdef OT_OTHER_X\n`endif\nendmodule\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "x")
    raw = {"partition_types": {"tq": {"module": "unrelated", "verilog_defines": ["OT_FAM_OLD"]}}}
    out = U.findings(raw, "p", None, main_repo=str(repo / ".git"), main_ref="main")
    assert "OT_FAM_NEW" in out[0] and "SIBLING-SET" in out[0] and "tq" in out[0] and "1 with a sibling" in out[-1]
    assert len(out) == 2 and "1 in RTL this plan does not reach (OT_OTHER_X)" in out[-1]     # not reached: summary only (PRECHECK-R3)


COLL = "rtl/rom/ot_coll_tp8_static.sv"
FACE = "rtl/qwen_split/qfd_coll_static_face.sv"


def test_bind_rtl_closure_qc_coll(tmp_path):
    """QC C1g coll_core (11-24): the plan names module qfd_coll_static_face only; its child ot_coll_tp8_static.sv was 603 lines
    in the tree vs 659 on main (OT_TP8S_RDPIPE / OT_TP8S_XEPRE added).  TREE-DRIFT must list the lagging child, UNSET-DEFINE
    must rank the new switches IN-BIND-RTL for coll_core, and skip the mutant / other-die switches from the listing."""
    import adv_tree_drift as T
    repo, tree = tmp_path / "repo", tmp_path / "tree"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    old = "module ot_coll_tp8_static;\nendmodule\n"
    face = "module qfd_coll_static_face;\n  ot_coll_tp8_static u_tp8 (.a(a));\nendmodule\n"
    for rel, txt in ((COLL, old), (FACE, face), ("rtl/s81/other.sv", "module other_die;\nendmodule\n"),
                     ("tools/die_plan/gen_phys.py", "# OT_GEN_ONLY consumed by the generator\n")):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(txt)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    for rel in (COLL, FACE, "tools/die_plan/gen_phys.py"):
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text((repo / rel).read_text())
    (repo / COLL).write_text("module ot_coll_tp8_static;\n`ifdef OT_TP8S_RDPIPE\n`endif\n`ifdef OT_TP8S_MUT_X\n`endif\nendmodule\n")
    (repo / "rtl/s81/other.sv").write_text("module other_die;\n`ifdef OT_S81_ELSE\n`endif\nendmodule\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "OPUS-FIX-QC-COLL-R3: OT_TP8S_RDPIPE gather rank select")
    raw = {"partition_types": {"coll_core": {"module": "qfd_qc_coll_core_part", "contents": [{"inst": "u_face", "module": "qfd_coll_static_face"}],
                                             "verilog_defines": ["OT_TP8S_SRDREG", "OT_GEN_ONLY"]}}}
    gd = str(repo / ".git")
    idx = T.rtl_index(str(tree))
    assert set(T.rtl_closure(raw, str(tree), index=idx)) == {FACE, COLL}
    dr = T.findings(raw, "p", tree=str(tree), main_repo=gd, main_ref="main")
    hit = [x for x in dr if x.startswith(f"WARN ADV-TREE-DRIFT rtl {COLL}: LAG")]
    assert hit and "reached by 1 type(s) (coll_core)" in hit[0] and "OT_TP8S_RDPIPE" in hit[0]
    assert "bind RTL closure 2 file(s)" in dr[-1] and "LAG 1" in dr[-1]
    un = U.findings(raw, "p", str(tree), main_repo=gd, main_ref="main")
    assert "OT_TP8S_RDPIPE" in un[0] and "IN-BIND-RTL" in un[0] and "coll_core" in un[0]
    assert not any("OT_TP8S_MUT_X" in x for x in un[:-1]) and not any("OT_S81_ELSE:" in x for x in un)
    assert "1 mutation/test control(s) skipped" in un[-1] and "1 in RTL this plan does not reach (OT_S81_ELSE)" in un[-1]
    ts = TS.findings(raw, "p", str(tree), main_repo=gd, main_ref="main")
    assert not any("OT_GEN_ONLY" in x for x in ts)                       # generator-consumed switch: found in tools/die_plan
    assert any("OT_TP8S_SRDREG: SWITCH-NOOP+UNDEFINED" in x for x in ts)
