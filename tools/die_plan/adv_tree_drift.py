"""ADV-TREE-DRIFT (PRECHECK-R2, COORD flow review 11-23; estimator, never a gate): fixes on main the bound tree is missing.

A die event tree is a copy of an older tree (S81 J8 j8_cut_tree <- d8j7_1117_work, main pin 3c913dbdfb23 of 11-17), so a fix
pushed to main later never reaches it unless someone carries it.  Known positives: the 11-21 u_cf view fix (main 31c7ccbd1b,
via-shadow OBS in physical/ref_tile/s81coll_cfifo_crs4/views/dsfd_cfifo_crs4/, UCF-VIEW-FIX 11-23) never reached any J7/J8
tree; the QC DPL-0033 kits predate main f60d28bf6d (physical/common_flow/grt183_make.sh diamond legalizer).

Scope (only these files are hashed, so it runs in seconds):
  view    every file the plan (and as-built) names that lives in a view (lef / lib / pins_file / budget_owner paths under
          */views/*, landing_evidence, memory-macro lefs) plus every main file of each named view directory
  porous  tools/die_plan/porous_views_data/ (and any named path with 'porous')
  flow    physical/common_flow/ (all files)
  tool    tools/die_plan/*.py (not test_*) and every other tools/ path the plan names
  rtl     rtl/ sources the plan names, plus the BIND-TREE RTL CLOSURE (PRECHECK-R3 11-24): every tree/rtl file defining a
          module a type names (module / contents[].module / hard_cores[].module) and, transitively, each module those files
          instantiate; one line per lagging file with the types that reach it (QC C1g coll_core: ot_coll_tp8_static.sv
          603 lines in the tree, 659 on main = RDPIPE/XEPRE missing; plans that name modules only never listed it)
Per file: tree blob id (git hash-object, in process) vs main's (`git ls-tree` of the warm bare repo / $OT_ADV_MAIN_REPO), then
one path-limited `git log --raw` over the differing paths:
  LAG      the tree copy equals an OLDER main version of the path: the fix(es) since are missing (main commits named)
  LOCAL    differs from every main version in the searched history (an intended private change: counted only)
  MISSING  on main inside a scope directory, absent in the tree (counted; view / flow ones listed)
The ADOPT-DIFF tool (tools/autopilot/event_adopt_diff.py) does the same three-way with a recorded pin and can `carry` the LAG
files; this check needs no pin (it uses .src-manifest.json main_sha / .fork.json src_main_sha only to bound the log) and runs
inside plan_gate_pre.  Stdlib only; never raises.
"""
import hashlib
import os
import re
import subprocess
import time
from pathlib import Path

CHECK = "ADV-TREE-DRIFT"
MAX_LINES = 20
BUDGET_S = float(os.environ.get("OT_ADV_TREE_DRIFT_BUDGET_S", "50"))
HORIZON_D = float(os.environ.get("OT_ADV_TREE_DRIFT_HORIZON_D", "10"))   # LOCAL = no main version this many days before the pin
WARM = "/srv/opentallas-scratch2/claude/warm/OpenTallas.git"
MAIN_REFS = ("refs/remotes/origin/main", "origin/main", "refs/heads/main", "main")
FLOW_DIRS = ("physical/common_flow",)
POROUS_DIRS = ("tools/die_plan/porous_views_data",)
TOOL_GLOB_DIR = "tools/die_plan"                 # top-level *.py, not test_*
ROOTS = ("physical/", "tools/", "rtl/")
PRIO = {"view": 0, "porous": 1, "flow": 2, "tool": 3, "rtl": 4, "other": 5}
HERE = Path(__file__).resolve().parent
_PATHISH = re.compile(r"[A-Za-z0-9_./+-]+")


def _w(msg):
    return f"WARN {CHECK} {msg}"


def _git(repo, args, timeout, input_=None):
    r = subprocess.run(["git", "--git-dir", repo] + args, capture_output=True, timeout=max(1.0, timeout), input=input_)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])}: {r.stderr.decode(errors='replace').strip()[-200:]}")
    return r.stdout


def _git_dir(cand):
    """git dir of a bare repo or a work tree, '' when not a repo"""
    if not cand or not os.path.isdir(cand):
        return ""
    try:
        r = subprocess.run(["git", "-C", cand, "rev-parse", "--absolute-git-dir"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    if r.returncode:
        return ""
    gd = r.stdout.strip()
    # a linked worktree: objects live in the common dir, refs too (rev-parse handles it); keep the per-worktree dir
    return gd


def _repo_main(kw):
    cands = [kw.get("main_repo"), os.environ.get("OT_ADV_MAIN_REPO"), WARM, str(HERE.parent.parent)]
    refs = [kw.get("main_ref") or os.environ.get("OT_ADV_MAIN_REF")] + list(MAIN_REFS)
    for c in cands:
        gd = _git_dir(c)
        if not gd:
            continue
        for ref in refs:
            if not ref:
                continue
            r = subprocess.run(["git", "--git-dir", gd, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"],
                               capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout.strip():
                return gd, r.stdout.strip()
    return "", ""


def _find_tree(plan_path):
    p = Path(plan_path).resolve().parent
    for q in [p] + list(p.parents):
        if (q / "tools" / "die_plan").is_dir() and (q / "physical").is_dir():
            return str(q)
    return None


def _blob(path):
    if os.path.islink(path):
        d = os.readlink(path).encode()
    else:
        with open(path, "rb") as f:
            d = f.read()
    return hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()


def _strings(o, out, depth=0):
    if depth > 60:
        return
    if isinstance(o, dict):
        for v in o.values():
            _strings(v, out, depth + 1)
    elif isinstance(o, list):
        for v in o:
            _strings(v, out, depth + 1)
    elif isinstance(o, str) and "/" in o and len(o) < 2000:
        out.add(o)


def _ref_paths(raw, tree, plan_path, extra_docs=()):
    """repo-relative candidate paths (each with its alternatives) the plan / as-built name"""
    ss = set()
    _strings(raw, ss)
    for d in extra_docs:
        _strings(d, ss)
    rt = os.path.realpath(tree) + "/"
    die = str(raw.get("die") or "") if isinstance(raw.get("die"), str) else str((raw.get("die") or {}).get("name") or "")
    pdir = ""
    try:
        rp = os.path.realpath(plan_path)
        if rp.startswith(rt):
            pdir = os.path.dirname(rp[len(rt):])
    except (OSError, TypeError):
        pass
    bases = [""] + ([pdir + "/"] if pdir else []) + ([f"physical/die_plan/{die}/"] if die else [])
    out = {}
    for s in ss:
        for tok in _PATHISH.findall(s):
            if "/" not in tok or tok.endswith("/") or ".." in tok:
                continue
            if tok.startswith("/"):
                if not tok.startswith(rt):
                    continue
                tok = tok[len(rt):]
            tok = tok[2:] if tok.startswith("./") else tok
            if tok.startswith(ROOTS):
                out.setdefault(tok, (tok,))
            elif "." in tok.rsplit("/", 1)[-1]:
                out.setdefault(tok, tuple(b + tok for b in bases[1:]))
    return out


_MODDECL = re.compile(r"^\s*(?:macro)?module\s+(?:automatic\s+)?([A-Za-z_]\w*)", re.M)
_INST = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|[A-Za-z_\\][\w\[\]:.]*\s*\()", re.M)
_CMT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
RTL_EXT = (".sv", ".v", ".svh", ".vh")
RTL_LINES = 16
MAX_CLOSURE = int(os.environ.get("OT_ADV_TREE_DRIFT_MAX_RTL", "6000"))


def _is_tb(rel):
    b = os.path.basename(rel)
    return b.startswith(("tb_", "test_")) or "/test/" in rel or "/tb/" in rel or b.endswith(("_sim.sv", "_sim.v"))


def plan_roots(raw):
    """{module: [types]} the plan instantiates by name: each type's module, contents[].module and hard_cores[].module"""
    out = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        if not isinstance(t, dict):
            continue
        ms = [t.get("module")]
        for k in ("contents", "hard_cores"):
            for c in t.get(k) or []:
                if isinstance(c, dict):
                    ms.append(c.get("module"))
        for m in ms:
            if isinstance(m, str) and m:
                out.setdefault(m, []).append(tn)
    return out


RTL_INDEX_S = float(os.environ.get("OT_ADV_TREE_DRIFT_RTL_S", "120"))
_IDX_MEMO = {}


def rtl_index(tree, deadline=None):
    """({module: [rel files]}, {rel file: set(instantiated identifiers)}) over tree/rtl (tb / test files left out).
    Memoised per tree in-process (ADV-UNSET-DEFINE reuses TREE-DRIFT's); inst gets key None = True when the walk was cut short."""
    base = os.path.realpath(tree)
    if base in _IDX_MEMO:
        return _IDX_MEMO[base]
    idx, inst = {}, {}
    deadline = deadline or time.time() + RTL_INDEX_S
    for root, _d, files in os.walk(os.path.join(base, "rtl")):
        if time.time() > deadline:
            inst[None] = True
            break
        for fn in files:
            if not fn.endswith(RTL_EXT):
                continue
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, base)
            if _is_tb(rel):
                continue
            try:
                with open(fp, errors="replace") as f:
                    s = _CMT.sub("", f.read())
            except OSError:
                continue
            for m in set(_MODDECL.findall(s)):
                idx.setdefault(m, []).append(rel)
            inst[rel] = set(_INST.findall(s))
    _IDX_MEMO[base] = (idx, inst)
    return idx, inst


def rtl_closure(raw, tree, deadline=None, index=None):
    """the bind-tree RTL the plan's types reach: {rel file: parent rel file | None for a root} -- files defining a module
    the plan names, then every file defining a module those files instantiate (whole-file over-approximation; a module
    defined in more than 4 files counts none of them: a generated variant family, not one source)"""
    idx, inst = index or rtl_index(tree, deadline)
    roots = plan_roots(raw)
    out = {}
    todo = [(m, None) for m in sorted(roots)]
    seen = set()
    while todo and len(out) < MAX_CLOSURE:
        m, parent = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        fs = idx.get(m) or []
        if len(fs) > 4:
            continue
        for f in fs:
            if f in out:
                continue
            out[f] = parent
            for c in sorted(inst.get(f, ())):
                if c in idx and c not in seen:
                    todo.append((c, f))
    return out


def closure_types(raw, index, files):
    """{rel file: sorted types} for the given closure files: the types whose root modules reach the file (reverse walk)"""
    idx, inst = index
    defs = {}
    for m, fs in idx.items():
        if len(fs) <= 4:
            for f in fs:
                defs.setdefault(f, set()).add(m)
    users = {}                                         # module -> files instantiating it
    for f, cs in inst.items():
        if f is None:
            continue
        for c in cs:
            if c in idx:
                users.setdefault(c, set()).add(f)
    roots = plan_roots(raw)
    out = {}
    for f in files:
        ts, seen, todo = set(), set(), [f]
        while todo and len(seen) < 20000:
            g = todo.pop()
            if g in seen:
                continue
            seen.add(g)
            for m in defs.get(g, ()):
                ts.update(roots.get(m, ()))
                todo.extend(users.get(m, ()))
        out[f] = sorted(ts)
    return out


def _cat(path):
    if "porous" in path:
        return "porous"
    if "/views/" in path or "landing_evidence" in path or "memory_macros" in path or path.endswith((".lef", ".lib")):
        return "view"
    if path.startswith(FLOW_DIRS[0] + "/"):
        return "flow"
    if path.startswith("tools/"):
        return "tool"
    if path.startswith("rtl/"):
        return "rtl"
    return "other"


def _view_dir(path):
    """the view directory of a file below */views/<name>/ (None otherwise)"""
    parts = path.split("/")
    for i in range(len(parts) - 2):
        if parts[i] == "views":
            return "/".join(parts[:i + 2])
    return None


def _ls_tree(repo, main, specs, deadline):
    """{path: oid} of main's blobs under specs (tree objects only: no -l, which would read every blob header and, in a
    partial clone, fetch missing blobs)"""
    res = {}
    for i in range(0, len(specs), 300):
        out = _git(repo, ["ls-tree", "-r", "-z", "--full-tree", main, "--"] + specs[i:i + 300], deadline - time.time())
        for ent in out.split(b"\0"):
            if not ent:
                continue
            meta, _, p = ent.partition(b"\t")
            f = meta.split()
            if len(f) >= 3 and f[1] == b"blob":
                res[p.decode(errors="replace")] = f[2].decode()
    return res


def _pin(tree):
    import json
    for name, key in ((".src-manifest.json", "main_sha"), (".fork.json", "src_main_sha")):
        p = Path(tree) / name
        try:
            if p.is_file() and p.stat().st_size < 200_000_000:
                with open(p) as f:
                    v = json.load(f).get(key)
                if v:
                    return str(v)
        except (OSError, ValueError, AttributeError):
            continue
    return ""


def _history(repo, rev, paths, tree_oid, since_ct, deadline, final=True):
    """{path: ('LAG', [(h, ct, subj), ...] missing commits, base (h, ct)) | ('LOCAL',)} from one path-limited log of rev (newest
    first); a path whose tree blob is no version in the walk is LOCAL when final, else left out; paths not reached in time: absent"""
    res = {}
    todo = list(paths)
    for i in range(0, len(todo), 300):
        chunk = todo[i:i + 300]
        left = deadline - time.time()
        if left < 2:
            break
        args = ["log", "--raw", "--no-abbrev", "--no-renames", "-z", "--format=%x01%H %ct %s", rev]
        if since_ct:
            args.insert(1, f"--since={since_ct}")
        try:
            out = _git(repo, args + ["--"] + chunk, left)
        except (RuntimeError, subprocess.TimeoutExpired):
            break
        seen = {p: [] for p in chunk}
        cur, pend = None, None
        for tok in out.split(b"\0"):
            if not tok:
                continue
            t = tok.decode(errors="replace")
            if "\x01" in t:            # a commit header; with -z the first raw meta follows it in the same token after "\n"
                hdr, _, t = t.split("\x01", 1)[1].partition("\n")
                h, ct, subj = (hdr.split(" ", 2) + ["", ""])[:3]
                cur = (h[:10], int(ct) if ct.isdigit() else 0, subj)
                pend = None
                t = t.strip("\n")
                if not t:
                    continue
            t = t.lstrip("\n")
            if t.startswith(":"):
                meta = t[1:].split()
                pend = (meta[2], meta[3]) if len(meta) >= 4 else None
                continue
            p = t
            if p in seen and p not in res and pend and cur:
                old, new = pend
                T = tree_oid[p]
                if new == T:
                    res[p] = ("LAG", list(seen[p]), cur)
                elif old == T:
                    res[p] = ("LAG", list(seen[p]) + [cur], None)
                else:
                    seen[p].append(cur)
            pend = None
        if final:
            for p in chunk:
                res.setdefault(p, ("LOCAL",))
    return res


def _run(raw, plan_path, tree, kw):
    tree = tree or _find_tree(plan_path)
    if not tree or not os.path.isdir(tree):
        return []
    # bind-tree RTL: the module closure of the plan's types in tree/rtl (the plan names RTL files only where a type lists
    # `sources`; QC / KV types name modules only, so a lagging tree copy such as QC ot_coll_tp8_static.sv went unseen).
    # Own budget (RTL_INDEX_S), before the BUDGET_S clock of the hash / history steps starts.
    t_a = time.time()
    rtlix, closure = None, {}
    if kw.get("rtl_closure", True) and os.path.isdir(os.path.join(tree, "rtl")):
        rtlix = rtl_index(tree)
        closure = rtl_closure(raw, tree, index=rtlix)
    t_rtl = time.time() - t_a
    t0 = time.time()
    deadline = t0 + BUDGET_S
    repo, main = _repo_main(kw)
    if not repo:
        return [_w("not checked: no main repo (warm bare repo / $OT_ADV_MAIN_REPO) resolves a main ref")]
    docs = []
    ab = kw.get("asbuilt")
    if ab and os.path.isfile(str(ab)):
        import json
        try:
            with open(ab) as f:
                docs.append(json.load(f))
        except (OSError, ValueError):
            pass
    refs = _ref_paths(raw, tree, plan_path, docs)
    # main listing of the scope dirs + the named files' dirs (no blob is read)
    dirs = set(FLOW_DIRS) | set(POROUS_DIRS) | {TOOL_GLOB_DIR}
    for alts in refs.values():
        for a in alts:
            dirs.add(_view_dir(a) or os.path.dirname(a) or a)
    for f in closure:
        dirs.add(os.path.dirname(f))
    dirs = {d for d in dirs if d}
    t_a = time.time()
    try:
        mainix = _ls_tree(repo, main, sorted(dirs, key=lambda d: (PRIO.get(_cat(d + '/'), 9), d)), deadline)
    except subprocess.TimeoutExpired:
        return [_w(f"not checked: git ls-tree of {len(dirs)} dirs in {repo} over the {BUDGET_S:.0f} s budget (loaded host?)")]
    t_ls = time.time() - t_a
    scope = {}                                        # path -> category
    for alts in refs.values():
        hit = next((a for a in alts if a in mainix), None) or next((a for a in alts if os.path.isfile(os.path.join(tree, a))), None)
        if hit:
            scope[hit] = _cat(hit)
    for f in closure:
        if f in mainix:
            scope.setdefault(f, "rtl")
    vdirs = {_view_dir(p) for p in scope if _view_dir(p)}
    for p in mainix:
        if p.startswith(tuple(d + "/" for d in FLOW_DIRS + POROUS_DIRS)) or _view_dir(p) in vdirs:
            scope.setdefault(p, _cat(p))
        elif os.path.dirname(p) == TOOL_GLOB_DIR and p.endswith(".py") and not os.path.basename(p).startswith("test_"):
            scope.setdefault(p, "tool")
    cache = _Cache(kw.get("cache_dir") or os.environ.get("OT_ADV_CACHE_DIR"))
    cur, differ, missing, tree_only, unread, skipped = 0, {}, [], 0, 0, 0
    tree_oid = {}
    t_a = time.time()
    hash_stop = t0 + BUDGET_S * 0.7                   # leave time for the history walk
    for p, cat in sorted(scope.items(), key=lambda kv: (PRIO.get(kv[1], 9), kv[0])):
        fp = os.path.join(tree, p)
        m = mainix.get(p)
        if not (os.path.isfile(fp) or os.path.islink(fp)):
            if m:
                missing.append(p)
            continue
        if not m:
            tree_only += 1
            continue
        if time.time() > hash_stop:
            skipped += 1
            continue
        try:
            oid = cache.oid(fp)
        except OSError:
            unread += 1
            continue
        if oid == m:
            cur += 1
        else:
            tree_oid[p] = oid
            differ[p] = cat
    cache.save()
    t_hash = time.time() - t_a
    pin = _pin(tree)
    pin_ct = 0
    if pin:
        try:
            pin_ct = int(_git(repo, ["show", "-s", "--format=%ct", pin + "^{commit}"], 20).strip() or 0)
        except (RuntimeError, subprocess.TimeoutExpired, ValueError):
            pin, pin_ct = "", 0                      # a label / unknown sha: no fast path
    order_d = sorted(differ, key=lambda p: (PRIO.get(differ[p], 9), p))
    t_a = time.time()
    hist = {}
    if pin_ct:      # fast path: pin..main (~1 s); catches every tree copy equal to the pin's or a later main version
        hist = _history(repo, f"{pin}..{main}", order_d, tree_oid, 0, deadline, final=False)
    # the rest (event-edited copies, copies older than the pin): main history back to HORIZON_D days before the pin / now
    since = (pin_ct or int(time.time())) - HORIZON_D * 86400
    rest = [p for p in order_d if p not in hist]
    if rest:
        hist.update(_history(repo, main, rest, tree_oid, since, deadline, final=True))
    t_log = time.time() - t_a
    lag = {p: hist[p] for p in differ if hist.get(p, ("?",))[0] == "LAG" and hist[p][1]}
    local = [p for p in differ if hist.get(p, ("?",))[0] == "LOCAL"]
    unres = [p for p in differ if p not in hist]
    # LAG lines: view / porous / flow one per view dir or file (same missing commits); tool / rtl / other one per category
    groups = {}
    for p, (_, miss, base) in lag.items():
        cat = differ[p]
        if PRIO.get(cat, 9) <= PRIO["flow"] or cat == "rtl":
            key = (cat, _view_dir(p) or p, tuple(h for h, _, _ in miss))
        else:
            key = (cat, cat, ())
        g = groups.setdefault(key, dict(cat=cat, files=[], miss={}, base=base))
        g["files"].append(p)
        for c in miss:
            g["miss"].setdefault(c[0], [c, 0])[1] += 1
    order = sorted(groups.items(), key=lambda kv: (PRIO.get(kv[1]["cat"], 9),
                                                  -max(c[1] for c, _ in kv[1]["miss"].values()), kv[0][1]))
    lines = []
    by_commit = {}
    # porous store entries <macro>.lef.<hash>.* count only for macros the plan names (other dies' views are not this tree's)
    stems = set()
    for alts in refs.values():
        b = os.path.basename(alts[0]).split(".")[0]
        stems |= {b, re.sub(r"_(tt|bc|ss|ff|tc)$", "", b)}
    def _keep(p):
        if _cat(p) == "porous" and ".lef." in os.path.basename(p):
            return os.path.basename(p).split(".lef.", 1)[0] in stems
        return _cat(p) in ("view", "flow", "porous")
    mis_list = sorted((p for p in missing if _keep(p)), key=lambda p: (PRIO[_cat(p)], p))
    mis_line = _w(f"MISSING {len(mis_list)} view/porous/flow file(s) on main absent in the tree: " + ", ".join(mis_list[:6]) +
                  (" ..." if len(mis_list) > 6 else "") + "; fix = carry from main or record why") if mis_list else None
    rtl_lag = [p for p in lag if differ[p] == "rtl"]
    rtypes = closure_types(raw, rtlix, [p for p in rtl_lag if p in closure]) if rtlix and rtl_lag else {}
    nrtl = 0
    for (_, name, _), g in order:
        if mis_line and PRIO.get(g["cat"], 9) > PRIO["flow"]:
            lines.append(mis_line)
            mis_line = None
        for h, (c, n) in g["miss"].items():
            by_commit[h] = by_commit.get(h, 0) + n
        miss = sorted(g["miss"].values(), key=lambda cn: (-cn[1], -cn[0][1]))
        if g["cat"] == "rtl":            # own budget: a bind-tree RTL copy behind main changes the netlist the kit builds
            nrtl += 1
            if nrtl > RTL_LINES:
                continue
            ts = rtypes.get(name) or []
            reach = (f"reached by {len(ts)} type(s) ({','.join(ts[:3])}{' ...' if len(ts) > 3 else ''})" if ts else
                     "named by the plan" if name not in closure else "in the closure")
            shown = "; ".join(f"{c[0]} {c[2][:80]}" for c, _ in miss[:3]) + (f"; +{len(miss) - 3} more" if len(miss) > 3 else "")
            base = f" (tree = main version of {g['base'][0]} {time.strftime('%m-%d', time.gmtime(g['base'][1]))})" if g["base"] else ""
            lines.append(_w(f"rtl {name}: LAG{base}, {reach}; missing {len(miss)} main commit(s): {shown}; "
                            f"fix = carry from main before bind (event_adopt_diff.py carry) or record why the tree keeps it"))
            continue
        if len(lines) >= MAX_LINES:
            continue
        per = PRIO.get(g["cat"], 9) > PRIO["flow"]
        shown = "; ".join(f"{c[0]} {c[2][:80]}" + (f" (x{n})" if per else "") for c, n in miss[:4]) + \
            (f"; +{len(miss) - 4} more" if len(miss) > 4 else "")
        nf = len(g["files"])
        files = ", ".join(os.path.basename(f) if f != name else f for f in sorted(g["files"])[:6 if per else 4]) + \
            (f" +{nf - (6 if per else 4)}" if nf > (6 if per else 4) else "")
        base = f" (tree = main version of {g['base'][0]} {time.strftime('%m-%d', time.gmtime(g['base'][1]))})" \
            if g["base"] and not per else ""
        what = f"{g['cat']} {name}" if not per else f"{g['cat']} files"
        lines.append(_w(f"{what}: LAG {nf} file(s) [{files}]{base}, missing {len(miss)} main commit(s): {shown}; "
                        f"fix = carry from main before bind (event_adopt_diff.py carry) or record why the tree keeps it"))
    if mis_line:
        lines.append(mis_line)
    cats = {}
    for p in lag:
        cats[differ[p]] = cats.get(differ[p], 0) + 1
    top = ", ".join(f"{h} x{n}" for h, n in sorted(by_commit.items(), key=lambda kv: -kv[1])[:6])
    lines.append(_w(f"summary: tree {tree} vs main {main[:10]} ({repo}): {len(scope)} files in scope, CURRENT {cur}, "
                    f"LAG {len(lag)} ({', '.join(f'{k} {v}' for k, v in sorted(cats.items(), key=lambda kv: PRIO.get(kv[0], 9))) or 'none'}), "
                    f"LOCAL {len(local)}{_bycat(local, differ)}, MISSING {len(missing)} ({len(mis_list)} listed scope), tree-only {tree_only}"
                    + (f", NOT HASHED {skipped} (time budget)" if skipped else "")
                    + (f", UNRESOLVED {len(unres)} (time budget)" if unres else "") + (f", unreadable {unread}" if unread else "")
                    + f"; bind RTL closure {len(closure)} file(s) from {len(plan_roots(raw))} plan module(s), LAG {len(rtl_lag)}"
                    + (" (rtl index CUT at the time budget: partial)" if rtlix and rtlix[1].get(None) else "")
                    + (f" ({nrtl - RTL_LINES} not listed)" if nrtl > RTL_LINES else "")
                    + f"; top missing commits: {top or 'none'}; pin {pin[:10] or '-'}; {time.time() - t0 + t_rtl:.1f} s "
                    f"(rtl index {t_rtl:.1f}, ls-tree {t_ls:.1f}, hash {t_hash:.1f}, log {t_log:.1f})"))
    return lines


def _bycat(paths, cat):
    n = {}
    for p in paths:
        n[cat[p]] = n.get(cat[p], 0) + 1
    return (" (" + ", ".join(f"{k} {v}" for k, v in sorted(n.items(), key=lambda kv: PRIO.get(kv[0], 9))) + ")") if n else ""


class _Cache:
    """blob ids keyed by (path, size, mtime_ns); on disk only with cache_dir / $OT_ADV_CACHE_DIR"""

    def __init__(self, d):
        self.path = os.path.join(d, "adv_tree_drift_oids.json") if d else None
        self.db, self.dirty = {}, False
        if self.path and os.path.isfile(self.path):
            import json
            try:
                with open(self.path) as f:
                    self.db = json.load(f)
            except (OSError, ValueError):
                self.db = {}

    def oid(self, fp):
        st = os.lstat(fp)
        k = f"{fp}|{st.st_size}|{st.st_mtime_ns}"
        v = self.db.get(k)
        if v is None:
            v = self.db[k] = _blob(fp)
            self.dirty = True
        return v

    def save(self):
        if not (self.path and self.dirty):
            return
        import json
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = f"{self.path}.{os.getpid()}.tmp"
            with open(tmp, "w") as f:
                json.dump(self.db, f)
            os.replace(tmp, self.path)
        except OSError:
            pass


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _run(raw or {}, plan_path, tree, kw)
    except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
        return [_w(f"not checked: {type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--tree")
    ap.add_argument("--repo")
    ap.add_argument("--asbuilt")
    a = ap.parse_args()
    t = time.time()
    with open(a.plan) as f:
        r = json.load(f)
    tl = time.time() - t
    for x in findings(r, a.plan, a.tree, main_repo=a.repo, asbuilt=a.asbuilt):
        print(x)
    print(f"# load {tl:.1f} s, check {time.time() - t - tl:.1f} s")
