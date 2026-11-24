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
        "properties": {"reset": {"type": "object"}, "hard": {"type": "boolean"}, "hard_cores": {"type": "array"}, "ft_slots": {"type": "array"}, "internal_stations": {"type": "array"}, "clock": {"type": "object", "additionalProperties": False, "properties": {"tap": {"type": "number"}%s}}}}},
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


def geom_plan(tmp, cores, ft=None, st=None, rst=None, name="geom.json", hard=False):
    t = {"clock": {"tap": 1.0}, "hard_cores": cores}
    if ft:
        t["ft_slots"] = ft
    if st:
        t["internal_stations"] = st
    if rst:
        t["reset"] = rst
    p = {"die": "x", "partition_types": {"ty1": t, "ty2": {"clock": {"tap": 1.0}}}}
    f = Path(tmp) / name
    f.write_text(json.dumps(p))
    return f


RING = {"inst": "cl_i_slg_Q_N_krsp", "origin_um": [544.0, 1261.0], "outline_um": [92.0, 55.0], "orient": "MX"}
HEAD = {"inst": "head0_e2", "origin_um": [60.0, 336.0], "outline_um": [216.0, 216.0], "orient": "R0"}


def test_geom_lists_every_station_relay_and_reset_site_inside_a_ring_core(tmp_path):
    tree = mk_tree(tmp_path / "t")
    p = geom_plan(tmp_path, [RING],
                  st=[{"conn": "bus:krsp", "regs_um": [[306, 468], [605, 1300], [610, 1270]]}],
                  ft=[{"name": "ft0", "regs_um": [[560, 1280]]}],
                  rst={"local_taps_um": [[8.64, 8.64], [600, 1300]], "tap_um": [590, 1262]})
    fs = chk(tree, p)
    assert kinds(fs) == ["GEOM-STATION-IN-CORE"] and len(fs) == 5
    txt = "\n".join(fs)
    for want in ("(605, 1300)", "(610, 1270)", "(560, 1280)", "reset.local_taps_um[1]", "reset.tap_um", "cl_i_slg_Q_N_krsp",
                 "type ty1"):
        assert want in txt
    assert "(306, 468)" not in txt


def test_geom_edges_other_types_and_hard_types_do_not_count(tmp_path):
    tree = mk_tree(tmp_path / "t")
    p = geom_plan(tmp_path, [RING], st=[{"conn": "c", "regs_um": [[544.0, 1280], [636.0, 1280], [600, 1316.0], [600, 1261.0]]}])
    assert chk(tree, p) == []                                   # on the edge = not inside
    raw = json.loads(p.read_text())
    raw["partition_types"]["ty2"]["internal_stations"] = [{"conn": "c", "regs_um": [[600, 1280]]}]   # ty2 has no cores
    p.write_text(json.dumps(raw))
    assert chk(tree, p) == []
    raw["partition_types"]["ty1"]["hard"] = True
    raw["partition_types"]["ty1"]["internal_stations"] = [{"conn": "c", "regs_um": [[600, 1280]]}]
    p.write_text(json.dumps(raw))
    assert chk(tree, p) == []
    assert len(chk(tree, geom_plan(tmp_path, [RING], st=[{"conn": "c", "regs_um": [[543.5, 1280]]}], name="h.json"))) == 0
    assert len(G.check_geom(geom_plan(tmp_path, [RING], st=[{"conn": "c", "regs_um": [[543.5, 1280]]}], name="h2.json"),
                            halo=1.0)) == 1


def test_geom_other_cores_warn_unless_strict_or_new_vs_baseline(tmp_path):
    tree = mk_tree(tmp_path / "t")
    p = geom_plan(tmp_path, [HEAD, RING], st=[{"conn": "c", "regs_um": [[168.0, 532.0], [605, 1300]]}])
    fs = G.check(tree, p)
    assert [x.split()[1] for x in fs if x.startswith("FAIL")] == ["GEOM-STATION-IN-CORE"]       # the ring core only
    assert any(x.startswith("WARN GEOM-INHERITED 1 ") for x in fs)
    assert len(chk(tree, p, strict_cores=True)) == 2
    assert chk(tree, p, skip=("GEOM",)) == []
    base = geom_plan(tmp_path, [HEAD, RING], st=[{"conn": "c", "regs_um": [[168.0, 532.0], [605, 1300]]}], name="base.json")
    assert chk(tree, p, baseline=base) == []                                                    # all inherited
    p2 = geom_plan(tmp_path, [HEAD, RING], st=[{"conn": "c", "regs_um": [[168.0, 532.0], [170.0, 540.0]]}], name="p2.json")
    fs = chk(tree, p2, baseline=base)
    assert len(fs) == 1 and "(170, 540)" in fs[0] and "head0_e2" in fs[0]                       # a new overlap with any core


def test_cli_strict_cores_flag(tmp_path):
    tree = mk_tree(tmp_path / "t")
    p = geom_plan(tmp_path, [HEAD], st=[{"conn": "c", "regs_um": [[168.0, 532.0]]}])
    me = Path(G.__file__)
    r = subprocess.run([sys.executable, "-I", str(me), "check", "--tree", str(tree), "--plan", str(p)], capture_output=True, text=True)
    assert r.returncode == 0 and "GEOM-INHERITED" in r.stdout
    r = subprocess.run([sys.executable, "-I", str(me), "check", "--tree", str(tree), "--plan", str(p), "--strict-cores"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "GEOM-STATION-IN-CORE" in r.stdout


def test_tools_sys_path_insert_resolves_imports_in_that_dir(tmp_path):
    """TOOLS-CONVERGE-1116: ca_region_table does sys.path.insert(tools/s81_head) and imports tools/s81_head/fallback_land.py; a
    different tools/die_plan/fallback_land.py of the same name must not be the one its attributes are checked against."""
    import plan_gate_pre as G
    dp = tmp_path / "tools" / "die_plan"
    sh = tmp_path / "tools" / "s81_head"
    dp.mkdir(parents=True)
    sh.mkdir(parents=True)
    (dp / "fallback_land.py").write_text("def other():\n    return 1\n")
    (sh / "fallback_land.py").write_text("CYC = 3\n\ndef part_boxes(p):\n    return p\n")
    (dp / "ca_region_table.py").write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1] / \"s81_head\"))\n"
        "import fallback_land as F\n\ndef f(p):\n    return F.part_boxes(p), F.CYC\n")
    assert G.check_tools(str(tmp_path)) == []
    (sh / "fallback_land.py").write_text("CYC = 3\n")          # a real miss in the dir it imports from is still found
    assert any("part_boxes" in x for x in G.check_tools(str(tmp_path)))


def test_probe_timeout_scales_with_plan_and_load(tmp_path):
    """S81-DIE-R3 11-19: no fixed 180 s: plan size and host load scale it; the env setting wins"""
    small = tmp_path / "p.json"; small.write_text("{}")
    big = tmp_path / "big.json"; big.write_bytes(b" " * 50_000_000)
    assert G.probe_timeout(str(small), env={}, load=0, ncpu=96) == pytest.approx(180, abs=1)
    assert G.probe_timeout(str(big), env={}, load=0, ncpu=96) == pytest.approx(180 + 20 * 50, abs=1)
    assert G.probe_timeout(str(small), env={}, load=290, ncpu=96) == pytest.approx(180 * 290 / 96, abs=1)
    assert G.probe_timeout(None, env={}, load=10, ncpu=96) == pytest.approx(180, abs=1)
    assert G.probe_timeout(str(big), env={"OT_PLAN_GATE_PRE_PROBE_S": "900"}, load=290, ncpu=96) == 900
    assert G.probe_timeout(str(small), env={"OT_PLAN_GATE_PRE_PROBE_S": "junk"}, load=0, ncpu=96) == pytest.approx(180, abs=1)

def _ss_sidecar(settle, raw):
    return {"count_aligned": {"root_settle_cycles": settle},
            "collector": {"root": "r", "boot_budget": {"ring_train_max_cycles": 21, "raw_reset_release_max_cycles": raw,
                                                        "local_registered_depths": {"r": 21, "a": 5}},
                          "edges": [{"src": "a", "dst": "r", "seam": True, "boot_transport_extra_cycles": 3}]}}


def test_start_settle_bound_matches_collector_model():
    # a: raw + 21 + 5; root: max(raw + 21, a + (21 train over a seam)) + 21
    assert G.start_settle_bound(_ss_sidecar(64, 331), 331) == 331 + 21 + 5 + 21 + 21
    assert G.start_settle_bound({}, 331) is None


def test_start_settle_warn_then_fail(tmp_path):
    sc = tmp_path / "sc.json"
    sc.write_text(json.dumps(_ss_sidecar(64, 331)))
    warn = G.check_startsettle(str(tmp_path), "unused", str(sc), None, today="2026-11-24", max_release=331)
    assert warn and all(w.startswith("WARN START-SETTLE") for w in warn)
    fail = G.check_startsettle(str(tmp_path), "unused", str(sc), None, today="2026-11-25", max_release=331)
    assert fail and all(w.startswith("FAIL START-SETTLE") for w in fail)
    sc.write_text(json.dumps(_ss_sidecar(422, 354)))
    assert G.check_startsettle(str(tmp_path), "unused", str(sc), None, today="2026-11-25", max_release=354) == []
    stale = G.check_startsettle(str(tmp_path), "unused", str(sc), None, today="2026-11-25", max_release=331)
    assert any("raw_reset_release_max_cycles 354 != plan max release 331" in w for w in stale)
