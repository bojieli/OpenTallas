#!/usr/bin/env python3
"""BIND-EQDEPTH 11-23: equal-depth ALIGN GROUPS, a hard bind / LATCHECK gate on every die.

Bits that must keep cycle alignment across a seam, a type split or relay lanes (a kv interface's busy/done levels, the
port selects and the data they select) must see the IDENTICAL register-stage count.  Nothing else enforces it: each lane
is checked against its own latency row (LATCHECK-1), so two lanes of one interface can both pass with different depths
after a later row moves bits between lanes (S81 kv_leaf t2 split: the B slice uses the level 'busy' as a port select,
FABLE-RC-ALL / S81-ALLFIX-INT 11-23).

Declaration (plan, read by the bind; the split row / plan delta only writes it):

  latency.align_groups = {
    "<group>": {
      "type":    "<partition type>",          optional: only partitions of this type (default: every partition)
      "sources": ["<inst>.<port>[hi:lo]", ..], leaf OUTPUT bits; every crossing sink each bit drives is measured
      "sinks":   ["<inst>.<port>", ..],        leaf INPUT bits; the crossing that drives each bit is measured
      "max_total": 3,                           optional: depth(group) [+ depth(max_total_with)] <= max_total
      "max_total_with": "<other group>",        optional: the partner group of the budget (e.g. the input direction)
      "note": "..."}}

  <inst> is the leaf instance path relative to its partition (the type's content names, e.g. u_lf.g_kv.u_kv; a one-leaf
  partition is "core") or the full as-built path.  [hi:lo] / [i] selects bits; no index = the whole port.

Per bit the stage count is the bound landed depth the binder routes (Binder.depth: boundary + ft stations + landing +
native source / receiver stations + landing pads + position-bank pad) plus the lane's LATCHECK as-built delta (kit
stations the bind RTL does not hold yet; 0 on a passing lane).  Each group is checked per partition:
  ALIGN_GROUP      bits with different depths (every off-majority bit listed with its lane), or a bit with no crossing
  ALIGN_BUDGET     depth over max_total
  ALIGN_GROUP_DECL a malformed declaration or a member that matches no leaf port (a stale declaration)
All are hard bind errors (no waiver); the full per-bit table is bind_align_groups.json."""
import re
from collections import Counter, defaultdict

SCHEMA = "opentallas.die_plan.bind_align_groups.v1"
MEMBER_RX = re.compile(r"^(?P<inst>[^\s\[\]]+)\.(?P<port>[A-Za-z_]\w*)(?:\[(?P<hi>\d+)(?::(?P<lo>\d+))?\])?$")
KEYS = {"type", "sources", "sinks", "max_total", "max_total_with", "note"}
LIST_MAX = 40


def parse_member(s):
    """'inst.port[hi:lo]' -> (inst, port, bits or None)"""
    m = MEMBER_RX.match(str(s).strip())
    if not m:
        raise ValueError(f"bad member {s!r} (want <inst>.<port>[hi:lo])")
    if m["hi"] is None:
        return m["inst"], m["port"], None
    hi, lo = int(m["hi"]), int(m["lo"] if m["lo"] is not None else m["hi"])
    return m["inst"], m["port"], list(range(min(hi, lo), max(hi, lo) + 1))


def parse(plan):
    """plan -> (groups {name: {type, sources: [(inst, port, bits)], sinks: [...], max_total, max_total_with}}, errors)"""
    raw = ((plan or {}).get("latency") or {}).get("align_groups") or {}
    groups, errs = {}, []
    if not isinstance(raw, dict):
        return {}, [f"ALIGN_GROUP_DECL */*: latency.align_groups must be an object, got {type(raw).__name__}"]
    for name, g in sorted(raw.items()):
        tag = f"{(g or {}).get('type') or '*'}/{name}" if isinstance(g, dict) else f"*/{name}"
        if not isinstance(g, dict):
            errs.append(f"ALIGN_GROUP_DECL {tag}: not an object")
            continue
        bad = sorted(set(g) - KEYS)
        if bad:
            errs.append(f"ALIGN_GROUP_DECL {tag}: unknown keys {bad}")
        ent = dict(type=g.get("type"), sources=[], sinks=[], max_total=g.get("max_total"),
                   max_total_with=g.get("max_total_with"))
        for side in ("sources", "sinks"):
            for s in g.get(side) or []:
                try:
                    ent[side].append(parse_member(s))
                except ValueError as exc:
                    errs.append(f"ALIGN_GROUP_DECL {tag}: {exc}")
        if not ent["sources"] and not ent["sinks"]:
            errs.append(f"ALIGN_GROUP_DECL {tag}: no sources and no sinks")
        mt = ent["max_total"]
        if mt is not None and (not isinstance(mt, int) or isinstance(mt, bool) or mt < 0):
            errs.append(f"ALIGN_GROUP_DECL {tag}: max_total must be an integer >= 0, got {mt!r}")
            ent["max_total"] = None
        if ent["max_total_with"] is not None and ent["max_total"] is None:
            errs.append(f"ALIGN_GROUP_DECL {tag}: max_total_with without max_total")
        groups[name] = ent
    for name, g in groups.items():
        w = g["max_total_with"]
        if w is not None and w not in groups:
            errs.append(f"ALIGN_GROUP_DECL {g['type'] or '*'}/{name}: max_total_with names unknown group {w!r}")
            g["max_total_with"] = None
    return groups, errs


# ---- per-bit stage counts from a Binder ------------------------------------------------------------------------------
def _xdescs(d):
    """crossing descriptors of one sink: an x desc itself, or the x members of an or/and reducer"""
    if not d:
        return []
    if d[0] == "x":
        return [d]
    if d[0] in ("or", "and"):
        return [x for x in d[1] if x and x[0] == "x"]
    return []


def collect(B, groups, lane_delta=None, extra=None):
    """-> {group: {partition: [bit record]}}, errors.  bit record = dict(bit, side, depths [(depth, lane, peer)])"""
    if extra is None:
        import bind_position_bank as PB
        extra = PB.extra
    lane_delta = lane_delta or {}
    F = B.F
    errs = []

    def depth_of(ci, pn, d):
        key = (d[1], d[6], d[2], d[3], d[4])
        L = B.bitpos[key][0] if key in B.bitpos else {}
        lane = L.get("lane") or ("spine" if L.get("spine") else "UNPLANNED")
        st = B.bitcyc[key] + (d[7] if len(d) > 7 else 0) + int(extra(B, ci, pn) or 0) + int(lane_delta.get(lane, 0))
        return st, lane

    want_types = {g["type"] for g in groups.values()}
    cells = defaultdict(list)                    # (type or None, inst) -> [ci]
    for ci, p in B.cpart.items():
        tn = B.parts.get(p, {}).get("type")
        names = {F.cells[ci].path}
        try:
            names.add(B.rel_of(ci))
        except Exception:                         # noqa: BLE001 (a cell without a partition root: full path only)
            pass
        for t in ({tn, None} & want_types):
            for n in names:
                cells[(t, n)].append(ci)
    src_cells = set()
    for g in groups.values():
        for inst, _p, _b in g["sources"]:
            src_cells.update(cells.get((g["type"], inst), ()))
    fanout = defaultdict(list)                   # (src ci, port, bit) -> [(sink ci, sink port, sink bit, desc)]
    if src_cells:
        for (ci, pn, i), d in B.sinks.items():
            for x in _xdescs(d):
                if x[2] in src_cells:
                    fanout[(x[2], x[3], x[4])].append((ci, pn, i, x))
    out = {}
    for name, g in groups.items():
        tag = f"{g['type'] or '*'}/{name}"
        per = defaultdict(list)
        for side in ("sources", "sinks"):
            for inst, port, bits in g[side]:
                cis = sorted(set(cells.get((g["type"], inst), ())))
                cis = [ci for ci in cis if port in F.cells[ci].ports]
                if not cis:
                    errs.append(f"ALIGN_GROUP_DECL {tag}: {side[:-1]} {inst}.{port} matches no leaf port"
                                + (f" in a partition of type {g['type']}" if g["type"] else ""))
                    continue
                for ci in cis:
                    w = len(F.cells[ci].ports[port])
                    sel = range(w) if bits is None else bits
                    over = [b for b in sel if b >= w]
                    if over:
                        errs.append(f"ALIGN_GROUP_DECL {tag}: {inst}.{port} has {w} bits, declared bit {max(over)}")
                    p = B.cpart[ci]
                    for b in sel:
                        if b >= w:
                            continue
                        lbl = f"{inst}.{port}[{b}]"
                        if side == "sources":
                            ds = [depth_of(sci, spn, x) + (f"{F.cells[sci].path}.{spn}[{si}]",)
                                  for sci, spn, si, x in fanout.get((ci, port, b), ())]
                        else:
                            ds = [depth_of(ci, port, x) + (f"{F.cells[x[2]].path}.{x[3]}[{x[4]}]",)
                                  for x in _xdescs(B.sinks.get((ci, port, b)))]
                        per[p].append(dict(bit=lbl, side=side[:-1], depths=sorted(set(ds))))
        out[name] = dict(per)
    return out, errs


# ---- the gate (pure: tests feed it records) ---------------------------------------------------------------------------
def check(groups, measured):
    """groups: parse() output; measured: collect() output -> (records, errors)"""
    recs, errs = [], []
    gdepth = defaultdict(dict)                   # group -> {partition: max depth}
    for name, g in sorted(groups.items()):
        tag = f"{g['type'] or '*'}/{name}"
        for p, bits in sorted((measured.get(name) or {}).items()):
            missing = [b["bit"] for b in bits if not b["depths"]]
            per_bit = {b["bit"]: sorted({d for d, _l, _q in b["depths"]}) for b in bits if b["depths"]}
            hist = Counter(d for b in bits for d, _l, _q in b["depths"])
            vals = sorted(hist)
            rec = dict(group=name, type=g["type"], partition=p, bits=len(bits), depths=dict(sorted(hist.items())),
                       missing=missing)
            if vals:
                gdepth[name][p] = vals[-1]
            if len(vals) > 1 or missing:
                ref = hist.most_common(1)[0][0] if hist else None
                off = []
                for b in bits:
                    for d, lane, peer in b["depths"]:
                        if d != ref:
                            off.append(f"{b['bit']}={d} (lane {lane} -> {peer})")
                rec.update(verdict="FAIL", majority=ref, off=off)
                msg = (f"ALIGN_GROUP {tag}: partition {p}: {len(bits)} bits must have one stage count, got "
                       f"{dict(sorted(hist.items()))}" + (f" (majority {ref})" if ref is not None else ""))
                if missing:
                    msg += f"; {len(missing)} bits on no crossing: {', '.join(missing[:LIST_MAX])}" + (
                        " ..." if len(missing) > LIST_MAX else "")
                if off:
                    msg += f"; off-majority: {', '.join(off[:LIST_MAX])}" + (" ..." if len(off) > LIST_MAX else "")
                errs.append(msg)
            else:
                rec.update(verdict="PASS", depth=vals[0])
            rec["per_bit"] = per_bit
            recs.append(rec)
    for rec in recs:
        g = groups[rec["group"]]
        if g["max_total"] is None or rec["partition"] not in gdepth[rec["group"]]:
            continue
        own = gdepth[rec["group"]][rec["partition"]]
        w = g["max_total_with"]
        part = 0
        if w:
            wd = gdepth.get(w, {})
            part = wd.get(rec["partition"], max(wd.values()) if wd else 0)
        tot = own + part
        rec["budget"] = dict(max_total=g["max_total"], own=own, partner=w, partner_depth=part, total=tot,
                             verdict="PASS" if tot <= g["max_total"] else "FAIL")
        if tot > g["max_total"]:
            rec["verdict"] = "FAIL"
            errs.append(f"ALIGN_BUDGET {g['type'] or '*'}/{rec['group']}: partition {rec['partition']}: depth {own}"
                        + (f" + {w} {part}" if w else "") + f" = {tot} > max_total {g['max_total']}")
    return recs, errs


def summary(recs, decl_errs=()):
    c = Counter(r["verdict"] for r in recs)
    return dict(groups=len({r["group"] for r in recs}), records=len(recs), passed=c.get("PASS", 0),
                failed=c.get("FAIL", 0), decl_errors=len(decl_errs),
                verdict="FAIL" if c.get("FAIL") or decl_errs else "PASS")


def bind_check(B, plan, la_recs=None):
    """in-bind hook (bind.py cmd_bind, after LATCHECK) -> (report or None, errors).  No declaration = (None, [])."""
    groups, errs = parse(plan)
    if not groups and not errs:
        return None, []
    delta = {r["lane"]: int(r.get("delta") or 0) for r in (la_recs or []) if r.get("verdict") == "FAIL"}
    measured, cerrs = collect(B, groups, delta)
    errs += cerrs
    recs, gerrs = check(groups, measured)
    return dict(schema=SCHEMA, summary=summary(recs, errs), decl_errors=errs, groups=recs), errs + gerrs
