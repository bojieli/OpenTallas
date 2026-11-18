#!/usr/bin/env python3 -I
"""flow_guard.py -- FLOW-HEALTH-1 (COORD 11-15): deterministic, no-LLM guards for the kit wave's pre-P&R failure classes.

11-15 00:00-06:30 the wave launched 972 builds and 874 failed BEFORE place and route; the same unfixed cause was retried for
hours: 419 kit_rtl "preferred HDL source missing" (a source dir that existed on one host only), 288 INFRA tool/source skew
(gen_phys.py newer than schema.py in a die tree; No module named ot_store / core_view_sha / signoff_profile), 14
KIT_NOT_SELF_CONTAINED, 11 INFRA-VIEW-MISSING.  Guards, all stdlib, none needs a model:

 1. PREFLIGHT (kit_wave.flow_preflight, before a row is launched; extends the existing src_incomplete / deep probe / bind
    preflight rather than replacing them):
      paths   every path the item's kit_rtl / bind inputs name, FOLLOWED: a bind dir's bind.f sources, an as-built / manifest
              json's files / prefer / netlist / rtl_roots (relative ones against its `base`) and every HDL path it names, a .sh
              recipe's /srv paths (and the .sh / .json / .f those name), broken links below a named directory; the count-frame
              sidecars (feed_*.json, regions_*.json) beside a plan_of_record.  Checked on EVERY candidate host (gen host + roam
              hosts); a host that lacks one is dropped for the item, an item no host can serve is not launched.
      tree    per die tree per host: the import closure of gen.py / gen_phys.py / bind.py resolves (a lazy `import core_view_sha`
              inside a function counts), and every `module.attr` / `from module import name` that a tree module uses exists in
              the tree's copy of that module (gen_phys newer than schema -> 'schema has no attribute full_area_hard_ip').
              Cached per host per tree DIGEST (the remote side compares the digest first and answers `same`).
 2. CIRCUIT-BREAKER: >= BREAKER_N fails of one normalised class in BREAKER_WINDOW_S open the class; every item whose LAST fail was
    that class is held (no launch, no auto-retry), one ALERT line names class, count and the first log.  A class the preflight can
    judge (missing path / import skew) closes when every held item's preflight passes; any other class goes half-open after
    BREAKER_COOLDOWN_S without a new fail (probation: reopens after PROBATION_N fails).
 3. skew_report(): per die tree per host, the modules of gen_phys's import closure whose content differs from main (used by
    flow_health.py hourly).

Pure functions + an injected `rpy(host, code, args, timeout)` (autopilot.rpy: python3 -I - with JSON argv, answer line AP_JSON)."""
import ast
import json
import os
import re
import time

BREAKER_N = 5
BREAKER_WINDOW_S = 1800
BREAKER_COOLDOWN_S = 1800
PROBES_PER_CLASS = 3            # WAVE-PILOT-FIX 11-17 (COORD, owner r556 against single-pilot holds): three probes per class, not one
PROBE_PASS_AFTER_S = 3600       # a probe RUNNING this long without a result counts as a pass for releasing its siblings
PROBATION_N = 2
PASS_TTL_S = 900
FAIL_TTL_S = 120
TREE_TTL_S = 600
MAX_PATHS_PER_CALL = 300
ENTRY_FILES = ("tools/die_plan/gen.py", "tools/die_plan/gen_phys.py", "tools/die_plan/bind.py")
SEARCH_DIRS = ("tools/die_plan", "tools", "physical/common_flow")

# ---------------------------------------------------------------- class keys

_P = re.compile(r"/(?:srv|home|tmp|var|usr|mnt)/[^\s\"',;:()\[\]]*")
_H = re.compile(r"\b[0-9a-f]{7,}\b")
_N = re.compile(r"\d+")
PF_MISSING = re.compile(r"HDL source missing|sources that are gone|file missing|No such file|KIT_NOT_SELF_CONTAINED|INFRA-VIEW-MISSING|"
                        r"FileNotFoundError|not found|count frame files not found", re.I)
PF_SKEW = re.compile(r"ModuleNotFoundError|No module named|ImportError|has no attribute|tool or source skew", re.I)


_ID = re.compile(r"\b(?=[A-Za-z0-9]*[a-z])[A-Za-z0-9]*_[A-Za-z0-9_]*\b")       # snake_case identifier: an item / module / type / core name
_ERR_TOK = re.compile(r"(?:Error|Exception|Violation)$")
_PROGRESS = re.compile(r"KW_ROAM|KW_STAGE|KW_PLACE_RC=\d+\s*$|ran on \S+, outputs copied back")


def norm_class(cls, why):
    """the failure's class key (FLOW-HEALTH-1 11-15, FABLE-FLOW-2000 (c): one error was split into 12 keys by item / module names and numbers):
    class + the text with paths / hashes / numbers masked, snake_case identifiers (item, type, module, core names) replaced by <id>, lists
    collapsed, 150 chars.  A progress line (KW_ROAM ... copied back) is never the evidence: a failure whose only text is progress is
    '<stage> no error line'."""
    s = f"{cls}: {why or ''}".replace("\n", " ")
    head, sep, evid = s.partition(" @")
    stage = evid.split(":", 1)[0].strip() if sep else ""
    rest = evid.split(":", 1)[1] if sep and ":" in evid else evid
    if sep and _PROGRESS.search(rest) and not re.search(r"Error|error:|Traceback|ERROR|Exception", rest):
        s = f"{head} @{stage}: no error line (progress text only)"
    s = _P.sub("<P>", s)
    s = re.sub(r"<P>(?:[, ]+<P>)+", "<P>", s)
    s = _H.sub("<H>", s)
    s = _N.sub("N", s)
    s = _ID.sub(lambda m: m.group(0) if (m.group(0).isupper() or _ERR_TOK.search(m.group(0))) else "<id>", s)
    s = re.sub(r"<id>(?:[, ]+<id>)+", "<id>", s)
    return re.sub(r"\s+", " ", s).strip()[:150]


_FAM_SUFFIX = re.compile(r"(?:__(?:cl|pv|t)[0-9a-z]*)+$")
STAGE_ORDER = ("mkdir", "src_manifest", "kit_snap", "kit_store", "bind", "bind_fetch", "kit_rtl", "gen", "gen_lint", "kit_topology", "preflight", "prov_views", "lec_tools", "views", "cells",
               "relay_bay", "sync_hub", "pipeline", "selfcontained", "type_overlay", "unit", "place", "cts", "grt", "route", "sta", "signoff")


def family_of(item):
    """the item name without its __cl<hash> / __pv<hash> / __t<n> suffixes: slice_station__t17 -> slice_station"""
    return _FAM_SUFFIX.sub("", str(item or "")) or str(item or "")


def stage_rank(stage):
    return STAGE_ORDER.index(stage) if stage in STAGE_ORDER else len(STAGE_ORDER)


def pf_kind(key):
    """which preflight can judge this class again ('' = none)"""
    if PF_SKEW.search(key):
        return "skew"
    if PF_MISSING.search(key):
        return "paths"
    return ""


def fail_stage(why):
    m = re.search(r"@([a-z_0-9]+)", why or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- remote probes (python3 -I on the host)

PATHS_PY = r'''
import json, os, re, sys
a = json.loads(sys.argv[1])
DEPTH = int(a.get("depth", 3))
HDL = (".sv", ".v", ".vh", ".svh")
KEYS = ("files", "prefer", "netlist", "rtl_roots", "sources", "bind_out")
TOK = re.compile(r"/(?:srv|home)/[^\s\"';)$,]*")
LANE = re.compile(r"^/srv/[^/]+/claude/[^/]+/[^/]+")
out = {}
def broken_below(d, cap=20000):
    n = 0
    base = d.rstrip("/").count("/")
    for r, ds, fs in os.walk(d):
        if r.count("/") - base >= 6:
            ds[:] = []
        for x in ds + fs:
            n += 1
            if n > cap:
                return ""
            p = os.path.join(r, x)
            if os.path.islink(p) and not os.path.exists(p):
                return p
    return ""
def jstrings(o, key=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from jstrings(v, k)
    elif isinstance(o, list):
        for v in o:
            yield from jstrings(v, key)
    elif isinstance(o, str):
        yield key, o
def refs(p):
    """[(path, hard)] a file names"""
    try:
        if os.path.getsize(p) > 20 * 2**20:
            return []
        txt = open(p, errors="replace").read()
    except OSError:
        return []
    r = []
    if p.endswith(".json"):
        try:
            d = json.loads(txt)
        except ValueError:
            return []
        base = d.get("base") if isinstance(d, dict) and isinstance(d.get("base"), str) and d["base"].startswith("/") else ""
        for k, s in jstrings(d):
            if not s or len(s) > 600 or "\n" in s or " " in s:
                continue
            if k in KEYS:
                q = s if s.startswith("/") else (os.path.join(base, s) if base else "")
                if q:
                    r.append((q, True))
            elif s.startswith("/") and s.lower().endswith(HDL):
                r.append((s, False))
            elif base and k in ("path", "file", "src", "rtl") and s.lower().endswith(HDL) and not s.startswith("/"):
                r.append((os.path.join(base, s), False))
        if base:
            r.append((base, True))
    elif p.endswith(".f"):
        for ln in txt.splitlines():
            ln = ln.strip()
            if ln.startswith("/") and " " not in ln:
                r.append((ln, True))
    else:
        for t in sorted(set(TOK.findall(txt))):
            t = t.rstrip(".")
            if len(t) > 8:
                r.append((t, False))
    return r
for top in a["paths"]:
    hard, soft, seen = [], [], set()
    todo = [(top, 0, True, top)]
    n = 0
    while todo and n < 400 and len(hard) < 4 and len(soft) < 4:
        p, dep, ishard, via = todo.pop(0)
        if p in seen:
            continue
        seen.add(p)
        n += 1
        tag = p if via == p else p + " (via " + via + ")"
        if not os.path.exists(p):
            (hard if ishard else soft).append(tag)
            continue
        if os.path.isdir(p):
            if ishard and LANE.match(p):
                b = broken_below(p)
                if b:
                    hard.append(b + " (broken link below " + p + ")")
            bf = os.path.join(p, "bind.f")
            if dep < DEPTH and os.path.isfile(bf):
                todo.append((bf, dep + 1, True, p))
        elif os.path.isfile(p) and dep < DEPTH and p.endswith((".json", ".sh", ".f")):
            for q, h in refs(p):
                todo.append((q, dep + 1, h and ishard, p))
    out[top] = {"hard": hard, "soft": soft}
print("AP_JSON " + json.dumps(out))
'''

TREE_PY = r'''
import ast, hashlib, importlib.util, json, os, sys
a = json.loads(sys.argv[1])
T, known = a["tree"], a.get("known") or ""
ENTRY, SEARCH = a["entry"], a["search"]
LOCAL = set(LOCAL_NAMES) if globals().get("LOCAL_NAMES") else None      # module names main's tools/ and physical/common_flow hold
def stat_digest():
    h = hashlib.sha1()
    for d in SEARCH[:1] + SEARCH[2:]:
        try:
            for e in sorted(os.scandir(os.path.join(T, d)), key=lambda e: e.name):
                if e.name.endswith(".py"):
                    s = e.stat()
                    h.update(f"{d}/{e.name}:{s.st_size}:{s.st_mtime_ns}\n".encode())
        except OSError:
            h.update((d + ":absent\n").encode())
    return h.hexdigest()[:16]
dg = stat_digest()
if known and known == dg:
    print("AP_JSON " + json.dumps({"digest": dg, "same": True})); sys.exit(0)
STD = set(getattr(sys, "stdlib_module_names", ())) | set(sys.builtin_module_names)
dirs = [os.path.join(T, d) for d in SEARCH]
def find(m, fdir):
    for d in [fdir] + dirs:
        p = os.path.join(d, m + ".py")
        if os.path.isfile(p):
            return p
        if os.path.isdir(os.path.join(d, m)):
            return os.path.join(d, m, "__init__.py") if os.path.isfile(os.path.join(d, m, "__init__.py")) else "<ns>"
    return ""
tops = {}
def topnames(p):
    if p in tops:
        return tops[p]
    names, flags = set(), [False]
    try:
        t = ast.parse(open(p, encoding="utf-8", errors="replace").read(), p)
    except (SyntaxError, OSError):
        tops[p] = None
        return None
    def walk(body):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
                if n.name == "__getattr__":
                    flags[0] = True
            elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for tg in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    for x in ast.walk(tg):
                        if isinstance(x, ast.Name):
                            names.add(x.id)
            elif isinstance(n, ast.Import):
                for al in n.names:
                    names.add((al.asname or al.name).split(".")[0])
            elif isinstance(n, ast.ImportFrom):
                for al in n.names:
                    if al.name == "*":
                        flags[0] = True
                    names.add(al.asname or al.name)
            elif isinstance(n, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
                for f in ("body", "orelse", "finalbody"):
                    walk(getattr(n, f, []) or [])
                for h in getattr(n, "handlers", []) or []:
                    walk(h.body)
    walk(t.body)
    tops[p] = (names, flags[0])
    return tops[p]
bad, seen, todo = [], set(), [os.path.join(T, e) for e in ENTRY]
def add(s):
    if s not in bad and len(bad) < 12:
        bad.append(s)
def optional(chain):
    return any(isinstance(x, ast.Try) and x.handlers for x in chain)
while todo:
    f = todo.pop()
    if f in seen or not os.path.isfile(f):
        continue
    seen.add(f)
    try:
        t = ast.parse(open(f, encoding="utf-8", errors="replace").read(), f)
    except SyntaxError:
        add("syntax " + os.path.relpath(f, T)); continue
    fdir = os.path.dirname(f)
    rel = os.path.relpath(f, T)
    alias = {}
    def res(m, chain):
        p = find(m, fdir)
        if p:
            if p != "<ns>":
                todo.append(p)
            return p
        if m in STD or optional(chain) or LOCAL is None or m not in LOCAL:
            return ""                          # third-party / unknown names are not skew: only a module main has and this tree lacks
        try:
            ok = importlib.util.find_spec(m) is not None
        except (ImportError, ValueError):
            ok = False
        if not ok:
            add(f"{rel}: No module named {m}")
        return ""
    def visit(n, chain):
        if isinstance(n, ast.Import):
            for al in n.names:
                m = al.name.split(".")[0]
                res(m, chain)
                if "." not in al.name:
                    alias.setdefault(al.asname or al.name, set()).add(m)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            m = n.module.split(".")[0]
            p = res(m, chain)
            if p and "." not in n.module and p != "<ns>":
                tn = topnames(p)
                if tn and not tn[1]:
                    for al in n.names:
                        if al.name != "*" and not al.name.startswith("__") and al.name not in tn[0] and not os.path.isfile(os.path.join(os.path.dirname(p), al.name + ".py")) \
                                and not optional(chain):
                            add(f"{rel}: from {m} import {al.name} (absent in {os.path.relpath(p, T)})")
        for c in ast.iter_child_nodes(n):
            visit(c, chain + [n] if isinstance(n, ast.Try) else chain)
    visit(t, [])
    shadow = {n.id for n in ast.walk(t) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
    shadow |= {x.arg for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) for x in
               n.args.args + n.args.kwonlyargs + ([n.args.vararg] if n.args.vararg else []) + ([n.args.kwarg] if n.args.kwarg else [])}
    for n in ast.walk(t):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and len(alias.get(n.value.id, ())) == 1 and n.value.id not in shadow \
                and isinstance(n.ctx, ast.Load):
            mod = next(iter(alias[n.value.id]))
            p = find(mod, fdir)
            if p and p != "<ns>":
                tn = topnames(p)
                if tn and not tn[1] and n.attr not in tn[0] and not n.attr.startswith("__") \
                        and not os.path.isfile(os.path.join(os.path.dirname(p), n.attr + ".py")):
                    add(f"{rel}: {mod}.{n.attr} (module {os.path.relpath(p, T)} has no attribute {n.attr})")
print("AP_JSON " + json.dumps({"digest": dg, "bad": bad, "n": len(seen)}))
'''

SHA_PY = r'''
import hashlib, json, os, sys
a = json.loads(sys.argv[1])
out = {}
for r in a["files"]:
    p = os.path.join(a["tree"], r)
    try:
        out[r] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    except OSError:
        out[r] = None
print("AP_JSON " + json.dumps(out))
'''

FRAME_PY = r'''
import glob, json, os, sys
a = json.loads(sys.argv[1])
out = {}
for plan in a["plans"]:
    d = os.path.dirname(plan)
    miss = []
    have = []
    if not os.path.isfile(plan):
        miss.append(plan)
    else:
        # QC N1B 11-17: a plan that NAMES its count-frame files (e.g. feed_s4q9m.json with regions_s29.json) is checked on
        # exactly those names; the feed/regions pairing below is only the fallback for a plan that names none
        named = set()
        try:
            stack = [json.load(open(plan))]
        except (OSError, ValueError):
            stack = []
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
            elif isinstance(o, str) and o.endswith(".json") and os.path.basename(o).startswith(("feed_", "regions_")) and len(o) < 4096:
                named.add(o)
        if named:
            for n in sorted(named):
                cands = [n] if os.path.isabs(n) else [os.path.join(os.path.dirname(d), n), os.path.join(d, n), os.path.join(d, os.path.basename(n))]
                hit = next((c for c in cands if os.path.isfile(c)), None)
                if hit:
                    have.append(os.path.basename(hit))
                else:
                    miss.append(cands[0] if os.path.isabs(n) else os.path.join(d, os.path.basename(n)))
            have = sorted(set(have))
        else:
            # count-frame sidecars beside a plan_of_record: feed_<s>.json and regions_<s>.json come in pairs
            feeds = {os.path.basename(p)[5:-5] for p in glob.glob(os.path.join(d, "feed_*.json"))}
            regs = {os.path.basename(p)[8:-5] for p in glob.glob(os.path.join(d, "regions_*.json"))}
            have = sorted(["feed_" + s + ".json" for s in feeds] + ["regions_" + s + ".json" for s in regs])
            for s in sorted(feeds - regs):
                miss.append(os.path.join(d, "regions_" + s + ".json"))
            for s in sorted(regs - feeds):
                miss.append(os.path.join(d, "feed_" + s + ".json"))
    out[plan] = {"hard": miss[:4], "soft": [], "have": have}
print("AP_JSON " + json.dumps(out))
'''


# ---------------------------------------------------------------- state

def fg_state(st):
    g = st.setdefault("flow_guard", {})
    for k, v in (("fails", []), ("open", {}), ("last", {}), ("pf_posted", {}), ("paths", {}), ("trees", {}), ("refused", []),
                 ("probation", {})):
        g.setdefault(k, v)
    return g


def _ok(r):
    return isinstance(r, dict) and not r.get("error")


# ---------------------------------------------------------------- preflight

def probe_paths(g, host, paths, rpy, now, timeout=180, code=PATHS_PY, tag=""):
    """{path: {"hard": [...], "soft": [...]}} for `paths` on `host` (cached per host+path); a path missing from the answer =
    unknown (ssh failed).  code/tag: the count-frame probe uses the same cache under its own tag"""
    out, todo = {}, []
    cache = g["paths"].setdefault(host, {})
    for p in paths:
        c = cache.get(tag + p)
        ttl = FAIL_TTL_S if c and (c["hard"] or c["soft"]) else PASS_TTL_S
        if c and now - c["t"] < ttl:
            out[p] = c
        else:
            todo.append(p)
    for i in range(0, len(todo), MAX_PATHS_PER_CALL):
        chunk = todo[i:i + MAX_PATHS_PER_CALL]
        r = rpy(host, code, {"paths" if code is PATHS_PY else "plans": chunk}, timeout=timeout)
        if not _ok(r):
            continue                                            # unknown = launch (a transport error is no input gap)
        for p in chunk:
            v = r.get(p)
            if isinstance(v, dict):
                cache[tag + p] = {"t": now, "hard": list(v.get("hard") or []), "soft": list(v.get("soft") or []),
                                  "have": list(v.get("have") or [])}
                out[p] = cache[tag + p]
    for p in [p for p, c in cache.items() if now - c["t"] > 4 * PASS_TTL_S]:
        del cache[p]
    return out


def tree_code(local_names=None):
    """TREE_PY with the module names main's tools hold (None: the 'No module named' check is off, attribute skew still runs)"""
    return ("LOCAL_NAMES = " + json.dumps(sorted(local_names)) + "\n" if local_names else "") + TREE_PY


def probe_tree(g, host, tree, rpy, now, timeout=180, code=None):
    """-> list of problems (strings) of tree on host, or None (unknown).  Cached per host+tree; the remote side answers
    'same' when the closure's directory digest equals the cached one."""
    c = g["trees"].setdefault(host, {}).get(tree)
    if c and now - c["t"] < TREE_TTL_S:
        return c["bad"]
    r = rpy(host, code or TREE_PY, {"tree": tree, "known": (c or {}).get("digest", ""), "entry": list(ENTRY_FILES),
                            "search": list(SEARCH_DIRS)}, timeout=timeout)
    if not _ok(r) or "digest" not in r:
        return None                                             # no / malformed answer = unknown = launch
    if r.get("same") and c:
        c["t"] = now
        return c["bad"]
    bad = list(r.get("bad") or [])
    if not r.get("n") and not bad:
        bad = ["tree has no tools/die_plan/gen.py"]             # nothing resolved at all = a pruned tree
    g["trees"][host][tree] = {"t": now, "digest": r.get("digest", ""), "bad": bad}
    return bad


def preflight_items(g, items, hosts_of, rpy, now=None, local_names=None):
    """items: {key: {"paths": [...], "trees": [...], "plans": [plan json paths]}}; hosts_of: {key: [hosts]}.
    -> {key: {"bad": {host: why}, "ok": [hosts], "kind": "paths"|"skew"|""}}  ("ok" empty = no host can serve the item)"""
    now = time.time() if now is None else now
    byhost, planhost = {}, {}
    for k, it in items.items():
        for h in hosts_of[k]:
            byhost.setdefault(h, set()).update(it["paths"])
            planhost.setdefault(h, set()).update(it.get("plans") or [])
    got = {h: probe_paths(g, h, sorted(ps), rpy, now) for h, ps in byhost.items()}
    frames = {h: probe_paths(g, h, sorted(ps), rpy, now, code=FRAME_PY, tag="frame:") for h, ps in planhost.items() if ps}
    out = {}
    for k, it in items.items():
        hs = hosts_of[k]
        bad, kinds = {}, {}
        for h in hs:
            why = None
            for p in it["paths"]:
                v = got[h].get(p)
                if not v:
                    continue
                if v["hard"]:
                    why, kinds[h] = "PATH-MISSING " + v["hard"][0], "paths"
                    break
                for s in v["soft"]:                         # incidental names count only where another candidate host has them
                    if any((got[o].get(p) is not None) and s not in got[o][p]["soft"] for o in hs if o != h):
                        why, kinds[h] = "PATH-MISSING " + s, "paths"
                        break
                if why:
                    break
            if why is None:
                for p in it.get("plans") or []:
                    v = (frames.get(h) or {}).get(p)
                    if not v:
                        continue
                    # every candidate host must hold every count-frame file ANY candidate holds beside this plan (feed_* / regions_*)
                    union = set(v.get("have") or [])
                    for o in hs:
                        union |= set(((frames.get(o) or {}).get(p) or {}).get("have") or [])
                    lack = [os.path.join(os.path.dirname(p), n) for n in sorted(union - set(v.get("have") or []))] if v.get("have") is not None \
                        and (v["have"] or v["hard"] == []) else []
                    if v["hard"] or lack:
                        why, kinds[h] = "PATH-MISSING count-frame file " + (v["hard"] or lack)[0], "paths"
                        break
            if why is None:
                for t in it["trees"]:
                    tb = probe_tree(g, h, t, rpy, now, code=tree_code(local_names))
                    if tb:
                        why, kinds[h] = "TREE-SKEW " + t + ": " + tb[0], "skew"
                        break
            if why:
                bad[h] = why
        ok = [h for h in hs if h not in bad]
        kind = ""
        if not ok and bad:
            kind = sorted(set(kinds.values()))[0] if kinds else ""
        out[k] = {"bad": bad, "ok": ok, "kind": kind}
    return out


def refusal_key(kind, bad):
    """one class per refusal: kind + the masked first reason"""
    w = next(iter(bad.values()), "") if bad else ""
    return norm_class("PREFLIGHT-" + (kind or "FLOW").upper(), w)


# ---------------------------------------------------------------- circuit breaker

CLASS_N = 3  # WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-2200 B): 3 fails per (die, stage, class) open the class breaker (was 10)
#                # FLOW-HEALTH-1 11-15 (FABLE-FLOW-1350): fails per hour of one (die, stage, class), counted across items
CLASS_WINDOW_S = 3600


def record_fail(st, die, item, cls, why, evidence="", now=None, legacy=True, stage="", inp=""):
    """called once per KIT-WAVE FAIL; returns the class key.  Opens the breaker at BREAKER_N fails in BREAKER_WINDOW_S
    (PROBATION_N while the class is on probation)"""
    now = time.time() if now is None else now
    g = fg_state(st)
    key = norm_class(cls, why)
    g["last"][f"{die}/{item}"] = key
    # class breaker over (die, stage, class) across items: >= CLASS_N in CLASS_WINDOW_S holds the class's items (half-open after the cooldown)
    k2 = f"CLASS {die}|{stage or fail_stage(why) or '-'}|{key}"[:200]
    g.setdefault("last2", {})[f"{die}/{item}"] = k2
    g["fails2"] = [f for f in g.get("fails2", []) if now - f[0] <= CLASS_WINDOW_S] + [[now, k2, f"{die}/{item}", evidence]]
    m2 = [f for f in g["fails2"] if f[1] == k2]
    if k2 in g["open"]:
        e2 = g["open"][k2]
        e2["n"] = max(e2.get("n", 0), len(m2)); e2["last_fail"] = now
        fam = family_of(item)
        if fam not in e2.setdefault("fams", []) and e2.get("state") != "probe": e2["fams"] = sorted(set(e2["fams"]) | {fam})
    elif len(m2) >= CLASS_N:
        g["open"][k2] = {"t": now, "n": len(m2), "first": m2[0][3] or evidence, "posted": 0, "kind": "", "last_fail": now, "die": die, "inp": inp,
                         "stage": stage or fail_stage(why) or "", "state": "shut", "probe": {},
                         "fams": sorted({family_of(str(f[2]).split("/", 1)[-1]) for f in m2})}
    if not legacy:
        return key
    g["fails"] = [f for f in g["fails"] if now - f[0] <= BREAKER_WINDOW_S]
    g["fails"].append([now, key, f"{die}/{item}", evidence])
    mine = [f for f in g["fails"] if f[1] == key]
    need = PROBATION_N if now < g["probation"].get(key, 0) else BREAKER_N
    if key in g["open"]:
        g["open"][key]["n"] = max(g["open"][key].get("n", 0), len(mine))
        g["open"][key]["last_fail"] = now
    elif len(mine) >= need:
        g["open"][key] = {"t": now, "n": len(mine), "first": mine[0][3] or evidence, "posted": 0, "kind": pf_kind(key),
                          "last_fail": now, "die": die}              # die: a probe of this die can close it (WAVE-PILOT-FIX)
        g["probation"].pop(key, None)
    return key


def _blocks(e, key, item, claim):
    """does open class entry e hold this item?  shut: yes.  probe (after the die's inputs changed): the FIRST item of each family may run (claim=True
    records it as the probe), every other item of that family stays held until the probe passes the class's stage"""
    if e.get("state") != "probe":
        return key
    pr = e.setdefault("probe", {})
    cur = probe_items(e)
    if item in cur:
        return ""
    if len(cur) < PROBES_PER_CLASS:                                           # WAVE-PILOT-FIX: three probes for the whole class
        if claim:
            if not cur:
                pr["*"] = item
            else:
                e.setdefault("probes", []).append(item)
            e.setdefault("probe_t", {})[item] = time.time()
        return ""
    return key


def probe_item(e):
    """the class's first probe item ('' = none claimed yet); a state written with per-family claims (before PROBE-ONE-1116) counts its first claim"""
    pr = e.get("probe") or {}
    return pr.get("*") or next(iter(pr.values()), "")


def probe_items(e):
    """every probe item the class has claimed (up to PROBES_PER_CLASS), first claim first"""
    out = [probe_item(e)] if probe_item(e) else []
    for i in e.get("probes") or []:
        if i not in out:
            out.append(i)
    return out


def held_key(st, die, item, claim=False):
    """the open class that holds an item: its own last fail's class, or (die-wide family hold, FABLE-FLOWCLASS-RETRY-2030 P4) any open class of
    the die whose failing families include the item's family, failed yet or not.  '' = free to launch"""
    g = st.get("flow_guard") or {}
    op = g.get("open") or {}
    k = (g.get("last") or {}).get(f"{die}/{item}")
    if k and k in op:
        if op[k].get("state") == "probe":
            return _blocks(op[k], k, item, claim)
        return k
    k2 = (g.get("last2") or {}).get(f"{die}/{item}")
    if k2 and k2 in op:
        r = _blocks(op[k2], k2, item, claim)
        if r:
            return r
    fam = family_of(item)
    for key, e in op.items():
        if e.get("kind") or e.get("die") != die or fam not in (e.get("fams") or []):
            continue
        r = _blocks(e, key, item, claim)
        if r:
            return r
    return ""


def probe_result(st, die, item, stage, passed, failed_stage=False, required_stage=None, required_input=None):
    """the probe launch of a family finished.  passed (it got past the class's stage, or was enqueued): the family leaves the class, the class closes
    when no family is left.  failed: the class is shut again until the die's inputs change once more.  -> list of (key, what)
    failed_stage=True judges each class separately against the actual failed stage; unknown stages never prove passage.
    PROBE-ONE-1116 (COORD 11-16): the class has ONE probe; when it passes the failing stage EVERY family of the class is released in the same
    tick (the class closes at once).  A family that fails again reopens the class by the normal breaker rule."""
    g = fg_state(st)
    out = []
    for key, e in list(g["open"].items()):
        if (e.get("kind") and e.get("state") != "probe") or e.get("die") != die or e.get("state") != "probe" or (item != probe_item(e) and item not in probe_items(e)):
            continue
        if required_stage is not None and e.get("stage") != required_stage:
            continue
        if required_input is not None and e.get("inp_probe") != required_input:
            continue
        stage_passed = (stage in STAGE_ORDER and e.get("stage") in STAGE_ORDER
                        and stage_rank(stage) > stage_rank(e["stage"])) if failed_stage else passed
        if stage_passed:
            fams = list(e.get("fams", []))
            out.append((key, f"probe {item} passed {e.get('stage') or 'the stage'}: family {family_of(item)} released"))
            close(st, key)
            out.append((key, f"all {len(fams)} famil{'y' if len(fams) == 1 else 'ies'} released in the same tick ({', '.join(fams[:12])}): class closed"))
        else:
            failed = e.setdefault("probes_failed", [])
            if item not in failed:
                failed.append(item)
            if all(i in failed for i in probe_items(e)):     # every claimed probe failed (none left running): shut until the inputs change again
                e["state"], e["probe"], e["probes"], e["probes_failed"], e["probe_t"] = "shut", {}, [], [], {}
                e["inp"] = e.get("inp_probe") or e.get("inp")
                out.append((key, f"probe {item} failed again at {stage} (all {len(failed)} claimed probe(s) failed): class stays shut until the inputs change again"))
            else:
                out.append((key, f"probe {item} failed at {stage}: {len(failed)} of {len(probe_items(e))} claimed probes failed, the others still run"))
    return out


def refresh_verified_source_probe(st, key, inp, evidence, active=False, now=None):
    """An exact current source proof may refresh an obsolete inactive source probe.
    The previous probe and failure entry stay in history. Active/unknown producers,
    missing old identity, and every other stage retain their existing lifecycle.
    """
    g = fg_state(st)
    e = g["open"].get(key) or {}
    if e.get("kind") or e.get("stage") != "src_manifest" or e.get("state") != "probe" or not inp:
        return False
    if e.get("inp_probe") == inp:
        return True
    if active or not e.get("inp_probe"):
        return False
    g.setdefault("source_probe_history", []).append(dict(
        key=key, previous=json.loads(json.dumps(e)), inp=inp, evidence=evidence,
        at=time.time() if now is None else now))
    e["inp_probe"], e["probe"] = inp, {}
    return True


def breaker_tick(st, now=None, inputs=None, trees=None):
    """a class the preflight cannot judge never releases on time or on preflight text (FABLE-FLOW-2000 b, FLOWCLASS-RETRY-2030 P4): when the inputs of
    the die it opened on change, it goes to PROBE state (one item per family may launch).  Only a probe that passes closes a family.
    inputs: {die: digest}.  -> [(key, what)] state changes (probe window opened).  A class opened without an input digest keeps the old cooldown."""
    now = time.time() if now is None else now
    g = fg_state(st)
    rel = []
    closed = []
    # WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-1700): NOTHING closes a class except a probe passing place.  A die src tree switch or an input
    # change only opens the PROBE window (three probes); a probe that runs long without a result is NOT a pass.
    # trees = {die: the die's current src tree identity}; the first sight of a die only records it.
    seen = g.setdefault("tree_seen", {})
    switched = set()
    for die, tr in (trees or {}).items():
        if tr and seen.get(die) not in (None, tr):
            switched.add(die)
        if tr:
            seen[die] = tr
    for key, b in list(g["open"].items()):
        if b.get("kind"):
            continue
        if b.get("die") in switched and b.get("state", "shut") == "shut":
            b["state"], b["probe"], b["probes"], b["probes_failed"], b["probe_t"] = "probe", {}, [], [], {}
            b["inp_probe"] = (inputs or {}).get(b.get("die")) or b.get("inp_probe") or b.get("inp")
            rel.append((key, "the die's src tree switched: PROBE window open (three probes), the class closes only when a probe passes place"))
            continue
        if b.get("inp"):
            cur = (inputs or {}).get(b.get("die"))
            if cur and cur != b["inp"] and b.get("state", "shut") == "shut":
                b["state"], b["probe"], b["inp_probe"] = "probe", {}, cur
                rel.append((key, "the die's inputs changed: PROBE window open, one item per family may launch"))
        elif now - float(b.get("last_fail") or b["t"]) >= BREAKER_COOLDOWN_S:
            rel.append((key, f"cooldown {BREAKER_COOLDOWN_S // 60} min without a new fail"))
            closed.append(key)
    for key in closed:
        close(st, key, now)
    return rel


def close(st, key, now=None):
    now = time.time() if now is None else now
    g = fg_state(st)
    g["open"].pop(key, None)
    g["probation"][key] = now + BREAKER_WINDOW_S
    for ik in [k for k, v in g["last"].items() if v == key]:
        del g["last"][ik]


def release_by_preflight(st, held_pf, now=None):
    """held_pf: {key: [bool pass per held item evaluated this tick]} -> [(key, why)] closed (every held item passes, >= 1)"""
    g = fg_state(st)
    rel = []
    for key, res in held_pf.items():
        b = g["open"].get(key)
        if b and b.get("kind") and res and all(res) and b.get("state") != "probe":
            # WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-1900 C): a preflight that passes may not see the cause, so it closes nothing; it opens the PROBE
            # window and the class closes only when a probe (a real launch) gets past the stage that failed.
            b["state"], b["probe"], b["probes"], b["probes_failed"], b["probe_t"] = "probe", {}, [], [], {}
            rel.append((key, f"preflight passes again for all {len(res)} held item(s): PROBE window open; the class closes only when a probe passes"))
    return rel


def alert_lines(st, now_s):
    """-> [(key, line)] one ALERT per newly opened class (marks posted)"""
    g = fg_state(st)
    out = []
    for key, b in g["open"].items():
        if b.get("posted"):
            continue
        held = sorted(k for k, v in g["last"].items() if v == key)
        out.append((key, f"- {now_s} ALERT [FLOW-GUARD -> COORD; cc KIT-OPS] CLASS-BREAKER open: '{key}' {b['n']} fails in "
                         f"{BREAKER_WINDOW_S // 60} min; first log {b.get('first') or 'n/a'}; {len(held)} item(s) held (no launch, no auto-retry): "
                         f"{' '.join(held[:12])}{' ...' if len(held) > 12 else ''}; releases when "
                         + ("the preflight passes again for every held item" if b.get("kind") else
                            "the die's inputs (plan block / src / overlay / the stage's tool files) change and one probe launch per family passes this stage")))
        b["posted"] = time.time()
    return out


def refusal_line(now_s, key, kind, n_items, sample, bad):
    return (f"- {now_s} ASK [FLOW-GUARD -> COORD; cc KIT-OPS] PREFLIGHT-REFUSED class '{key}': {n_items} row(s) not launched, no host holds "
            f"every input (kind {kind or 'paths'}); e.g. {' '.join(sample[:6])}: " + "; ".join(f"{h}: {w[:200]}" for h, w in list(bad.items())[:4])
            + "; one line per class, the rows launch when a later preflight passes")


# ---------------------------------------------------------------- source skew (hourly report)

def closure_files(read, entry=ENTRY_FILES, search=SEARCH_DIRS):
    """module files (tree-relative) the entry modules import, resolved against `search` dirs.  read(rel) -> text or None
    (main's copy).  Imports of a module that does not resolve are ignored here (the tree probe reports them)."""
    out, todo, seen = [], list(entry), set()
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        seen.add(rel)
        txt = read(rel)
        if txt is None:
            continue
        out.append(rel)
        try:
            tree = ast.parse(txt)
        except SyntaxError:
            continue
        here = rel.rsplit("/", 1)[0] if "/" in rel else ""
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
                names.add(n.module.split(".")[0])
        for m in sorted(names):
            for d in [here] + list(search):
                cand = f"{d}/{m}.py" if d else f"{m}.py"
                if read(cand) is not None:
                    todo.append(cand)
                    break
    return sorted(out)


# the kit scripts a die tree carries into every kit (core_flow.stage_grt183 copies them): GRT early stops lived in these and stayed in trees that
# predate main (FLOW-HEALTH-1 11-16: the S81 tree B6gG3b still stopped GRT at iteration 15 four days after main deleted the rule)
KIT_SCRIPTS = ("physical/common_flow/grt183_make.sh", "physical/common_flow/grt183_resume.tcl", "physical/common_flow/grt_stall_resume.tcl",
               "physical/common_flow/failfast_rules.py", "physical/common_flow/hold_guard_grt.tcl")


def skew_report(trees, main_sha, read_main, rpy, hosts_of):
    """trees: [(die, tree)]; main_sha(rel) -> sha1 of main's file or None; hosts_of: {die: [hosts]}.
    -> [(die, host, tree, [rel differing from main])] only where something differs (a missing file counts)"""
    files = closure_files(read_main)
    files += [f for f in KIT_SCRIPTS if f not in files and main_sha(f) is not None]
    want = {r: main_sha(r) for r in files}
    jobs = [(die, h, tree) for die, tree in trees for h in hosts_of.get(die, [])]

    def one(job):
        die, h, tree = job
        r = rpy(h, SHA_PY, {"tree": tree, "files": files}, timeout=180)
        if not _ok(r):
            return (die, h, tree, ["<unreachable: " + str((r or {}).get("error"))[:80] + ">"])
        diff = [f for f in files if r.get(f) != want[f]]
        return (die, h, tree, diff) if diff else None

    # every (die, host, tree) probe is independent: one worker per host at a time keeps the sshd load flat (COORD 11-16: cover everything, no cap)
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max(1, min(16, len(jobs)))) as ex:
        return [x for x in ex.map(one, jobs) if x]
