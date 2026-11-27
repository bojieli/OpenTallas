"""P-FLAG-SCHEMA-UNREGISTERED guard: every plan key a die_plan tool READS must be registered in schema.SCHEMA.

Plans fail PRE with SCHEMA-UNKNOWN-KEY when a flag lands in a generator without a schema entry (clk_land_clear 6c3946992b3,
QC clock.tap_sites_um 16da0e083c11, HEAD East 48-way prep 11-26 22:00).  This test statically (AST, no import of the tools)
collects the plan-dict reads of tools/die_plan/*.py and asserts each key path resolves in schema.SCHEMA.

Reliable patterns (the scanner follows only what it can prove is a plan dict):
  roots     a name `raw` / `plan`, or an attribute `.raw` / `.plan` (self.raw, P.raw)  -> the plan top level
  steps     X["lit"]  X.get("lit"[, d])  "lit" in X          -> key under X;   X[non-literal] / loop var over X.items()/.values()/X
            -> the schema's additionalProperties / items branch ("*")
  aliases   `a = <chain>` (also `chain or {}`, `chain if c else {}`), `for k, v in <chain>.items()`, `for v in <chain>.values()`,
            comprehension targets; assignment of anything else un-aliases the name.  Linear per function, branches ignored.
  skipped   writes (Store context, setdefault, pop): a tool deriving a key in memory is not a plan input.
A key is a violation only when its parent schema node is CLOSED (additionalProperties False); free-form nodes
({"type": "object"}, additionalProperties schema) accept anything, as schema.validate does.

A violation means: register the key in schema.py (real plan input) or, if the dict is not a plan, add the (file, path) to
NOT_PLAN below with the reason.
"""
import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402

ROOT_NAMES = {"raw", "plan"}
ROOT_ATTRS = {"raw", "plan"}
SCAN_GLOBS = ["*.py"]
SKIP_FILE = lambda p: p.name.startswith("test_") or p.name == "schema.py" or p.name == "conftest.py"  # noqa: E731

# (file basename, "dotted.path") -> reason: reads of a dict that is called raw/plan but is not a die plan, or a key the code
# only probes for legacy plans.  Keep each entry commented; an entry that stops matching fails test_allowlist_not_stale.
# Key = (file, dotted path prefix); "" = every read in that file.  A prefix matches the path itself and everything below it.
_MANIFEST = "reads the as-built / bind manifest (opentallas as-built JSON), which the code calls plan/raw; a die plan has no 'asbuilt' key"
_CORE = "dict named plan/raw here is a core-infra / hook plan (core_tree, cells, clock_ndr ...), not a die plan"
NOT_PLAN = {
    ("adv_core_param.py", "asbuilt"): _MANIFEST,
    ("bind.py", "asbuilt"): _MANIFEST,
    ("bind_verify.py", "asbuilt"): _MANIFEST,
    ("kit_topology.py", "asbuilt"): _MANIFEST,
    ("manifest_paths.py", "asbuilt"): _MANIFEST,
    ("plan_gate_pre.py", "asbuilt"): _MANIFEST,
    ("reset_boot_contract.py", "asbuilt"): _MANIFEST,
    ("reset_boot_contract.py", "reset_boot_contract"): "reset/BOOT contract pointer: manifest-level key, checked equal on plan and as-built manifest",
    ("tree_precheck.py", "asbuilt"): _MANIFEST,
    ("adv_gpl_td.py", "types"): "legacy fallback `plan.get('partition_types') or plan.get('types')`: the 'types' spelling is not a plan key",
    ("clock_landing_plan.py", "partition_types.*._cland_geom"): "underscore key is derived in memory by the landing planner on P.types, never plan input",
    ("core_clock_contract.py", ""): "core clock contract record (pins/signed/signoff_*), not a die plan",
    ("core_clock_routing.py", ""): _CORE,
    ("core_infra.py", ""): _CORE,
    ("core_tap_retarget.py", ""): "partition types given as a list of {name: ...} records (legacy shape), not a schema'd plan dict",
    ("count_align_bind.py", ""): "count-aligned crossing PLAN (count_align_plan.py --out: summary/regions/crossings), not a die plan",
    ("fallback_land.py", ""): "types list/dict argument shaped {name: ...}; same legacy list form as core_tap_retarget",
    ("ft_ports.py", ""): "pushdown feed-through declaration spec (arcs), not a die plan",
    ("latpkg_check.py", ""): "reads a latency package record whose 'name' is its own field",
    ("orient_realize.py", ""): "layer table (layers[].name), schema.ASAP7_LAYERS shape, not a die plan",
    ("qc_clk_mesh3.py", ""): "QC-CLK-MESH-3 mesh spec (spine/top/stages/top_repeaters), not a die plan",
    ("class_merge.py", "lanes.*.spine"): "probe of a lane flag no die plan sets; lanes are closed in the schema so a plan with it already fails PRE",
    ("strip_body.py", "grid_um"): "legacy top-level probe; the plan key is die.grid_um (registered)",
    ("routed_reach.py", "layer_budget"): "fallback after die.layer_budget (registered); top-level spelling is not a plan key",
}


# ---------------------------------------------------------------------------------------------------------------- schema side
def _subs(node):
    out = [node]
    for k in ("allOf", "anyOf", "oneOf"):
        for s in node.get(k, []) or []:
            out += _subs(s)
    for k in ("if", "then", "else"):
        if isinstance(node.get(k), dict):
            out += _subs(node[k])
    return out


def _step(node, key):
    """-> (child, violation): child None = free-form / unknown (stop checking); violation True = closed node lacks key"""
    if not isinstance(node, dict):
        return None, False
    subs = _subs(node)
    if key == "*":
        kids = []
        for s in subs:
            it = s.get("items")
            if isinstance(it, dict):
                kids.append(it)
            ap = s.get("additionalProperties")
            if isinstance(ap, dict):
                kids.append(ap)
        return ({"allOf": kids} if kids else None), False
    kids, closed, anyprops = [], False, False
    for s in subs:
        props = s.get("properties")
        if isinstance(props, dict):
            anyprops = True
            if key in props:
                kids.append(props[key])
        if s.get("additionalProperties") is False:
            closed = True
        elif isinstance(s.get("additionalProperties"), dict) or s.get("additionalProperties") is True:
            ap = s["additionalProperties"]
            if not (isinstance(s.get("properties"), dict) and key in s["properties"]):
                return (ap if isinstance(ap, dict) else None), False
        if s.get("patternProperties"):
            return None, False
    if kids:
        return {"allOf": kids}, False
    if closed and anyprops:
        return None, True
    return None, False


def unregistered(path, key):
    """True when path + (key,) names a key a closed schema node does not register"""
    node = schema.SCHEMA
    for step in tuple(path) + (key,):
        node, bad = _step(node, step)
        if bad:
            return True
        if node is None:
            return False
    return False


# ---------------------------------------------------------------------------------------------------------------- AST side
class Scan(ast.NodeVisitor):
    def __init__(self, fname):
        self.f = fname
        self.env = {}
        self.reads = []          # (line, path, key)

    # -- chain resolution -------------------------------------------------------------------------------------------
    def chain(self, e, record=True):
        """-> path tuple of the plan node e denotes, or None"""
        if isinstance(e, ast.Name):
            if e.id in self.env:
                return self.env[e.id]
            return () if e.id in ROOT_NAMES and e.id not in self.env else None
        if isinstance(e, ast.Attribute):
            if e.attr in ROOT_ATTRS and isinstance(e.value, ast.Name):
                return ()
            return None
        if isinstance(e, ast.Subscript):
            par = self.chain(e.value, record)
            if par is None:
                return None
            s = e.slice
            if isinstance(s, ast.Constant) and isinstance(s.value, str):
                if record and isinstance(e.ctx, ast.Load):
                    self.reads.append((e.lineno, par, s.value))
                return par + (s.value,)
            return par + ("*",)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "get" and e.args:
            par = self.chain(e.func.value, record)
            a = e.args[0]
            if par is not None and isinstance(a, ast.Constant) and isinstance(a.value, str):
                if record:
                    self.reads.append((e.lineno, par, a.value))
                return par + (a.value,)
            return None
        if isinstance(e, ast.BoolOp):
            for v in e.values:
                c = self.chain(v, record)
                if c is not None:
                    return c
            return None
        if isinstance(e, ast.IfExp):
            for v in (e.body, e.orelse):
                c = self.chain(v, False)
                if c is not None:
                    return self.chain(v, record)
            return None
        return None

    def bind(self, target, path):
        if isinstance(target, ast.Name):
            if path is None:
                self.env.pop(target.id, None)
                if target.id in ROOT_NAMES:
                    self.env[target.id] = None      # rebound to a non-plan value
            else:
                self.env[target.id] = path
        elif isinstance(target, (ast.Tuple, ast.List)):
            for t in target.elts:
                self.bind(t, None)

    def bind_iter(self, target, it):
        """for/comprehension target over iterable expression it"""
        kind = None
        base = it
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr in ("items", "values") and not it.args:
            kind, base = it.func.attr, it.func.value
        par = self.chain(base)
        if par is None:
            self.bind(target, None)
            return
        if kind == "items" and isinstance(target, (ast.Tuple, ast.List)) and len(target.elts) == 2:
            self.bind(target.elts[0], None)
            self.bind(target.elts[1], par + ("*",))
        elif kind != "items":
            self.bind(target, par + ("*",))
        else:
            self.bind(target, None)

    # -- visitors ---------------------------------------------------------------------------------------------------
    def visit_FunctionDef(self, n):
        saved = dict(self.env)
        for a in n.args.args + n.args.kwonlyargs:
            self.env.pop(a.arg, None)
            if a.arg in ROOT_NAMES:
                self.env[a.arg] = ()
        for s in n.body:
            self.visit(s)
        self.env = saved

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, n):
        self.visit(n.value)
        path = self.chain(n.value, record=False)
        for t in n.targets:
            self.bind(t, path)
            if isinstance(t, ast.Subscript):
                pass

    def visit_AnnAssign(self, n):
        if n.value is not None:
            self.visit(n.value)
            self.bind(n.target, self.chain(n.value, record=False))

    def visit_For(self, n):
        self.visit(n.iter)
        self.bind_iter(n.target, n.iter)
        for s in n.body + n.orelse:
            self.visit(s)

    def _comp(self, n):
        saved = dict(self.env)
        for g in n.generators:
            self.visit(g.iter)
            self.bind_iter(g.target, g.iter)
            for c in g.ifs:
                self.visit(c)
        for fld in ("elt", "key", "value"):
            if hasattr(n, fld):
                self.visit(getattr(n, fld))
        self.env = saved

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _comp

    def visit_Subscript(self, n):
        self.chain(n)
        self.generic_visit(n)

    def visit_Call(self, n):
        if isinstance(n.func, ast.Attribute) and n.func.attr == "get":
            self.chain(n)
        self.generic_visit(n)

    def visit_Compare(self, n):
        if (len(n.ops) == 1 and isinstance(n.ops[0], (ast.In, ast.NotIn)) and isinstance(n.left, ast.Constant)
                and isinstance(n.left.value, str)):
            par = self.chain(n.comparators[0], record=False)
            if par is not None:
                self.reads.append((n.lineno, par, n.left.value))
        self.generic_visit(n)


def scan_file(path):
    tree = ast.parse(Path(path).read_text(), filename=str(path))
    s = Scan(Path(path).name)
    s.visit(tree)
    return s.reads


def scan_dir(d=HERE):
    """-> {(file, 'dotted.path.key'): [lines]} of every unregistered read"""
    out = {}
    for g in SCAN_GLOBS:
        for f in sorted(Path(d).glob(g)):
            if SKIP_FILE(f):
                continue
            try:
                reads = scan_file(f)
            except SyntaxError:
                continue
            for line, path, key in reads:
                if unregistered(path, key):
                    out.setdefault((f.name, ".".join(path + (key,))), []).append(line)
    return out


# ---------------------------------------------------------------------------------------------------------------- tests
def test_every_generator_plan_key_is_registered():
    bad = {k: v for k, v in scan_dir().items() if not _allowed(*k)}
    msg = "\n".join(f"{f}:{lines[:3]} plan key '{p}' is not registered in schema.SCHEMA (register it in schema.py, or "
                    f"allowlist (file, path) in NOT_PLAN with the reason)" for (f, p), lines in sorted(bad.items()))
    assert not bad, "SCHEMA-UNKNOWN-KEY risk:\n" + msg


def _match(entry, f, path):
    ef, ep = entry
    return ef == f and (ep == "" or path == ep or path.startswith(ep + "."))


def _allowed(f, path):
    return any(_match(e, f, path) for e in NOT_PLAN)


def test_allowlist_not_stale():
    found = scan_dir()
    stale = [e for e in NOT_PLAN if not any(_match(e, f, p) for f, p in found)]
    assert not stale, f"NOT_PLAN entries no longer matching a read (remove them): {stale}"


def test_allowlist_entries_have_reasons():
    assert all(isinstance(v, str) and len(v) > 10 for v in NOT_PLAN.values())


def _scan_src(src):
    s = Scan("x.py")
    s.visit(ast.parse(src))
    return [(p, k) for _l, p, k in s.reads if unregistered(p, k)]


def test_selftest_fake_top_level_key_fails():
    assert _scan_src("def f(raw):\n    return raw.get('definitely_not_registered_flag')\n") == [((), "definitely_not_registered_flag")]
    assert _scan_src("def f(plan):\n    return plan['zz_fake']\n") == [((), "zz_fake")]
    assert _scan_src("def f(self):\n    return 'zz_fake' in self.raw\n") == [((), "zz_fake")]


def test_selftest_fake_nested_key_fails_through_aliases():
    src = ("def f(raw):\n"
           "    for tn, t in raw['partition_types'].items():\n"
           "        ck = t.get('clock') or {}\n"
           "        x = ck.get('zz_fake_clock_key')\n")
    assert _scan_src(src) == [(("partition_types", "*", "clock"), "zz_fake_clock_key")]


def test_selftest_registered_and_unrelated_pass():
    src = ("def f(raw, other):\n"
           "    a = raw.get('clock') or {}\n"
           "    b = other.get('zz_fake')\n"
           "    raw = {}\n"
           "    c = raw.get('zz_fake')\n"
           "    return [x for x in raw.get('partition_types', {}).values()]\n")
    assert _scan_src(src) == []


def test_selftest_known_flags_resolve():
    for path, key in [((), "clk_land_clear"), (("partition_types", "*", "clock"), "tap_sites_um")]:
        assert not unregistered(path, key), (path, key)
