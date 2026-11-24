"""tree_precheck: SCHEMA-KEYS / TREE-SOURCES / TREE-FRESH, report only (PRE-SCHEMA-KEYS 11-24)."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree_precheck as T  # noqa: E402

SCHEMA_PY = '''
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "die": {"type": "string"}, "asbuilt": {"type": "object"},
    "partition_types": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": False,
        "properties": {"module": {"type": "string"}%s}}}%s}}
def _check(v, s, path, errs):
    if s.get("type") == "object" and isinstance(v, dict):
        props = s.get("properties", {}); addl = s.get("additionalProperties", True)
        for k, x in v.items():
            if k in props: _check(x, props[k], f"{path}.{k}", errs)
            elif addl is False: errs.append(f"{path}: unknown key '{k}'")
            elif isinstance(addl, dict): _check(x, addl, f"{path}.{k}", errs)
def validate_structure(obj):
    errs = []; _check(obj, SCHEMA, "$", errs); return errs
'''


def _schema(root, type_extra="", top_extra=""):
    d = Path(root) / "tools" / "die_plan"
    d.mkdir(parents=True, exist_ok=True)
    (d / "schema.py").write_text(SCHEMA_PY % (type_extra, top_extra))
    return Path(root)


def _plan(p, **kw):
    raw = {"die": "s81", "partition_types": {"ta": {"module": "m_a", "read_lockup": 1}, "tb": {"module": "m_b", "read_lockup": 2}}}
    raw.update(kw)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(raw))
    return p


def test_schema_keys_tree_older_than_rt(tmp_path):
    tree = _schema(tmp_path / "tree")
    rt = _schema(tmp_path / "rt", type_extra=', "read_lockup": {"type": "integer"}')
    plan = _plan(tree / "physical/die_plan/s81/p.json")
    L = T.check_schema_keys(tree, plan, rt)
    w = [x for x in L if x.startswith("WARN")]
    assert len(w) == 1, L
    assert "$.partition_types.*.read_lockup x2 unknown to gate tree" in w[0] and "knows it (the gate tree is older" in w[0]
    assert any(x.startswith("LIST SCHEMA-KEYS") and ": 2 unknown" in x for x in L)


def test_schema_keys_both_and_rt_only(tmp_path):
    tree = _schema(tmp_path / "tree", top_extra=', "min_cycles": {"type": "object"}')
    rt = _schema(tmp_path / "rt")
    plan = _plan(tree / "p.json", min_cycles={}, zz=1)
    w = [x for x in T.check_schema_keys(tree, plan, rt) if x.startswith("WARN")]
    assert any("$.zz x1" in x and "too" in x for x in w), w
    assert any("$.min_cycles" in x and "unknown to the launch rt" in x for x in w), w


def test_schema_keys_tree_without_schema(tmp_path):
    rt = _schema(tmp_path / "rt", type_extra=', "read_lockup": {"type": "integer"}')
    (tmp_path / "tree").mkdir()
    plan = _plan(tmp_path / "tree" / "p.json")
    L = T.check_schema_keys(tmp_path / "tree", plan, rt)
    assert any("not checked against the gate tree" in x for x in L), L


def test_tree_sources_missing(tmp_path):
    tree = tmp_path / "tree"
    pd = tree / "physical/die_plan/s81"
    (tree / "rtl").mkdir(parents=True)
    (tree / "rtl/a.sv").write_text("module a; endmodule\n")
    (tree / "s81_svc_hi4_sources").mkdir()
    (tree / "s81_svc_hi4_sources/x.sv").write_text("")
    (tree / "lst.f").write_text("// list\n+incdir+rtl\nrtl/a.sv\nrtl/gone.sv\n")
    ab = {"base": "../../..", "files": ["rtl/a.sv", "lst.f", "rtl/missing.sv"],
          "prefer": ["s81_svc_hi4_sources/x.sv", "s81_svc_r5_hi4_sources/y.sv"]}
    plan = _plan(pd / "p.json", asbuilt=ab, note="type_split _remap_clock_sources rule")
    out = tmp_path / "out"
    out.mkdir()
    (out / "bind.f").write_text("rtl/a.sv\nrtl/emitted_gone.sv\n")
    L = T.check_tree_sources(tree, plan, json.loads(plan.read_text()), out=out)
    txt = "\n".join(L)
    assert "files x1 missing" in txt and "rtl/missing.sv" in txt
    assert "files:lst.f x1" in txt and "rtl/gone.sv" in txt
    assert "prefer x1" in txt and "s81_svc_r5_hi4_sources/y.sv" in txt
    assert "*_sources folder x1 missing" in txt and "s81_svc_r5_hi4_sources" in txt and "OUT/bind.f x1" in txt
    assert "s81_svc_hi4_sources;" not in txt and "_remap_clock_sources" not in txt


def test_tree_sources_clean_with_asbuilt_file(tmp_path):
    tree = tmp_path / "tree"
    (tree / "rtl").mkdir(parents=True)
    (tree / "rtl/a.sv").write_text("")
    abf = tree / "ab.json"
    abf.write_text(json.dumps({"base": ".", "files": ["rtl/a.sv"]}))
    plan = _plan(tree / "p.json")
    L = T.check_tree_sources(tree, plan, json.loads(plan.read_text()), asbuilt=abf)
    assert not [x for x in L if x.startswith("WARN")], L


def _fork(tree, src, h="", host="", t=None):
    tree.mkdir(parents=True, exist_ok=True)
    (tree / ".fork.json").write_text(json.dumps({"src": (f"{host}:" if host else "") + str(src), "src_real": str(src),
                                                 "src_host": host or os.uname().nodename, "src_manifest_hash": h,
                                                 "time_epoch": int(t or time.time()), "time_utc": "2026-11-24T10:00:00Z"}))


def test_tree_fresh_local_reseal_and_newer(tmp_path):
    src, tree = tmp_path / "src", tmp_path / "fork"
    (src / "tools/die_plan").mkdir(parents=True)
    (src / ".src-manifest.sha256").write_text("b" * 64 + "\n")
    _fork(tree, src, h="a" * 64, t=time.time() - 3600)
    (src / "tools/die_plan/schema.py").write_text("x")
    plan = _plan(tree / "p.json")
    L = T.check_tree_fresh(tree, plan)
    txt = "\n".join(L)
    assert "FORK-STALE" in txt and "bbbbbbbbbbbb" in txt and "aaaaaaaaaaaa" in txt, L
    assert "SOURCE-NEWER" in txt and "tools/die_plan 1" in txt, L


def test_tree_fresh_unsealed_source_untouched(tmp_path):
    src, tree = tmp_path / "src", tmp_path / "fork"
    (src / "rtl").mkdir(parents=True)
    (src / "rtl/a.sv").write_text("")
    os.utime(src / "rtl/a.sv", (time.time() - 7200, time.time() - 7200))
    _fork(tree, src, t=time.time() - 3600)
    L = T.check_tree_fresh(tree, _plan(tree / "p.json"))
    assert not [x for x in L if x.startswith("WARN")] and ", fresh" in L[-1], L


def test_tree_fresh_remote_gone_and_unreachable(tmp_path):
    tree = tmp_path / "fork"
    _fork(tree, "/srv/x/amd1_tree", host="epyc10")
    plan = _plan(tree / "p.json")
    seen = []
    L = T.check_tree_fresh(tree, plan, runner=lambda h, s: (seen.append(h), (0, "OT_GONE\n"))[1])
    assert seen == ["epyc10"] and "is gone" in L[0]
    L = T.check_tree_fresh(tree, plan, runner=lambda h, s: (124, "ERR TimeoutExpired"))
    assert "not reachable" in L[0]
    _fork(tree, "/srv/x", host="epyc4")
    L = T.check_tree_fresh(tree, plan, runner=lambda h, s: (_ for _ in ()).throw(AssertionError("no ssh to a terminated host")))
    assert "terminated host" in L[0]


def test_not_a_fork_and_report_only(tmp_path):
    tree = _schema(tmp_path / "tree")
    plan = _plan(tree / "p.json")
    L = T.findings(tree, plan, rt=tree)
    assert any("not an ot-tree-fork fork" in x for x in L)
    assert L[-1].startswith("LIST TREE-PRECHECK") and "report only" in L[-1]
    assert T.main(["--tree", str(tree), "--plan", str(plan), "--json", str(tmp_path / "o.json")]) == 0
    assert json.loads((tmp_path / "o.json").read_text())["findings"]


def test_runs_first_in_plan_gate_pre(tmp_path, monkeypatch):
    import plan_gate_pre as G
    tree = _schema(tmp_path / "tree")
    plan = _plan(tree / "p.json")
    monkeypatch.setenv("OT_TREE_PRECHECK", "on")
    f = G.check(str(tree), str(plan), skip=[c for c in G.CLASSES if c not in ("TREEPRE",)])
    assert f and f[0].startswith(("WARN SCHEMA-KEYS", "LIST SCHEMA-KEYS")), f[:3]
    assert any(x.startswith("LIST TREE-PRECHECK") for x in f) and not any(x.startswith("FAIL") for x in f if "TREE" in x)
    monkeypatch.setenv("OT_TREE_PRECHECK", "off")
    assert not any("TREE-PRECHECK" in x for x in G.check(str(tree), str(plan), skip=list(G.CLASSES)))


def test_bind_hook_writes_stamp(tmp_path, monkeypatch):
    import types
    import bind
    tree = _schema(tmp_path / "tree")
    plan = _plan(tree / "p.json")
    monkeypatch.setenv("OT_TREE_PRECHECK", "on")
    monkeypatch.setattr(bind.E, "REPO", tree)
    monkeypatch.setenv("OT_TREE_PRECHECK_RAN", "0")          # restored after the test: the hook sets it for the gate child
    out = tmp_path / "out"
    bind._tree_precheck(types.SimpleNamespace(plan=str(plan), asbuilt=None, out=str(out)))
    rec = json.loads((out / "tree_precheck.json").read_text())
    assert rec["tree"] == str(tree) and rec["findings"][-1].startswith("LIST TREE-PRECHECK")
    assert os.environ["OT_TREE_PRECHECK_RAN"] == "1"
