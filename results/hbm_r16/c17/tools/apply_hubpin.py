#!/usr/bin/env python3
"""HBM-MU-QUAD-6/HUBPIN: per-quadrant core_conns + face fixes for the quadrant-split hub services.
usage: apply_hubpin.py IN_PLANDIR OUT_PLANDIR REPORT.json [--tools GATE_TOOLS] [--ccsplit CCSPLIT.py] [--wt RTL_WT]

 1. OUT = full copy of IN with every symlink DEREFERENCED (real files and dirs only; gates/ not copied), so nothing
    this script writes can reach another plan through a link; every write also asserts its resolved path is in OUT.
 2. ccsplit: core_conns.json rewritten per quadrant (leaf X__qk -> partner Y__qk) with ccsplit.py.
 3. For every core port the b1n check.py core_faces rule reports as facing away (mean cos < -0.1), in order
    (COORD HBM-CORES-R8 (1) 10-27: ONE plan pin group per RTL port, no copy groups; B only with --allow-output-copies):
    A  RE-PIN: move the port's single base pin group to the
       core face where EVERY instance of the master that binds that group has mean cos >= 0 toward its own partners
       (instances bound to existing copies are unaffected; an instance on a copy may also be re-bound to the base when
       the base re-pin suits it and all base binders).  No new pins, no new groups.
    B  OUTPUT-ONLY copy (port is an RTL output of the master): bind an existing copy on the facing face, else add a
       copy group '<port>__<F>' (F = core-frame face).  Each master relying on B is listed in the report
       (wrapper_needs: `output X__F; assign X__F = X;`).
    C  FLAG (input port, or no legal face): left for COORD (variant type / strap+mux / small core move).
    Pin legality like the existing tables: W/E faces M4, N/S faces M5, 0.048 pitch, 0.024 offset, 0.019 inset,
    >= 8.64 um from the corners, no track shared with another pin on that face, face total <= 0.6 of its tracks;
    a group is placed as a block at the partners' projection, every other track where possible.
 4. A copy added in B whose base no instance binds any more is collapsed into the base (base re-pinned there).
 5. unused_pins re-derived for every instance of a touched table.
"""
import argparse, collections, hashlib, json, math, os, re, shutil, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("report")
ap.add_argument("--tools", default="/srv/opentallas-scratch2/claude/codex-hbm-1027/gate_tools")
ap.add_argument("--ccsplit", default="/srv/opentallas-scratch2/claude/hbm-mu-quad-6-1027/ccsplit.py")
ap.add_argument("--wt", default="/srv/opentallas-scratch2/claude/wt/hbm-cores-r7-1027", help="RTL worktree (port dirs)")
ap.add_argument("--allow-output-copies", action="store_true",
                help="method B (output copy groups); OFF by default: COORD HBM-CORES-R8 (1) one plan pin group per RTL port")
ap.add_argument("--dir-cache", default=str(Path(__file__).resolve().parent / "rtl_files_cache.json"),
                help="module -> RTL file cache (keyed by the worktree HEAD)")
a = ap.parse_args()
sys.path.insert(0, a.tools)
import check as C, schema as S  # noqa: E402

PITCH, OFF, INSET, END, TRK = 0.048, 0.024, 0.019, 8.64, 0.6
PIN6_CAP = 5.5   # HBM-R16/C17: destination face <= pin6 capacity (pins/um over L-2*8.64, pincap.py)
LAYER = dict(W="M4", E="M4", N="M5", S="M5")
OPP = dict(N="S", S="N", E="W", W="E")
PERP = dict(N="EW", S="EW", E="NS", W="NS")
OK_COS = float(os.environ.get("C17_OK_COS", "-1e-9"))  # C17: -0.1 = G0C away threshold
POL = ("superset-face master (COORD 06:01 ruling 2b): unused pin groups stay registered inside the master and are "
       "declared here; never tied or stubbed")
src, out = Path(a.inp).resolve(), Path(a.out).resolve()
if out == src or str(out).startswith(str(src) + "/"):
    sys.exit("OUT must not be IN or inside it")
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out, symlinks=False, ignore=shutil.ignore_patterns("gates"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_real(p, text):
    p = Path(p)
    rp = p.parent.resolve() / p.name
    if not str(rp).startswith(str(out) + "/") or any(q.is_symlink() for q in [p, *p.parents] if str(q).startswith(str(out))):
        raise SystemExit(f"refusing to write {p}: resolves outside OUT or through a symlink")
    if p.exists():
        p.unlink()
    p.write_text(text)


rep = dict(inp=str(src), out=str(out), tools=a.tools, wt=a.wt,
           ccsplit=dict(script=a.ccsplit, sha=sha(a.ccsplit)[:12]), fixes=[], flagged=[], tables={}, iters=[],
           port_dirs={}, wrapper_needs=[])
# ---- 2. ccsplit
cc_tmp = out / "core_conns.json.ccsplit_tmp"
r = subprocess.run([sys.executable, a.ccsplit, str(out / "die_plan.json"), str(src / "core_conns.json"),
                    str(cc_tmp), str(out / "ccsplit_report.json")], capture_output=True, text=True, check=True)
write_real(out / "core_conns.json", cc_tmp.read_text()); cc_tmp.unlink()
rep["ccsplit"].update(stdout=r.stdout.strip(), in_sha=sha(src / "core_conns.json")[:12],
                      out_sha=sha(out / "core_conns.json")[:12])
print("ccsplit:", r.stdout.strip(), flush=True)

raw = json.loads((out / "die_plan.json").read_text()); T = raw["partition_types"]
cache, orig_sha, touched = {}, {}, set()


def pins_of(f):
    if f not in cache:
        orig_sha[f] = sha(out / f)
        d = json.loads((out / f).read_text())
        if isinstance(d, dict):
            raise SystemExit(f"{f}: dict-form pin table not handled")
        cache[f] = d
    return cache[f]


def pname(p):
    return p.get("name") or (p["bus"] + ("" if p.get("bit") is None else f"[{p['bit']}]"))


def gbase(n):
    return re.sub(r"\[\d+\]$", "", n)


def lface(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def tface(o, f):     # type-frame face <-> core-frame face (self-inverse for R0/MX/MY/R180)
    if o in ("MX", "R180") and f in "NS":
        f = OPP[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPP[f]
    return f


def group_face(ps, g, w, h):
    fs = collections.Counter(lface(p["x"], p["y"], w, h) for p in ps if gbase(pname(p)) == g)
    return fs.most_common(1)[0][0] if fs else None


def score(o, Fc, dirs):
    nx, ny = C._NORMAL[tface(o, Fc)]
    return max(nx * d[1] + ny * d[2] for d in dirs)


def users_of(f):
    return [(tn, h) for tn, t in T.items() for h in t.get("hard_cores", []) if h.get("pins_file") == f]


# ---- port directions from the master RTL (ANSI + non-ANSI declarations)
_mod_cache = {}
_HEAD = subprocess.run(["git", "-C", a.wt, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
try:
    _FC = json.loads(Path(a.dir_cache).read_text())
except (OSError, ValueError):
    _FC = {}


def module_of(f):
    m = re.match(r"^(.*?)__\d+(?:\.\d+)?x\d", Path(f).name)
    return m.group(1) if m else Path(f).stem


def rtl_dirs(mod, want):
    if mod in _mod_cache:
        return _mod_cache[mod]
    files = []
    key = f"{a.wt}@{_HEAD}:{mod}"
    if key in _FC:
        files = _FC[key]
    else:
      try:
        g = subprocess.run(["git", "-C", a.wt, "grep", "-l", "-E", rf"^\s*module\s+{re.escape(mod)}\b", "--",
                            "*.sv", "*.v"], capture_output=True, text=True, timeout=300).stdout.split()
        files = sorted(g, key=lambda p: (not p.startswith("physical/die_plan/hbm_arch_cores/wrappers/"),
                                         not p.startswith("rtl/"), p))
        _FC[key] = files
        Path(a.dir_cache).write_text(json.dumps(_FC, indent=1))
      except Exception:
        pass
    best = ({}, None)
    for fn in files[:8]:
        txt = (Path(a.wt) / fn).read_text(errors="replace")
        txt = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", txt, flags=re.S))
        m = re.search(rf"\bmodule\s+{re.escape(mod)}\b(.*?)\bendmodule\b", txt, re.S)
        if not m:
            continue
        body = re.sub(r"\[[^\]]*\]", " ", m.group(1))
        d = {}
        for dm in re.finditer(r"\b(input|output|inout)\b((?:(?!\b(?:input|output|inout)\b)[^;()])*)", body):
            for piece in dm.group(2).split(","):
                toks = re.findall(r"[A-Za-z_]\w*", piece.split("=")[0])
                toks = [t for t in toks if t not in ("wire", "logic", "reg", "var", "signed", "unsigned", "bit")]
                if toks:
                    d[toks[-1]] = dm.group(1)
        cov = len(want & set(d))
        if best[1] is None or cov > best[1][0]:
            best = (d, (cov, fn))
    _mod_cache[mod] = best
    return best


def port_dir(f, port):
    mod = module_of(f)
    d, info = rtl_dirs(mod, {gbase(pname(p)) for p in pins_of(f)})
    k = f"{mod}.{port}"
    rep["port_dirs"][k] = dict(dir=d.get(port, "unknown"), rtl=info[1] if info else None)
    return d.get(port, "unknown")


# ---- the b1n rule, with partner directions for EVERY checked group (thresholds lifted) or for the failing ones
MSG = re.compile(r"type (\S+) core (\S+) port (\S+): (\d+) pins on face (\S+) face away .*\(re-pin to face ([NSEW])\)$")


def run_faces(all_groups):
    C._PIN_CACHE.clear()
    P = S.Plan(raw, out / "die_plan.json")
    last = {}
    o_bf, o_w, o_a = C.best_face, C.FACE_WARN_COS, C.FACE_AWAY_COS

    def bf(dirs):
        last["d"] = list(dirs); return o_bf(dirs)

    class Rep(C.Report):
        def err(self, check, msg, **kw):
            super().err(check, msg, **kw)
            self.items[-1]["dirs"] = last.get("d")
    C.best_face = bf
    if all_groups:
        C.FACE_WARN_COS = C.FACE_AWAY_COS = 1e9
    try:
        R = Rep(True); summ = C.check_core_faces(P, R, str(out), None, max_msgs=10 ** 9)
    finally:
        C.best_face, C.FACE_WARN_COS, C.FACE_AWAY_COS = o_bf, o_w, o_a
    res = []
    for i in R.errors():
        m = MSG.match(i["msg"])
        if m:
            res.append((m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(6), i.get("dirs") or []))
    return res, summ


def face_state(ps, lf, w, h, exclude=()):
    L = h if lf in "WE" else w
    onf = [p for p in ps if lface(p["x"], p["y"], w, h) == lf and gbase(pname(p)) not in exclude]
    used = {round(((p["y"] if lf in "WE" else p["x"]) - OFF) / PITCH) for p in onf}
    lo = int(math.ceil((END - OFF) / PITCH - 1e-9)); hi = int(math.floor((L - END - OFF) / PITCH + 1e-9))
    return len(onf), used, lo, hi, min(int(TRK * int((L - 2 * END) / PITCH)), int(PIN6_CAP * (L - 2 * END)))


def place(ps, w, hh, lf, src_pins, along, newname, exclude=()):
    """[(pin, k)] block placement of src_pins on core face lf around coordinate `along`, or (None, why)."""
    nonf, used, lo, hi, cap = face_state(ps, lf, w, hh, exclude)
    n = len(src_pins)
    if nonf + n > cap:
        return None, f"face {lf}: {nonf}+{n} pins > cap {cap}"
    kt = (along - OFF) / PITCH
    free = sorted((k for k in range(lo, hi + 1) if k not in used), key=lambda k: (abs(k - kt), k))
    taken = set(used); pick = []
    for k in free:
        if len(pick) == n:
            break
        if k - 1 not in taken and k + 1 not in taken:
            pick.append(k); taken.add(k)
    for k in free:
        if len(pick) == n:
            break
        if k not in taken:
            pick.append(k); taken.add(k)
    if len(pick) < n:
        return None, f"face {lf}: {len(pick)} free tracks < {n}"
    pick.sort()
    srt = sorted(src_pins, key=lambda p: (len(pname(p)), pname(p)))
    res = []
    for p, k in zip(srt, pick):
        pos = round(OFF + k * PITCH, 6)
        x, y = {"W": (INSET, pos), "E": (w - INSET, pos), "S": (pos, INSET), "N": (pos, hh - INSET)}[lf]
        res.append(dict(name=newname(p), layer=LAYER[lf], x=round(x, 6), y=round(y, 6)))
    return res, None


def along_of(binders, w, hh, lf, D, port):
    """target coordinate along core face lf: mean partner direction over binders, mapped into the core frame."""
    ux = uy = 0.0; n = 0
    for tn, h in binders:
        o = h.get("orient", "R0")
        for d in D.get((tn, h["inst"], port), []):
            x, y = d[1], d[2]
            if o in ("MY", "R180"):
                x = -x
            if o in ("MX", "R180"):
                y = -y
            ux += x; uy += y; n += 1
    ux, uy = (ux / n, uy / n) if n else (0.0, 0.0)
    return (hh / 2 + uy * hh / 2) if lf in "WE" else (w / 2 + ux * w / 2)


def binders_of(f, port, g):
    return [(tn, h) for tn, h in users_of(f) if h.get("pin_select", {}).get(port, port) == g]


def set_sel(h, port, g):
    sel = h.get("pin_select", {})
    if g == port:
        sel.pop(port, None)
    else:
        sel[port] = g
    if sel:
        h["pin_select"] = sel
    else:
        h.pop("pin_select", None)


def try_repin(f, ps, w, hh, port, g, binders, D, extra=None):
    """method A: best core face for group g s.t. every binder (and `extra`, re-bound to g) has mean cos >= 0."""
    allb = binders + ([extra] if extra else [])
    cur = group_face(ps, g, w, hh)
    gp = [p for p in ps if gbase(pname(p)) == g]
    best, why = None, []
    for F in "NSEW":
        if F == cur:
            continue
        sc = [score(h.get("orient", "R0"), F, D[(tn, h["inst"], port)]) for tn, h in allb if D.get((tn, h["inst"], port))]
        if not sc or min(sc) < OK_COS:
            why.append(f"{F}: min cos {min(sc) if sc else float('nan'):+.2f}"); continue
        new, err = place(ps, w, hh, F, gp, along_of(allb, w, hh, F, D, port), lambda p: pname(p), exclude={g})
        if new is None:
            why.append(err); continue
        key = (min(sc), sum(sc))
        if best is None or key > best[0]:
            best = (key, F, new, sc)
    return best, why


for it in range(5):
    al, summ = run_faces(False)
    rep["iters"].append(dict(away=len(al), summary=summ)); print("pass", it, "away ports", len(al), flush=True)
    if not al:
        break
    D = {(tn, ci, lp): dirs for tn, ci, lp, _n, _bf, dirs in run_faces(True)[0]}
    done, seen = 0, set()
    for tn, ci, port, n, bf, dirs in al:
        h = next(x for x in T[tn]["hard_cores"] if x["inst"] == ci)
        f = h.get("pins_file")
        if not f:
            rep["flagged"].append(dict(type=tn, core=ci, port=port, why="no pins_file")); continue
        if (f, port) in seen:
            continue                                   # group changed this pass: re-judged next pass
        ps = pins_of(f); w, hh = h["outline_um"]; o = h.get("orient", "R0")
        g = h.get("pin_select", {}).get(port, port)
        cur_face = group_face(ps, g, w, hh)
        pdir = port_dir(f, port)
        fix = dict(type=tn, core=ci, port=port, pins=n, table=f, port_dir=pdir, from_group=g, from_face_core=cur_face,
                   suggested_type_face=bf, pass_=it)
        # A: re-pin the ONE base group (existing copies are the PORTS lane's: never moved or newly bound here); an
        # instance on a copy is re-bound to the base when the base re-pin suits it and every base binder
        cands = [(port, binders_of(f, port, port), None if g == port else (tn, h))]
        best = None; whys = []
        for grp, bnd, extra in cands:
            b, why = try_repin(f, ps, w, hh, port, grp, bnd, D, extra)
            whys.append(dict(group=grp, binders=[f"{x}.{y['inst']}" for x, y in bnd + ([extra] if extra else [])],
                             why=why))
            if b and (best is None or b[0] > best[0][0]):
                best = (b, grp, bnd, extra)
        if best:
            (key, F, new, sc), grp, bnd, extra = best
            old = [p for p in ps if gbase(pname(p)) == grp]
            ps[:] = [p for p in ps if gbase(pname(p)) != grp] + new
            if extra:
                set_sel(h, port, grp)
            touched.add(f); seen.add((f, port)); done += 1
            fix.update(method="A_repin", to_group=grp, to_face_core=F,
                       binders=[f"{x}.{y['inst']}" for x, y in bnd + ([extra] if extra else [])],
                       binder_cos=[round(s, 3) for s in sc], moved_pins=len(old))
            rep["fixes"].append(fix); continue
        # B: output-only copy
        if pdir == "output" and a.allow_output_copies:
            base = port
            src_pins = [p for p in ps if gbase(pname(p)) == base]
            sc = {F: score(o, F, dirs) for F in "NSEW"}
            order = [tface(o, bf)] + sorted((F for F in "NSEW" if F not in (tface(o, bf), cur_face)),
                                            key=lambda F: -sc[F])
            got = None; bw = []
            for F in order:
                if sc[F] < OK_COS:
                    bw.append(f"{F}: cos {sc[F]:+.2f}"); continue
                ex = [cg for cg in [base] + [f"{base}__{X}" for X in "NSEW"]
                      if group_face(ps, cg, w, hh) == F and sum(1 for p in ps if gbase(pname(p)) == cg) == len(src_pins)]
                if ex:
                    got = (ex[0], F, "B_select_existing_output_copy", 0); break
                cg = f"{base}__{F}"
                new, err = place(ps, w, hh, F, src_pins, along_of([(tn, h)], w, hh, F, D, port),
                                 lambda p, cg=cg: cg + pname(p)[len(base):])
                if new is None:
                    bw.append(err); continue
                if {q["name"] for q in new} & {pname(p) for p in ps}:
                    raise SystemExit(f"{f}: duplicate pin names for {cg}")
                ps.extend(new); touched.add(f)
                got = (cg, F, "B_add_output_copy", len(new)); break
            if got:
                set_sel(h, port, got[0]); seen.add((f, port)); done += 1
                fix.update(method=got[2], to_group=got[0], to_face_core=got[1], cos=round(sc[got[1]], 3),
                           pins_added=got[3], repin_rejected=whys)
                rep["fixes"].append(fix); continue
            whys.append(dict(copy=bw))
        fix.update(method="C_flag", why=("no single-group face suits every instance (copies not allowed: COORD "
                                         "HBM-CORES-R8 (1)); options: variant type / ft pair / core move / orient"),
                   repin_rejected=whys)
        rep["flagged"].append(fix)
    for f in touched:
        write_real(out / f, json.dumps(cache[f]) + "\n")
    write_real(out / "die_plan.json", json.dumps(raw, indent=1) + "\n")
    if not done:
        break
# dedupe flags: keep the last pass's verdict per (type, core, port) still away
final, fsumm = run_faces(False)
still = {(x[0], x[1], x[2]) for x in final}
last = {}
for x in rep["flagged"]:
    if (x["type"], x["core"], x["port"]) in still:
        last[(x["type"], x["core"], x["port"])] = x
rep["flagged"] = list(last.values())
# orientation what-if for every flagged instance (COORD option; NOT applied): away groups of the instance per orient
Dfin = {(tn, ci, lp): dirs for tn, ci, lp, _n, _bf, dirs in run_faces(True)[0]}
rep["orient_whatif"] = {}
for tn, ci in sorted({(x["type"], x["core"]) for x in rep["flagged"]}):
    h = next(x for x in T[tn]["hard_cores"] if x["inst"] == ci); ps = pins_of(h["pins_file"]); w, hh = h["outline_um"]
    sel = h.get("pin_select", {}); res = {}
    for o2 in ("R0", "MX", "MY", "R180"):
        bad = side = 0
        for (t2, c2, lp), dirs in Dfin.items():
            if (t2, c2) != (tn, ci) or not dirs:
                continue
            fs = [lface(p["x"], p["y"], w, hh) for p in ps if gbase(pname(p)) == sel.get(lp, lp)]
            if not fs:
                continue
            m = sum(score(o2, F, dirs) for F in fs) / len(fs)
            bad += m < C.FACE_AWAY_COS; side += C.FACE_AWAY_COS <= m < C.FACE_WARN_COS
        res[o2] = dict(away=bad, side=side)
    rep["orient_whatif"][f"{tn}.{ci}"] = dict(current=h.get("orient", "R0"), by_orient=res)

# ---- 4. collapse B copies whose base no instance binds any more
added_now = collections.defaultdict(set)
for x in rep["fixes"]:
    if x["method"] == "B_add_output_copy":
        added_now[x["table"]].add(x["to_group"])
rep["collapse"] = []
for f in sorted(added_now):
    ps = cache[f]; us = users_of(f)
    for g in sorted(added_now[f]):
        b = re.sub(r"__[NSEW]$", "", g)
        binds = [h.get("pin_select", {}).get(b, b) for _, h in us]
        if b in binds or g not in binds:
            continue
        gp = {pname(p)[len(g):]: p for p in ps if gbase(pname(p)) == g}
        bp = [p for p in ps if gbase(pname(p)) == b]
        if sorted(gp) != sorted(pname(p)[len(b):] for p in bp):
            continue
        for p in bp:
            q = gp[pname(p)[len(b):]]; p["x"], p["y"], p["layer"] = q["x"], q["y"], q["layer"]
        ps[:] = [p for p in ps if gbase(pname(p)) != g]
        for _, h in us:
            if h.get("pin_select", {}).get(b) == g:
                set_sel(h, b, b)
        rep["collapse"].append(dict(table=f, base=b, from_copy=g, pins=len(bp)))
        for x in rep["fixes"]:
            if x["table"] == f and x.get("to_group") == g:
                x["method"] = "A_repin(collapsed copy)"; x["to_group"] = b
    write_real(out / f, json.dumps(ps) + "\n")

# ---- 5. unused_pins for every instance of a touched table
for tn, t in T.items():
    for h in t.get("hard_cores", []):
        f = h.get("pins_file")
        if f not in touched:
            continue
        gs = {(m.group(1), m.group(1) + "__" + m.group(2)) for p in cache[f]
              for m in [re.match(r"^(.*)__([NSEW])(\[\d+\])?$", pname(p))] if m}
        sel = h.get("pin_select", {})
        allg = {b for b, _ in gs} | {g for _, g in gs}
        bound = {sel.get(b, b) for b, _ in gs}
        un = (set(h.get("unused_pins", [])) - allg) | (allg - bound)
        if un:
            h["unused_pins"] = sorted(un); h.setdefault("unused_pins_policy", POL)
        else:
            h.pop("unused_pins", None); h.pop("unused_pins_policy", None)
write_real(out / "die_plan.json", json.dumps(raw, indent=1) + "\n")

# ---- copy groups the wrappers must provide (method B outputs still bound to a copy)
for f in sorted(touched):
    for tn, h in users_of(f):
        for lp, g in h.get("pin_select", {}).items():
            if any(x.get("to_group") == g and x["table"] == f and x["method"].startswith("B_") for x in rep["fixes"]):
                rep["wrapper_needs"].append(dict(module=module_of(f), copy=g, of=lp,
                                                 wrapper=f"output {g}; assign {g} = {lp};"))
rep["wrapper_needs"] = [dict(t) for t in {tuple(sorted(d.items())) for d in rep["wrapper_needs"]}]

# ---- legality + sha of every touched table
for f in sorted(touched):
    ps = cache[f]
    w, hh = users_of(f)[0][1]["outline_um"]
    names = [pname(p) for p in ps]

    def trk(p):
        F = lface(p["x"], p["y"], w, hh)
        return F, ((p["y"] if F in "WE" else p["x"]) - OFF) / PITCH
    off = sum(1 for p in ps if abs(trk(p)[1] - round(trk(p)[1])) > 1e-4)
    layer_bad = sum(1 for p in ps if p["layer"] != LAYER[trk(p)[0]])
    tc = collections.Counter((trk(p)[0], p["layer"], round(trk(p)[1])) for p in ps)
    fu = {F: round(sum(1 for p in ps if lface(p["x"], p["y"], w, hh) == F) /
                   int(((hh if F in "WE" else w) - 2 * END) / PITCH), 3) for F in "NSEW"}
    old = json.loads((src / f).read_text())
    rep["tables"][f] = dict(
        old_sha=orig_sha[f], new_sha=sha(out / f), pins_before=len(old), pins_after=len(ps),
        legality=dict(duplicates=len(names) - len(set(names)), off_track=off, layer_not_face_layer=layer_bad,
                      shared_tracks=sum(v - 1 for v in tc.values() if v > 1), face_use=fu),
        added_groups=sorted({gbase(pname(p)) for p in ps} - {gbase(pname(p)) for p in old}),
        moved_groups=sorted({gbase(pname(p)) for p in old if p not in ps and gbase(pname(p)) in {gbase(pname(q)) for q in ps}}),
        users=[f"{tn}.{h['inst']}" for tn, h in users_of(f)])

rep["final"] = dict(away=len(final), summary=fsumm, left=[x[:5] for x in final])
rep["counts"] = dict(collections.Counter(x["method"] for x in rep["fixes"]))
rep["counts"]["C_flag"] = len(rep["flagged"])
rep["counts"]["copy_pins_added"] = sum(d["pins_after"] - d["pins_before"] for d in rep["tables"].values())
rep["die_plan_sha"] = dict(old=sha(src / "die_plan.json"), new=sha(out / "die_plan.json"))
Path(a.report).write_text(json.dumps(rep, indent=1, default=list) + "\n")
print("counts", rep["counts"], "final away", len(final))
for f, d in rep["tables"].items():
    print(f, d["old_sha"][:12], "->", d["new_sha"][:12], d["pins_before"], "->", d["pins_after"], d["legality"],
          "moved", len(d["moved_groups"]), "added", len(d["added_groups"]))
for x in rep["flagged"]:
    print("FLAG", x["type"], x["core"], x["port"], x["port_dir"], x["why"])
for k, v in rep["orient_whatif"].items():
    print("ORIENT", k, v["current"], {o: (d["away"], d["side"]) for o, d in v["by_orient"].items()})
print("die_plan", rep["die_plan_sha"]["old"][:12], "->", rep["die_plan_sha"]["new"][:12])
