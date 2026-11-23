"""ADV-CORE-PARAM (PRECHECK-R2, estimator, never a gate): the parameters a hard core instance gets at bind time must equal the
parameters its SIGNED view was built with.

Known class (KV D27d3 / D28 44c3cbf51e50): the bind's regen_constants.kv_ectl derives RESPONSE_LAT = 8 + D(krq) + D(krs) and
QK_ISSUE_AGE = max(34, RL + 11) from the LANDED lane depths; the plan re-spaced o_ectl_Q_N_rq / i_slg_Q_N_krsp stations 3->5 / 5->8,
so every ectl frame bound 42/31 while the signed qkd_ectlk_q0..q3 views were built at 37/26: every hg kit stopped at gen_lint
(qkd_ectl3_kiss_st_cols__columns_built_for_other_params), found a day after the bind.

Statically (plan + tree, no bind):
  FAMILY   bind-time values of regen_constants laws that land in hard cores, priced from the plan's latency.lanes cycles
           (= landed depth; rh12 bind: 352/352 ectl members landed == plan cycles).  Today: kv_ectl (RESPONSE_LAT /
           QK_ISSUE_AGE; one die-wide value = max frame round trip).  Lanes found by end-bus (ports[0].src.bus ~ o_ectl_*rq,
           ports[-1].dst.bus ~ i_slg_*krsp), frame = the partition holding the ectl (krq src part == krs dst part).
  BUILT    what the signed view was built with, first found wins:
             1 built-for guard RTL in the tree: a module with `localparam CORE_X = v` and a generate-if `P != CORE_X ...` that
               instantiates a *_built_for_* module (the gen_lint trap itself); it covers the hard modules defined in files of the
               same directory (qkd_ectl3_kiss_st_cols.sv -> qkd_ectlk_columns.sv: qkd_ectlk_q0..q3)
             2 tools/die_plan/hard_core_built_params.json registry (params {} = built at the module header defaults, read from
               the module's RTL in the guard dir)
  GENERIC  (a) plan param_wrap.params vs the view's landing_evidence/manifest.json (D -> DEPTH, width -> W) and vs registry
               params of param_wrap.base / the row module (overlapping keys);
           (b) as-built hard_params sidecars (opentallas.frame_kit.hard_params.v1; baked into the bind's leaf stubs) vs the
               registry record of the same master;
           (c) built-for guard values vs the guarded hard modules' header defaults (two records of one view disagree);
           (d) a guarded parameter (from 1) that the tree's previous bind of record (physical/die_plan/<die>/plan_of_record/
               bind_of_record/param_regen.json) sets to another value, for parameters no FAMILY rule re-prices.
findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-CORE-PARAM ..."]; kw asbuilt=PATH (as-built manifest), max_lines=20.
"""
import json
import os
import re
import time
from pathlib import Path

TAG = "ADV-CORE-PARAM"
STATS = {}   # coverage of the last run (frames priced, param_wrap rows with a view record, sidecar masters compared, guards)
MAX_LINES = 20
# regen_constants.kv_ectl constants (LANDING_SEG, QK_WBR, QK_KIT); refreshed from the sibling module when importable
KV_LANDING_SEG, KV_QK_WBR, KV_QK_KIT = 8, 11, 34


def _rc_consts():
    global KV_LANDING_SEG, KV_QK_WBR, KV_QK_KIT
    try:
        import regen_constants as RC  # noqa: F401  (lives next to this file in tools/die_plan)
        KV_LANDING_SEG, KV_QK_WBR, KV_QK_KIT = int(RC.LANDING_SEG), int(RC.QK_WBR), int(RC.QK_KIT)
        return "regen_constants"
    except Exception:
        return "built-in"


def _json(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _int(v):
    try:
        return int(str(v).strip().replace("_", ""), 0)
    except Exception:
        return None


def _die(raw):
    d = raw.get("die")
    return (d.get("name") if isinstance(d, dict) else d) or ""


# ------------------------------------------------------------------------------------------------ RTL records in the tree
_CMT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_MODHDR = re.compile(r"\bmodule\s+(\w+)\s*#\s*\((.*?)\)\s*\(", re.S)
_HPAR = re.compile(r"\bparameter\s+(?:integer\s+|int\s+|logic\s+|bit\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,;)]+)")
_LP = re.compile(r"\blocalparam\s+(?:integer\s+|int\s+)?(?:\[[^\]]*\]\s*)?(CORE_\w+)\s*=\s*([^;]+);")
_GIF = re.compile(r"\bif\s*\((.*?)\)\s*begin\b[^\n]*\n?(.{0,400}?)\bend\b", re.S)


def _guard_dirs(tree, die):
    """cores/ of the plan's die first, then of every die (a substituted hard-core wrapper can live under another die)"""
    dp = Path(tree) / "physical" / "die_plan"
    out = [dp / die / "cores"] if die else []
    try:
        out += sorted(d / "cores" for d in dp.iterdir() if (d / "cores").is_dir())
    except OSError:
        pass
    res = []
    for d in out:
        if d.is_dir() and d not in res:
            res.append(d)
    return res


SKIP_DIRS = frozenset(("results", "run", "runs", "logs", "objects", "kits", "reports", "tmp", "work"))


def scan_guards(tree, die, budget_s=25.0):
    """-> {guard_module: dict(file, params {P: v}, hard {hard_module: {P: default}})}"""
    t0 = time.time()
    seen, res = set(), {}
    for root in _guard_dirs(tree, die):
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
            if time.time() - t0 > budget_s:
                return res
            for fn in fns:
                if not fn.endswith((".sv", ".v")):
                    continue
                f = Path(dp) / fn
                try:
                    rp = f.resolve()
                    if rp in seen or f.stat().st_size > 8_000_000:
                        continue
                    seen.add(rp)
                    b = f.read_bytes()
                except OSError:
                    continue
                if b"built_for" not in b or b"CORE_" not in b:
                    continue
                _parse_guard(f, b.decode(errors="replace"), res)
    return res


def _parse_guard(f, text, res):
    t = _CMT.sub(" ", text)
    for m in re.finditer(r"\bmodule\s+(\w+)\b(.*?)\bendmodule\b", t, re.S):
        name, body = m.group(1), m.group(2)
        lps = {k: v.strip() for k, v in _LP.findall(body)}
        if not lps:
            continue
        params = {}
        for g in _GIF.finditer(body):
            if not re.search(r"\w*built_for\w*", g.group(2)):
                continue
            for p, rhs in re.findall(r"\b(\w+)\s*!=\s*([\w']+)", g.group(1)):
                if rhs in lps:
                    v = _int(lps[rhs])
                    if v is not None:
                        params[p] = v
                elif _int(rhs) is not None:
                    params[p] = _int(rhs)
        if not params:
            continue
        hard = {}
        for sib in sorted(f.parent.glob("*.sv")) + sorted(f.parent.glob("*.v")):
            if sib == f:
                continue
            try:
                st = _CMT.sub(" ", sib.read_text(errors="replace"))
            except OSError:
                continue
            for h in _MODHDR.finditer(st):
                hard[h.group(1)] = {k: _int(v) for k, v in _HPAR.findall(h.group(2))}
        res[name] = dict(file=str(f), params=params, hard=hard)


# ------------------------------------------------------------------------------------------------ registry
def load_registry(tree):
    for base in ([Path(tree) / "tools" / "die_plan"] if tree else []) + [Path(__file__).resolve().parent]:
        j = _json(base / "hard_core_built_params.json")
        if isinstance(j, dict) and isinstance(j.get("entries"), list):
            return j["entries"], str(base / "hard_core_built_params.json")
    return [], None


def reg_params(entries, die, module):
    c = [e for e in entries if e.get("module") == module and (not e.get("die") or e.get("die") == die)]
    if not c:
        return None
    if all(e.get("params") == c[0].get("params") for e in c):
        return dict(c[0].get("params") or {})
    return None   # several parameter sets: needs the record sha (bind-time HCPARAM-ALL), not judged here


# ------------------------------------------------------------------------------------------------ FAMILY: kv_ectl
def _lane_ends(raw):
    P = {x.get("id"): x for x in raw.get("ports") or [] if isinstance(x, dict)}
    lat = (raw.get("latency") or {}).get("lanes") or {}
    for L in raw.get("lanes") or []:
        ps = L.get("ports") or []
        if not ps or ps[0] not in P or ps[-1] not in P:
            continue
        a, z = P[ps[0]], P[ps[-1]]
        row = lat.get(L.get("id")) or {}
        cyc = row.get("cycles")
        if not isinstance(cyc, int):
            cyc = L.get("fixed_cycles") if isinstance(L.get("fixed_cycles"), int) else None
        yield L.get("id"), (a.get("src") or {}), (z.get("dst") or {}), cyc


def kv_ectl_family(raw):
    """-> None | dict(RESPONSE_LAT, QK_ISSUE_AGE, frames {part: (rt, krq, krs, Lq, Ls)}, rule)"""
    req, rsp = {}, {}
    for lid, s, d, cyc in _lane_ends(raw):
        if re.match(r"^o_ectl_\w*rq$", str(s.get("bus", ""))):
            req.setdefault(s.get("part"), []).append((cyc, lid))
        if re.match(r"^i_slg_\w*krsp$", str(d.get("bus", ""))):
            rsp.setdefault(d.get("part"), []).append((cyc, lid))
    if not req:
        return None
    frames, odd = {}, []
    for part in sorted(req):
        q, s = req[part], rsp.get(part) or []
        if not s or any(c is None for c, _ in q + s):
            odd.append(part)
            continue
        cq, lq = max(q)
        cs, ls = max(s)
        frames[part] = (KV_LANDING_SEG + cq + cs, cq, cs, lq, ls)
    if not frames:
        return None
    rl = max(v[0] for v in frames.values())
    return dict(RESPONSE_LAT=rl, QK_ISSUE_AGE=max(KV_QK_KIT, rl + KV_QK_WBR), frames=frames, odd=odd,
                rule=f"RESPONSE_LAT = {KV_LANDING_SEG} + D(krq) + D(krs) (max frame), QK_ISSUE_AGE = max({KV_QK_KIT}, RL + {KV_QK_WBR})")


FAMILIES = [
    # name, die, hard-core module regex (the cores that carry the regenerated params), price fn, params it re-prices
    dict(name="kv_ectl", die="qwen_kvsys", hard=r"^qkd_ectlk_q\d+$", price=kv_ectl_family, params=("RESPONSE_LAT", "QK_ISSUE_AGE"),
         fix="restore the krq+krs station depth of every ectl frame (o_ectl_*_rq / i_slg_*_krsp internal_stations + lane "
             "fixed_cycles) to {need} cycles, or re-harden the hard cores at the bind values and set CORE_* in the guard"),
]


# ------------------------------------------------------------------------------------------------ main
def _built_for(module, guards, entries, die):
    """-> (params, source) for a hard module"""
    for gname, g in guards.items():
        if module in g["hard"]:
            return dict(g["params"]), f"built-for guard {gname} ({_short(g['file'])})"
    rp = reg_params(entries, die, module)
    if rp:
        return rp, "registry hard_core_built_params.json"
    if rp == {}:
        for g in guards.values():
            if module in g["hard"]:
                return {k: v for k, v in g["hard"][module].items() if v is not None}, "registry {} = module header defaults"
        return {}, "registry {} (module defaults; header not found)"
    return None, None


def _short(p, n=3):
    return "/".join(Path(p).parts[-n:])


def _rows(raw):
    for tn, t in (raw.get("partition_types") or {}).items():
        if isinstance(t, dict):
            for hc in t.get("hard_cores") or []:
                if isinstance(hc, dict):
                    yield tn, hc


def _check(raw, plan_path, tree, kw):
    out, nwarn = [], 0
    die = _die(raw)
    entries, regf = load_registry(tree)
    guards = scan_guards(tree, die) if tree and Path(tree).is_dir() else {}
    parts = {p.get("name"): p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    covered = set()
    STATS.clear()
    STATS.update(guards=sorted(guards), family_frames=0, pw_rows=0, pw_recorded=0, sidecar_masters=0, registry_rows=0)
    STATS["registry_rows"] = sum(1 for _, hc in _rows(raw) if reg_params(entries, die, hc.get("module")))

    # FAMILY rules
    for fam in FAMILIES:
        if fam["die"] and die and fam["die"] != die:
            continue
        pr = fam["price"](raw)
        if not pr:
            continue
        covered |= set(fam["params"])
        STATS["family_frames"] += len(pr["frames"])
        bytype = {}
        for part, fr in pr["frames"].items():
            bytype.setdefault(parts.get(part), []).append((part, fr))
        for tn in sorted(t for t in bytype if t):
            hcs = [hc for t2, hc in _rows(raw) if t2 == tn and re.match(fam["hard"], str(hc.get("module", "")))]
            if not hcs:
                continue
            diffs, srcs = [], set()
            for hc in hcs:
                bp, src = _built_for(hc.get("module"), guards, entries, die)
                if bp is None:
                    continue
                srcs.add(src)
                for p in fam["params"]:
                    if p in bp and _int(bp[p]) is not None and _int(bp[p]) != pr[p]:
                        diffs.append((hc.get("module"), p, _int(bp[p]), pr[p]))
            if not diffs:
                continue
            nwarn += 1
            frs = sorted(bytype[tn], key=lambda x: -x[1][0])
            part, (rt, cq, cs, lq, ls) = frs[0]
            mods = sorted({d[0] for d in diffs})
            bv = {p: sorted({d[2] for d in diffs if d[1] == p}) for p in fam["params"]}
            need = None
            if "RESPONSE_LAT" in bv and bv["RESPONSE_LAT"]:
                need = bv["RESPONSE_LAT"][0] - KV_LANDING_SEG
            pv = " / ".join(f"{p} {pr[p]}" for p in fam["params"])
            bvs = " / ".join(f"{p} {'/'.join(map(str, bv[p])) or '?'}" for p in fam["params"])
            out.append(f"WARN {TAG} {tn}: {fam['name']} hard cores {','.join(mods)} bind regen {pv} ({pr['rule']}; die max "
                       f"frame {max(v[0] for v in pr['frames'].values())}, this type's worst frame {part} krq {cq} ({lq}) + "
                       f"krs {cs} ({ls}) = {rt}) vs signed view built {bvs} [{'; '.join(sorted(srcs))}]: the kit stops at "
                       f"gen_lint (*_built_for_other_params) / HARD_CORE_PARAM_ALL; fix: "
                       + fam["fix"].format(need=need if need is not None else "?"))
        if pr.get("odd"):
            out.append(f"WARN {TAG} {fam['name']}: {len(pr['odd'])} frame(s) without a priced krq+krs lane pair "
                       f"({', '.join(map(str, pr['odd'][:4]))}): not priced")

    # GENERIC (a) param_wrap vs view records
    base_dir = Path(tree) if tree else Path(plan_path).resolve().parent
    for tn, hc in _rows(raw):
        pw = hc.get("param_wrap")
        if not isinstance(pw, dict) or not isinstance(pw.get("params"), dict):
            continue
        rec, src = {}, None
        STATS["pw_rows"] += 1
        for key in ("lef", "lib"):
            r = hc.get(key)
            if not r:
                continue
            d = (Path(r) if os.path.isabs(r) else base_dir / r).parent
            man = _json(d / "landing_evidence" / "manifest.json")
            if isinstance(man, dict) and man.get("master") in (None, hc.get("module")):
                for mk, pk in (("D", "DEPTH"), ("width", "W")):
                    if _int(man.get(mk)) is not None:
                        rec[pk] = _int(man.get(mk))
                src = f"{_short(d / 'landing_evidence/manifest.json', 4)}"
            break
        for m in (pw.get("base"), hc.get("module")):
            rp = reg_params(entries, die, m) if m else None
            if rp:
                for k, v in rp.items():
                    rec.setdefault(k, _int(v) if _int(v) is not None else v)
                src = (src + " + " if src else "") + f"registry {m}"
        if set(rec) & set(pw["params"]):
            STATS["pw_recorded"] += 1
        bad = [(k, rec[k], pw["params"][k]) for k in sorted(set(rec) & set(pw["params"]))
               if str(_int(pw["params"][k]) if _int(pw["params"][k]) is not None else pw["params"][k]) != str(rec[k])]
        if bad:
            nwarn += 1
            if len(out) < MAX_LINES:
                out.append(f"WARN {TAG} {tn}: {hc.get('inst')} ({hc.get('module')}) plan param_wrap "
                           + ", ".join(f"{k} {p}" for k, r, p in bad) + " vs signed view built "
                           + ", ".join(f"{k} {r}" for k, r, p in bad) + f" [{src}]; fix: plan param_wrap = the view's "
                           "values, or a view built at the plan values")

    # GENERIC (b) hard_params sidecars vs registry
    ab = kw.get("asbuilt")
    abj = _json(ab) if ab else (raw.get("asbuilt") if isinstance(raw.get("asbuilt"), dict) else None)
    if isinstance(abj, dict) and abj.get("hard_params"):
        mdir = Path(ab).resolve().parent if ab else Path(plan_path).resolve().parent
        b = abj.get("base")
        abase = (Path(b) if os.path.isabs(str(b)) else mdir / str(b)) if b else (Path(tree) if tree else mdir)
        hp = abj.get("hard_params")
        for f in (hp if isinstance(hp, list) else [hp]):
            p = Path(f) if os.path.isabs(str(f)) else abase / str(f)
            j = _json(p)
            if not isinstance(j, dict) or j.get("schema") != "opentallas.frame_kit.hard_params.v1":
                continue
            for mst, ps in (j.get("masters") or {}).items():
                rp = reg_params(entries, die, mst)
                if not rp or not isinstance(ps, dict):
                    continue
                STATS["sidecar_masters"] += 1
                bad = [(k, rp[k], ps[k]) for k in sorted(set(rp) & set(ps)) if str(rp[k]) != str(ps[k])]
                if bad:
                    nwarn += 1
                    if len(out) < MAX_LINES:
                        out.append(f"WARN {TAG} {mst}: hard_params sidecar {_short(p)} bakes " + ", ".join(
                            f"{k} {s}" for k, r, s in bad) + " vs registry built " + ", ".join(f"{k} {r}" for k, r, s in bad)
                            + "; fix: sidecar = the signed record (or re-harvest the registry)")

    # GENERIC (c) guard values vs guarded hard modules' header defaults; (d) previous bind of record vs guard
    plan_mods = {hc.get("module") for _, hc in _rows(raw)}
    for gname, g in sorted(guards.items()):
        for hm, dfl in sorted(g["hard"].items()):
            if hm not in plan_mods:
                continue
            bad = [(p, v, dfl[p]) for p, v in g["params"].items() if p in dfl and dfl[p] is not None and dfl[p] != v]
            if bad:
                nwarn += 1
                if len(out) < MAX_LINES:
                    out.append(f"WARN {TAG} {hm}: built-for guard {gname} says " + ", ".join(f"{p} {v}" for p, v, d in bad)
                               + " but the module header defaults are " + ", ".join(f"{p} {d}" for p, v, d in bad)
                               + f" ({_short(g['file'])}); fix: one record (CORE_* = the signed views' build values)")
    if tree and die:
        prj = _json(Path(tree) / "physical" / "die_plan" / die / "plan_of_record" / "bind_of_record" / "param_regen.json")
        if isinstance(prj, dict):
            gp = {}
            for gname, g in guards.items():
                if any(hm in plan_mods for hm in g["hard"]):
                    for p, v in g["params"].items():
                        if p not in covered:
                            gp[p] = (v, gname)
            seenp = {}
            for r in list(prj.get("derived") or []) + list(prj.get("changed") or []):
                p = r.get("param")
                if p in gp and _int(r.get("bound")) is not None and _int(r.get("bound")) != gp[p][0]:
                    seenp.setdefault(p, set()).add(_int(r.get("bound")))
            for p, vs in sorted(seenp.items()):
                nwarn += 1
                if len(out) < MAX_LINES:
                    out.append(f"WARN {TAG} {gp[p][1]}: previous bind of record sets {p} {sorted(vs)} vs built-for guard "
                               f"{gp[p][0]} (no static rule re-prices {p}); fix: re-harden or re-plan before the bind")
    if nwarn:
        out = out[:MAX_LINES]
        out.append(f"WARN {TAG} summary: {nwarn} hard-core parameter mismatch(es) (guards {len(guards)}, registry "
                   f"{'yes' if regf else 'no'})")
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        global MAX_LINES
        MAX_LINES = int(kw.get("max_lines", MAX_LINES))
        if not isinstance(raw, dict) or not raw.get("partition_types"):
            return [f"WARN {TAG} not checked: no partition_types in {plan_path}"]
        _rc_consts()
        return _check(raw, plan_path, tree, kw)
    except Exception as e:  # never raise
        return [f"WARN {TAG} not checked: {type(e).__name__}: {e}"]


if __name__ == "__main__":
    import sys
    t0 = time.time()
    pp = sys.argv[1]
    with open(pp) as f:
        r = json.load(f)
    t1 = time.time()
    ab = sys.argv[3] if len(sys.argv) > 3 else None
    lines = findings(r, pp, sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None, asbuilt=ab)
    print("\n".join(lines) if lines else f"(no {TAG} findings)")
    print(f"# coverage {json.dumps(STATS)}")
    print(f"# load {t1 - t0:.1f}s check {time.time() - t1:.2f}s plan {pp}")
