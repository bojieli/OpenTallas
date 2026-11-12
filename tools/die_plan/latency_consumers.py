#!/usr/bin/env python3
"""DIE-HBM-92-LCHK (F4): bind-time latency-consumer consistency, a bind correctness check (like PARAM_REGEN), not a
sign-off gate.  It reads only what a bind already has: the as-built leaf map (path -> module + parameters), the bus
groups (landed - as-built cycles per crossing member) and the die hook's param_regen record.

  (1) R8 (tools/die_plan/r8.py check) runs in every bind, with the die's own R8 options (landing table exempt /
      replica / bus mode, strap pads).  Its result is always recorded.  It is a bind ERROR (R8_UNLANDED) only when the
      bind adds stages to as-built 0-stage crossings AND the die has neither landing pads (asbuilt.land_align r8 / cell)
      nor a param_regen hook: nothing then absorbs the added cycles, so torn buses would pass silently (HBM bind_d,
      DIE-HBM-92-FLAT 11-08).  Dies with pads or a hook keep their own r8 gate; here it is advisory.
  (2) Declared latency contracts: d4g_bank_latency RULES (request port -> response port round trip) + CONTRACTS below
      + asbuilt.latency_contracts + the hook's LATENCY_CONTRACTS (module attribute, or "latency_contracts" in the dict
      regen() returns) + a module attribute (* ot_fixed_latency = "req,req>resp,resp:PARAM;align:p,p" *) in the RTL.
      Per as-built instance:  added = max landed delta on its request ports + max on its response ports.
      added != 0 and the hook did not regenerate (inst, PARAM) -> FIXED_LATENCY_MISMATCH inst/param/as-built/needed.
      An align contract (ports sampled on one edge) whose ports land with different deltas -> FIXED_LATENCY_MISALIGNED.
      advisory=True on a contract: reported as ADVISORY_MISMATCH, never an error (fixed-age consumers with no parameter).
      design_loop=N on a contract: the consumer was designed for N crossing stages round trip, so the report also gives
      required = landed loop - N (the "added" field stays landed minus as-built and understates it when the as-built
      depths were already outside the design).
      Core pin cycles (HBM-HUB-RTL-1 11-11, tools/die_plan/core_pin_cycles.py): asbuilt.core_pin_cycles names hard-core
      recipes that add edges at their own output pins (e.g. the vecd4ae rd1 bank read stage, rr*/pr +1).  Those edges
      count on the response side of every consumer fed by such a pin (added += pin), so a bound rd1 bank makes each
      unregenerated fixed-latency reader a FIXED_LATENCY_MISMATCH; a value the hook regenerated as "as-built + pin"
      (record.core_pin_regen) must equal as-built + added, else FIXED_LATENCY_MISMATCH too.  No declaration: unchanged.
      Port lists are regexes (fullmatch).  A loop through several leaves is checked at the consumer leaf only; its
      inner hops are covered by (1).
  (3) Advisory census: undeclared latency-named parameters (*RETURN*, *_LAT, *_RT, *DELAY*) of leaves whose crossings
      add cycles, flagged when the RTL compares / indexes with them.  Never an error.

    python3 tools/die_plan/latency_consumers.py BIND_DIR [--plan PLAN] [--manifest ASBUILT_SPEC] [--json OUT]
    (plan / manifest default to BIND_DIR/provenance_bind.json; exit 1 on any error)
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]
import core_pin_cycles as CPC  # noqa: E402

# module -> [contract]; ports are fullmatch regexes; req = consumer outputs, resp = consumer inputs (DIE-HBM-92-FLAT)
CONTRACTS = {
    "ot_hbm_vm_lg_pair_tap": [dict(param="READ_RETURN", req=["near_rq"], resp=["near_rr"]),
                              dict(param="WRITE_RETURN", req=["near_wq"], resp=["near_w_done"])],
    "ot_hbm_hc_q_static": [dict(param="DONE_LAT", req=["lg_wq"], resp=["lg_w_done"])],
    "ot_hbm_idx_rootctl_static_am": [dict(param="CR_RT", req=["cq"], resp=["cr"]),
                                     dict(param="VM_RT", req=["vm_rq"], resp=["vm_rr"])],
    # HBM-HUB-RTL-1 11-11 (rd1): the remaining fixed-latency readers of the VM bank read round trip
    "ot_hgi_dma_back_static_vp4_banks_cp": [dict(param="RR_RT", req=["rq"], resp=["rr"])],
    "ot_hbm_idx_vm_share2_static_r": [dict(param="BANK_RT", req=["vm_rq"], resp=["vm_rr"])],
    "ot_hgi_sm_xload_cl2_ctlx": [dict(param="RD_LAT", req=["rq"], resp=["rr"])],
    "ot_hgi_coll_gq_issue": [dict(param="VM_RT", req=["vm_rq_(lo|hi)"], resp=["vm_rr_(lo|hi)"])],
    "ot_hbm_idx_vm_query_static_n12": [dict(param="VM_RT_EXTRA", req=["vm_rq"], resp=["vm_rr"])],
    "ot_hbm_hc_root_static_s": [dict(param="XRD", req=["q[di]_.*"], resp=[]), dict(param="XRU", req=[], resp=["qps.*"])],
    "ot_hgi_sfu_lg_pair_tap_leaf": [dict(align=["c_rq", "local_read"]), dict(align=["c_wq", "local_write"])],
    "ot_hgi_sfu_lg_pair_tap_leaf_term": [dict(align=["c_rq", "local_read"]), dict(align=["c_wq", "local_write"])],
    "ot_hbm_router_ids_static_2src": [dict(align=["run_v", "run1_v", "run_layer", "run1_layer"])],
    # TRANSPORT-1 11-08: QC fixed-age readers with no parameter to regenerate (param = a label, not an RTL parameter).
    # advisory=True reports a landed delta on the loop as ADVISORY_MISMATCH and is never a bind error.
    # qfd_dv_s5_lrly: SU memory delay ML in the lane head; qfd_native59_*: the e1/e2/e3 ring of the embedding read.
    # TRANSPORT-2 11-08: design_loop = crossing stages (request + response) the consumer's ring was designed for.  These
    # rings assume a same-edge loop, so the as-built stages are already an error and "required" counts every landed stage.
    "qfd_dv_s5_lrly": [dict(param="ML", req=["v[abc]_(addr|re)"], resp=["v[abc]_q"], advisory=True, design_loop=0),
                       dict(param="CROM_ML", req=["crom_(addr|re)"], resp=["cr_q"], advisory=True, design_loop=0)],
    "qfd_native59_dv_headprep_obs1": [dict(param="EMB_CODE_RING", req=["emb_code_(addr|re)"], resp=["emb_code_q"], advisory=True, design_loop=0),
                                      dict(param="EMB_SCALE_RING", req=["emb_scale_(addr|re)"], resp=["emb_scale_q"], advisory=True, design_loop=0)],
}
LAT_NAME = re.compile(r"RETURN|_LAT$|(^|_)RT$|DELAY")
_INT = re.compile(r"\s*(\d*)'[sS]?([bdhBDH])([0-9a-fA-F_]+)\s*")


def rules_contracts(src_root=REPO):
    """d4g_bank_latency RULES as contracts (port, kind, param, default, ref, ref_rt, why)"""
    sys.path.insert(0, str(Path(src_root) / "tools" / "hbm_die_v16"))
    try:
        import d4g_bank_latency as BL
    except ImportError:
        return {}
    out = defaultdict(list)
    for mod, rs in BL.RULES.items():
        for port, kind, param, *_ in rs:
            if kind == "wr":
                resp = [re.sub(r"wq(\d*)$", r"w_done\1", port), re.sub(r"wq(\d*)$", r"wq_done\1", port), port + "_done"]
            else:
                resp = [re.sub(r"([rp])q(\d*)$", lambda m: ("rr" if m.group(1) == "r" else "pr") + m.group(2), port)]
            out[mod].append(dict(param=param, req=[port + r"\d*"], resp=[r + r"\d*" for r in resp], src="d4g RULES"))
    return out


def parse_attr(s):
    """(* ot_fixed_latency = "a,b>c,d:PARAM;align:x,y" *) -> [contract]"""
    out = []
    for part in filter(None, (x.strip() for x in str(s).split(";"))):
        if part.startswith("align:"):
            out.append(dict(align=part[6:].split(","), src="rtl attribute"))
        else:
            ports, param = part.rsplit(":", 1)
            req, resp = (ports.split(">") + [""])[:2]
            out.append(dict(param=param.strip(), req=[p for p in req.split(",") if p], resp=[p for p in resp.split(",") if p],
                            src="rtl attribute"))
    return out


def _int(v):
    if isinstance(v, int):
        return v
    s = str(v).strip().strip('"')
    if re.fullmatch(r"[01]{8,64}", s):                       # Yosys binary parameter value (32 bits)
        return int(s, 2)
    m = _INT.fullmatch(s)
    if m:
        return int(m.group(3).replace("_", ""), dict(b=2, d=10, h=16)[m.group(2).lower()])
    try:
        return int(s)
    except ValueError:
        return None


def _mname(ytype):
    """Yosys module key -> RTL module name ($paramod\\M\\P=V / $paramod$hash\\M -> M)"""
    s = str(ytype or "")
    return s.split("\\")[1] if s.startswith("$paramod") and "\\" in s else s.lstrip("\\")


def yosys_leaves(yjs, top=None):
    """as-built leaf map from the Yosys JSON: {path: dict(module, params, src, attrs)} for every instance"""
    mods = yjs["modules"]
    top = top or next(m for m, v in mods.items() if v.get("attributes", {}).get("top"))
    # bind_elab_keep is the elaboration wrapper (u_die + variant keeps); bus_groups paths start at the die itself
    if top == "bind_elab_keep" and mods[top].get("cells", {}).get("u_die", {}).get("type") in mods:
        top = mods[top]["cells"]["u_die"]["type"]
    name = lambda m: mods[m].get("attributes", {}).get("hdlname") or _mname(m)
    out, st = {}, [(top, "")]
    while st:
        m, p = st.pop()
        for cn, c in mods[m].get("cells", {}).items():
            t = c["type"]
            if t not in mods:
                continue
            q = f"{p}.{cn}" if p else cn
            v = mods[t]
            ps = dict(v.get("parameter_default_values", {}))
            ps.update(c.get("parameters", {}))
            out[q] = dict(module=name(t), params={k: _int(x) if _int(x) is not None else x for k, x in ps.items()},
                          src=v.get("attributes", {}).get("src"), attrs=v.get("attributes", {}))
            st.append((t, q))
    return out


def binder_leaves(B, yjs):
    """the bind's own leaf cells (substituted variants, core-split leaves); params = as-built (param_regen undone)"""
    mods = yjs["modules"]
    undo = {(c["inst"], c["param"]): c["asbuilt"] for c in (B.param_regen or {}).get("changed", [])}
    out = {}
    for c in B.F.cells:
        if c.kind != "leaf":
            continue
        ps = dict(B.param_defaults.get((c.ytype, c.module), {}))
        ps.update(c.params)
        ps = {k: undo.get((c.path, k), v) for k, v in ps.items()}
        a = mods.get(c.ytype, {}).get("attributes", {})
        out[c.path] = dict(module=c.module, alias=a.get("hdlname") or _mname(c.ytype),
                           params={k: _int(v) if _int(v) is not None else v for k, v in ps.items()},
                           src=a.get("src"), attrs=a)
    return out


def _deltas(bg, absolute=False):
    """{leaf: {port: {added cycles}}} on the sink and source side; absolute=True gives landed stages instead of landed - as-built"""
    ins, outs = defaultdict(lambda: defaultdict(set)), defaultdict(lambda: defaultdict(set))
    for g in bg["landing"]:
        for m in g["members"]:
            d = m.get("landed_stages", m["bound_stages"]) - (0 if absolute else m["asbuilt_stages"])
            ins[g["sink"]][m["sink_port"]].add(d)
            s, pn = m["source"].rsplit(".", 1)
            outs[s][pn].add(d)
    return ins, outs


def _pick(side, pats):
    rx = [re.compile(p) for p in pats]
    return {pn: ds for pn, ds in side.items() if any(r.fullmatch(pn) for r in rx)}


def _compares(src, module, cache):
    """does the module body compare / index with a parameter? {param: bool} or None (source not readable)"""
    f = str(src or "").split(":")[0]
    if f not in cache:
        try:
            cache[f] = re.sub(r"//[^\n]*", "", Path(f).read_text(errors="replace"))
        except OSError:
            cache[f] = None
    t = cache[f]
    if t is None:
        return None
    m = re.search(r"\bmodule\s+%s\b(.*?)\bendmodule\b" % re.escape(module), t, re.S)
    return m.group(1) if m else None


def check(leaves, bg, param_regen=None, ab=None, raw=None, r8_opts=None, src_root=REPO, limit=60):
    """-> dict(errors=[str], r8=..., contracts=[rows], advisory=[rows], stats=...)"""
    ab = ab or {}
    pr = param_regen or {}
    # An absolute-law hook may derive the already-correct value. The binder
    # records each explicitly validated target, including unchanged ones;
    # merely having a hook still does not qualify any other parameter.
    regen = {(c["inst"], c["param"]): c
             for c in list(pr.get("derived", [])) + list(pr.get("changed", []))}
    hooked = bool(ab.get("param_regen")) or bool(pr)
    landed = bool(ab.get("land_align"))                  # the bind lands crossings (r8 table or cell pads)
    table = defaultdict(list)
    for src in (CONTRACTS, rules_contracts(src_root)):
        for mod, cs in src.items():
            table[mod] += [dict(c, src=c.get("src", "latency_consumers.CONTRACTS")) for c in cs]
    for c in list(ab.get("latency_contracts", [])) + list(pr.get("latency_contracts", [])):
        table[c["module"]].append(dict(c, src=c.get("src", "die declaration")))
    for v in leaves.values():
        a = v.get("attrs", {}).get("ot_fixed_latency")
        if a and v["module"] not in table:
            table[v["module"]] += parse_attr(a)
    ins, outs = _deltas(bg)
    ins_abs, outs_abs = _deltas(bg, absolute=True)
    pins = core_pins(leaves, bg, ab, src_root)
    for k, x in (pr.get("record", {}).get("core_pin_cycles") or {}).items():
        s, _, pn = k.partition("|")
        pins[(s, pn)] = max(pins.get((s, pn), 0), int(x))
    pin_regen = {(r["inst"], r["param"]): r for r in pr.get("record", {}).get("core_pin_regen", [])}
    errors, rows = [], []
    for path, v in sorted(leaves.items()):
        seen = set()
        for c in table.get(v["module"]) or table.get(v.get("alias"), []):
            key = c.get("param") or tuple(c["align"])
            if key in seen:
                continue
            seen.add(key)
            if "align" in c:
                got = _pick(ins.get(path, {}), c["align"])
                ds = sorted({d for x in got.values() for d in x})
                if len(ds) > 1:
                    rows.append(dict(inst=path, module=v["module"], align=sorted(got), deltas={k: sorted(x) for k, x in got.items()},
                                     verdict="MISALIGNED", src=c["src"]))
                    errors.append(f"FIXED_LATENCY_MISALIGNED {path} ({v['module']}): ports sampled on one edge land with "
                                  f"different added delay {({k: sorted(x) for k, x in sorted(got.items())})}")
                continue
            rq, rs = _pick(outs.get(path, {}), c["req"]), _pick(ins.get(path, {}), c["resp"])
            pin = max([x for (s, pn), x in pins.items() if s == path and any(re.fullmatch(r, pn) for r in c["resp"])] or [0])
            if not rq and not rs and not pin:
                continue
            dq = sorted({d for x in rq.values() for d in x}) or [0]
            dr = sorted({d for x in rs.values() for d in x}) or [0]
            added = dq[-1] + dr[-1] + pin
            asb = v["params"].get(c["param"])
            row = dict(inst=path, module=v["module"], param=c["param"], asbuilt=asb, added=added, req=dq, resp=dr,
                       torn=len(dq) > 1 or len(dr) > 1, src=c["src"])
            if pin:
                row["core_pin"] = pin
            if c.get("design_loop") is not None:
                lq = sorted({d for x in _pick(outs_abs.get(path, {}), c["req"]).values() for d in x}) or [0]
                lr = sorted({d for x in _pick(ins_abs.get(path, {}), c["resp"]).values() for d in x}) or [0]
                row.update(landed_loop=lq[-1] + lr[-1], design_loop=c["design_loop"], required=lq[-1] + lr[-1] - c["design_loop"])
            if isinstance(asb, int):
                row["needed"] = CPC.plus(asb, row.get("required", added), c["param"])
            if added == 0 and row.get("required", 0) == 0:
                row["verdict"] = "MATCH"
            elif (path, c["param"]) in pin_regen and pin_regen[(path, c["param"])]["bound"] != CPC.plus(asb, added, c["param"]):
                row.update(verdict="FIXED_LATENCY_MISMATCH", bound=pin_regen[(path, c["param"])]["bound"])
                errors.append(f"FIXED_LATENCY_MISMATCH {path} ({v['module']}) {c['param']}: hook regenerated as-built + core pin "
                              f"{pin_regen[(path, c['param'])]['pin']} = {row['bound']}, but the loop adds {added} "
                              f"(request {dq} + response {dr} + core pin {pin}) -> needs {CPC.plus(asb, added, c["param"])}")
            elif (path, c["param"]) in regen:
                value = regen[(path, c["param"])]["bound"]
                row.update(verdict="REGEN", bound=value, needed=value,
                           asbuilt_plus_added=asb + added if isinstance(asb, int) else None)
            elif c.get("advisory"):
                row["verdict"] = "ADVISORY_MISMATCH"
            else:
                row["verdict"] = "FIXED_LATENCY_MISMATCH"
                errors.append(f"FIXED_LATENCY_MISMATCH {path} ({v['module']}) {c['param']}: as-built {asb}, the bind adds "
                              f"{added} cycles on its loop (request {dq} + response {dr}{', TORN' if row['torn'] else ''}) -> "
                              f"needs {row.get('needed', f'{asb}+{added}')}; no param_regen hook regenerated it ({c['src']})")
            rows.append(row)
    # (3) advisory: undeclared latency-named parameters on crossings that add cycles
    adv, cache = defaultdict(lambda: dict(n=0, params=defaultdict(set), eg=None, max_added=0)), {}
    for path, v in leaves.items():
        dmax = max([d for x in list(ins.get(path, {}).values()) + list(outs.get(path, {}).values()) for d in x] or [0])
        names = [p for p in v["params"] if LAT_NAME.search(p) and p not in {c.get("param") for c in table.get(v["module"], [])}]
        if dmax <= 0 or not names:
            continue
        body = _compares(v.get("src"), v["module"], cache)
        cmp_ = {p: body is None or bool(re.search(r"(==|!=|>=|<=|<|>)\s*\(?\s*%s\b|\b%s\b\s*-\s*1\s*\]|\[\s*%s\b" % (p, p, p), body))
                for p in names}
        names = [p for p in names if cmp_[p]]
        if not names:
            continue
        a = adv[v["module"]]
        a["n"] += 1
        a["eg"] = a["eg"] or path
        a["max_added"] = max(a["max_added"], dmax)
        for p in names:
            a["params"][p].add(str(v["params"][p]))
    advisory = [dict(module=m, n=a["n"], eg=a["eg"], max_added=a["max_added"], params={p: sorted(x)[:6] for p, x in a["params"].items()})
                for m, a in sorted(adv.items(), key=lambda kv: -kv[1]["n"])]
    # (1) R8 on every bind
    adds = sum(1 for g in bg["landing"] for m in g["members"]
               if m["asbuilt_stages"] == 0 and m.get("landed_stages", m["bound_stages"]) > 0)
    r8s = dict(checked=False, adds_to_zero_stage_members=adds, landing_pads=landed, param_regen_hook=hooked)
    if raw is not None:
        import r8 as R8
        o = dict(r8_opts or {})
        keep = (list(R8.EXEMPT), dict(R8.LANDED))
        try:
            R8.configure(o.pop("exempt", ()), o.pop("landed", ()))
            msgs, st = R8.check(bg, raw, None, limit=limit, **o)
        finally:
            R8.EXEMPT[:] = keep[0]
            R8.LANDED.clear()
            R8.LANDED.update(keep[1])
        ne = sum(1 for s, _ in msgs if s == "ERROR")
        r8s.update(checked=True, stats=st, errors=ne, messages=[f"{s} {m}" for s, m in msgs][:limit], options=r8_opts or {})
        bad = st["groups_unequal"] + st["replica_unequal"] + st["inversions"] + st["types_conflicting"] + st["landed_over_margin"]
        if bad and adds and not landed and not hooked:
            errors.append(f"R8_UNLANDED the bind adds stages to {adds} as-built 0-stage crossing members and the die has no "
                          f"landing pads (asbuilt.land_align) and no param_regen hook: {st['groups_unequal']} unequal "
                          f"landing groups, {st['replica_unequal']} unequal replica sets, {st['inversions']} inversions, "
                          f"{st['types_conflicting']} type pad conflicts (tools/die_plan/r8.py pads -> land_r8)")
        r8s["verdict"] = ("ERROR" if any(e.startswith("R8_UNLANDED") for e in errors) else
                          "PASS" if not bad else "ADVISORY (die has R8 pads or a param_regen hook)")
    stats = dict(leaves=len(leaves), contract_modules=len(table), instances_checked=len(rows),
                 verdicts={k: sum(1 for r in rows if r["verdict"] == k) for k in sorted({r["verdict"] for r in rows})},
                 advisory_families=len(advisory), errors=len(errors))
    return dict(schema="opentallas.die_plan.latency_consumers.v1", stats=stats, errors=errors, r8=r8s,
                contracts=[r for r in rows if r["verdict"] != "MATCH"], advisory=advisory)


def core_pins(leaves, bg, ab, base=REPO):
    """{(sink leaf, sink port): edges added inside the source cores} over the crossing members (asbuilt.core_pin_cycles)"""
    rules = CPC.load(ab, base)
    out = {}
    if not rules or not bg:
        return out
    for g in bg["landing"]:
        for m in g["members"]:
            s, pn = m["source"].rsplit(".", 1)
            x = CPC.added_port(rules, s, (leaves.get(s) or {}).get("module"), pn)
            if x:
                out[(g["sink"], m["sink_port"])] = max(out.get((g["sink"], m["sink_port"]), 0), x)
    return out


def r8_options(ab, base):
    """the die's own R8 options: landing table exempt / replica / bus (asbuilt.land_r8), land_r8_exempt, strap pads"""
    o = dict(exempt=list(ab.get("land_r8_exempt", [])), strap_pads=bool(ab.get("land_r8_strap_pads")))
    if ab.get("land_align") == "r8" and ab.get("land_r8"):
        f = Path(ab["land_r8"])
        f = f if f.is_absolute() else Path(base) / f
        try:
            js = json.loads(f.read_text())
            o["exempt"] = list(js.get("exempt", [])) + o["exempt"]
            o.update(replica=js.get("replica", "all"), bus=js.get("bus", "part"))
        except (OSError, ValueError):
            o["table_unreadable"] = str(f)
    o.pop("table_unreadable", None)
    return o


def _load(p):
    import gzip
    p = Path(p)
    for q in (p, Path(str(p) + ".gz")):
        if q.exists():
            with (gzip.open(q, "rt") if q.suffix == ".gz" else open(q)) as f:
                return json.load(f)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bind_dir", type=Path)
    ap.add_argument("--plan")
    ap.add_argument("--manifest", help="the bind's as-built spec (asbuilt.*.json); default from provenance_bind.json")
    ap.add_argument("--base", default=str(REPO), help="repo root the manifest's relative paths resolve against")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    d = a.bind_dir
    prov = (_load(d / "provenance_bind.json") or {}).get("provenance", {})
    plan, man = a.plan or prov.get("plan"), a.manifest or prov.get("manifest")
    ab = {}
    if man:
        mp = Path(man) if Path(man).is_absolute() else Path(a.base) / man
        ab = _load(mp) or {}
    raw = None
    if plan and Path(plan).exists():
        import schema as S
        raw = S.load(plan)
    yjs = _load(d / "asbuilt.json")
    res = check(yosys_leaves(yjs, ab.get("top")), _load(d / "bus_groups.json"), _load(d / "param_regen.json"), ab, raw,
                r8_options(ab, a.base), src_root=Path(a.base))
    res.update(bind_dir=str(d), plan=plan, manifest=man)
    if a.json:
        a.json.write_text(json.dumps(res, indent=1, default=str) + "\n")
    for e in res["errors"]:
        print("ERROR", e)
    for r in res["contracts"]:
        if r["verdict"] == "ADVISORY_MISMATCH":
            print(f"ADVISORY_MISMATCH {r['inst']} ({r['module']}) {r['param']}: the bind adds {r['added']} cycles on a fixed-age "
                  f"loop (request {r['req']} + response {r['resp']}{', TORN' if r['torn'] else ''})"
                  + (f"; landed loop {r['landed_loop']}, required +{r['required']} over design {r['design_loop']}" if "required" in r else ""))
    for r in res["advisory"]:
        print(f"ADVISORY {r['module']} n={r['n']} max_added={r['max_added']} {json.dumps(r['params'])[:160]} e.g. {r['eg']}")
    print(f"LATENCY_CONSUMERS {'FAIL' if res['errors'] else 'PASS'} {json.dumps(res['stats'])} r8={res['r8'].get('verdict')} "
          f"{json.dumps(res['r8'].get('stats', {}))[:300]}")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
