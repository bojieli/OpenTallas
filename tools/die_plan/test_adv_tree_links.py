"""ADV-TREE-LINKS (FP-CONVERGE-QC 11-25): pass case plus mutants (symlinked rtl/ dir, symlinked bind dir, symlinked file, content differing from rt/main)."""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_tree_links as L  # noqa: E402
import plan_advisory as PA  # noqa: E402


def mktree(root):
    for d in ("rtl/a", "tools/die_plan", "physical/die_plan/qwen_compute/bind"):
        (root / d).mkdir(parents=True)
    (root / "rtl/a/m.sv").write_text("module m; endmodule\n")
    (root / "tools/die_plan/x.py").write_text("X=1\n")
    (root / "physical/die_plan/qwen_compute/plan.json").write_text("{}")
    return root


def classes(lines):
    return sorted({l.split()[2] for l in lines if l.startswith("WARN") and "not checked" not in l})


def test_pass_case(tmp_path):
    t = mktree(tmp_path / "tree")
    assert L.findings({}, str(t / "physical/die_plan/qwen_compute/plan.json"), str(t)) == []
    # a symlink that stays inside the tree is fine
    os.symlink(t / "rtl/a", t / "rtl/inside")
    assert L.findings({}, None, str(t)) == []


def test_symlinked_rtl_dir_is_found(tmp_path):
    t = mktree(tmp_path / "tree")
    old = tmp_path / "old_private" / "rtl"
    (old / "a").mkdir(parents=True)
    (t / "rtl/a/m.sv").unlink()
    (t / "rtl/a").rmdir()
    (t / "rtl").rmdir()
    os.symlink(old, t / "rtl")
    out = L.findings({}, None, str(t))
    assert out[0].startswith("WARN ADV-TREE-LINKS LINK-OUT rtl (dir symlink) -> ") and str(old) in out[0]
    assert out[-1].startswith("LIST ADV-TREE-LINKS 1 finding(s)")


def test_symlinked_bind_dir_and_file(tmp_path):
    t = mktree(tmp_path / "tree")
    other = tmp_path / "QC-CB-C1L" / "bind"
    other.mkdir(parents=True)
    b = t / "physical/die_plan/qwen_compute/bind"
    b.rmdir()
    os.symlink(other, b)
    os.symlink(tmp_path / "QC-CB-C1L" / "bind", t / "rtl/a/link_dir")
    f = tmp_path / "QC-CB-C1L" / "y.sv"
    f.write_text("x")
    os.symlink(f, t / "rtl/a/y.sv")
    out = L.findings({}, None, str(t))
    rels = sorted(l.split()[3] for l in out if "LINK-OUT" in l)
    assert rels == ["physical/die_plan/qwen_compute/bind", "rtl/a/link_dir", "rtl/a/y.sv"]


def test_content_differs_from_rt_manifest(tmp_path, monkeypatch):
    import tool_root as T
    t = mktree(tmp_path / "tree")
    sha = "a" * 12 + "0" * 12
    rt = tmp_path / "rt"
    rt.mkdir()
    good = hashlib.sha256(b"X=1\n").hexdigest()
    (rt / f"{sha}.manifest.json").write_text(json.dumps({"files": {"tools/die_plan/x.py": good}}))
    monkeypatch.setattr(T, "RT_ROOTS", (str(rt),))
    monkeypatch.setattr(T.find_manifest, "__defaults__", ((str(rt),),))
    monkeypatch.setenv("OT_TOOLS_SHA", sha)
    assert L.findings({}, None, str(t)) == []
    (t / "tools/die_plan/x.py").write_text("X=2\n")                      # mutant: a hand-patched tool
    out = L.findings({}, None, str(t))
    assert classes(out) == ["CONTENT-RT"] and "tools/die_plan/x.py" in out[0]


def test_registered_in_plan_advisory():
    assert ("TREE-LINKS", "adv_tree_links") in PA.CHECKS
