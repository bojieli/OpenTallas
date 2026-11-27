"""P-FLAG-SCHEMA-UNREGISTERED (FABLE-FLOW-0910 b11): every plan key a generator reads must be declared in the plan schema.

HEAD East 48-way prep rejected an unknown key at 22:00 11-26 and QC PRE refused tap_sites_um (fixed 16da0e083c11) because a
generator read a key that die_plan.schema.json did not declare.  This test lists, by AST, every `<section>.get("k")` /
`<section>["k"]` read in the plan generators, where <section> is a top-level plan section (clock, reset, budgets, latency, ...),
directly, through `(x.get("clock") or {})`, or through a local name bound to such a read, and fails on a key the schema declares
under no object named <section>.  An exemption needs a reason in EXEMPT.
"""
import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTIONS = ("clock", "reset", "budgets", "latency", "pin_track_pg", "clk_land_clear", "tap_reach", "gpl_td", "street_sizing",
            "land_reach", "relay_spread", "ft_core_detour", "die", "infrastructure")
FILES = ("gen.py", "gen_phys.py", "gen_rtl.py", "gen_lane_latcheck.py", "gen_cb_strip.py", "die_clock.py", "die_infra.py")
# (section, key): reason.  These dicts are NOT the plan section even though the local name or key matches.
EXEMPT = {
    ("clock", "pin_layer"): "gen_phys writes the kit BUDGET json (bud['clock']), not the plan clock section",
    ("reset", "snap"): "die_infra writes its own metadata dict (meta['reset']), not the plan reset section",
}


def declared():
    out = {}

    def walk(x, name=None):
        if isinstance(x, dict):
            props = x.get("properties")
            if isinstance(props, dict):
                if name:
                    out.setdefault(name, set()).update(props)
                for k, v in props.items():
                    walk(v, k)
            for k, v in x.items():
                if k != "properties":
                    walk(v, name if k in ("items", "additionalProperties", "patternProperties") else None)
        elif isinstance(x, list):
            for v in x:
                walk(v, name)

    walk(json.loads((HERE / "die_plan.schema.json").read_text()))
    return out


def _section(n, sections):
    if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or):
        return _section(n.values[0], sections)
    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args
            and isinstance(n.args[0], ast.Constant) and n.args[0].value in sections):
        return n.args[0].value
    if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value in sections:
        return n.slice.value
    return None


def reads(src, sections=SECTIONS):
    """{(section, key): [line, ...]} of the literal plan-section key reads in one module source"""
    found = {}
    tree = ast.parse(src)
    for fn in [tree] + [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        var = {}
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                s = _section(n.value, sections)
                if s:
                    var[n.targets[0].id] = s
        for n in ast.walk(fn):
            key = base = None
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                key, base = n.args[0].value, n.func.value
            elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
                key, base = n.slice.value, n.value
            if key is None:
                continue
            s = _section(base, sections) or (var.get(base.id) if isinstance(base, ast.Name) else None)
            if s:
                found.setdefault((s, key), set()).add(n.lineno)
    return {k: sorted(v) for k, v in found.items()}


def test_scanner_finds_chained_and_bound_reads():
    src = ('def f(t):\n    a = (t.get("clock") or {}).get("k1")\n    c = t.get("clock", {})\n    b = c.get("k2")\n'
           '    d = t["reset"]["k3"]\n    e = other.get("k4")\n')
    assert set(reads(src)) == {("clock", "k1"), ("clock", "k2"), ("reset", "k3")}


def test_every_generator_plan_key_is_declared_in_the_schema():
    dec = declared()
    bad = []
    for f in FILES:
        p = HERE / f
        if not p.is_file():
            continue
        for (sec, key), lines in reads(p.read_text()).items():
            if key not in dec.get(sec, ()) and (sec, key) not in EXEMPT:
                bad.append(f"{f}:{lines[0]} reads {sec}.{key} but the schema declares no {sec}.{key}")
    assert not bad, "P-FLAG-SCHEMA-UNREGISTERED:\n" + "\n".join(bad)


def test_reserved_pocket_flag_is_declared():
    assert "reserved_pocket_fill" in declared()["clock"]
