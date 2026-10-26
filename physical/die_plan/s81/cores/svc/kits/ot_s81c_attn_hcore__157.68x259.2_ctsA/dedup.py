"""TYPE-DEDUP: collapse near-duplicate partition types into one type (opt-in plan transform, never in place).

    python3 tools/die_plan/dedup.py analyze PLAN.json [--out report.json]
    python3 tools/die_plan/dedup.py apply   PLAN.json --out-plan NEW.json [--report r.json] [--only canon,..]
    python3 tools/die_plan/gen.py dedup     PLAN.json --out-plan NEW.json         (same as apply)

Every unique partition type costs a kit, a P&R run, a closure and an abstract.  Two types are merged only when the
merge is EXACT by construction:

1. Same netlist (the `netlist_key`): outline, the bus interface (name, dir, width, kind, leaf binding), the ft slots
   (name, width, stations), the contents (inst, module, params, bind) and the hard cores (inst, module).  Pure
   geometry (content origins, core placement, clock taps, internal stations, notes, cell counts) is NOT part of the
   key: the merged type takes the canonical type's internal floorplan, which is valid for every instance because the
   pin table is the same (point 2).
2. Same die interface: each instance of a merged type is re-typed to the canonical type with one of the four orients
   (its own orient first) such that
   (a) every port touching it keeps the identical die-frame pins (bit, layer, coordinate) and face, and
   (b) its type-frame pin table (bus, bit, layer, type face, coordinate) equals the canonical type's reference table
       (G0 'identical pin tables across a replicated type').
   Then the die-level netlist and the abutted geometry are unchanged bit for bit; only the type name (and possibly
   the orient) of that instance changes.  Ports, lanes, latency and census are untouched.
A group member that fails (2) for any instance stays a separate type and is reported GEOM-BLOCKED with the first
failing port.  Members whose key differs only in contents `params` are reported STRAP candidates (not merged here:
under R7 a per-instance strap must be a real planned lane from a configuration register, never a tie cell); members
that differ only in ft-slot population are reported FT-POP (needs a lane reassignment by the die owner, since an
unused slot would be an unbound bus = tie-off).

`--fix-order` also accepts a member whose instances match the canonical pin table up to the BIT ORDER of some ports
(same faces, same tracks): the port orders are then re-solved die-wide as parity constraints (port order XOR type
order = mirror flip of the instance, per partition end; a type-declared ft slot shares one order for both sides).  The
netlist is untouched (bit i of a port still connects bit i at both ends); only which track carries which bit
changes, on both abutting partitions alike.  The types whose pin tables change are listed (their kits regenerate).

`--bound-rtl DIR` (default PLANDIR/bind/bound_r8/rtl) adds a netlist gate: a member whose bound partition RTL differs
from its canonical's (comments and module name ignored) is not merged unless `--plan-only`.

The transform writes provenance to NEWDIR/dedup_provenance.json ({merged: {old type: {into, instances: {part: [old
orient, new orient]}}}, reordered_ports, pin_table_touched_types, source_digest}) and a line in the plan `note`.  It
never edits the input file.
"""
import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART  # noqa: E402

ORIENTS = ("R0", "MX", "MY", "R180")
# contents fields that are placement / bookkeeping only (not netlist)
CONTENT_GEOM = {"origin_um", "outline_um", "note", "kit", "geom_pass", "cells", "status", "obs_max", "orient"}
BUS_GEOM = {"face", "window_um", "layers", "order", "note"}
SLOT_GEOM = {"in_face", "out_face", "in_window_um", "out_window_um", "layers", "order", "regs_um", "note"}


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def _strip(d, drop):
    return {k: v for k, v in d.items() if k not in drop}


def netlist_key(t, params=True, slots=True):
    """netlist identity of a partition type (see module doc).  params=False drops contents params (strap analysis);
    slots=False drops the ft slots (ft-population analysis)."""
    cd = CONTENT_GEOM | (set() if params else {"params"})
    return _canon(dict(
        outline=[round(float(v), 4) for v in t["outline_um"]],
        hard=bool(t.get("hard", False)),
        buses=sorted((_canon(_strip(b, BUS_GEOM)) for b in t.get("buses", []))),
        slots=sorted((_canon(_strip(s, SLOT_GEOM)) for s in t.get("ft_slots", []))) if slots else None,
        contents=sorted((_canon(_strip(c, cd)) for c in t.get("contents", []))),
        cores=sorted((c["inst"], c["module"]) for c in t.get("hard_cores", [])),
        reset=t.get("reset", {}).get("sync_stages"),
        sources=sorted(t.get("sources", [])),
    ))


class Iface:
    """die-interface oracle on a live Plan: per-part ports, die pins and type-frame pin tables, with cheap re-typing."""

    def __init__(self, raw):
        self.raw = raw
        self.P = S.Plan(raw)
        self.raw_ports = {p["id"]: p for p in raw["ports"]}
        self.ports_of = defaultdict(list)
        for p in raw["ports"]:
            for side in ("src", "dst"):
                if p[side]["part"] != DIE_PART:
                    self.ports_of[p[side]["part"]].append((p["id"], side))
        self.inst = defaultdict(list)
        for p in raw["partitions"]:
            self.inst[p["type"]].append(p["name"])

    def _pins(self, pid):
        try:
            return tuple(self.P.port_pins(pid))
        except (ValueError, KeyError, TypeError) as e:
            return ("ERR", str(e))

    def die_sig(self, part):
        """{(pid, side): (face, pins)} in the die frame."""
        out = {}
        for pid, side in self.ports_of[part]:
            pr = self.P.ports[pid]
            out[(pid, side)] = (pr.get("face"), self._pins(pid))
        return out

    def type_table(self, part, sig=None):
        """{(bus, bit): (layer, type face, type coord)} for one instance, as G0 check_abutment builds it."""
        P = self.P
        sig = sig if sig is not None else self.die_sig(part)
        p = P.parts[part]
        w, h = P.ptype(part)["outline_um"]
        o = p.get("orient", "R0")
        ox, oy = p["origin_um"]
        tab = {}
        for (pid, side), (f, pins) in sig.items():
            pr = P.ports[pid]
            if pins and pins[0] == "ERR":
                tab[(pr[side]["bus"], "ERR")] = pins
                continue
            df = f
            if side == "dst" and pr["src"]["part"] != DIE_PART:
                df = S.OPP[f]
            tf = P.type_face(part, df)
            if df in "EW":
                flip, base, ext = o in ("MX", "R180"), oy, h
            else:
                flip, base, ext = o in ("MY", "R180"), ox, w
            for bit, ln, c in pins:
                tc = (ext - (c - base)) if flip else (c - base)
                tab[(pr[side]["bus"], bit)] = (ln, tf, round(tc, 4))
        return tab

    def retype(self, part, tn, orient):
        """re-type one instance in place (Plan + raw), re-resolving its ports; returns the undo record."""
        P = self.P
        old = P.parts[part]
        new = dict(old, type=tn, orient=orient)
        P.parts[part] = new
        P.__dict__.pop("_bus_cache", None)
        for pid, _ in self.ports_of[part]:
            P.ports[pid] = P._resolve_port(self.raw_ports[pid])
        return old

    def undo(self, part, old):
        self.P.parts[part] = old
        self.P.__dict__.pop("_bus_cache", None)
        for pid, _ in self.ports_of[part]:
            self.P.ports[pid] = self.P._resolve_port(self.raw_ports[pid])


def _first_diff(a, b):
    ks = sorted(set(a) | set(b), key=str)
    for k in ks:
        if a.get(k) != b.get(k):
            return k, a.get(k), b.get(k)
    return None


def _bitless(tab):
    """type-frame table without the bit -> track assignment: {bus: sorted (layer, face, coord)}."""
    out = defaultdict(list)
    for (bus, bit), v in tab.items():
        out[bus].append(v if bit != "ERR" else ("ERR",))
    return {b: sorted(map(tuple, v)) for b, v in out.items()}


def _die_bitless(sig):
    return {k: (f, tuple(sorted((ln, c) for _, ln, c in pins)) if pins and pins[0] != "ERR" else pins)
            for k, (f, pins) in sig.items()}


def try_merge(I, canon, member, fix_order=False):
    """per instance of `member`: the orient that keeps (a) die pins and (b) the canonical type-frame table.
    fix_order: accept an orient where (a)/(b) hold up to the bit order of some ports (same tracks, same faces); the
    order is then repaired die-wide by `order_solve`.  -> (ok, {part: (old orient, new orient)}, reason, n_reordered)"""
    ref_part = sorted(I.inst[canon])[0]
    ref_tab = I.type_table(ref_part)
    ref_bl = _bitless(ref_tab)
    moves = {}
    for part in sorted(I.inst[member]):
        own = I.P.parts[part].get("orient", "R0")
        before = I.die_sig(part)
        why = None
        best = None
        for o in (own,) + tuple(x for x in ORIENTS if x != own):
            old = I.retype(part, canon, o)
            after = I.die_sig(part)
            tab = I.type_table(part, after)
            I.undo(part, old)
            if after == before and tab == ref_tab:
                best = (o, 0)
                break
            if fix_order and _die_bitless(after) == _die_bitless(before) and _bitless(tab) == ref_bl:
                nb = sum(1 for b in ref_bl if {k: v for k, v in tab.items() if k[0] == b} !=
                         {k: v for k, v in ref_tab.items() if k[0] == b})
                if best is None or nb < best[1]:
                    best = (o, nb)
                continue
            if after != before:
                d = _first_diff(after, before)
                why = why or f"{part}@{o}: die pins of port {d[0][0]} change"
            else:
                d = _first_diff(tab, ref_tab)
                why = why or f"{part}@{o}: type-frame pin table differs from {ref_part} at {d[0]}"
        if best is None:
            return False, moves, why
        moves[part] = (own, best[0])
    return True, moves, None


# ------------------------------------------------------------------ die-wide bit-order repair (parity constraints)
def _flip(orient, die_face):
    return int((die_face in "EW" and orient in ("MX", "R180")) or (die_face in "NS" and orient in ("MY", "R180")))


def _unit(t, tn, bus):
    """the order variable a bus end belongs to: a type-declared slot side shares the slot's one `order` field."""
    for s_ in t.get("ft_slots", []):
        for sfx, wk in (("_i", "in_window_um"), ("_o", "out_window_um")):
            if bus == s_["name"] + sfx:
                return ((tn, "slot:" + s_["name"]), True) if (wk in s_ and "layers" in s_) else ((tn, "bus:" + bus), False)
    for b in t.get("buses", []):
        if b["name"] == bus:
            return (tn, "bus:" + bus), all(k in b for k in ("window_um", "face", "layers"))
    return (tn, "bus:" + bus), False


class _UF:
    def __init__(self):
        self.par, self.rel = {}, {}

    def find(self, x):
        if x not in self.par:
            self.par[x], self.rel[x] = x, 0
            return x, 0
        r, acc, path = x, 0, []
        while self.par[r] != r:
            path.append(r)
            acc ^= self.rel[r]
            r = self.par[r]
        a = acc
        for n in path:                      # path compression
            nxt = self.rel[n]
            self.par[n], self.rel[n] = r, a
            a ^= nxt
        return r, acc

    def union(self, a, b, d):
        """a XOR b = d; False on conflict."""
        ra, pa = self.find(a)
        rb, pb = self.find(b)
        if ra == rb:
            return (pa ^ pb) == d
        self.par[ra], self.rel[ra] = rb, pa ^ pb ^ d
        return True


def _resolved(raw):
    """{pid: (die face, order bit)} of every port as the Plan resolves it (port or type geometry)."""
    key = id(raw)
    if _RES_CACHE.get("k") != key:
        P = S.Plan(raw)
        _RES_CACHE.update(k=key, v={pid: (pr.get("face"), int(pr.get("order", "lsb_low") == "lsb_high"))
                                    for pid, pr in P.ports.items()})
    return _RES_CACHE["v"]


_RES_CACHE = {}


def order_system(raw, parts, alias):
    """parity constraints port_order XOR unit_order = flip(end) for every partition end; `parts` = {name: (type,
    orient)}, `alias` maps merged-away units to canonical units.  -> (UF, ok, first conflict)"""
    T = raw["partition_types"]
    res = _resolved(raw)
    uf = _UF()
    for pr in raw["ports"]:
        face = res[pr["id"]][0]
        for side in ("src", "dst"):
            pn = pr[side]["part"]
            if pn == DIE_PART:
                continue
            tn, o = parts[pn]
            df = face if (side == "src" or pr["src"]["part"] == DIE_PART) else S.OPP[face]
            u, _ = _unit(T[tn], tn, pr[side]["bus"])
            u = alias.get(u, u)
            if not uf.union(("p", pr["id"]), ("u",) + u, _flip(o, df)):
                return uf, False, f"port {pr['id']} end {pn}.{pr[side]['bus']}"
    return uf, True, None


def order_solve(raw, merges):
    """merges: {member type: (canon, {part: (o0, o1)})}.  -> (ok, new port orders {pid: 0/1}, unit values, reason)"""
    T = raw["partition_types"]
    parts = {p["name"]: (p["type"], p.get("orient", "R0")) for p in raw["partitions"]}
    alias = {}
    for m, (c, moves) in merges.items():
        for part, (o0, o1) in moves.items():
            parts[part] = (c, o1)
        for pr in raw["ports"]:
            for side in ("src", "dst"):
                if pr[side]["part"] in moves:
                    um, _ = _unit(T[m], m, pr[side]["bus"])
                    uc, _ = _unit(T[c], c, pr[side]["bus"])
                    alias[um] = uc
    uf, ok, why = order_system(raw, parts, alias)
    if not ok:
        return False, None, None, why
    # per component pick the parity that changes the fewest port orders
    orig = {pid: v[1] for pid, v in _resolved(raw).items()}
    comp = defaultdict(lambda: [0, 0])
    for pid, v in orig.items():
        r, par = uf.find(("p", pid))
        comp[r][par ^ v] += 1                   # root value that keeps this port unchanged
    root_val = {r: (0 if c[0] >= c[1] else 1) for r, c in comp.items()}
    orders = {}
    for pid in orig:
        r, par = uf.find(("p", pid))
        orders[pid] = root_val[r] ^ par
    units = {}
    for n in list(uf.par):
        if n[0] == "u":
            r, par = uf.find(n)
            units[n[1:]] = root_val.get(r, 0) ^ par
    return True, orders, units, None


def bound_rtl(raw, tn, rtl_dirs):
    """normalized bound partition RTL of type tn (comments, blank lines and the module name removed) or None."""
    import re
    mod = raw["partition_types"][tn].get("module", tn)
    for d in rtl_dirs or ():
        for cand in (f"{mod}.sv", f"{mod}__{tn}.sv", f"{tn}.sv"):
            f = Path(d) / cand
            if f.exists():
                txt = f.read_text(errors="replace")
                txt = re.sub(r"//.*", "", txt).replace(mod, "__MOD__")
                return [ln.rstrip() for ln in txt.splitlines() if ln.strip()], str(f)
    return None


def rtl_compare(raw, a, b, rtl_dirs):
    """-> dict(status same / differs / n/a, lines, files)."""
    ra, rb = bound_rtl(raw, a, rtl_dirs), bound_rtl(raw, b, rtl_dirs)
    if ra is None or rb is None:
        return dict(status="n/a")
    if ra[0] == rb[0]:
        return dict(status="same", files=[ra[1], rb[1]])
    import difflib
    d = [ln for ln in difflib.unified_diff(ra[0], rb[0], lineterm="", n=0)
         if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    return dict(status="differs", lines=len(d), files=[ra[1], rb[1]], example=d[:4])


def analyze(raw, fix_order=False, rtl_dirs=None, plan_only=False):
    """-> report dict: exact groups (MERGE / GEOM-BLOCKED / RTL-DIFFERS), strap candidates, ft-population families.
    fix_order: allow merges that need a die-wide bit-order repair (order_solve); rtl_dirs: bound partition RTL dirs,
    a member whose bound netlist differs from its canonical's is not merged unless plan_only."""
    T = raw["partition_types"]
    I = Iface(raw)
    if fix_order:
        _, ok0, why0 = order_system(raw, {p["name"]: (p["type"], p.get("orient", "R0")) for p in raw["partitions"]},
                                    {})
        if not ok0:
            fix_order = False                    # the plan's own orders are not a consistent system: no repair
    by = defaultdict(list)
    for tn, t in T.items():
        by[netlist_key(t)].append(tn)
    groups = []
    accepted = {}                                # member -> (canon, moves) across all groups (die-wide order system)
    for k, tns in by.items():
        if len(tns) < 2:
            continue
        tns = sorted(tns, key=lambda n: (-len(I.inst[n]), n))
        canon = tns[0]
        g = dict(canon=canon, members=[], blocked=[])
        heads = [canon]
        for m in tns[1:]:
            done = False
            reasons = []
            for h in heads:
                rc = rtl_compare(raw, h, m, rtl_dirs)
                if rc["status"] == "differs" and not plan_only:
                    reasons.append(f"vs {h}: bound RTL differs ({rc['lines']} lines, e.g. {rc['example'][:2]})")
                    continue
                ok, moves, why = try_merge(I, h, m, fix_order)
                if not ok:
                    reasons.append(f"vs {h}: {why}")
                    continue
                reorder = None
                if fix_order:
                    trial = dict(accepted)
                    trial[m] = (h, moves)
                    ok2, orders, _, why2 = order_solve(raw, trial)
                    if not ok2:
                        reasons.append(f"vs {h}: bit-order repair conflicts at {why2}")
                        continue
                    res = _resolved(raw)
                    reorder = sum(1 for pid, o in orders.items() if o != res[pid][1])
                accepted[m] = (h, moves)
                g["members"].append(dict(type=m, into=h, instances={p: list(v) for p, v in moves.items()},
                                         orient_changes=sum(1 for v in moves.values() if v[0] != v[1]),
                                         rtl=rc, reordered_ports_total=reorder))
                done = True
                break
            if not done:
                g["blocked"].append(dict(type=m, reason="; ".join(reasons)))
                heads.append(m)
        g["types_before"] = len(tns)
        g["types_after"] = len(heads)
        g["all"] = tns
        groups.append(g)
    groups.sort(key=lambda g: g["canon"])
    # strap candidates: equal without contents params, unequal with
    strap = []
    byp = defaultdict(list)
    for tn, t in T.items():
        byp[netlist_key(t, params=False)].append(tn)
    for k, tns in byp.items():
        sub = {netlist_key(T[n]) for n in tns}
        if len(tns) > 1 and len(sub) > 1:
            strap.append(dict(types=sorted(tns), param_variants=len(sub),
                              params=_param_diff([T[n] for n in sorted(tns)])))
    # ft-population families: equal without ft slots, unequal with
    ftpop = []
    byf = defaultdict(list)
    for tn, t in T.items():
        byf[netlist_key(t, slots=False)].append(tn)
    for k, tns in byf.items():
        sub = {netlist_key(T[n]) for n in tns}
        if len(tns) > 1 and len(sub) > 1:
            sl = [sorted((s["width"], s.get("stations", 1)) for s in T[n].get("ft_slots", [])) for n in tns]
            ftpop.append(dict(types=len(tns), slot_signatures=len(sub), example=sorted(tns)[:4],
                              slots_min=min(len(x) for x in sl), slots_max=max(len(x) for x in sl),
                              ft_bits_min=sum(w for w, _ in min(sl, key=lambda x: sum(w for w, _ in x))),
                              ft_bits_max=sum(w for w, _ in max(sl, key=lambda x: sum(w for w, _ in x)))))
    before = len(T)
    after = before - sum(len(g["members"]) for g in groups)
    return dict(schema="opentallas.die_plan.dedup.v1", die=raw["die"]["name"], types_before=before,
                types_after=after, partitions=len(raw["partitions"]), fix_order=fix_order, plan_only=plan_only,
                rtl_dirs=[str(d) for d in rtl_dirs or ()],
                exact_groups=groups, strap_candidates=strap, ft_population=ftpop)


def _param_diff(ts):
    """{inst: {param: [values per type]}} for params that vary across the types."""
    out = {}
    per = [{c["inst"]: c.get("params", {}) for c in t.get("contents", [])} for t in ts]
    for inst in sorted(per[0]):
        keys = set().union(*(set(p.get(inst, {})) for p in per))
        for k in sorted(keys):
            vals = [p.get(inst, {}).get(k) for p in per]
            if len({_canon(v) for v in vals}) > 1:
                out.setdefault(inst, {})[k] = vals
    return out


def plan_digest(raw):
    return hashlib.sha256(_canon(raw).encode()).hexdigest()[:16]


def apply(raw, rep=None, only=None):
    """new plan with every MERGE member re-typed to its canonical type and removed (and, for a fix_order report, the
    port / type orders of the die-wide bit-order repair); the input is untouched."""
    rep = rep or analyze(raw)
    new = copy.deepcopy(raw)       # provenance goes to a sidecar (the plan schema has no free top-level keys)
    parts = {p["name"]: p for p in new["partitions"]}
    merged = {}
    sel = {}
    for g in rep["exact_groups"]:
        if only and g["canon"] not in only:
            continue
        for m in g["members"]:
            sel[m["type"]] = (m["into"], {p: tuple(v) for p, v in m["instances"].items()})
    reordered, touched = [], set()
    if rep.get("fix_order") and sel:
        ok, orders, units, why = order_solve(raw, sel)
        if not ok:
            raise ValueError(f"bit-order repair conflicts: {why}")
        res = _resolved(raw)
        for pr in new["ports"]:
            o = "lsb_high" if orders[pr["id"]] else "lsb_low"
            if res[pr["id"]][1] != orders[pr["id"]]:
                reordered.append(pr["id"])
                if all(k in pr for k in ("face", "layers", "window_um")):
                    pr["order"] = o          # port-declared geometry; type-derived ports follow their type's unit
                for side in ("src", "dst"):
                    pn = pr[side]["part"]
                    if pn != DIE_PART and parts[pn]["type"] not in sel:   # a merged instance takes its canon's table
                        touched.add(parts[pn]["type"])
        for (tn, key), v in units.items():
            if tn in sel or tn not in new["partition_types"]:
                continue
            t = new["partition_types"][tn]
            kind, name = key.split(":", 1)
            o = "lsb_high" if v else "lsb_low"
            if kind == "slot":
                for s_ in t.get("ft_slots", []):
                    if s_["name"] == name and s_.get("order", "lsb_low") != o:
                        s_["order"] = o
                        touched.add(tn)
            else:
                for b in t.get("buses", []):
                    if b["name"] == name and all(k in b for k in ("window_um", "face", "layers")) and \
                            b.get("order", "lsb_low") != o:
                        b["order"] = o
                        touched.add(tn)
    for mt, (into, moves) in sel.items():
        for part, (o0, o1) in moves.items():
            assert parts[part]["type"] == mt and parts[part].get("orient", "R0") == o0
            parts[part]["type"] = into
            parts[part]["orient"] = o1
        del new["partition_types"][mt]
        merged[mt] = dict(into=into, instances={p: list(v) for p, v in moves.items()})
    for tn, t in new["partition_types"].items():
        n = sum(1 for p in new["partitions"] if p["type"] == tn)
        if any(m["into"] == tn for m in merged.values()) and "note" in t:
            t["note"] = f"{t['note']} [TYPE-DEDUP: {n} instance(s) after merging " \
                        f"{sorted(k for k, m in merged.items() if m['into'] == tn)}]"
    prov = dict(schema="opentallas.die_plan.dedup_provenance.v1", source_digest=plan_digest(raw),
                types_before=len(raw["partition_types"]), types_after=len(new["partition_types"]), merged=merged,
                fix_order=bool(rep.get("fix_order")), reordered_ports=sorted(reordered),
                pin_table_touched_types=sorted(touched - set(sel)))
    new["note"] = (new.get("note", "") + f" [TYPE-DEDUP transform of plan {prov['source_digest']}: "
                   f"{prov['types_before']} -> {prov['types_after']} types, {len(reordered)} ports bit-order "
                   f"repaired; provenance in dedup_provenance.json]").strip()
    return new, prov


def verify(raw, new):
    """exactness of an applied merge.  The netlist is untouched (ports, lanes, latency, census: same ids, widths,
    ends); every port keeps its face, window, layers and its set of pin tracks (only a bit-order repair may permute
    bits within a port); every type's instances share one type-frame pin table; every rect is unchanged; the new plan
    validates.  -> list of problems (empty = exact)."""
    probs = []
    strip = lambda ps: [{k: v for k, v in p.items() if k != "order"} for p in ps]   # noqa: E731
    if _canon(strip(raw["ports"])) != _canon(strip(new["ports"])):
        probs.append("ports changed beyond bit order")
    for k in ("lanes", "latency", "census", "die", "clock", "reset"):
        if _canon(raw.get(k)) != _canon(new.get(k)):
            probs.append(f"{k} changed")
    probs += [f"validate: {e}" for e in S.validate(new)[:20]]
    A, B = Iface(raw), Iface(new)
    for pid in A.P.ports:
        pa, pb = A._pins(pid), B._pins(pid)
        if A.P.ports[pid].get("face") != B.P.ports[pid].get("face") or \
                sorted((ln, c) for _, ln, c in pa) != sorted((ln, c) for _, ln, c in pb):
            probs.append(f"port {pid}: die pin tracks differ")
    for tn, insts in B.inst.items():
        ref = B.type_table(sorted(insts)[0])
        for p in insts:
            if B.type_table(p) != ref:
                probs.append(f"type {tn}: {p} type-frame pin table differs from {sorted(insts)[0]}")
    old_rect = {p: A.P.rect(p) for p in A.P.parts}
    for p in B.P.parts:
        if B.P.rect(p) != old_rect[p]:
            probs.append(f"partition {p}: rect changed")
    return probs


# ------------------------------------------------------------------------- bound-netlist variants (kit count)
def _variant_cat(ln):
    import re
    if "ot_dp_dly" in ln or re.search(r"\bpd\d+_", ln):
        return "pad"            # R8 landing pad (as-built relative timing)
    if re.match(r"[+-]\s*(input|output)\s", ln):
        return "port_width"     # bound port narrowed to the bits this instance uses
    if "ot_dp_st" in ln:
        return "port_width"     # its boundary flop width
    if re.match(r"[+-]\s*wire\b", ln):
        return "wire"
    if re.match(r"[+-]\s*parameter\b", ln):
        return "param"
    return "other"


def variants(raw, rtl_dir):
    """bound partition modules per plan type (the real kit count) and what separates each variant from the type's
    first module: R8 pads, narrowed ports, params, other.  -> dict"""
    import difflib
    import re
    T = raw["partition_types"]
    mods = {t.get("module", tn): tn for tn, t in T.items()}
    groups = defaultdict(list)
    for f in sorted(Path(rtl_dir).glob("*.sv")):
        if f.name == "bind_cells.sv" or "bound_top" in f.name or "hard_models" in f.name:
            continue
        m = f.stem.split("__")[0]
        tn = mods.get(m) or mods.get(re.sub(r"_v\d+$", "", m)) or "?" + m
        groups[tn].append(f)

    def norm(f):
        t = f.read_text(errors="replace")
        mm = re.search(r"^module\s+(\w+)", t, re.M)
        t = re.sub(r"//.*", "", t)
        if mm:
            t = t.replace(mm.group(1), "__MOD__")
        return [ln.strip() for ln in t.splitlines() if ln.strip()]
    out = {}
    for tn, fs in sorted(groups.items()):
        base = norm(fs[0])
        diffs = []
        for f in fs[1:]:
            d = [ln for ln in difflib.unified_diff(base, norm(f), lineterm="", n=0)
                 if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
            c = defaultdict(int)
            for ln in d:
                c[_variant_cat(ln)] += 1
            cls = "identical" if not d else "+".join(sorted(k for k in c if k != "wire")) or "wire"
            diffs.append(dict(module=f.stem, lines=len(d), cats=dict(c), cls=cls))
        out[tn] = dict(modules=[f.stem for f in fs], diffs=diffs)
    return dict(die=raw["die"]["name"], rtl_dir=str(rtl_dir), plan_types=len(T), bound_modules=sum(
        len(v["modules"]) for v in out.values()), types_with_variants=sum(1 for v in out.values() if len(v["modules"]) > 1),
        by_class=_count_cls(out), types=out)


def _count_cls(out):
    c = defaultdict(int)
    for v in out.values():
        for d in v["diffs"]:
            c[d["cls"]] += 1
    return dict(c)


def summary_lines(rep):
    yield f"{rep['die']}: {rep['types_before']} types -> {rep['types_after']} (exact merges), " \
          f"{rep['partitions']} partitions"
    for g in rep["exact_groups"]:
        ms = ", ".join(f"{m['type']}->{m['into']}" + (f" ({m['orient_changes']} reorient)" if m["orient_changes"]
                                                       else "") + (f" [bound RTL {m['rtl']['status']}]")
                       for m in g["members"])
        bl = "; ".join(f"{b['type']}: {b['reason'][:300]}" for b in g["blocked"])
        yield f"  group {g['all']}: {g['types_before']} -> {g['types_after']}" + (f"  MERGE {ms}" if ms else "") + \
              (f"  GEOM-BLOCKED {bl}" if bl else "")
    for s in rep["strap_candidates"]:
        yield f"  STRAP candidate {s['types'][:6]}{'...' if len(s['types']) > 6 else ''} ({len(s['types'])} types, " \
              f"{s['param_variants']} param variants): {_canon(s['params'])[:160]}"
    for f in rep["ft_population"]:
        yield f"  FT-POP family {f['example']}... {f['types']} types, {f['slot_signatures']} slot populations, " \
              f"{f['slots_min']}-{f['slots_max']} slots, {f['ft_bits_min']}-{f['ft_bits_max']} ft bits"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("analyze")
    a1.add_argument("plan")
    a1.add_argument("--out")
    a3 = sub.add_parser("variants", help="bound partition modules per plan type and what separates them")
    a3.add_argument("plan")
    a3.add_argument("--rtl", help="bound RTL dir (default PLANDIR/bind/bound_r8/rtl)")
    a3.add_argument("--out")
    a2 = sub.add_parser("apply")
    a2.add_argument("plan")
    a2.add_argument("--out-plan", required=True)
    a2.add_argument("--report")
    a2.add_argument("--only", help="comma list of canonical types whose groups to merge (default all)")
    for x in (a1, a2):
        x.add_argument("--fix-order", action="store_true",
                       help="allow merges that need a die-wide bit-order repair of ports (same tracks, permuted bits)")
        x.add_argument("--bound-rtl", action="append", default=None,
                       help="bound partition RTL dir (default PLANDIR/bind/bound_r8/rtl when present); repeatable")
        x.add_argument("--no-rtl", action="store_true", help="skip the bound-RTL identity gate")
        x.add_argument("--plan-only", action="store_true",
                       help="merge plan-exact members even when their bound RTL differs (reported)")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    if a.cmd == "variants":
        d = Path(a.rtl) if a.rtl else Path(a.plan).resolve().parent / "bind" / "bound_r8" / "rtl"
        v = variants(raw, d)
        print(f"{v['die']}: {v['plan_types']} plan types -> {v['bound_modules']} bound modules "
              f"({v['types_with_variants']} types with variants); variant classes {v['by_class']}")
        for tn, x in v["types"].items():
            if x["diffs"]:
                print(f"  {tn}: {len(x['modules'])} modules: " + ", ".join(f"{d['module']} [{d['cls']}]"
                                                                        for d in x["diffs"]))
        if a.out:
            Path(a.out).write_text(json.dumps(v, indent=1) + "\n")
        return 0
    rtl = a.bound_rtl
    if rtl is None and not a.no_rtl:
        d = Path(a.plan).resolve().parent / "bind" / "bound_r8" / "rtl"
        rtl = [str(d)] if d.is_dir() else []
    rep = analyze(raw, a.fix_order, [] if a.no_rtl else rtl, a.plan_only)
    for ln in summary_lines(rep):
        print(ln)
    if a.cmd == "analyze":
        if a.out:
            Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
        return 0
    out = Path(a.out_plan)
    if out.resolve() == Path(a.plan).resolve():
        print("dedup apply: refusing to overwrite the input plan (opt-in transform: write a copy)")
        return 2
    new, prov = apply(raw, rep, set(a.only.split(",")) if a.only else None)
    probs = verify(raw, new)
    rep["verify"] = prov["verify"] = dict(exact=not probs, problems=probs[:50])
    out.write_text(json.dumps(new, indent=1) + "\n")
    (out.parent / "dedup_provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"wrote {out}: {prov['types_before']} -> {prov['types_after']} types, {len(prov['reordered_ports'])} ports "
          f"bit-order repaired, {len(prov['pin_table_touched_types'])} other types' pin tables touched; verify "
          f"{'EXACT' if not probs else 'FAIL: ' + '; '.join(probs[:5])}")
    return 0 if not probs else 1


if __name__ == "__main__":
    sys.exit(main())
