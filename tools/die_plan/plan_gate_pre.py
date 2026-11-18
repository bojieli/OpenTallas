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
CLASSES = ("SCHEMA", "INPUT", "TOOLS", "ROWS", "GEOM", "KITFIT", "FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE")
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


def _probe(tree, *args, timeout=180):
    sd = Path(tree) / "tools" / "die_plan"
    if not (sd / "schema.py").is_file():
        return None, f"{sd}/schema.py does not exist"
    try:
        r = subprocess.run([sys.executable, "-I", "-B", "-c", _SCHEMA_PROBE, str(sd), *map(str, args)],
                           capture_output=True, text=True, timeout=timeout, cwd=str(tree))
    except subprocess.TimeoutExpired:
        return None, "schema probe timed out"
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
def check(tree, plan, sidecar=None, asbuilt=None, compose_tree=None, baseline=None, proofs=(), rows_files=(),
          skip=(), want_list=False, require_asbuilt=False, strict_cores=False, halo=0.0, elab_dir=None, ref_tools=None,
          toolstale_level="FAIL"):
    findings = []
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
    if "KITFIT" not in skip:                             # KITFIT-1116: every hard core at its kit offset (origin + track_offset), every type
        sys.path.insert(0, str(Path(__file__).resolve().parent))          # -I drops the script dir
        import kit_fit as KF
        findings += ["FAIL " + m for m in KF.findings((_load(plan) or {}).get("partition_types") or {}, halo)]
    if not set(skip) >= {"FIXEDCYC", "ROWSINK", "MODULES", "TOOLSTALE"}:       # BIND-SPEED-1118: bind_rowcheck.py, seconds
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bind_rowcheck as RC
        findings += RC.check_all(tree, plan, _load(plan), asbuilt, elab_dir, ref_tools, skip, toolstale_level)
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
    m = sub.add_parser("mkproof")
    m.add_argument("--plan", required=True)
    m.add_argument("--baseline-plan")
    m.add_argument("--lane", required=True)
    m.add_argument("--evidence", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--result", default="pass", choices=("pass", "fail", "withdrawn"))
    a = ap.parse_args(argv)
    if a.cmd == "mkproof":
        pr = mkproof(a.plan, a.baseline_plan, a.lane, a.evidence, a.result)
        Path(a.out).write_text(json.dumps(pr, indent=1) + "\n")
        print(f"{a.out}: {len(pr['types'])} types, result {a.result}")
        return 0
    try:
        f = check(a.tree, a.plan, a.sidecar, a.asbuilt, a.compose_tree, a.baseline_plan, a.rows_proof, a.rows, a.skip,
                  a.list, a.require_asbuilt, a.strict_cores, a.site_halo_um, a.elab_dir, a.ref_tools)
    except (OSError, ValueError) as e:
        print(f"plan_gate_pre: cannot read input: {e}", file=sys.stderr)
        return 2
    lst = [x for x in f if x.startswith("LIST ")]
    fails = [x for x in f if x.startswith("FAIL ")]
    warns = [x for x in f if x.startswith("WARN ")]
    if not a.quiet:
        for x in lst + fails + warns:
            print(x)
    print(f"PLAN-GATE-PRE {'FAIL' if fails else 'PASS'} tree={a.tree} plan={a.plan} findings={len(fails)}"
          + (" classes=" + ",".join(sorted({x.split()[1].split('-')[0] for x in fails})) if fails else ""))
    if a.json:
        Path(a.json).write_text(json.dumps({"tree": a.tree, "plan": a.plan, "findings": fails}, indent=1) + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
