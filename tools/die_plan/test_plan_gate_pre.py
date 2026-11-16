"""tests for plan_gate_pre.py (PLAN-GATE-PRE-1115): synthetic bind trees, one per failure class seen on 11-15."""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402

SCHEMA_PY = '''
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "die": {"type": "string"},
    "partition_types": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": False,
        "properties": {"reset": {"type": "object"}, "clock": {"type": "object", "additionalProperties": False, "properties": {"tap": {"type": "number"}%s}}}}},
    "asbuilt": {"type": "object"}}}
%s
def validate_structure(obj):
    errs = []
    def chk(v, s, path):
        if s.get("type") == "object":
            if not isinstance(v, dict):
                errs.append(path + ": expected object"); return
            props = s.get("properties", {}); addl = s.get("additionalProperties", True)
            for k, x in v.items():
                if k in props: chk(x, props[k], path + "." + k)
                elif addl is False: errs.append(path + ": unknown key '" + k + "'")
                elif isinstance(addl, dict): chk(x, addl, path + "." + k)
    chk(obj, SCHEMA, "$")
    return errs

def core_tap_early_ps(P, tp, corner="TT"):
    return 0.0
'''
BAND = ', "band_fixed_um": {"type": "number"}'
GEN = '''
import schema
import reset_tree as RT
from reset_tree import pin_root_copies
def f(P, tp):
    return schema.core_tap_early_ps(P, tp, "FF", 1)
def g():
    return RT.pin_root_copies(1)
'''
GEN_OK = '''
import schema
import reset_tree as RT
def f(P, tp):
    return schema.core_tap_early_ps(P, tp, "FF")
def g():
    return RT.pin_root_copies(1, 2)
'''
RT_NEW = "def pin_root_copies(a, b):\n    return a\n"
RT_OLD = "def other():\n    return 1\n"


def mk_tree(root, schema_extra="", gen=GEN_OK, rt=RT_NEW, dump=True):
    d = Path(root) / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "schema.py").write_text(SCHEMA_PY % (schema_extra, ""))
    (d / "gen_phys.py").write_text(gen)
    (d / "reset_tree.py").write_text(rt)
    (d / "test_x.py").write_text("import schema\nschema.nothing_here()\n")   # tests are not callers
    if dump:   # in a child process: never import the tree's `schema` into this session (the real one is on sys.path)
        out = subprocess.run([sys.executable, "-I", "-c", "import json, sys; sys.path.insert(0, sys.argv[1]); import schema; "
                              "print(json.dumps(schema.SCHEMA, indent=1))", str(d)],
                             capture_output=True, text=True, check=True).stdout
        (d / "die_plan.schema.json").write_text(out)
    return Path(root)


def plan(tmp, keys=None, rows=None, asbuilt=None, name="plan.json"):
    clock = {"tap": 1.0}
    clock.update(keys or {})
    t = {"clock": clock}
    if rows is not None:
        t["reset"] = {"consumer_localization": rows}
    p = {"die": "x", "partition_types": {"ty1": t}}
    if asbuilt is not None:
        p["asbuilt"] = asbuilt
    f = Path(tmp) / name
    f.write_text(json.dumps(p))
    return f


def chk(*a, **k):
    """FAIL findings only (WARN lines are advisory)"""
    return [x for x in G.check(*a, **k) if x.startswith("FAIL")]


def kinds(fs):
    return sorted({x.split()[1] for x in fs if x.startswith("FAIL")})


def test_clean_tree_passes(tmp_path):
    tree = mk_tree(tmp_path / "t")
    assert chk(tree, plan(tmp_path)) == []


def test_schema_unknown_key_is_the_g1d_miss(tmp_path):
    tree = mk_tree(tmp_path / "t")          # bind tree: B6gE schema, no band keys
    fs = chk(tree, plan(tmp_path, {"band_fixed_um": 3}))
    assert kinds(fs) == ["SCHEMA-UNKNOWN-KEY"] and "band_fixed_um" in fs[0] and "overlay" in fs[0]


def test_schema_tree_skew_vs_compose_tree(tmp_path):
    bind = mk_tree(tmp_path / "bind")
    comp = mk_tree(tmp_path / "comp", schema_extra=BAND)
    fs = chk(bind, plan(tmp_path), compose_tree=comp)
    assert kinds(fs) == ["SCHEMA-TREE-SKEW"] and "band_fixed_um" in fs[0]
    assert chk(comp, plan(tmp_path, {"band_fixed_um": 1}), compose_tree=comp) == []


def test_schema_json_stale_is_a_warning_only(tmp_path):
    tree = mk_tree(tmp_path / "t")
    (tree / "tools/die_plan/die_plan.schema.json").write_text("{}\n")
    fs = G.check(tree, plan(tmp_path))
    assert fs and fs[0].startswith("WARN SCHEMA-JSON-STALE") and kinds(fs) == []


def test_schema_does_not_import(tmp_path):
    tree = mk_tree(tmp_path / "t")
    (tree / "tools/die_plan/schema.py").write_text("raise RuntimeError('boom')\n")
    fs = chk(tree, plan(tmp_path), skip=("TOOLS",))
    assert kinds(fs) == ["SCHEMA-LOAD"] and "boom" in fs[0]


def test_tools_skew_is_the_kv_7u_tree(tmp_path):
    tree = mk_tree(tmp_path / "t", gen=GEN, rt=RT_OLD)
    fs = chk(tree, plan(tmp_path))
    txt = "\n".join(fs)
    assert kinds(fs) == ["TOOLS-SKEW"]
    assert "core_tap_early_ps" in txt and "4 positional arguments, def takes 3" in txt   # arity
    assert "reset_tree.pin_root_copies" in txt                                                  # missing attribute
    assert "from reset_tree import pin_root_copies" in txt                                       # missing import


def test_tools_ignores_shadowed_guarded_and_dunder(tmp_path):
    gen = textwrap.dedent('''
        import schema
        import reset_tree as RT
        def a(schema):
            return schema.get("x")                 # parameter shadows the module
        def b():
            return hasattr(RT, "later") and RT.later
        def c():
            return RT.__file__
        def d():
            import reset_tree as LC                # same local name, two modules: ambiguous
            return LC.nothing
        def e():
            import schema as LC
            return LC.nothing
    ''')
    tree = mk_tree(tmp_path / "t", gen=gen)
    assert chk(tree, plan(tmp_path)) == []


def test_tools_keyword_and_star_calls(tmp_path):
    gen = "import schema\ndef a(x):\n    schema.core_tap_early_ps(*x)\n    schema.core_tap_early_ps(1, 2, corner='FF')\n" \
          "    schema.core_tap_early_ps(1, 2, nope=1)\n"
    tree = mk_tree(tmp_path / "t", gen=gen)
    fs = chk(tree, plan(tmp_path))
    assert len(fs) == 1 and "unexpected keyword 'nope'" in fs[0]


def test_tools_syntax_error_named(tmp_path):
    tree = mk_tree(tmp_path / "t")
    (tree / "tools/die_plan/bad.py").write_text("def (:\n")
    fs = chk(tree, plan(tmp_path))
    assert kinds(fs) == ["TOOLS-SYNTAX"] and "bad.py" in fs[0]


def test_input_closure_names_every_missing_path(tmp_path):
    tree = mk_tree(tmp_path / "t")
    base = tmp_path / "src"
    (base / "rtl").mkdir(parents=True)
    (base / "rtl/a.sv").write_text("x")
    (base / "hp").mkdir()
    ab = {"base": str(base), "files": ["rtl/a.sv", "rtl/gone.sv"], "rtl_roots": ["rtl", "nodir"],
          "hard_params": ["hp/col_h9.hard_params.json"], "map_file": str(tmp_path / "map.json"),
          "clock_landing_table": "sc.json"}
    fs = chk(tree, plan(tmp_path, asbuilt=ab))
    txt = "\n".join(fs)
    assert kinds(fs) == ["INPUT-MISSING"]
    for want in ("rtl/gone.sv", "nodir", "col_h9.hard_params.json", "map.json", "sc.json"):
        assert want in txt
    assert "a.sv" not in txt.replace("gone.sv", "")
    (base / "hp/col_h9.hard_params.json").write_text("{}")
    fs2 = chk(tree, plan(tmp_path, asbuilt=ab))
    assert "col_h9" not in "\n".join(fs2)


def test_input_relative_base_and_override_manifest(tmp_path):
    tree = mk_tree(tmp_path / "t")
    (tmp_path / "m/src").mkdir(parents=True)
    (tmp_path / "m/src/f.sv").write_text("x")
    abf = tmp_path / "m/ab.json"
    abf.write_text(json.dumps({"base": "src", "files": ["f.sv", "g.sv"]}))
    fs = chk(tree, plan(tmp_path), asbuilt=abf)
    assert len(fs) == 1 and "g.sv" in fs[0] and "f.sv" not in fs[0].replace("g.sv", "")


def test_input_no_asbuilt_warn_or_fail(tmp_path):
    tree = mk_tree(tmp_path / "t")
    assert kinds(chk(tree, plan(tmp_path))) == []
    assert kinds(chk(tree, plan(tmp_path), require_asbuilt=True)) == ["INPUT-NO-ASBUILT"]


def test_rows_need_proof_unless_equal_to_baseline(tmp_path):
    tree = mk_tree(tmp_path / "t")
    base = plan(tmp_path, name="base.json")
    p = plan(tmp_path, rows=[{"a": 1}])
    fs = chk(tree, p, baseline=base)
    assert kinds(fs) == ["ROWS-NO-PROOF"] and "ty1" in fs[0]
    assert chk(tree, p, baseline=plan(tmp_path, rows=[{"a": 1}], name="b2.json")) == []   # unchanged rows
    assert kinds(chk(tree, p)) == ["ROWS-NO-PROOF"]                                        # no baseline: all rows


def test_rows_proof_pass_stale_and_withdrawn(tmp_path):
    tree = mk_tree(tmp_path / "t")
    base = plan(tmp_path, name="base.json")
    p = plan(tmp_path, rows=[{"a": 1}])
    pf = tmp_path / "proof.json"
    pr = G.mkproof(p, base, "QC-SC-ROWS-1115", "ev.log")
    pf.write_text(json.dumps(pr))
    assert chk(tree, p, baseline=base, proofs=[pf]) == []
    p2 = plan(tmp_path, rows=[{"a": 2}], name="p2.json")                    # rows changed after the dry-run
    assert kinds(chk(tree, p2, baseline=base, proofs=[pf])) == ["ROWS-PROOF-STALE"]
    pr["result"] = "withdrawn"
    pf.write_text(json.dumps(pr))
    assert kinds(chk(tree, p, baseline=base, proofs=[pf])) == ["ROWS-NO-PROOF", "ROWS-PROOF-NOT-PASS"]
    pf.write_text(json.dumps({"schema": "other"}))
    assert "ROWS-PROOF-SCHEMA" in kinds(chk(tree, p, baseline=base, proofs=[pf]))


def test_rows_file_needs_proof_naming_its_sha(tmp_path):
    tree = mk_tree(tmp_path / "t")
    rf = tmp_path / "rows.json"
    rf.write_text("[1]")
    p = plan(tmp_path)
    assert kinds(chk(tree, p, rows_files=[rf])) == ["ROWS-NO-PROOF"]
    import hashlib
    sha = hashlib.sha256(rf.read_bytes()).hexdigest()[:16]
    (tmp_path / "rows.json.proof.json").write_text(json.dumps(
        {"schema": G.PROOF_SCHEMA, "result": "pass", "files": {"rows.json": sha}}))
    assert chk(tree, p, rows_files=[rf]) == []


def test_cli_exit_codes_and_mkproof(tmp_path):
    tree = mk_tree(tmp_path / "t")
    p = plan(tmp_path, {"band_fixed_um": 3})
    me = Path(G.__file__)
    r = subprocess.run([sys.executable, "-I", str(me), "check", "--tree", str(tree), "--plan", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "PLAN-GATE-PRE FAIL" in r.stdout and "SCHEMA-UNKNOWN-KEY" in r.stdout
    ok = plan(tmp_path, name="ok.json")
    r = subprocess.run([sys.executable, "-I", str(me), "check", "--tree", str(tree), "--plan", str(ok)],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "PLAN-GATE-PRE PASS" in r.stdout
    r = subprocess.run([sys.executable, "-I", str(me), "check", "--tree", str(tree), "--plan", str(tmp_path / "none.json")],
                       capture_output=True, text=True)
    assert r.returncode == 2
    rp = plan(tmp_path, rows=[{"a": 1}], name="rp.json")
    out = tmp_path / "pf.json"
    r = subprocess.run([sys.executable, "-I", str(me), "mkproof", "--plan", str(rp), "--lane", "L", "--evidence", "e",
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(out.read_text())["types"].keys() == {"ty1"}
