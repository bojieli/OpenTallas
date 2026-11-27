import json
import subprocess
from pathlib import Path

import adv_define_noop as A

OLD = "module m(input a, output y);\nassign y = a;\nendmodule\n"
NEW = "module m(input a, output y);\n`ifdef OT_X_SPLIT\nassign y = ~a;\n`else\nassign y = a;\n`endif\nendmodule\n"


def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def _main(tmp):
    repo = tmp / "src"
    (repo / "rtl").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "rtl/m.sv").write_text(OLD)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "old")
    (repo / "rtl/m.sv").write_text(NEW)
    _git(repo, "commit", "-q", "-am", "add OT_X_SPLIT")
    return repo / ".git"


def _tree(tmp, body):
    t = tmp / "tree"
    (t / "rtl").mkdir(parents=True)
    (t / "physical/die_plan/d").mkdir(parents=True)
    (t / "rtl/m.sv").write_text(body)
    return t


def plan(defs):
    return {"partition_types": {"a": {"verilog_defines": defs}, "b": {}}}


def test_noop_when_tree_lags_main(tmp_path):
    repo = _main(tmp_path)
    t = _tree(tmp_path, OLD)
    out = A.findings(plan(["OT_X_SPLIT"]), tree=t, main_repo=repo, main_ref="main")
    assert out[0].startswith("WARN ADV-DEFINE-NOOP NOOP OT_X_SPLIT (set on a)")
    assert "rtl/m.sv LAG" in out[0]
    assert "1 NOOP, 0 LAG, 0 UNKNOWN, 0 tool-read" in out[-1]


def test_clean_when_tree_has_main_copy(tmp_path):
    repo = _main(tmp_path)
    t = _tree(tmp_path, NEW)
    out = A.findings(plan(["OT_X_SPLIT=1"]), tree=t, main_repo=repo, main_ref="main")
    assert len(out) == 1 and "0 NOOP, 0 LAG, 0 UNKNOWN" in out[0]


def test_unknown_and_no_main(tmp_path):
    repo = _main(tmp_path)
    t = _tree(tmp_path, NEW)
    out = A.findings(plan(["OT_TYPO"]), tree=t, main_repo=repo, main_ref="main")
    assert "UNKNOWN OT_TYPO" in out[0]
    src = repo.parent
    (src / "tools").mkdir()
    (src / "tools/gen.py").write_text("if 'OT_GEN_ONLY' in defines: pass\n")
    _git(src, "add", ".")
    _git(src, "commit", "-q", "-m", "tool switch")
    out = A.findings(plan(["OT_GEN_ONLY"]), tree=t, main_repo=repo, main_ref="main")
    assert len(out) == 1 and "1 tool-read" in out[0]
    out = A.findings(plan(["OT_X_SPLIT"]), tree=_tree(tmp_path / "o", OLD), main_repo=tmp_path / "none")
    assert "main not checked" in out[0] and "NOOP OT_X_SPLIT" in out[0]


def test_tree_found_above_plan_and_never_raises(tmp_path):
    t = _tree(tmp_path, NEW)
    p = t / "physical/die_plan/d/plan.json"
    p.write_text(json.dumps(plan(["OT_X_SPLIT"])))
    out = A.findings(plan(["OT_X_SPLIT"]), str(p), main_repo=tmp_path / "none")
    assert "0 NOOP" in out[-1]
    assert A.findings({"partition_types": None}) == []
    assert A.findings(plan(["OT_X_SPLIT"]))[0].startswith("WARN ADV-DEFINE-NOOP not checked")
