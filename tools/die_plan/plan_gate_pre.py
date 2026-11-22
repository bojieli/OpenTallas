#!/usr/bin/env python3
"""plan_gate_pre: pre-bind closure check for a die plan event (PLAN-GATE-PRE-1115, ruling r196, FABLE-FLOW-1800 class 1).

A plan gate (G0 / elab / bind) is run on a hand-assembled tree: compose tree + bind overlay + rows of other lanes + staged
tools.  Nothing compared the parts before the 1-2 h bind started.  This check takes seconds, reads only, and fails fast with
one named reason per defect.  It is a precondition check, not a limit on the design run.

    python3 -I tools/die_plan/plan_gate_pre.py check --tree BINDTREE --plan PLAN.json [--sidecar SC.json]
        [--asbuilt AB.json] [--compose-tree T] [--baseline-plan BASE.json] [--rows-proof P.json ...]
        [--rows FILE ...] [--skip CLASS ...] [--json OUT] [--quiet]
    python3 -I tools/die_plan/plan_gate_pre.py mkproof --plan PLAN.json --baseline-plan BASE.json --lane LANE
        --evidence PATH --out P.json [--result pass]

BINDTREE is the directory the bind runs in (cwd of `python3 tools/die_plan/bind.py`): it holds tools/die_plan/*.py and the
overlay.  Five classes, each finding line starts `FAIL <CLASS> ...`:

  SCHEMA   every key of the composed plan is known to BINDTREE/tools/die_plan/schema.py (the G1d miss: overlay ovl_b6E carried
           the B6gE schema, the compose tree the BANDTAP one: 17 "unknown key band_fixed_um"); die_plan.schema.json of the
           tree equals the dump of its schema.py; with --compose-tree every schema property of the compose tree exists in
           the bind tree (SCHEMA-TREE-SKEW names the overlay).
  INPUT    every path the elab/bind reads exists: the as-built lists files / prefer / netlist / rtl_roots / hard_params
           (resolved against base as bind.py does), map_file, clock_landing_table, dead-input proofs, the plan and sidecar.
           The G1d miss: hard_params.json removed by a cleanup, found after the elab.  Its manifest is also the keep set for
           cleanup (--list prints the resolved paths).
  TOOLS    the tool modules of BINDTREE/tools/die_plan come from one consistent source: every `import X; X.attr`, `from X
           import a` and call `X.f(...)` between sibling modules resolves to a name that exists with a matching arity.
           Catches the KV 7u tree (core_tap_early_ps called with another arity than schema.py defines, reset_tree
           without pin_root_copies, a gen_phys.py older than the schema.py next to it).
  GEOM     no station, relay or reset-relay site (ft_slots / internal_stations regs_um, reset.local_taps_um, reset.tap_um) lies
           inside a landing ring core (cl_*) of its own type, every overlap listed (G0 has no such check: 2 KV krsp stations in
           ring cores passed it, r235).  With --baseline-plan every overlap the baseline lacks is refused, with --strict-cores
           every overlap; the overlaps over other cores of adopted plans are only counted (WARN).
  ROWS     rows of another lane in the plan (reset.consumer_localization, the rows a lane merges into an event) carry a
           passing ROWS-PROOF: a dry-run of the consumer check on the EMITTED bind RTL, keyed by the rows' sha.  Rows equal to
           the --baseline-plan (the adopted plan) need none.  QC-SC-ROWS' reset rows had never been dry-run: 9/9 types
           rejected at bind, after 1-2 h.

BIND-SPEED-1118 adds four classes (bind_rowcheck.py; run inside `bind` after the elab, and by `bind_fast.py precheck`):
  FIXEDCYC lane fixed_cycles vs its latency row (double-counted / stale table); ROWSINK R8 table rows whose sink / port is no leaf of
  the elaborated die (names compared in u_r0_u_x instance form too; --elab-dir OUT); MODULES modules named by asbuilt.substitute_inst /
  substitute / sub_core_leaf that exist nowhere; TOOLSTALE tools/die_plan files older than the live tree (--ref-tools, $OT_RT_CURRENT).

LANDREMAP-1122 (FLOW-OPS-R2, COORD): with --baseline-plan, every type whose hard core (landing cl_*, ectl, any) or clock tap
  table moved against BASE re-solves its reset tree and renumbers rst_rl_<k>.  A landing reset reference (landing_reader_start /
  landing_writer_start / landing_local_resets / landing_raw_branches; collector_tree excluded) that still names, at the same
  plan path, the same relay as BASE while that name is now a DIFFERENT relay (depth, site, kind) of the new tree was not
  remapped: FAIL LANDREMAP with the landing_remap.py command.  KV R6d (ae4b6866747e vs plan_r6c): 7 EMIT errors after a 1-2 h
  bind, refused here in ~3 s.  bind.py runs this class against $OT_PLAN_GATE_BASELINE, else the plan recorded in
  OUT/provenance_bind.json, else in <plan dir>/bind_of_record/provenance_bind.json (the tree's previous bind of record).

ABSPATH-1122 (FLOW-OPS-R2, COORD): an absolute path in the plan json (or its --sidecar, or <plan dir>/wave_prepare.json) that
  lies outside the plan's own tree (--tree, else the nearest parent holding tools/die_plan or physical+rtl; realpath counted)
  is an input that dies with its snapshot (HEAD r16/r17: sink censuses into the deleted s81_head_r4_s0 -> kit_rtl /
  abs_inputs).  ABSPATH-MISSING (target gone) and ABSPATH-OUTSIDE (target present): WARN before ABSPATH_STRICT_FROM (live
  plans keep cutting), FAIL from it; $OT_PLAN_ABSPATH=fail (composers / new plans) or =warn overrides; a bind always warns.
  Keys provenance / source* / note* / comment* / receipt* / evidence* / proof* / report* / history / *_log are records.  Fix: `plan_gate_pre.py localize --plan P --out P2` copies each present outside
  file into <plan dir>/inputs/ and rewrites the reference tree-relative (composers run it before G0).

ISTCYC-1122 (FLOW-OPS-R2, COORD): with --baseline-plan, every lane whose end-bus internal_stations depth (source OUT bus +
  destination IN bus, the deepest bus:<name> row as the kit merges them) changed against BASE, and whose BASE fixed_cycles
  followed the rule fixed_cycles = source + destination, must carry the new source + destination; else FAIL ISTCYC with the
  lane, the depths and the required cycles (the bind refuses it later: native_istations "fixed_cycles must equal source +
  destination").  Only lanes on types whose stations changed are read.  Fix: `plan_gate_pre.py reprice --plan P
  --baseline-plan B --out P2` sets exactly those lanes (fixed_cycles and latency fixed / cycles / natural by the same delta).

DEADIN-1122 (FLOW-OPS-R2, COORD): with an as-built that names dead_input_proofs, the bind's own dead_inputs.ProvenDead
  validation (repository-relative paths, PASS verdict, defines / re-proofs, dependency module hashes, selected source) runs here,
  before the elab: OPUS-FIX-S81-COLROM-R6 kit G lost 28 min of elab to "dead-input proof must be repository-relative".

REMAP-BASE-1122 (FLOW-OPS-R2, COORD): LANDREMAP and ISTCYC compare against the remap base, resolved without the lane naming
  it: --remap-base, else --baseline-plan, else $OT_PLAN_REMAP_BASE, else the plan recorded in <plan dir>/bind_of_record/
  provenance_bind.json (the tree's last bind).  publish_gate passes the die's live plan (kit_wave.json), ot_build passes its
  --remap-base / the same fallback, private-spec the wave plan it forks from.  The base used is printed as a WARN-free LIST line.

R8STALE-1122 (FLOW-OPS-R2, COORD; FAM-KV-IOPC-R4 pc_v3: +5 stations on 32 pi bundles, reprice ran, 3 strict binds then died at
  R8_FAIL_FAST with 30 R8_STALE): with a remap base, every lane whose end-bus station depth changed against the base is looked up
  in the as-built's R8 tables (land_r8 + land_r8_extra, member "lane").  A table that is byte-identical to the base tree's copy
  (same tree-relative path) was not re-derived after the change: FAIL R8STALE with the members and the regeneration recipe (one
  strict bind stops at R8_FAIL_FAST and writes OUT/r8_derived.json; install it, or r8_refresh.py, then bind).  Base copy not found:
  WARN with the same recipe.

TAPNAME-1122 (FLOW-OPS-R2, COORD): for every clock.tap_mode "density" type with clock.added_taps, the density base is solved
  exactly as the bind does (taps._density_base) and the added names must be clk_t<base>, clk_t<base+1>, ... in order (cbf_q00
  clk_t101 for t114, coll_core clk_t130 for t126: EMIT "density added tap names/order must be ..." after 30+ min of bind).
  FAIL TAPNAME names each wrong name and its expected one.  A clock-section reference to a clk_t<k> that is no tap of the
  type (k >= base + added), or to a misnamed added tap, is FAIL TAPNAME-RETAP: the reset tree / consumer sites still carry
  old tap indices; re-run the tap package (retap.py) on the solved base.

Exit 0 = clean, 1 = at least one FAIL, 2 = usage / unreadable input.  Library: check(...) returns (findings, info).
"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

PROOF_SCHEMA = "opentallas.rows_proof.v1"
ROWS_KEY = "consumer_localization"
LIST_KEYS = ("files", "prefer", "netlist", "rtl_roots", "hard_params")
CLASSES = ("SCHEMA", "INPUT", "TOOLS", "ROWS", "GEOM", "KITFIT", "FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE", "LANDREMAP", "ABSPATH", "ISTCYC", "DEADIN", "TAPNAME", "R8STALE", "RELAYSINK", "EMITNAME")
# GEOM scope.  Stations of the adopted plans already lie over planned cores (KV 7u: 335 sites over head/pvg cores; S81 B6gE 51,
# QC S4q7e 24: through-stations over native / lane cores), and G0 accepts them, so a plain "no site inside any core" would refuse
# every adopted plan.  Default: refuse the overlaps with the landing ring cores the ring split adds (instance name cl_*), the
# class G0 missed on 7w+v21.  --baseline-plan BASE: refuse every overlap that BASE does not already have (new = refused, same
# type + site + core = inherited).  --strict-cores: refuse every overlap.  The rest is counted in one WARN line.
REFUSE_CORES = r"^cl_"


def _load(p):
    return json.loads(Path(p).read_text())


def _canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- SCHEMA
_SCHEMA_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import schema
mode = sys.argv[2]
if mode == "validate":
    obj = json.load(open(sys.argv[3]))
    print(json.dumps({"errors": schema.validate_structure(obj)}))
elif mode == "keys":
    out = set()
    def walk(s, path):
        if not isinstance(s, dict):
            return
        for k, v in (s.get("properties") or {}).items():
            out.add(path + "." + k)
            walk(v, path + "." + k)
        if isinstance(s.get("additionalProperties"), dict):
            walk(s["additionalProperties"], path + ".*")
        if isinstance(s.get("items"), dict):
            walk(s["items"], path + "[]")
    walk(schema.SCHEMA, "$")
    dump = json.dumps(schema.SCHEMA, indent=1) + "\n"
    print(json.dumps({"keys": sorted(out), "dump": dump if len(sys.argv) > 3 else None}))
"""


PROBE_BASE_S = 180          # one schema import + validate of a small plan on an idle host
PROBE_S_PER_MB = 20         # validate time grows with the plan file (S81 plan ~100+ MB)


def probe_timeout(plan=None, env=None, load=None, ncpu=None):
    """S81-DIE-R3 11-19 (COORD): the schema probe timeout, never a fixed 180 s.  OT_PLAN_GATE_PRE_PROBE_S (> 0) wins;
    otherwise (180 s + 20 s per MB of the plan) x max(1, 1-min load / cpus), so a big plan on a host at load 290/96
    (epyc8, D8i C6 r10 'schema probe timed out') gets the time the work needs instead of a false SCHEMA-LOAD FAIL."""
    env = os.environ if env is None else env
    try:
        v = float(env.get("OT_PLAN_GATE_PRE_PROBE_S") or 0)
    except ValueError:
        v = 0
    if v > 0:
        return v
    mb = 0.0
    if plan:
        try:
            mb = os.path.getsize(plan) / 1e6
        except OSError:
            mb = 0.0
    if load is None:
        try:
            load = os.getloadavg()[0]
        except OSError:
            load = 0.0
    ncpu = ncpu or os.cpu_count() or 1
    return (PROBE_BASE_S + PROBE_S_PER_MB * mb) * max(1.0, load / ncpu)


def _probe(tree, *args, timeout=None):
    if timeout is None:
        plan = next((a for a in args if isinstance(a, (str, Path)) and str(a).endswith(".json") and os.path.isfile(a)), None)
        timeout = probe_timeout(plan)
    sd = Path(tree) / "tools" / "die_plan"
    if not (sd / "schema.py").is_file():
        return None, f"{sd}/schema.py does not exist"
    try:
        r = subprocess.run([sys.executable, "-I", "-B", "-c", _SCHEMA_PROBE, str(sd), *map(str, args)],
                           capture_output=True, text=True, timeout=timeout, cwd=str(tree))
    except subprocess.TimeoutExpired:
        return None, f"schema probe timed out ({timeout:.0f} s; OT_PLAN_GATE_PRE_PROBE_S overrides)"
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["?"])[-1]
        return None, f"schema.py of the bind tree does not import: {tail}"
    return json.loads(r.stdout), None


def check_schema(tree, plan, compose_tree=None):
    out = []
    res, err = _probe(tree, "validate", plan)
    if err:
        return [f"FAIL SCHEMA-LOAD {err}"]
    errs = res["errors"]
    unk = {}
    other = []
    for e in errs:
        m = re.search(r"unknown key '([^']+)'", e)
        if m:
            unk.setdefault(m.group(1), []).append(e)
        else:
            other.append(e)
    for k, es in sorted(unk.items()):
        out.append(f"FAIL SCHEMA-UNKNOWN-KEY '{k}' x{len(es)} not in {tree}/tools/die_plan/schema.py (first: {es[0]}); "
                   f"the plan comes from a newer schema than this bind tree (overlay/tool mismatch)")
    for e in other[:5]:
        out.append(f"FAIL SCHEMA-INVALID {e}")
    if len(other) > 5:
        out.append(f"FAIL SCHEMA-INVALID ... and {len(other) - 5} more")
    kres, kerr = _probe(tree, "keys", "dump")
    if not kerr:
        jf = Path(tree) / "tools" / "die_plan" / "die_plan.schema.json"
        if jf.is_file() and jf.read_text() != kres["dump"]:
            out.append(f"WARN SCHEMA-JSON-STALE {jf} differs from the dump of {tree}/tools/die_plan/schema.py "
                       f"(re-dump: python3 -I tools/die_plan/schema.py dump-schema)")
        if compose_tree:
            cres, cerr = _probe(compose_tree, "keys")
            if cerr:
                out.append(f"FAIL SCHEMA-LOAD compose tree: {cerr}")
            else:
                miss = sorted(set(cres["keys"]) - set(kres["keys"]))
                if miss:
                    out.append(f"FAIL SCHEMA-TREE-SKEW {len(miss)} schema properties of the compose tree {compose_tree} "
                               f"are missing in the bind tree {tree}: {', '.join(miss[:8])}"
                               f"{' ...' if len(miss) > 8 else ''}")
    return out


# ---------------------------------------------------------------- INPUT
def manifest_paths(ab, manifest_dir, tree):
    """[(key, resolved Path, kind)] for one as-built section, resolved as tools/die_plan/bind.py does."""
    tree, manifest_dir = Path(tree), Path(manifest_dir)
    b = ab.get("base")
    if b is None:
        base = tree
    elif Path(b).is_absolute():
        base = Path(b)
    else:
        base = manifest_dir / b
    res = []

    def add(key, p, rel_to, kind="file"):
        if not isinstance(p, str) or not p:
            return
        q = Path(p) if Path(p).is_absolute() else Path(rel_to) / p
        res.append((key, q, kind))

    for k in LIST_KEYS:
        v = ab.get(k) or []
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            continue
        for p in v:
            add(k, p, base, "dir" if k == "rtl_roots" else "file")
    add("map_file", ab.get("map_file"), manifest_dir)
    add("clock_landing_table", ab.get("clock_landing_table"), base)
    for k in ("dead_input_reproofs", "dead_input_proofs"):
        v = ab.get(k)
        if isinstance(v, str):
            v = [v]
        if isinstance(v, list):
            for p in v:
                add(k, p, tree)
    pr = ab.get("param_regen")
    if isinstance(pr, dict):
        add("param_regen", pr.get("file"), tree)
    return base, res


def check_inputs(tree, plan, sidecar=None, asbuilt=None, want_list=False, require_asbuilt=False):
    out = []
    listing = []
    for what, p in (("plan", plan), ("sidecar", sidecar)):
        if p and not Path(p).is_file():
            out.append(f"FAIL INPUT-MISSING {what} {p}")
    raw = _load(plan)
    if asbuilt:
        ab, mdir = _load(asbuilt), Path(asbuilt).resolve().parent
    else:
        ab, mdir = raw.get("asbuilt"), Path(plan).resolve().parent
    if not isinstance(ab, dict):
        lvl = "FAIL" if require_asbuilt else "WARN"
        return out + [f"{lvl} INPUT-NO-ASBUILT {plan} has no `asbuilt` section and no --asbuilt manifest: no bind inputs to check"]
    base, paths = manifest_paths(ab, mdir, tree)
    if not base.is_dir():
        out.append(f"FAIL INPUT-MISSING base {base}")
    miss = {}
    for key, p, kind in paths:
        listing.append(str(p))
        ok = p.is_dir() if kind == "dir" else p.exists()
        if ok and p.is_symlink() and not p.exists():
            ok = False
        if not ok:
            miss.setdefault(key, []).append(str(p))
    for key, ps in sorted(miss.items()):
        out.append(f"FAIL INPUT-MISSING {key} x{len(ps)} (base {base}): " + "; ".join(ps[:4])
                   + (f"; ... +{len(ps) - 4}" if len(ps) > 4 else ""))
    if want_list:
        out.append("LIST " + json.dumps(sorted(set(listing))))
    return out


# ---------------------------------------------------------------- TOOLS
class _Mod:
    def __init__(self, name, path):
        self.name, self.path = name, path
        self.any = False          # exports unknowable (star import / __getattr__)
        self.names = {}           # name -> FunctionDef | None
        self.dups = set()
        self.tree = None
        self.error = None
        try:
            warnings.simplefilter("ignore")
            self.tree = ast.parse(Path(path).read_text(errors="replace"), filename=str(path))
        except SyntaxError as e:
            self.error = f"{path}:{e.lineno}: {e.msg}"
            return
        self._scan(self.tree.body)

    def _define(self, n, fn=None):
        if n in self.names:
            self.dups.add(n)
        self.names[n] = fn

    def _scan(self, body):
        for s in body:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if s.name == "__getattr__":
                    self.any = True
                self._define(s.name, s if not s.decorator_list else None)
            elif isinstance(s, ast.ClassDef):
                self._define(s.name)
            elif isinstance(s, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                tg = s.targets if isinstance(s, ast.Assign) else [s.target]
                for t in tg:
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            self._define(x.id)
            elif isinstance(s, (ast.Import, ast.ImportFrom)):
                for a in s.names:
                    if a.name == "*":
                        self.any = True
                    else:
                        self._define((a.asname or a.name).split(".")[0])
            elif isinstance(s, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
                for f in ("body", "orelse", "finalbody", "handlers"):
                    for sub in getattr(s, f, []) or []:
                        self._scan(sub.body if isinstance(sub, ast.ExceptHandler) else [sub])
            if isinstance(s, (ast.Global,)):
                pass

    def has(self, n):
        return self.any or n in self.names


def _arity_error(fn, call):
    """None, or why `call` cannot bind to FunctionDef `fn` (only when every argument is plain)."""
    if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
        return None
    a = fn.args
    pos = [x.arg for x in a.posonlyargs + a.args]
    kwonly = [x.arg for x in a.kwonlyargs]
    ndef = len(a.defaults)
    required = pos[:len(pos) - ndef] if ndef else list(pos)
    kwreq = [x.arg for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    npos = len(call.args)
    if npos > len(pos) and not a.vararg:
        return f"{npos} positional arguments, def takes {len(pos)}"
    names = {k.arg for k in call.keywords}
    for k in names:
        if k not in pos and k not in kwonly and not a.kwarg:
            return f"unexpected keyword '{k}'"
        if k in pos[:npos]:
            return f"'{k}' given twice"
    miss = [r for r in required[npos:] if r not in names] + [r for r in kwreq if r not in names]
    if miss:
        return f"missing {', '.join(miss)} (def takes {len(pos)} positional)"
    return None


def check_tools(tree, max_findings=12):
    d = Path(tree) / "tools" / "die_plan"
    if not d.is_dir():
        return [f"FAIL TOOLS-LOAD {d} does not exist"]
    mods = {}
    for p in sorted(d.glob("*.py")):
        if p.is_file() and not p.stem.startswith("test_") and p.stem != "conftest":
            mods[p.stem] = _Mod(p.stem, p)
    out = []
    for m in mods.values():
        if m.error:
            out.append(f"FAIL TOOLS-SYNTAX {m.error}")
    found = []
    all_mods = mods
    extra_cache = {}
    for m in all_mods.values():
        if m.tree is None or m.name.startswith("test_") or m.name == "conftest":
            continue
        # a module that does sys.path.insert(0, <here>/"X") imports X's modules first (ca_region_table -> tools/s81_head/fallback_land.py):
        # resolve those names in tools/X, not in the same-named sibling of tools/die_plan (a checker false positive on KV 7u/7uh)
        mods = dict(all_mods)
        try:
            src = m.path.read_text()
        except (OSError, AttributeError, UnicodeDecodeError):
            src = ""
        for xd in re.findall(r"sys\.path\.insert\(\s*\d+\s*,[^\n]*?[\"']([A-Za-z0-9_]+)[\"']\s*\)", src):
            xdir = Path(tree) / "tools" / xd
            if xdir.is_dir() and xd != "die_plan":
                for xp in xdir.glob("*.py"):
                    if xp.stem in mods and not xp.stem.startswith("test_"):
                        key = str(xp)
                        extra_cache.setdefault(key, _Mod(xp.stem, xp))
                        mods[xp.stem] = extra_cache[key]
        alias = {}                  # local name -> sibling module name
        multi = set()               # local names bound to more than one module (function-local imports)
        frm = {}                    # local name -> (module, name)
        for n in ast.walk(m.tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    parts = a.name.split(".")
                    tgt = parts[-1] if (len(parts) == 1 or parts[-2] == "die_plan") else None
                    if tgt in mods and tgt != m.name and (a.asname or len(parts) == 1):
                        if alias.get(a.asname or a.name, tgt) != tgt:
                            multi.add(a.asname or a.name)
                        alias[a.asname or a.name] = tgt
            elif isinstance(n, ast.ImportFrom):
                mod = (n.module or "")
                last = mod.split(".")[-1] if mod else ""
                pkg = (n.level > 0 and not mod) or mod.endswith("die_plan")
                if pkg:
                    for a in n.names:
                        if a.name in mods and a.name != m.name:
                            if alias.get(a.asname or a.name, a.name) != a.name:
                                multi.add(a.asname or a.name)
                            alias[a.asname or a.name] = a.name
                elif (n.level > 0 or mod == last) and last in mods and last != m.name:
                    for a in n.names:
                        if a.name == "*" or (a.name.startswith("__") and a.name.endswith("__")):
                            continue
                        tm = mods[last]
                        if tm.tree is not None and not tm.has(a.name) and not (d / f"{a.name}.py").is_file():
                            found.append(f"{m.name}.py:{n.lineno} `from {mod} import {a.name}`: {last}.py has no {a.name}")
                        frm[a.asname or a.name] = (last, a.name)
        # a local name that is also assigned / a parameter / a loop target anywhere is not (only) the module
        rebound = {x.id for x in ast.walk(m.tree) if isinstance(x, ast.Name) and isinstance(x.ctx, (ast.Store, ast.Del))}
        rebound |= {x.arg for x in ast.walk(m.tree) if isinstance(x, ast.arg)}
        guarded = set()            # hasattr(X, "name") / getattr(X, "name", d): the module may legitimately lack it
        for x in ast.walk(m.tree):
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id in ("hasattr", "getattr") \
                    and len(x.args) >= 2 and isinstance(x.args[0], ast.Name) and isinstance(x.args[1], ast.Constant):
                guarded.add((x.args[0].id, x.args[1].value))
        for r in rebound | multi:
            alias.pop(r, None)
            frm.pop(r, None)
        for n in ast.walk(m.tree):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias \
                    and not (n.attr.startswith("__") and n.attr.endswith("__")) and (n.value.id, n.attr) not in guarded:
                tm = mods[alias[n.value.id]]
                if tm.tree is not None and not tm.has(n.attr):
                    found.append(f"{m.name}.py:{n.lineno} {tm.name}.{n.attr}: {tm.name}.py has no {n.attr}")
            if isinstance(n, ast.Call):
                tgt = None
                f = n.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in alias:
                    tgt = (alias[f.value.id], f.attr)
                elif isinstance(f, ast.Name) and f.id in frm:
                    tgt = frm[f.id]
                if tgt:
                    tm = mods[tgt[0]]
                    fn = tm.names.get(tgt[1]) if tm.tree is not None and tgt[1] not in tm.dups else None
                    if fn is not None:
                        why = _arity_error(fn, n)
                        if why:
                            found.append(f"{m.name}.py:{n.lineno} {tm.name}.{tgt[1]}(...): {why} "
                                         f"(def {tm.name}.py:{fn.lineno})")
    for f in found[:max_findings]:
        out.append(f"FAIL TOOLS-SKEW {f}")
    if len(found) > max_findings:
        out.append(f"FAIL TOOLS-SKEW ... and {len(found) - max_findings} more")
    return out


# ---------------------------------------------------------------- ROWS
def _find_rows(node, path=""):
    """{path: rows} for every non-empty ROWS_KEY below node."""
    got = {}
    if isinstance(node, dict):
        for k, v in node.items():
            if k == ROWS_KEY and v:
                got[f"{path}.{k}"] = v
            else:
                got.update(_find_rows(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            got.update(_find_rows(v, f"{path}[{i}]"))
    return got


def plan_rows(plan_raw):
    """{partition type: sha of its rows} for rows carried in partition_types."""
    out = {}
    for t, v in (plan_raw.get("partition_types") or {}).items():
        rows = _find_rows(v)
        if rows:
            out[t] = _canon_sha(rows)
    return out


def delta_rows(plan_raw, base_raw=None):
    cur = plan_rows(plan_raw)
    base = plan_rows(base_raw) if base_raw else {}
    return {t: s for t, s in cur.items() if base.get(t) != s}


def check_rows(plan, baseline=None, proofs=(), rows_files=()):
    out = []
    raw = _load(plan)
    need = delta_rows(raw, _load(baseline) if baseline else None)
    good, bad = {}, []
    for pf in proofs:
        try:
            pr = _load(pf)
        except (OSError, ValueError) as e:
            out.append(f"FAIL ROWS-PROOF-UNREADABLE {pf}: {e}")
            continue
        if pr.get("schema") != PROOF_SCHEMA:
            out.append(f"FAIL ROWS-PROOF-SCHEMA {pf}: schema {pr.get('schema')!r}, need {PROOF_SCHEMA}")
            continue
        if pr.get("result") != "pass":
            bad.append((pf, pr.get("result"), pr.get("lane")))
            for t in (pr.get("types") or {}):
                good.pop(t, None)
                bad.append((t, "withdrawn/failed proof", pr.get("lane")))
            continue
        for t, s in (pr.get("types") or {}).items():
            good[t] = (s, pr.get("lane"), pf)
    bad_types = {b[0] for b in bad}
    for pf, res, lane in bad:
        if pf not in need:
            out.append(f"FAIL ROWS-PROOF-NOT-PASS {pf}: result {res!r} (lane {lane})")
    nop, stale = [], []
    for t, s in sorted(need.items()):
        if t in bad_types:
            nop.append(t)
        elif t not in good:
            nop.append(t)
        elif good[t][0] != s:
            stale.append(t)
    if nop:
        out.append(f"FAIL ROWS-NO-PROOF {len(nop)} partition types carry {ROWS_KEY} rows that differ from the baseline "
                   f"and have no passing ROWS-PROOF (dry-run of the consumer check on the EMITTED bind RTL): "
                   + ", ".join(nop[:6]) + (f", ... +{len(nop) - 6}" if len(nop) > 6 else ""))
    if stale:
        out.append(f"FAIL ROWS-PROOF-STALE {len(stale)} types: proof sha differs from the plan's rows (rows changed after "
                   f"the dry-run): " + ", ".join(stale[:6]))
    for rf in rows_files:
        rp = Path(rf)
        if not rp.is_file():
            out.append(f"FAIL ROWS-MISSING {rf}")
            continue
        sha = hashlib.sha256(rp.read_bytes()).hexdigest()[:16]
        ok = any(pr_ok for pr_ok in _file_proofs(rp, sha, proofs))
        if not ok:
            out.append(f"FAIL ROWS-NO-PROOF rows file {rf} (sha {sha}) has no passing ROWS-PROOF naming it")
    return out


def _file_proofs(rp, sha, proofs):
    cands = list(proofs) + [str(rp) + ".proof.json"]
    for pf in cands:
        try:
            pr = _load(pf)
        except (OSError, ValueError):
            continue
        if pr.get("schema") == PROOF_SCHEMA and pr.get("result") == "pass" and pr.get("files", {}).get(rp.name) == sha:
            yield True


def mkproof(plan, baseline, lane, evidence, result="pass"):
    raw = _load(plan)
    d = delta_rows(raw, _load(baseline) if baseline else None)
    return {"schema": PROOF_SCHEMA, "lane": lane, "result": result, "plan": str(plan),
            "plan_sha": hashlib.sha256(Path(plan).read_bytes()).hexdigest()[:16], "evidence": str(evidence),
            "check": "dry-run of the consumer check (reset_consumers.localize) on the EMITTED bind RTL of every type below",
            "types": d}


# ---------------------------------------------------------------- GEOM
def type_sites(t):
    """(name, (x, y)) for every station, relay and reset-relay site of one partition type (type frame, um)."""
    for i, sl in enumerate(t.get("ft_slots") or []):
        for j, p in enumerate(sl.get("regs_um") or []):
            yield f"ft_slots[{i}:{sl.get('name')}].regs_um[{j}]", p
    for i, st in enumerate(t.get("internal_stations") or []):
        for j, p in enumerate(st.get("regs_um") or []):
            yield f"internal_stations[{i}:{st.get('conn')}].regs_um[{j}]", p
    rs = t.get("reset") or {}
    for j, p in enumerate(rs.get("local_taps_um") or []):
        yield f"reset.local_taps_um[{j}]", p
    if rs.get("tap_um"):
        yield "reset.tap_um", rs["tap_um"]


def core_boxes(t):
    out = []
    for c in t.get("hard_cores") or []:
        try:
            ox, oy = c["origin_um"]
            w, h = c["outline_um"]
        except (KeyError, TypeError, ValueError):
            continue
        out.append((c.get("inst", "?"), float(ox), float(oy), float(ox) + float(w), float(oy) + float(h)))
    return out


def geom_overlaps(raw, halo=0.0):
    """[(type, site name, (x, y), core inst, box)] for every site strictly inside (halo-grown) a hard-core box of ITS OWN type."""
    out = []
    for tn, t in (raw.get("partition_types") or {}).items():
        if t.get("hard"):
            continue
        boxes = core_boxes(t)
        if not boxes:
            continue
        for name, p in type_sites(t):
            try:
                x, y = float(p[0]), float(p[1])
            except (TypeError, ValueError, IndexError):
                continue
            for inst, x0, y0, x1, y1 in boxes:
                if x0 - halo < x < x1 + halo and y0 - halo < y < y1 + halo:
                    out.append((tn, name, (x, y), inst, (x0, y0, x1, y1)))
    return out


def check_geom(plan, halo=0.0, strict_cores=False, baseline=None, refuse=REFUSE_CORES):
    """FAIL STATION-IN-CORE per refused overlapping site (all listed); one WARN line counts the tolerated overlaps."""
    out = []
    ref = re.compile(refuse)
    known = None
    if baseline:
        known = {(tn, name, xy, inst) for tn, name, xy, inst, _ in geom_overlaps(_load(baseline), halo)}
    n_inh = 0
    for tn, name, (x, y), inst, b in geom_overlaps(_load(plan), halo):
        if known is not None:
            refused = (tn, name, (x, y), inst) not in known
        else:
            refused = strict_cores or bool(ref.match(inst))
        if strict_cores:
            refused = True
        if not refused:
            n_inh += 1
            continue
        out.append(f"FAIL GEOM-STATION-IN-CORE type {tn}: {name} at ({x:g}, {y:g}) lies inside hard core {inst} "
                   f"[{b[0]:g}, {b[1]:g}, {b[2]:g}, {b[3]:g}]")
    if n_inh:
        out.append(f"WARN GEOM-INHERITED {n_inh} station/relay sites lie over other hard cores (tolerated: adopted plans carry "
                   f"them; --baseline-plan refuses new ones, --strict-cores all)")
    return out


# ---------------------------------------------------------------- driver
LR_NAME = re.compile(r"^rst_rl_\d+$")
LR_SKIP = ("collector_tree",)        # a self-contained tree with its own relay names


def landing_reset_refs(t):
    """{plan path: rst_rl_<k>} of every generated reset relay name the type's clock section references (collector_tree excluded)"""
    out = {}

    def walk(o, path):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if k in LR_SKIP:
                continue
            if isinstance(v, str) and LR_NAME.match(v):
                out[f"{path}/{k}"] = v
            else:
                walk(v, f"{path}/{k}")
    walk(t.get("clock") or {}, "clock")
    return out


def moved_types(raw, base_raw):
    """{type: [what moved]}: hard-core boxes (origin / outline) or the clock tap tables differ from the baseline"""
    out = {}
    bt = base_raw.get("partition_types") or {}
    for tn, t in (raw.get("partition_types") or {}).items():
        b = bt.get(tn)
        if not isinstance(b, dict) or not isinstance(t, dict) or t.get("hard"):
            continue
        cb, cn = {c[0]: c[1:] for c in core_boxes(b)}, {c[0]: c[1:] for c in core_boxes(t)}
        why = [k for k in cn if k in cb and cn[k] != cb[k]]
        ck, bk = t.get("clock") or {}, b.get("clock") or {}
        why += [k for k in ("taps", "added_taps") if ck.get(k) != bk.get(k)]
        if why:
            out[tn] = why
    return out


def check_landremap(plan, baseline, tree_fn=None, max_list=4):
    """FAIL LANDREMAP per moved type whose landing reset references were not remapped (see LANDREMAP-1122 in the doc).
    tree_fn(raw, plan_path, type) -> {relay name: identity}; injectable for tests."""
    if not baseline:
        return []
    raw, braw = _load(plan), _load(baseline)
    if not raw or not braw:
        return []
    mv = moved_types(raw, braw)
    if not mv:
        return []
    if tree_fn is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import schema
        import reset_tree as RT
        plans = {}

        def tree_fn(r, pp, tn):
            if id(r) not in plans:
                plans[id(r)] = schema.Plan(r, Path(pp).parent / "die_plan.json")
            return {x["q"]: (x.get("depth"), tuple(round(float(c), 2) for c in x.get("xy") or ()), x.get("kind"))
                    for x in RT.for_type(plans[id(r)], tn)["relays"]}
    out, bad = [], []
    for tn in sorted(mv):
        rn = landing_reset_refs(raw["partition_types"][tn])
        rb = landing_reset_refs(braw["partition_types"][tn])
        same = {p: v for p, v in rn.items() if rb.get(p) == v}
        if not same:
            continue
        try:
            tb, tw = tree_fn(braw, baseline, tn), tree_fn(raw, plan, tn)
        except Exception as e:  # noqa: BLE001 - the bind reports the tree error itself
            out.append(f"WARN LANDREMAP {tn}: reset tree not built ({type(e).__name__}: {str(e)[:160]}); remap check skipped")
            continue
        stale = sorted((p, v) for p, v in same.items() if tb.get(v) != tw.get(v))
        if not stale:
            continue
        inv = {}
        for n_, idt in tw.items():
            inv.setdefault(idt, []).append(n_)
        nofix = [(p, v) for p, v in stale if len(inv.get(tb.get(v), [])) != 1]
        if nofix:                                        # PORTPAD-1122: landing_remap's identity pass cannot place these; never suggest it
            ex = "; ".join(f"{p} = {v} {tb.get(v)}: {len(inv.get(tb.get(v), []))} new relay(s) of that identity" for p, v in nofix[:max_list])
            out.append(f"FAIL LANDREMAP-NOREMAP {tn}: {len(nofix)} landing reset reference(s) name a relay with no unique successor "
                       f"in the new reset tree ({ex}); landing_remap cannot fix this: re-site the landing branch with a plan row")
            if len(nofix) == len(stale):
                continue
        bad.append(tn)
        ex = "; ".join(f"{p} = {v} was {tb.get(v)} now {tw.get(v)}" for p, v in stale[:max_list])
        out.append(f"FAIL LANDREMAP {tn}: {','.join(mv[tn][:3])} moved vs baseline but {len(stale)} landing reset "
                   f"reference(s) still name the old relays ({ex})")
    if bad:
        out.append(f"FAIL LANDREMAP RUN landing_remap: python3 -I tools/die_plan/landing_remap.py {baseline} {plan} OUT.json "
                   f"--types {','.join(bad)} --root . --receipt RECEIPT.json   (then bind OUT.json)")
    return out


ABSPATH_STRICT_FROM = "2026-11-29"           # present-but-outside absolute inputs: WARN before this day, FAIL from it
ABS_RE = re.compile(r"^/(?:srv|home|mnt|data|scratch|tmp|opt|archive|nvme)[^\s\"';|&<>]*$")
ABS_SKIP = re.compile(r"^(?:provenance|source.*|note.*|comment.*|receipt.*|evidence.*|proof.*|.*_proof|report.*|.*_report|history|why|.*_log)$", re.I)


def plan_tree_root(plan, tree=None):
    """the plan's own tree: --tree, else the nearest parent of the plan holding tools/die_plan or physical + rtl"""
    if tree:
        return Path(tree)
    d = Path(plan).resolve().parent if not Path(plan).is_dir() else Path(plan)
    for q in [Path(plan).absolute().parent, *Path(plan).absolute().parents, d, *d.parents]:
        if (q / "tools" / "die_plan").is_dir() or ((q / "physical").is_dir() and (q / "rtl").is_dir()):
            return q
    return Path(plan).absolute().parent


def abs_refs(obj, path=""):
    """[(json path, absolute path string)] of every absolute path value outside record keys (ABS_SKIP)"""
    out = []
    items = obj.items() if isinstance(obj, dict) else enumerate(obj) if isinstance(obj, list) else ()
    for k, v in items:
        if isinstance(k, str) and ABS_SKIP.match(k):
            continue
        if isinstance(v, str):
            if ABS_RE.match(v):
                out.append((f"{path}/{k}", v))
        elif isinstance(v, (dict, list)):
            out += abs_refs(v, f"{path}/{k}")
    return out


def _inside(p, roots):
    cands = {Path(p).absolute()}
    try:
        cands.add(Path(p).resolve())
    except (OSError, RuntimeError):
        pass
    for r in roots:
        for c in cands:
            try:
                c.relative_to(r)
                return True
            except ValueError:
                pass
    return False


def abspath_findings(plan, tree=None, sidecar=None, level=None, today=None, max_list=6, already=""):
    """FAIL/WARN ABSPATH lines (see ABSPATH-1122 in the doc); a path named in `already` (earlier findings, e.g. INPUT-MISSING) is not repeated."""
    import time as _t
    root = plan_tree_root(plan, tree)
    roots = {root.absolute()}
    try:
        roots.add(root.resolve())
    except OSError:
        pass
    lv = (level or os.environ.get("OT_PLAN_ABSPATH") or "").lower()
    strict = (today or _t.strftime("%Y-%m-%d")) >= ABSPATH_STRICT_FROM
    files = [Path(plan)] + ([Path(sidecar)] if sidecar else []) + [Path(plan).parent / "wave_prepare.json"]
    miss, outside = [], []
    for f in dict.fromkeys(files):
        if not f.is_file():
            continue
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for jp, v in abs_refs(doc):
            if _inside(v, roots) or v in already:
                continue
            (outside if Path(v).exists() else miss).append(f"{f.name}:{jp} = {v}")
    out = []
    if miss:
        tag = "FAIL" if lv == "fail" or (strict and lv != "warn") else "WARN"
        out.append(f"{tag} ABSPATH-MISSING {len(miss)} absolute input(s) outside tree {root} do not exist (kit gen dies at "
                   f"abs_inputs; FAIL from {ABSPATH_STRICT_FROM}): " + "; ".join(miss[:max_list]))
    if outside:
        tag = "FAIL" if lv == "fail" or (strict and lv != "warn") else "WARN"
        out.append(f"{tag} ABSPATH-OUTSIDE {len(outside)} absolute input(s) outside tree {root} (die with their snapshot; "
                   f"FAIL from {ABSPATH_STRICT_FROM}): " + "; ".join(outside[:max_list]))
    if out:
        out.append(f"{out[0].split()[0]} ABSPATH fix: python3 -I tools/die_plan/plan_gate_pre.py localize --plan {plan} --out PLAN2.json"
                   + (f" --tree {tree}" if tree else ""))
    return out


def localize(plan, out, tree=None, sidecar=None):
    """copy every present outside absolute input file of the plan into <plan dir>/inputs/<sha12>_<name> and rewrite the
    reference tree-relative; -> (n copied, [unresolved]).  Directories and missing targets are reported, not changed."""
    import shutil
    root = plan_tree_root(plan, tree).absolute()
    pdir = Path(plan).absolute().parent
    raw = json.loads(Path(plan).read_text())
    done, left = {}, []

    def fix(o):
        items = list(o.items()) if isinstance(o, dict) else list(enumerate(o)) if isinstance(o, list) else []
        for k, v in items:
            if isinstance(k, str) and ABS_SKIP.match(k):
                continue
            if isinstance(v, str) and ABS_RE.match(v) and not _inside(v, {root, root.resolve()}):
                src = Path(v)
                if not src.is_file():
                    left.append(v)
                    continue
                if v not in done:
                    h = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
                    dst = pdir / "inputs" / f"{h}_{src.name}"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        tmp = dst.with_name(dst.name + ".part")
                        shutil.copyfile(src, tmp)
                        os.replace(tmp, dst)
                    try:
                        done[v] = str(dst.relative_to(root))
                    except ValueError:
                        done[v] = str(dst)
                o[k] = done[v]
            elif isinstance(v, (dict, list)):
                fix(v)
    fix(raw)
    Path(out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    return len(done), left


def _bus_depth(raw, tn, bus):
    rows = [e for e in ((raw.get("partition_types") or {}).get(tn) or {}).get("internal_stations") or []
            if e.get("conn") == "bus:" + str(bus)]
    return max((len(e.get("regs_um") or []) for e in rows), default=0)


def istcyc_lanes(raw, braw):
    """[(lane id, src (type, bus), dst (type, bus), base depth, new depth, base fixed, new fixed)] for the lanes whose end-bus
    station depth changed vs the baseline and whose baseline fixed_cycles == baseline source + destination; touched types only"""
    bt, nt = braw.get("partition_types") or {}, raw.get("partition_types") or {}
    changed = {tn for tn, t in nt.items() if isinstance(t, dict) and tn in bt
               and (t.get("internal_stations") or []) != ((bt.get(tn) or {}).get("internal_stations") or [])}
    if not changed:
        return []
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    parts = {p.get("name"): p for p in raw.get("partitions") or []}
    blanes = {L.get("id"): L for L in braw.get("lanes") or []}
    out = []
    for L in raw.get("lanes") or []:
        ps = [ports.get(x) for x in L.get("ports") or []]
        if not ps or not ps[0] or not ps[-1]:
            continue
        try:
            src = (parts[ps[0]["src"]["part"]]["type"], ps[0]["src"]["bus"])
            dst = (parts[ps[-1]["dst"]["part"]]["type"], ps[-1]["dst"]["bus"])
        except (KeyError, TypeError):
            continue
        if src[0] not in changed and dst[0] not in changed:
            continue
        b = blanes.get(L.get("id"))
        if b is None:
            continue
        db = _bus_depth(braw, *src) + _bus_depth(braw, *dst)
        dn = _bus_depth(raw, *src) + _bus_depth(raw, *dst)
        bfx, nfx = int(b.get("fixed_cycles", 0) or 0), int(L.get("fixed_cycles", 0) or 0)
        if dn == db or bfx != db:
            continue
        out.append((L.get("id"), src, dst, db, dn, bfx, nfx))
    return out


def depth_changed_lanes(raw, braw):
    """{lane id: (base depth, new depth)} for lanes on types whose internal_stations changed, whose source OUT + destination IN
    station depth differs from the base (no fixed_cycles rule: every bound depth that moves)"""
    bt, nt = braw.get("partition_types") or {}, raw.get("partition_types") or {}
    changed = {tn for tn, t in nt.items() if isinstance(t, dict) and tn in bt
               and (t.get("internal_stations") or []) != ((bt.get(tn) or {}).get("internal_stations") or [])}
    if not changed:
        return {}
    ports = {p.get("id"): p for p in raw.get("ports") or []}
    parts = {p.get("name"): p for p in raw.get("partitions") or []}
    out = {}
    for L in raw.get("lanes") or []:
        ps = [ports.get(x) for x in L.get("ports") or []]
        if not ps or not ps[0] or not ps[-1]:
            continue
        try:
            src = (parts[ps[0]["src"]["part"]]["type"], ps[0]["src"]["bus"])
            dst = (parts[ps[-1]["dst"]["part"]]["type"], ps[-1]["dst"]["bus"])
        except (KeyError, TypeError):
            continue
        if src[0] not in changed and dst[0] not in changed:
            continue
        db = _bus_depth(braw, *src) + _bus_depth(braw, *dst)
        dn = _bus_depth(raw, *src) + _bus_depth(raw, *dst)
        if db != dn:
            out[L.get("id")] = (db, dn)
    return out


def check_r8stale(tree, plan, baseline, asbuilt=None, max_list=6):
    """FAIL / WARN R8STALE (see R8STALE-1122)"""
    if not baseline:
        return []
    raw, braw = _load(plan), _load(baseline)
    if not raw or not braw:
        return []
    lanes = depth_changed_lanes(raw, braw)
    if not lanes:
        return []
    ab, mdir = None, Path(plan).parent
    if asbuilt:
        ab, mdir = _load(asbuilt), Path(asbuilt).parent
    if not isinstance(ab, dict):
        ab = raw.get("asbuilt") if isinstance(raw.get("asbuilt"), dict) else None
    if not ab:
        return []
    base, _ = manifest_paths(ab, mdir, tree)
    tabs = []
    if ab.get("land_r8"):
        tabs.append(ab["land_r8"])
    tabs += list(ab.get("land_r8_extra") or [])
    root, broot = plan_tree_root(plan, tree).absolute(), plan_tree_root(baseline).absolute()
    out = []
    recipe = (f"regenerate: one strict bind of this plan stops at R8_FAIL_FAST and writes OUT/r8_derived.json (OUT/bus_groups.json); "
              f"install it as the table (or python3 -I tools/die_plan/r8_refresh.py {plan} OUT/bus_groups.json TABLE --asbuilt AB), then bind")
    for rel in tabs:
        tp = Path(os.path.normpath(Path(rel) if Path(rel).is_absolute() else Path(base) / rel))
        try:
            members = (json.loads(tp.read_text()) or {}).get("members") or []
        except (OSError, ValueError):
            continue
        hit = sorted({str(m.get("lane")) for m in members if m.get("lane") in lanes})
        if not hit:
            continue
        try:
            bcopy = broot / tp.absolute().relative_to(root)
        except ValueError:
            bcopy = None
        ex = ", ".join(f"{x} {lanes[x][0]}->{lanes[x][1]}" for x in hit[:max_list])
        nm = sum(1 for m in members if m.get("lane") in lanes)
        if bcopy is not None and bcopy.is_file() and bcopy.read_bytes() == tp.read_bytes():
            out.append(f"FAIL R8STALE {tp}: {nm} member(s) on {len(hit)} lane(s) whose station depth changed vs the base ({ex}), "
                       f"but the table is byte-identical to the base copy {bcopy} (not re-derived); {recipe}")
        else:
            out.append(f"WARN R8STALE {tp}: {nm} member(s) on {len(hit)} lane(s) whose station depth changed vs the base ({ex}); "
                       f"base copy {'not found' if bcopy is None or not bcopy.is_file() else 'differs (re-derived?)'}; if not re-derived: {recipe}")
    return out


def check_istcyc(plan, baseline, max_list=8):
    """FAIL ISTCYC per touched lane whose fixed_cycles was not re-priced (see ISTCYC-1122 in the doc)"""
    if not baseline:
        return []
    raw, braw = _load(plan), _load(baseline)
    if not raw or not braw:
        return []
    bad = [x for x in istcyc_lanes(raw, braw) if x[6] != x[4]]
    if not bad:
        return []
    out = [f"FAIL ISTCYC lane {lid}: stations {s[0]}.{s[1]} -> {d[0]}.{d[1]} source+destination {db} -> {dn}, fixed_cycles "
           f"{nfx} (base {bfx}), required {dn}" for lid, s, d, db, dn, bfx, nfx in bad[:max_list]]
    if len(bad) > max_list:
        out.append(f"FAIL ISTCYC ... {len(bad) - max_list} more lane(s)")
    out.append(f"FAIL ISTCYC fix: python3 -I tools/die_plan/plan_gate_pre.py reprice --plan {plan} --baseline-plan {baseline} "
               f"--out PLAN2.json   ({len(bad)} lane(s): " + ",".join(str(x[0]) for x in bad[:20]) + ")")
    return out


def reprice(plan, baseline, out):
    """set fixed_cycles = new source + destination on exactly the ISTCYC lanes; the latency row (fixed / cycles / natural)
    moves by the same delta.  -> {lane: (old, new)}"""
    raw, braw = json.loads(Path(plan).read_text()), json.loads(Path(baseline).read_text())
    lat = (raw.get("latency") or {}).get("lanes") or {}
    byid = {L.get("id"): L for L in raw.get("lanes") or []}
    done = {}
    for lid, _s, _d, _db, dn, _bfx, nfx in istcyc_lanes(raw, braw):
        if nfx == dn:
            continue
        byid[lid]["fixed_cycles"] = dn
        r = lat.get(lid)
        if r is not None:
            for f in ("fixed", "cycles", "natural"):
                if f in r:
                    r[f] = int(r[f]) + (dn - nfx)
        done[lid] = (nfx, dn)
    Path(out).write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    return done


def check_deadin(tree, plan, asbuilt):
    """FAIL DEADIN <bind error> when dead_inputs.ProvenDead refuses the as-built's dead-input proofs (see DEADIN-1122)"""
    ab = _load(asbuilt) if asbuilt else None
    if not isinstance(ab, dict) or not ab.get("dead_input_proofs"):
        return []
    raw = _load(plan) or {}
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import dead_inputs
        dead_inputs.ProvenDead(ab, tree, {k: dict(v) for k, v in (raw.get("partition_types") or {}).items()})
    except ValueError as e:
        return [f"FAIL DEADIN {e} (bind.py would refuse this after the elab; as-built {asbuilt})"]
    except Exception as e:  # noqa: BLE001 - the bind reports anything else itself
        return [f"WARN DEADIN check not run: {type(e).__name__}: {str(e)[:200]}"]
    return []


def check_tapname(plan, base_fn=None, max_list=6, tree=None):
    """FAIL TAPNAME / TAPNAME-RETAP lines (see TAPNAME-1122).  base_fn(P, raw, type) -> density base tap count; injectable.
    TAPNAME-UNCHECKED-1122 (COORD, QC-PLAN-R13 / QC-SLE-R5: run from a bare rt dir the density base inputs were not found, a WARN was
    printed and the broken v3p7d plan reported PASS): the base is solved with the plan's repo-relative inputs read from --tree; a base
    that still cannot be solved is FAIL TAPNAME-UNCHECKED (non-zero, verdict UNCHECKED), never a silent PASS."""
    raw = _load(plan)
    if not raw:
        return []
    todo = []
    for tn, ty in (raw.get("partition_types") or {}).items():
        ck = (ty or {}).get("clock") or {} if isinstance(ty, dict) else {}
        if ck.get("tap_mode") != "density":
            continue
        refs = [v for v in _tap_ref_names(ck)]
        if ck.get("added_taps") or refs:
            todo.append((tn, ck, refs))
    if not todo:
        return []
    if base_fn is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import schema
        import taps as TP
        _pc = {}

        def base_fn(_P, _raw, tn):
            here, root0 = os.getcwd(), TP._root
            try:
                if tree and Path(tree).is_dir():
                    # plan inputs (sink_bins_file ...) are repo-relative: read them from --tree, not from the tool tree this
                    # checker runs from (a bare rt/<sha> dir holds tools only)
                    os.chdir(tree)
                    TP._root = lambda: Path(tree).resolve()
                if "P" not in _pc:               # a plan the schema cannot load is UNCHECKED too (inside the per-type try)
                    _pc["P"] = schema.Plan(raw, Path(here, plan) if not Path(plan).is_absolute() else Path(plan))
                return len(TP._density_base(_pc["P"], tn))
            finally:
                os.chdir(here)
                TP._root = root0
    out = []
    for tn, ck, refs in todo:
        added = [str((a or {}).get("name")) for a in ck.get("added_taps") or []]
        if not added and not refs:
            continue
        try:
            nb = base_fn(None, raw, tn)
        except Exception as e:  # noqa: BLE001 - the bind reports a density solve error itself
            out.append(f"FAIL TAPNAME-UNCHECKED {tn}: density base not solved ({type(e).__name__}: {str(e)[:160]}); added tap names NOT checked "
                       f"-- re-run with --tree <tree holding the plan inputs> (tree {tree or '-'})")
            continue
        exp = [f"clk_t{nb + i}" for i in range(len(added))]
        wrong = [(a, e) for a, e in zip(added, exp) if a != e]
        if wrong:
            out.append(f"FAIL TAPNAME {tn}: density base gives {nb} taps, so added_taps must be {exp[0]}..{exp[-1]}; "
                       + "; ".join(f"{a} should be {e}" for a, e in wrong[:max_list]))
        names = {"clk"} | {f"clk_t{i}" for i in range(1, nb)} | set(exp)
        bad = sorted({r for r in refs if r not in names or r in {a for a, _ in wrong}}, key=lambda s: int(s[5:]) if s[5:].isdigit() else -1)
        if bad:
            out.append(f"FAIL TAPNAME-RETAP {tn}: clock references name {len(bad)} tap(s) that are not taps of the solved base "
                       f"({nb} density + {len(added)} added): {', '.join(bad[:max_list])}; re-run the tap package (retap) on this base")
    return out


def _tap_ref_names(ck):
    """clk_t<k> names the clock section references outside the tap tables (landing_remap.tap_refs rule)"""
    out = []

    def walk(o):
        items = o.items() if isinstance(o, dict) else enumerate(o) if isinstance(o, list) else ()
        for k, v in items:
            if isinstance(k, str) and k in ("taps", "added_taps"):
                continue
            if isinstance(v, str) and re.match(r"^clk_t\d+$", v):
                out.append(v)
            else:
                walk(v)
    walk(ck)
    return out


def remap_base(plan, explicit=None, baseline=None):
    """(path, how) of the LANDREMAP / ISTCYC base (REMAP-BASE-1122); (None, why) when none resolves or it is the plan itself"""
    cands = [(explicit, "--remap-base"), (baseline, "--baseline-plan"), (os.environ.get("OT_PLAN_REMAP_BASE"), "$OT_PLAN_REMAP_BASE")]
    try:
        prov = json.loads((Path(plan).parent / "bind_of_record" / "provenance_bind.json").read_text())["provenance"]["plan"]
        cands.append((prov, "bind_of_record/provenance_bind.json"))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    for c, how in cands:
        if not c:
            continue
        try:
            if not Path(c).is_file():
                continue
            if Path(c).resolve() == Path(plan).resolve() or Path(c).read_bytes() == Path(plan).read_bytes():
                return None, f"{how} {c} is the plan itself"
        except OSError:
            continue
        return str(c), how
    return None, "no base (pass --remap-base, set $OT_PLAN_REMAP_BASE, or keep the tree bind_of_record)"


def _src_def(text, name):
    """the source of top-level `def NAME` in TEXT, or ''"""
    m = re.search(r"(?ms)^def " + re.escape(name) + r"\(.*?(?=^\S)", text + "\nEND\n")
    return m.group(0) if m else ""


def emit_name_fns(tree):
    """(landing_name(pn), bind_name(pn)) of the TREE's tools, without importing them: bind.emit_top writes partition instance
    sv_id(pn); the clock-landing pass looks for the expression it re-escapes right before 'expected exactly one bound instance'.
    None when the tree's tools do not have that form."""
    d = Path(tree) / "tools" / "die_plan"
    try:
        bt, ct = (d / "bind.py").read_text(), (d / "clock_landings.py").read_text()
    except OSError:
        return None
    i = ct.find("expected exactly one bound instance")
    if i < 0:
        return None
    m = list(re.finditer(r"re\.escape\(((?:[^()]|\([^()]*\))*)\) \+ r\" \\\(", ct[max(0, i - 1500):i]))
    if not m:
        return None
    expr = m[-1].group(1)
    ns = {"re": re}
    try:
        for fn in ("ident", "bind_inst_id"):
            src = _src_def(ct, fn)
            if src:
                exec(src, ns)                            # noqa: S102 - the tree's own helper definitions (pure string functions)
        exec(_src_def(bt, "sv_id"), ns)                  # noqa: S102
        land = eval("lambda pn: " + expr, ns)            # noqa: S307
        return land, ns["sv_id"]
    except Exception:  # noqa: BLE001
        return None


def check_emitname(tree, plan, asbuilt=None):
    """FAIL EMITNAME (FABLE-FLOW-0230 B1: FLOW-STRIPBODY-R2 1.9 h, then 'EMIT clock landing: expected exactly one bound instance'):
    with a clock landing table, the partition instance name the landing pass looks for must equal the one bind.emit_top writes,
    and no two partitions may share an instance name.  Seconds, before the elab."""
    raw = _load(plan) or {}
    ab = _load(asbuilt) if asbuilt else raw.get("asbuilt")
    if not isinstance(ab, dict) or not ab.get("clock_landing_table"):
        return []
    fns = emit_name_fns(tree)
    if fns is None:
        return ["WARN EMITNAME clock-landing / bind instance-name form not readable from the tree's tools: not checked"]
    land, bind_id = fns
    out, seen = [], {}
    for p in raw.get("partitions") or []:
        pn = p.get("name") if isinstance(p, dict) else None
        if not pn:
            continue
        try:
            a, b = land(pn), bind_id(pn)
        except Exception as e:  # noqa: BLE001
            return [f"WARN EMITNAME not checked: {type(e).__name__}: {e}"]
        if a != b:
            out.append(f"FAIL EMITNAME partition {pn}: the clock-landing pass looks for instance {a}, bind writes {b} -- the bind stops "
                       f"at EMIT ('clock landing: expected exactly one bound instance'); run the bind on tools where both agree")
        if b in seen:
            out.append(f"FAIL EMITNAME partitions {seen[b]} and {pn} share the bound instance name {b} (two matches at EMIT)")
        seen.setdefault(b, pn)
    return out[:12] + ([f"FAIL EMITNAME ... {len(out) - 12} more"] if len(out) > 12 else [])


def check(tree, plan, sidecar=None, asbuilt=None, compose_tree=None, baseline=None, proofs=(), rows_files=(),
          skip=(), want_list=False, require_asbuilt=False, strict_cores=False, halo=0.0, elab_dir=None, ref_tools=None,
          toolstale_level="FAIL", abspath_level=None, remap=None):
    findings = []
    rb, rb_how = remap_base(plan, remap, baseline) if not {"LANDREMAP", "ISTCYC"} <= {s.upper() for s in skip} else (None, "")
    skip = {s.upper() for s in skip}
    if "SCHEMA" not in skip:
        findings += check_schema(tree, plan, compose_tree)
    if "INPUT" not in skip:
        findings += check_inputs(tree, plan, sidecar, asbuilt, want_list, require_asbuilt)
    if "TOOLS" not in skip:
        findings += check_tools(tree)
    if "ROWS" not in skip:
        findings += check_rows(plan, baseline, proofs, rows_files)
    if "GEOM" not in skip:
        findings += check_geom(plan, halo, strict_cores, baseline)
    if "LANDREMAP" not in skip:                          # LANDREMAP-1122: seconds, before any bind
        findings += check_landremap(plan, rb)
    if "TAPNAME" not in skip:                            # TAPNAME-1122: density added tap names, seconds before the bind
        findings += check_tapname(plan, tree=tree)
    if "DEADIN" not in skip:                             # DEADIN-1122: bind dead-input proof checks, before the elab
        findings += check_deadin(tree, plan, asbuilt)
    if "ISTCYC" not in skip:                             # ISTCYC-1122: touched lanes only, seconds
        findings += check_istcyc(plan, rb)
    if "R8STALE" not in skip:                            # R8STALE-1122: R8 table not re-derived after a station change
        findings += check_r8stale(tree, plan, rb, asbuilt)
    if "EMITNAME" not in skip:                           # B1 (FABLE-FLOW-0230): clock-landing EMIT instance names, seconds
        findings += check_emitname(tree, plan, asbuilt)
    if "ABSPATH" not in skip:                            # ABSPATH-1122: inputs that die with a snapshot tree
        findings += abspath_findings(plan, tree, sidecar, abspath_level, already="\n".join(findings))
    if "KITFIT" not in skip:                             # KITFIT-1116: every hard core at its kit offset (origin + track_offset), every type
        sys.path.insert(0, str(Path(__file__).resolve().parent))          # -I drops the script dir
        import kit_fit as KF
        findings += ["FAIL " + m for m in KF.findings((_load(plan) or {}).get("partition_types") or {}, halo)]
    if not set(skip) >= {"FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE", "RELAYSINK"}:       # BIND-SPEED-1118: bind_rowcheck.py, seconds
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bind_rowcheck as RC
        findings += RC.check_all(tree, plan, _load(plan), asbuilt, elab_dir, ref_tools, skip, toolstale_level)
    if rb:
        findings.append(f"LIST REMAP-BASE {rb} ({rb_how})")      # which base LANDREMAP / ISTCYC used (REMAP-BASE-1122)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plan_gate_pre", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--tree", required=True)
    c.add_argument("--plan", required=True)
    c.add_argument("--sidecar")
    c.add_argument("--asbuilt")
    c.add_argument("--compose-tree")
    c.add_argument("--baseline-plan")
    c.add_argument("--remap-base", help="REMAP-BASE-1122: base plan for LANDREMAP / ISTCYC only (default: --baseline-plan, $OT_PLAN_REMAP_BASE, <plan dir>/bind_of_record)")
    c.add_argument("--rows-proof", action="append", default=[])
    c.add_argument("--rows", action="append", default=[])
    c.add_argument("--skip", action="append", default=[], choices=CLASSES)
    c.add_argument("--require-asbuilt", action="store_true", help="a plan without an as-built section is a FAIL")
    c.add_argument("--strict-cores", action="store_true", help="GEOM: also refuse sites over the planned head/pvg cores")
    c.add_argument("--site-halo-um", type=float, default=0.0, help="GEOM: grow every core box by this margin")
    c.add_argument("--elab-dir", help="bind OUT dir holding the elab's asbuilt.json (enables ROWSINK / the elab half of MODULES)")
    c.add_argument("--ref-tools", help="live reference tree for TOOLSTALE; \"auto\" = $OT_RT_CURRENT or <scratch>/claude/rt/current (default: not run)")
    c.add_argument("--list", action="store_true", help="print the resolved input paths (cleanup keep set)")
    c.add_argument("--json")
    c.add_argument("--quiet", action="store_true")
    lz = sub.add_parser("localize", help="ABSPATH-1122: copy outside absolute inputs into <plan dir>/inputs/, rewrite tree-relative")
    lz.add_argument("--plan", required=True)
    lz.add_argument("--out", required=True)
    lz.add_argument("--tree")
    rp = sub.add_parser("reprice", help="ISTCYC-1122: re-price fixed_cycles of the lanes whose station count changed vs BASE")
    rp.add_argument("--plan", required=True)
    rp.add_argument("--baseline-plan", required=True)
    rp.add_argument("--out", required=True)
    m = sub.add_parser("mkproof")
    m.add_argument("--plan", required=True)
    m.add_argument("--baseline-plan")
    m.add_argument("--lane", required=True)
    m.add_argument("--evidence", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--result", default="pass", choices=("pass", "fail", "withdrawn"))
    a = ap.parse_args(argv)
    if a.cmd == "reprice":
        d = reprice(a.plan, a.baseline_plan, a.out)
        print(f"reprice: {len(d)} lane(s) re-priced; wrote {a.out}" + "".join(f"\n  {k}: fixed_cycles {o} -> {n}" for k, (o, n) in sorted(d.items())))
        return 0
    if a.cmd == "localize":
        n, left = localize(a.plan, a.out, a.tree)
        print(f"localize: {n} outside input file(s) copied into {Path(a.plan).absolute().parent / 'inputs'}; wrote {a.out}"
              + (f"; NOT localized (missing / not a file): {'; '.join(left[:8])}" if left else ""))
        return 1 if left else 0
    if a.cmd == "mkproof":
        pr = mkproof(a.plan, a.baseline_plan, a.lane, a.evidence, a.result)
        Path(a.out).write_text(json.dumps(pr, indent=1) + "\n")
        print(f"{a.out}: {len(pr['types'])} types, result {a.result}")
        return 0
    try:
        f = check(a.tree, a.plan, a.sidecar, a.asbuilt, a.compose_tree, a.baseline_plan, a.rows_proof, a.rows, a.skip,
                  a.list, a.require_asbuilt, a.strict_cores, a.site_halo_um, a.elab_dir, a.ref_tools, remap=a.remap_base)
    except (OSError, ValueError) as e:
        print(f"plan_gate_pre: cannot read input: {e}", file=sys.stderr)
        return 2
    lst = [x for x in f if x.startswith("LIST ")]
    fails = [x for x in f if x.startswith("FAIL ")]
    warns = [x for x in f if x.startswith("WARN ")]
    if not a.quiet:
        for x in lst + fails + warns:
            print(x)
    unchecked = [x for x in fails if x.split()[1].endswith("-UNCHECKED")]
    print(f"PLAN-GATE-PRE {'UNCHECKED' if unchecked and len(unchecked) == len(fails) else 'FAIL' if fails else 'PASS'} tree={a.tree} plan={a.plan} findings={len(fails)}"
          + (" classes=" + ",".join(sorted({x.split()[1].split('-')[0] for x in fails})) if fails else ""))
    if a.json:
        Path(a.json).write_text(json.dumps({"tree": a.tree, "plan": a.plan, "findings": fails}, indent=1) + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
