"""build_graph: stamps, staleness messages, dependency order (FABLE-PIPELINE-R1)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph as G  # noqa: E402


@pytest.fixture(autouse=True)
def _nocache(monkeypatch):
    monkeypatch.setenv("OT_BUILD_HASH_CACHE", "off")


def mk(tmp_path, runs):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"a": 1, "b": 2}))
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    (rtl / "m.sv").write_text("module m; endmodule\n")

    def rule(name, rc=0):
        def run(node):
            runs.append(name)
            return rc
        return run
    elab = G.Node("elab", [G.Input.tree("rtl", rtl, ("*.sv",))], run=rule("elab"), out=tmp_path / "o")
    bind = G.Node("bind", [G.Input.json("plan", plan)], deps=["elab"], run=rule("bind"), out=tmp_path / "o")
    kit = G.Node("kit", [G.Input.value("env", {"OT_X": "1"})], deps=["bind"], run=rule("kit"), out=tmp_path / "o")
    return plan, rtl, [kit, bind, elab]


def test_first_build_runs_all_in_order_then_nothing(tmp_path):
    runs = []
    plan, rtl, nodes = mk(tmp_path, runs)
    assert G.build(nodes, "kit", log=lambda s: None) == 0
    assert runs == ["elab", "bind", "kit"]
    assert G.build(nodes, "kit", log=lambda s: None) == 0
    assert runs == ["elab", "bind", "kit"]            # all fresh: nothing re-run
    assert all(s.fresh for _, s in G.plan(nodes, "kit"))


def test_plan_change_rebuilds_bind_and_kit_not_elab(tmp_path):
    runs = []
    plan, rtl, nodes = mk(tmp_path, runs)
    G.build(nodes, "kit", log=lambda s: None)
    del runs[:]
    plan.write_text(json.dumps({"b": 2, "a": 1}, indent=3))          # same content, other formatting: still fresh
    assert G.build(nodes, "kit", log=lambda s: None) == 0 and runs == []
    plan.write_text(json.dumps({"a": 1, "b": 3}))
    lines = []
    assert G.build(nodes, "kit", dry=True, log=lines.append) == 3 and runs == []
    txt = "\n".join(lines)
    assert "elab       FRESH" in txt and "bind       STALE" in txt and "input plan" in txt and "changed" in txt
    assert "kit        STALE   dependency bind is stale" in txt
    assert G.build(nodes, "kit", log=lambda s: None) == 0
    assert runs == ["bind", "kit"]


def test_rtl_change_rebuilds_everything_and_names_the_input(tmp_path):
    runs = []
    plan, rtl, nodes = mk(tmp_path, runs)
    G.build(nodes, "kit", log=lambda s: None)
    del runs[:]
    (rtl / "n.sv").write_text("module n; endmodule\n")
    st = dict((n.name, s) for n, s in G.plan(nodes, "kit"))
    assert not st["elab"].fresh and "input rtl" in st["elab"].why[0]
    G.build(nodes, "kit", log=lambda s: None)
    assert runs == ["elab", "bind", "kit"]


def test_failed_node_leaves_no_stamp_and_stops(tmp_path):
    runs = []
    plan, rtl, nodes = mk(tmp_path, runs)
    by = {n.name: n for n in nodes}
    by["bind"].run = lambda node: 7
    assert G.build(nodes, "kit", log=lambda s: None) == 1
    assert runs == ["elab"] and not by["bind"].stamp_path().exists() and not by["kit"].stamp_path().exists()

    def refuse(node):
        raise G.BuildError("plan key 'foo' unknown to runtime pin abc")
    by["bind"].run = refuse
    lines = []
    assert G.build(nodes, "kit", log=lines.append) == 1
    assert any("plan key 'foo' unknown to runtime pin abc" in x for x in lines)


def test_rerun_drops_stamp_first(tmp_path):
    """a node that was fresh, went stale and then fails must not keep its old stamp (the artefact may be half rewritten)"""
    runs = []
    plan, rtl, nodes = mk(tmp_path, runs)
    G.build(nodes, "kit", log=lambda s: None)
    by = {n.name: n for n in nodes}
    plan.write_text(json.dumps({"a": 9}))
    by["bind"].run = lambda node: 1
    assert G.build(nodes, "kit", log=lambda s: None) == 1
    assert not by["bind"].stamp_path().exists()


def test_missing_input_and_force(tmp_path):
    runs = []
    plan, rtl, nodes = mk(tmp_path, runs)
    G.build(nodes, "kit", log=lambda s: None)
    del runs[:]
    plan.unlink()
    st = dict((n.name, s) for n, s in G.plan(nodes, "kit"))
    assert not st["bind"].fresh and "MISSING" in " ".join(st["bind"].why)
    plan.write_text(json.dumps({"a": 1, "b": 2}))
    assert G.build(nodes, "kit", log=lambda s: None) == 0 and runs == []
    assert G.build(nodes, "kit", log=lambda s: None, force=("bind",)) == 0 and runs == ["bind"]


def test_order_errors():
    a = G.Node("a", deps=["b"])
    b = G.Node("b", deps=["a"])
    with pytest.raises(ValueError, match="cycle"):
        G.order([a, b])
    with pytest.raises(ValueError, match="unknown node"):
        G.order([G.Node("a", deps=["zz"])])
    with pytest.raises(ValueError, match="duplicate input labels"):
        G.Node("x", [G.Input.value("k", 1), G.Input.value("k", 2)])


def test_seal_and_json_drop(tmp_path):
    t = tmp_path / "t"
    t.mkdir()
    (t / "f").write_text("1")
    h0 = G.sha_tree(t)
    (t / ".src-manifest.sha256").write_text("a" * 64 + "\n")
    assert G.sha_tree(t, use_seal=True) == "seal:" + "a" * 64 and G.sha_tree(t, use_seal=False) != h0   # the seal file itself is content
    j = tmp_path / "j.json"
    j.write_text(json.dumps({"keep": 1, "note": "x"}))
    h = G.sha_json_file(j, drop=("note",))
    j.write_text(json.dumps({"keep": 1, "note": "y"}))
    assert G.sha_json_file(j, drop=("note",)) == h


def test_hash_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BUILD_HASH_CACHE", str(tmp_path / "c" / "h.json"))
    G._CACHE = None
    f = tmp_path / "f"
    f.write_text("abc")
    h = G.sha_file(f)
    G.flush_cache()
    assert (tmp_path / "c" / "h.json").is_file()
    G._CACHE = None
    assert G.sha_file(f) == h
    f.write_text("abcd")
    assert G.sha_file(f) != h
    G._CACHE = None
