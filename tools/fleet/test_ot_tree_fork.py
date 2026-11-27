"""FLOW-TREEFORK-R1 (FABLE-FLOW-2000 A4/A5): ot-tree-fork makes a private nlink-1 copy, never follows a link into an event tree,
records provenance; src_manifest verify names the writer of a broken seal; kit_wave private-spec refuses a --tree that links into an
event tree and --fork makes the tree with the fork tool."""
import hashlib
import json
import os
import re
import stat
import sys
import types
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TF = SourceFileLoader("ot_tree_fork", str(HERE / "ot-tree-fork")).load_module()
sys.path.insert(0, str(HERE.parent / "autopilot"))
import src_manifest as SM  # noqa: E402


def mk(p, text="x"):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(TF, "LOG", str(tmp_path / "home/.local/state/ot-tree-fork/forks.jsonl"))
    monkeypatch.setenv("OT_TREE_FORK_FLOOR_GB", "0")
    monkeypatch.delenv("OT_EVENT_TREE_ROOTS", raising=False)


def sealed_tree(root):
    """a read-only src_manifest-like tree (event tree)"""
    mk(root / "tools/a.py", "A=1\n")
    mk(root / "plan/plan_c.json", "{}\n")
    mk(root / SM.MANIFEST, json.dumps({"main_sha": "abc123", "manifest_hash": "f" * 64}))
    mk(root / SM.HASHFILE, "f" * 64 + "\n")
    SM.make_ro(str(root))
    return root


def test_fork_is_nlink1_copy_with_provenance(tmp_path):
    src = tmp_path / "lane/src"
    mk(src / "a/x.txt", "hello")
    os.link(src / "a/x.txt", src / "a/y.txt")             # a hardlink inside SRC becomes two private files
    os.symlink("x.txt", src / "a/rel_link")
    os.symlink(str(src / "a/x.txt"), src / "abs_link")      # absolute link into SRC -> rewritten into DST
    os.symlink("/usr/bin", src / "ext_link")                # outside, not an event tree: kept verbatim, not dereferenced
    os.chmod(src / "a/x.txt", 0o444)
    dst = tmp_path / "lane/fork"
    rec = TF.fork(str(src), str(dst), jobs=4, out=lambda *_: None)
    assert (dst / "a/x.txt").read_text() == "hello"
    for f in ("a/x.txt", "a/y.txt"):
        assert os.lstat(dst / f).st_nlink == 1
        assert os.lstat(dst / f).st_ino != os.lstat(src / f).st_ino
        assert os.lstat(dst / f).st_mode & stat.S_IWUSR          # private fork is writable
    assert os.readlink(dst / "a/rel_link") == "x.txt"
    assert os.path.realpath(dst / "abs_link") == str(dst / "a/x.txt")
    assert os.readlink(dst / "ext_link") == "/usr/bin"
    fj = json.loads((dst / ".fork.json").read_text())
    assert fj["src_real"] == str(src) and fj["files"] == 2 and fj["external_links_n"] == 1
    assert TF.verify(str(dst), str(src)) == []
    assert not list(tmp_path.glob("lane/fork.forking-*"))
    assert json.loads(open(TF.LOG).read().splitlines()[-1])["dst"] == str(dst)
    assert rec["method"] in ("copy", "reflink", "mixed")


def test_bind_fork_rebases_filelists_and_preserves_captured_identity(tmp_path):
    old_tree, new_tree = tmp_path / "old/tree", tmp_path / "new/tree"
    old_bind, new_bind = tmp_path / "old/bind", tmp_path / "new/bind"
    for root in (old_tree, new_tree):
        mk(root / "leaf.sv", "module leaf; endmodule\n")
    rtl = mk(old_bind / "rtl/top.sv", f"module top; endmodule // {old_tree}/leaf.sv:1.1\n")
    captured = {"root": "u_reset_root"}
    digest = hashlib.sha256(json.dumps(captured, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = mk(old_bind / "rtl/top.reset_tree.json", json.dumps({
        "bound_module": "top", "tree": captured, "tree_sha256": digest,
        "bound_rtl_sha256": hashlib.sha256(rtl.read_bytes()).hexdigest(),
        "provenance": {"tree": str(old_tree)},
    }))
    mk(old_bind / "bind.f", f"{old_tree}/leaf.sv\n{rtl}\n")
    mk(old_bind / "bind_report.json", json.dumps({"files": [str(rtl)]}))
    mk(old_bind / "asbuilt.json", json.dumps({"creator": str(old_tree)}))
    args = [str(old_bind), str(new_bind), "--bind-tree", str(old_tree), str(new_tree)]
    assert TF.main(args) == 0
    assert (new_bind / "bind.f").read_text().splitlines() == [str(new_tree / "leaf.sv"), str(new_bind / "rtl/top.sv")]
    assert json.loads((new_bind / "bind_report.json").read_text())["files"] == [str(new_bind / "rtl/top.sv")]
    assert (new_bind / "asbuilt.json").read_bytes() == (old_bind / "asbuilt.json").read_bytes()
    assert (new_bind / "rtl/top.sv").read_bytes() == rtl.read_bytes()
    assert (new_bind / "rtl/top.reset_tree.json").read_bytes() == receipt.read_bytes()
    assert (new_bind / "rtl/top.sv").stat().st_ino != rtl.stat().st_ino

    untrusted = tmp_path / "new/untrusted"
    args[1] = str(untrusted)
    rtl.write_text(rtl.read_text().replace(str(old_tree), str(new_tree)))
    assert TF.main(args) == 4
    assert not untrusted.exists()


def test_fork_refuses_symlink_into_event_tree(tmp_path):
    ev = sealed_tree(tmp_path / "claude/kw45/src_kv_d27d3")
    src = tmp_path / "claude/lane/tree"
    mk(src / "f.txt")
    os.symlink(str(ev), src / "evlink")
    with pytest.raises(TF.Refused) as e:
        TF.fork(str(src), str(tmp_path / "claude/lane/fork"), out=lambda *_: None)
    assert "event tree" in str(e.value)
    assert not (tmp_path / "claude/lane/fork").exists()
    rec = TF.fork(str(src), str(tmp_path / "claude/lane/fork2"), materialize=True, out=lambda *_: None)
    assert (tmp_path / "claude/lane/fork2/evlink/tools/a.py").read_text() == "A=1\n"
    assert not os.path.islink(tmp_path / "claude/lane/fork2/evlink")
    assert os.lstat(ev / "tools/a.py").st_nlink == 1                 # the event tree's link count is untouched
    assert rec["materialized"]


def test_materialize_copies_external_scratch_sources(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch/claude"
    monkeypatch.setattr(TF, "SCRATCH_TREE_RE", re.compile(re.escape(str(scratch)) + "/"))
    monkeypatch.delenv("OT_TREE_FORK_ALLOW_EXTERNAL", raising=False)
    src = scratch / "carrier"
    donor = scratch / "donor"
    original = mk(donor / "rtl/leaf.sv", "module leaf; endmodule")
    src.mkdir()
    (src / "leaf.sv").symlink_to(original)
    (src / "rtl").symlink_to(donor / "rtl")
    dst = scratch / "fork"
    with pytest.raises(TF.Refused, match="another scratch tree"):
        TF.fork(str(src), str(dst), out=lambda *_: None)
    assert not dst.exists()

    rec = TF.fork(str(src), str(dst), materialize=True, out=lambda *_: None)
    assert len(rec["materialized"]) == 2
    assert rec["external_links_n"] == 0
    assert TF.seal_check(str(dst)) == []
    for copied in (dst / "leaf.sv", dst / "rtl/leaf.sv"):
        assert not copied.is_symlink()
        assert copied.read_bytes() == original.read_bytes()
        assert copied.stat().st_ino != original.stat().st_ino
    assert original.stat().st_nlink == 1


def test_materialize_refuses_dangling_scratch_source(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch/claude"
    monkeypatch.setattr(TF, "SCRATCH_TREE_RE", re.compile(re.escape(str(scratch)) + "/"))
    src = scratch / "carrier"
    src.mkdir(parents=True)
    (src / "leaf.sv").symlink_to(scratch / "missing/leaf.sv")
    with pytest.raises(TF.Refused, match="another scratch tree"):
        TF.fork(str(src), str(scratch / "fork"), materialize=True, out=lambda *_: None)


def test_fork_of_a_symlinked_src_copies_the_tree_and_never_writes_into_it(tmp_path):
    """the 11-21 incident: the lane's path was a SYMLINK to the event tree; a fork resolves it once and copies"""
    ev = sealed_tree(tmp_path / "claude/kw45/src_kv_d27d3")
    alias = tmp_path / "claude/kv-plan-r3/d27c/tree"
    alias.parent.mkdir(parents=True)
    os.symlink(str(ev), alias)
    dst = tmp_path / "claude/hub/tree_h3"
    TF.fork(str(alias), str(dst), out=lambda *_: None)
    (dst / "plan/plan_c.json").write_text('{"changed": 1}')          # the lane's compose writes its own copy
    assert (ev / "plan/plan_c.json").read_text() == "{}\n"
    assert all(os.lstat(p).st_nlink == 1 for p in ev.rglob("*") if p.is_file())
    assert json.loads((dst / ".fork.json").read_text())["src_sealed"] is True


def test_dst_refusals(tmp_path):
    ev = sealed_tree(tmp_path / "claude/kw45/src_x")
    src = tmp_path / "claude/lane/src"
    mk(src / "f")
    for bad in (src / "inner", tmp_path / "claude/kw45/new", src):
        with pytest.raises(TF.Refused):
            TF.fork(str(src), str(bad), out=lambda *_: None)
    link = tmp_path / "claude/lane/evdir"
    os.symlink(str(ev), link)
    with pytest.raises(TF.Refused):                                    # DST behind a symlink into an event tree
        TF.fork(str(src), str(link / "sub"), out=lambda *_: None)


def test_event_root_and_verify(tmp_path, monkeypatch):
    ev = sealed_tree(tmp_path / "x/ro_tree")
    assert TF.event_root(str(ev / "tools/a.py")) == str(ev)
    assert TF.event_root(str(tmp_path / "claude/kw45/t/y")) == str(tmp_path / "claude/kw45/t")
    w = tmp_path / "writable_manifest_tree"
    mk(w / SM.MANIFEST, "{}")
    assert TF.event_root(str(w)) == ""                                 # a writable tree (a fork, a compose) is not an event tree
    monkeypatch.setenv("OT_EVENT_TREE_ROOTS", str(w))
    assert TF.event_root(str(w / "q")) == str(w)
    bad = tmp_path / "bad"
    mk(bad / "a")
    os.link(bad / "a", bad / "b")
    os.symlink(str(ev / "tools"), bad / "l")
    errs = TF.verify(str(bad))
    assert any(e.startswith("SHARED-INODE") for e in errs) and any(e.startswith("EVENT-LINK") for e in errs)
    assert TF.main(["--verify", str(bad)]) == 4
    assert TF.main(["--verify", str(tmp_path / "nope")]) == 4


def test_no_room_refused(tmp_path, monkeypatch):
    src = tmp_path / "src"
    mk(src / "f", "y" * 10)
    monkeypatch.setenv("OT_TREE_FORK_FLOOR_GB", "1e9")
    monkeypatch.setattr(TF, "reflink_ok", lambda *a: False)
    assert TF.main([str(src), str(tmp_path / "dst")]) == 5
    assert not list(tmp_path.glob("dst*"))


def test_host_runs_remote_with_script_on_stdin(tmp_path, monkeypatch):
    seen = {}

    def run(argv, input=None, text=None):
        seen.update(argv=argv, input=input)
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(TF.subprocess, "run", run)
    for k in TF.REMOTE_ENV:                     # E11-IO-STALL-1124: these travel to the remote side; this test checks the bare command
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OT_LANE", "LANE-X")
    assert TF.main(["/a/src", "/a/dst", "--host", "epyc8", "--jobs", "8"]) == 0
    assert "epyc8" in seen["argv"] and "ot-tree-fork" in seen["input"]
    assert seen["argv"][-1] == "OT_LANE=LANE-X python3 -I - /a/src /a/dst --jobs 8"


def test_seal_verify_names_the_writer(tmp_path, monkeypatch):
    """D27d3: verify --ro failed on nlink 11 and named nobody; now it names the other tree, the symlink into the tree and its lane"""
    claude = tmp_path / "claude"
    ev = claude / "kw45/src_kv_d27d3"
    mk(ev / "tools/a.py", "A=1\n")
    other = claude / "fable-fix-kv-hub/tree_h3"
    mk(other / "tools/keep.txt")
    os.link(ev / "tools/a.py", other / "tools/a.py")                  # a cp -al copy elsewhere
    os.symlink(str(ev), claude / "fable-fix-kv-hub/tree_link")       # a "private" tree that is really the event tree
    errs = ["SRC_MANIFEST DRIFT tools/a.py (hardlinked, nlink 2: a write or chmod elsewhere reaches this file)"]
    out = SM.writer_report(str(ev), errs, scan_roots=[str(claude)], budget_s=30)
    txt = "\n".join(out)
    assert str(other) in txt and "lane fable-fix-kv-hub" in txt
    assert "tree_link" in txt and "resolves into this tree" in txt
    errs2 = ["SRC_MANIFEST DRIFT plan/plan_c.json (modified: not the manifest content)"]
    mk(ev / "plan/plan_c.json")
    assert any("changed 1 file" in l and "plan/plan_c.json" in l for l in SM.writer_report(str(ev), errs2, scan_roots=[], budget_s=5))


def _kw():
    import kit_wave as KW
    return KW


def test_private_spec_refuses_tree_linked_into_event_tree(tmp_path):
    KW = _kw()
    ev = sealed_tree(tmp_path / "claude/kw45/src_kv_d27d3")
    alias = tmp_path / "claude/lane/tree_h3"
    alias.parent.mkdir(parents=True)
    os.symlink(str(ev), alias)
    die_src = tmp_path / "claude/kw45/src_kv_d26"
    die_src.mkdir(parents=True)
    assert "link into event tree" in KW.private_tree_event_refusal(str(alias), str(die_src))
    assert KW.private_tree_event_refusal(str(ev), str(die_src)) == ""          # the real path of a sealed tree: read-only use is fine
    good = tmp_path / "claude/lane/fork"
    TF.fork(str(alias), str(good), out=lambda *_: None)
    assert KW.private_tree_event_refusal(str(good), str(die_src)) == ""
    held = tmp_path / "claude/lane/held"
    mk(held / "f")
    os.symlink(str(ev / "plan"), held / "plan")
    assert "holds symlink" in KW.private_tree_event_refusal(str(held), str(die_src))


def test_private_spec_fork_calls_tool_on_gen_host(tmp_path):
    KW = _kw()
    seen = {}

    def run(argv, **kw):
        seen["argv"] = argv
        return types.SimpleNamespace(returncode=0, stdout="TREE-FORK OK", stderr="")
    rc, msg = KW.fork_private_tree("/s/src", "/d/dst", "epyc8", run=run)
    assert rc == 0 and msg == "TREE-FORK OK"
    assert seen["argv"][2].endswith("tools/fleet/ot-tree-fork") and seen["argv"][3:] == ["/s/src", "/d/dst", "--host", "epyc8"]


def test_outside_symlinks_are_listed_as_a_warning_and_still_kept(tmp_path):
    """FLEET-OPS 11-25 Q2 (report only): the default stays 'kept verbatim', the fork says how many leave the tree and where they go"""
    src = tmp_path / "lane/src"
    mk(src / "a.txt")
    for i in range(3):
        os.symlink(f"/usr/lib/x{i}", src / f"l{i}")
    msgs = []
    TF.fork(str(src), str(tmp_path / "lane/fork"), jobs=2, out=msgs.append)
    w = [m for m in msgs if "TREE-FORK WARN 3 symlink(s)" in m]
    assert w and "/usr/lib x3" in w[0]
    assert os.readlink(tmp_path / "lane/fork/l1") == "/usr/lib/x1"
    msgs.clear()
    os.environ["OT_TREE_FORK_LINK_WARN"] = "0"
    try:
        TF.fork(str(src), str(tmp_path / "lane/fork2"), jobs=2, out=msgs.append)
    finally:
        del os.environ["OT_TREE_FORK_LINK_WARN"]
    assert not any("WARN" in m for m in msgs)


def test_fork_json_is_never_written_through_a_link_and_links_into_other_scratch_trees_are_refused(tmp_path, monkeypatch):
    """FLEET-OPS 11-25 F-06 (third recurrence): a .fork.json that is a kept link rewrote the paused C1L tree"""
    monkeypatch.setattr(TF, "SCRATCH_TREE_RE", __import__("re").compile("^" + str(tmp_path) + "/claude/"))
    other = tmp_path / "claude/paused_tree"
    other.mkdir(parents=True)
    victim = mk(other / ".fork.json", "ORIGINAL")
    src = tmp_path / "claude/lane/src"
    mk(src / "a.txt")
    os.symlink(str(victim), src / ".fork.json")                 # the poisoned provenance link
    rec = TF.fork(str(src), str(tmp_path / "claude/lane/fork"), jobs=2, out=lambda *_: None)
    assert victim.read_text() == "ORIGINAL"
    f = tmp_path / "claude/lane/fork/.fork.json"
    assert f.is_file() and not f.is_symlink() and json.loads(f.read_text())["files"] >= 1
    os.symlink(str(other / "x"), src / "into_other")
    mk(other / "x")
    with pytest.raises(TF.Refused):
        TF.fork(str(src), str(tmp_path / "claude/lane/fork2"), jobs=2, out=lambda *_: None)
    assert not (tmp_path / "claude/lane/fork2").exists()
    monkeypatch.setenv("OT_TREE_FORK_ALLOW_EXTERNAL", "1")
    TF.fork(str(src), str(tmp_path / "claude/lane/fork3"), jobs=2, out=lambda *_: None)
    bad = TF.seal_check(str(src))
    assert any("into_other" in b for b in bad) and any(".fork.json is a symlink" in b or ".fork.json" in b for b in bad)
