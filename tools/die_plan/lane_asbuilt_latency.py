#!/usr/bin/env python3
"""LATCHECK-1 11-12: AS-BUILT lane latency == latency table, on every plan lane of a bind (structural, no kit run).

The token schedule is static (no handshake): a lane that delivers on a different cycle than the latency table pairs the
wrong beat at the consumer.  The bind prices each lane in the table, but the KIT later inserts source-side stations
(kit_istations.py --apply: u_ist_<bus>_<j> before u_bout_<bus>) that a bind without kit_source_station_pricing has
ALREADY counted in the receiver pad (u_lpad_<bus> ot_dp_dly D).  The bind-only RTL (and the token sim run on it) cannot
see this: the lane is long by the kit's source count (QC cb lanes +2, HBM N4U_NE +9; COORD 11-12 15:29 ruling).

Per plan lane (spine lanes skipped), the delivered stage count is read from the BOUND RTL instances plus what the kit
WILL insert, predicted from the plan's internal_stations exactly as kit_istations.py does it:
  source  : u_bout_<o> (1; a registered hard pin = the macro register, 1) + u_bout_<o>_pad<j> + u_ist_<o>_<j> already
            in the bound RTL (native stations) + one core pin-face chain u_ist_<o>__<cores>_<g>_<j> (bound or kit)
            + KIT bus chain: depth(bus:<o>) - (pads + bound u_ist), never below 0
  ft      : u_ft_<ob>_<k> + u_fx_<ob>_<k> (cross-tap hop flops) in every feedthrough partition of the lane
  landing : the bound clock-landing cycles of the lane (sum over its crossings; a count-aligned ring is priced at its
            table K, never at its flop count)
  receiver: u_bin_<i> (1; registered hard pin 1) + u_bin_<i>_pad<j> + u_lpad_<i> D + bound u_ist_<i>_<j> + core chain
            + KIT bus chain: 0 when a packed u_lpad_<i> exists (kit_istations packed_input_delay absorbs the IN stations
            into the D registers), else depth(bus:<i>) - (pads + bound u_ist)
FAIL unless delivered == the plan latency table cycles (latency.lanes[lane].cycles).  An end whose partition module is
not in the bind RTL (dissolved / no generated module) is UNOBSERVED (listed, not a failure: nothing to count).

Wired into `bind.py bind` (every lane, one pass, LANE_ASBUILT errors; a strict bind fails on any).  Standalone, read-only
on an existing bind output dir:
  lane_asbuilt_latency.py BIND_DIR PLAN.json [--asbuilt MANIFEST] [--pricing as-bound|on] [--tsv OUT.tsv] [--json OUT]
--pricing on predicts the same bind with asbuilt kit_source_station_pricing true (receiver pad D - kit source depth,
native_istations.annotate_kit's rule) so an OFF bind shows what the switch would change.  Each FAIL carries a cause class (DOUBLE_PAD: kit source stations
also in the receiver pad; STALE_TABLE: latency row 'fixed' != the lane's fixed_cycles; UNPRICED_KIT_STATIONS: the excess
is kit-inserted stations the lane's fixed_cycles never priced; OTHER).
Exit 0 PASS, 4 FAIL, 5 no failure but some lane UNOBSERVED, 1 no bound top (EMIT stopped)."""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

INST_RX = re.compile(r"^[ \t]*(\w+)[ \t]*(#\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?\s*(u_(?:bout|bin|lpad|ist|ft|fx|rs)_\w+)\s*\(",
                     re.M)
D_RX = re.compile(r"\.D\(\s*(\d+)\s*\)")
HDR_RX = re.compile(r"partition type (\S+?)\.\s")
MOD_RX = re.compile(r"^\s*module\s+(\w+)", re.M)


def sv_id(s):
    """gen_rtl.sv_id (kept local so the CLI runs from a lone copy)"""
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


class ModuleIndex:
    """the lane-stage instances of one bound partition module: name -> (master, D)"""

    def __init__(self, text):
        self.inst = {}
        for m in INST_RX.finditer(text):
            d = D_RX.search(m.group(2) or "")
            self.inst[m.group(3)] = (m.group(1), int(d.group(1)) if d else None)
        self._chains = None

    def has(self, name):
        return name in self.inst

    def pads(self, side, n):
        rx = re.compile(rf"u_b{side}_{re.escape(n)}_pad(\d+)")
        return sorted(int(m.group(1)) for k in self.inst for m in [rx.fullmatch(k)] if m)

    def ist(self, n):
        rx = re.compile(rf"u_ist_{re.escape(n)}_(\d+)")
        return sorted(int(m.group(1)) for k in self.inst for m in [rx.fullmatch(k)] if m)

    def core_chain_depth(self, n):
        """deepest per-core pin-face chain u_ist_<n>__<tag>_<j> (every chain of one bus has one depth)"""
        rx = re.compile(rf"u_ist_{re.escape(n)}__(\w+)_(\d+)")
        by = defaultdict(set)
        for k in self.inst:
            m = rx.fullmatch(k)
            if m:
                by[m.group(1)].add(int(m.group(2)))
        return max((len(v) for v in by.values()), default=0)

    def lpad(self, n):
        v = self.inst.get(f"u_lpad_{n}")
        return None if v is None else int(v[1] or 0)

    def ft(self, o):
        rx = re.compile(rf"u_f[tx]_{re.escape(o)}_(\d+)")
        return sum(1 for k in self.inst if rx.fullmatch(k))


def kit_depth(typ, bus):
    """kit_istations.py chain depths of bus:<bus> on a plan type -> (bus chain depth, core pin-face chain depth).
    Bus chain = the deepest non-core entry (bus_entries merges per-core rows; bit_route / exact rows of one conn extend
    one chain to the deepest); core chains (entries with 'core') all carry one depth (core_pin_stations)."""
    rows = [e for e in (typ or {}).get("internal_stations", []) if e.get("conn") == "bus:" + bus]
    return (max((len(e.get("regs_um", [])) for e in rows if not e.get("core")), default=0),
            max((len(e.get("regs_um", [])) for e in rows if e.get("core")), default=0))


def side_stages(ix, typ, bus, side, reg_hard, lpad_override=None):
    """-> (stages, detail dict, problems) of one lane end ('out' = source, 'in' = receiver)"""
    n = sv_id(bus)
    io = "out" if side == "out" else "in"
    det, prob = {}, []
    face = 1 if (reg_hard or ix.has(f"u_b{io}_{n}")) else 0
    if not face:
        prob.append(f"no u_b{io}_{n} face register")
    pads = ix.pads(io, n)
    ist = ix.ist(n)
    if ist and ist != list(range(len(ist))):
        prob.append(f"u_ist_{n}_* not a contiguous chain {ist[:6]}")
    lp = ix.lpad(n) if side == "in" else None
    if lpad_override is not None:
        lp = lpad_override
    lp = lp or 0
    bound_core = ix.core_chain_depth(n)
    kdep, kcore = (0, 0) if reg_hard else kit_depth(typ, bus)
    kit_core = 0 if bound_core else kcore
    have = len(pads) + len(ist)
    if side == "in" and lp:
        kit_bus = 0                                  # packed receiver delay absorbs the IN stations (packed_input_delay)
    else:
        kit_bus = max(0, kdep - have)
        if kdep and have > kdep:
            prob.append(f"bound {have} pad/station stages > {kdep} planned (kit_istations refuses)")
    det.update(face=face, pads=len(pads), bound_ist=len(ist), core_chain=bound_core or kit_core, lpad=lp,
               kit_ist=kit_bus + kit_core)
    return face + len(pads) + len(ist) + (bound_core or kit_core) + lp + kit_bus, det, prob


def plan_hops(plan):
    """lane id -> [(ft partition, out bus)] from the plan's port chain"""
    ports = {x["id"]: x for x in plan.get("ports", [])}
    out = {}
    for ln in plan.get("lanes", []):
        hp = [ports[q] for q in ln.get("ports", []) if q in ports]
        out[ln["id"]] = [(x["dst"]["part"], y["src"]["bus"]) for x, y in zip(hp, hp[1:])]
    return out


def kit_source_pricing(typ, bus, lane_fixed, native_src):
    """the receiver pad cut native_istations.annotate_kit applies with kit_source_station_pricing on (0 = none)"""
    if native_src:
        return 0
    n = kit_depth(typ, bus)[0]
    return n if n and lane_fixed >= n else 0


def source_cut(ms, typ, bus_out, lane_fixed):
    """the kit source stations a kit_source_station_pricing bind cut from this lane's receiver pad: the lane's source
    bus chain depth unless the source stations are native (u_ist_<o>_* already in the bound source module)"""
    return kit_source_pricing(typ, bus_out, lane_fixed, bool(ms is not None and ms.ist(sv_id(bus_out))))


def source_cuts(plan, rows, module_of, ptype_of, types, sel=True):
    """VERIFY-PRICING-1 11-12: {(source partition, bus_out): (cut, lane)} for a bind made with asbuilt
    kit_source_station_pricing = sel (true, or a type list; split variants follow split_of).  The same station source
    and rule as check(), so bind verify credits exactly the stations this check counts as kit-inserted at the source."""
    if not sel:
        return {}
    only = None if sel is True else set(sel)
    fixed = {x["id"]: int(x.get("fixed_cycles", 0) or 0) for x in plan.get("lanes", [])}
    out = {}
    for r in rows:
        lane = r.get("lane")
        if not lane:
            continue
        st = ptype_of(r["src"])
        typ = types.get(st)
        if only is not None and st not in only and (typ or {}).get("split_of") not in only:
            continue
        ms = module_of(r["src"])
        if ms is None:
            continue
        md = module_of(r["dst"])
        if md is not None and md.has(f"u_rs_{sv_id(r['bus_in'])}"):
            continue                                 # reset spine (ot_dp_rsync): no lane latency
        n = source_cut(ms, typ, r["bus_out"], fixed.get(lane, 0))
        if n:
            out[(r["src"], r["bus_out"])] = (n, lane)
    return out


def check(plan, rows, module_of, ptype_of, types, landing_of, *, spine=(), pricing=None):
    """rows: bind_latency buses (lane, src, dst, bus_out, bus_in, macro_pin_reg_ends?); module_of(part) -> ModuleIndex
    or None; ptype_of(part) -> plan type name; types: type name -> plan type; landing_of(lane) -> bound landing cycles.
    pricing: None = count the receiver pad as bound; "on" = predict kit_source_station_pricing true on a bind made
    without it (pad D - kit source depth); "off" = predict it false on a bind made with it (pad = table - boundary - ft
    - landing - native source stations, as lane_pad() without the kit term).  -> (records, errors)"""
    table = plan.get("latency", {}).get("lanes", {})
    fixed = {x["id"]: int(x.get("fixed_cycles", 0) or 0) for x in plan.get("lanes", [])}
    hops = plan_hops(plan)
    recs, errs = [], []
    for r in rows:
        lane = r.get("lane")
        if not lane or lane in spine:
            continue
        s, d = r["src"], r["dst"]
        ms, md = module_of(s), module_of(d)
        if md is not None and md.has(f"u_rs_{sv_id(r['bus_in'])}"):
            continue                                 # reset spine (ot_dp_rsync): no lane latency
        reg = set(r.get("macro_pin_reg_ends") or ())
        st, dt = ptype_of(s), ptype_of(d)
        rec = dict(lane=lane, src=s, src_type=st, bus_out=r["bus_out"], dst=d, dst_type=dt, bus_in=r["bus_in"],
                   table=int(table.get(lane, {}).get("cycles", r.get("plan_cycles", 2))),
                   bind_plan_cycles=r.get("plan_cycles"))
        if ms is None or md is None:
            rec.update(verdict="UNOBSERVED", why="no bound module for " + ", ".join(
                p for p, m in ((s, ms), (d, md)) if m is None))
            recs.append(rec)
            continue
        probs = []
        sn, sdet, p1 = side_stages(ms, types.get(st), r["bus_out"], "out", "src" in reg)
        ft = 0
        for part, ob in hops.get(lane, []):
            mf = module_of(part)
            if mf is None:
                probs.append(f"ft partition {part}: no bound module")
                continue
            ft += mf.ft(sv_id(ob))
        land = int(landing_of(lane) or 0)
        cut = source_cut(ms, types.get(st), r["bus_out"], fixed.get(lane, 0))
        override = None
        lp = md.lpad(sv_id(r["bus_in"]))
        if pricing == "on" and cut and lp is not None:
            override = max(0, lp - cut)
        elif pricing == "off" and cut:
            override = max(0, rec["table"] - 2 - ft - land - sdet["bound_ist"])
        if pricing:
            rec["pricing_cut"] = cut
        dn, ddet, p2 = side_stages(md, types.get(dt), r["bus_in"], "in", "dst" in reg, override)
        probs += [f"src {x}" for x in p1] + [f"dst {x}" for x in p2]
        tot = sn + ft + land + dn
        rec.update(source=sdet, receiver=ddet, ft=ft, landing=land, delivered=tot, delta=tot - rec["table"],
                   verdict="PASS" if tot == rec["table"] and not probs else "FAIL")
        if probs:
            rec["problems"] = probs
        if rec["verdict"] == "FAIL":
            # cause class (report only; the gate is delivered == table):
            #  DOUBLE_PAD   kit source stations also counted in the receiver pad (kit_source_station_pricing off)
            #  STALE_TABLE  latency-table row 'fixed' != the lane's fixed_cycles (table not regenerated)
            cls = []
            if cut and sdet["kit_ist"] and ddet["lpad"] and rec["delta"] == min(cut, ddet["lpad"]):
                cls.append("DOUBLE_PAD")
            trow = table.get(lane)
            if trow is not None and int(trow.get("fixed", 0) or 0) != fixed.get(lane, 0):
                cls.append("STALE_TABLE")
            if not cls and 0 < rec["delta"] <= sdet["kit_ist"] + ddet["kit_ist"]:
                cls.append("UNPRICED_KIT_STATIONS")      # kit stations the table (lane fixed_cycles) never priced
            rec["class"] = cls or ["OTHER"]
            errs.append(f"LANE_ASBUILT {lane}: delivered {tot} != latency table {rec['table']} ({rec['delta']:+d}; "
                        f"src {s}.{r['bus_out']} face {sdet['face']} pads {sdet['pads']} ist {sdet['bound_ist']} "
                        f"core {sdet['core_chain']} kit {sdet['kit_ist']} + ft {ft} + landing {land} + dst {d}.{r['bus_in']} "
                        f"face {ddet['face']} pads {ddet['pads']} ist {ddet['bound_ist']} core {ddet['core_chain']} "
                        f"lpad D{ddet['lpad']} kit {ddet['kit_ist']})" + (f" [{'; '.join(probs)}]" if probs else ""))
        recs.append(rec)
    return recs, errs


def summary(recs):
    c = Counter(r["verdict"] for r in recs)
    return dict(lanes=len(recs), passed=c.get("PASS", 0), failed=c.get("FAIL", 0), unobserved=c.get("UNOBSERVED", 0),
                delta=dict(sorted(Counter(r["delta"] for r in recs if r["verdict"] == "FAIL").items())),
                classes=dict(Counter("+".join(r["class"]) for r in recs if r["verdict"] == "FAIL")),
                verdict="FAIL" if c.get("FAIL") else "INCOMPLETE" if c.get("UNOBSERVED") else "PASS")


# ---- in-bind hook (bind.py cmd_bind) ---------------------------------------------------------------------------------
def bind_check(B, out, lat):
    """run on the RTL this bind just emitted (out/rtl) -> (records, errors)"""
    rtl = Path(out) / "rtl"
    idx = {}

    def module_of(p):
        if p not in B.parts:
            return None
        mod = B.types.get(B.parts[p].get("type"), {}).get("module")
        if mod not in idx:
            f = rtl / f"{mod}.sv"
            idx[mod] = ModuleIndex(f.read_text()) if mod and f.is_file() else None
        return idx[mod]
    spine = {L["lane"] for L in B.links if L.get("spine") and L.get("lane")}
    land = defaultdict(int)
    for L in B.links:
        if L.get("lane"):
            land[L["lane"]] = max(land[L["lane"]], int(L.get("clock_landing_cycles", 0)))
    return check(B.plan, lat, module_of, lambda p: B.parts.get(p, {}).get("type"), B.types, land.get, spine=spine)


# ---- standalone CLI on a bind output dir ----------------------------------------------------------------------------
def load_bind_dir(bd, plan, plan_path=None):
    bd = Path(bd)
    rtl = bd / "rtl"
    mod_file, type_mod = {}, {}
    for f in rtl.glob("*.sv"):
        with open(f, errors="replace") as fh:
            head = fh.read(4096)
        h = HDR_RX.search(head)
        m = MOD_RX.search(head)
        if h and m:
            mod_file[m.group(1)] = f
            type_mod[h.group(1)] = m.group(1)
    top = next(rtl.glob("*_bound_top.sv"), None)
    part_mod = {}
    if top is not None:
        txt = top.read_text(errors="replace")
        for m in re.finditer(r"^[ \t]*(\w+)\s*(?:#\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*)?(\w+)\s*\(", txt, re.M):
            if m.group(1) in mod_file:
                part_mod[m.group(2)] = m.group(1)
    mod_type = {v: k for k, v in type_mod.items()}
    parts = plan["partitions"]
    parts = {p["name"]: p for p in parts} if isinstance(parts, list) else parts
    idx = {}

    if top is None:
        # an EMIT stop leaves no bound top: partition -> module is then unknown (split / canon types), refuse
        raise SystemExit(f"lane_asbuilt_latency: {rtl} has no *_bound_top.sv (the bind did not finish emitting); "
                         "nothing to check")

    def module_of(p):
        mod = part_mod.get(sv_id(p))
        if mod is None:
            return None
        if mod not in idx:
            idx[mod] = ModuleIndex(mod_file[mod].read_text(errors="replace"))
        return idx[mod]

    def ptype_of(p):
        mod = part_mod.get(sv_id(p))
        return mod_type.get(mod) or parts.get(p, {}).get("type")
    rep = json.loads((bd / "bind_report.json").read_text()) if (bd / "bind_report.json").is_file() else {}
    types = dict(plan["partition_types"])
    for sp in rep.get("type_splits") or []:          # bind-made split types inherit their base type's stations
        if isinstance(sp, dict) and sp.get("type") and sp.get("split_of") in types:
            types.setdefault(sp["type"], types[sp["split_of"]])
    for tn in list(mod_type.values()):
        if tn not in types:
            base = re.sub(r"_v\d+$", "", tn)
            if base in types:
                types[tn] = types[base]
    cl = next((p for p in (bd / "bind_clock_landings.json", bd.parent / "bind_clock_landings.json") if p.is_file()), None)
    land = defaultdict(int)
    if cl is not None:
        d = json.loads(cl.read_text())
        # QC-REGION-1 COUNT FRAME: the landing cycles must be in the plan's frame (clock.spine.feed); legacy = no-op
        import count_frame as CF
        try:
            CF.check_same(d.get("count_frame"), CF.load(plan, plan_path), f"{cl}")
        except CF.FrameError as ex:
            raise SystemExit(f"lane_asbuilt_latency: {ex}")
        if isinstance(d.get("lane_added_cycles"), dict):
            land.update({k: int(v) for k, v in d["lane_added_cycles"].items()})
        else:
            for q in d.get("ports", []):
                land[q["lane"]] += int(q.get("added_cycles", 0))
    rows = json.loads((bd / "bind_latency.json").read_text())["buses"]
    return rows, module_of, ptype_of, types, land.get, part_mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bind_dir")
    ap.add_argument("plan")
    ap.add_argument("--asbuilt", help="the bind's asbuilt manifest (reads kit_source_station_pricing for the report)")
    ap.add_argument("--pricing", choices=("as-bound", "on", "off"), default="as-bound",
                    help="as-bound, or predict the bind with kit_source_station_pricing on / off (needs --asbuilt)")
    ap.add_argument("--tsv")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    rows, module_of, ptype_of, types, landing_of, part_mod = load_bind_dir(a.bind_dir, plan, a.plan)
    ab = json.loads(Path(a.asbuilt).read_text()) if a.asbuilt else {}
    bound_sel = ab.get("kit_source_station_pricing")
    mode = None
    if a.pricing != "as-bound":
        if not a.asbuilt:
            raise SystemExit("lane_asbuilt_latency: --pricing on/off needs --asbuilt (the bind's switch state)")
        if bool(bound_sel) == (a.pricing == "on"):
            print(f"lane_asbuilt_latency: the bind already has kit_source_station_pricing {bool(bound_sel)}; = as bound")
        else:
            mode = a.pricing
    recs, errs = check(plan, rows, module_of, ptype_of, types, landing_of, pricing=mode)
    sm = summary(recs)
    sm.update(bind_dir=str(a.bind_dir), plan=str(a.plan), pricing=a.pricing, bound_pricing=bound_sel if a.asbuilt else "unknown",
              modules_indexed=len(set(part_mod.values())))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=sm, lanes=recs), indent=1) + "\n")
    if a.tsv:
        with open(a.tsv, "w") as f:
            f.write("lane\tsrc_type\tbus_out\tdst_type\tbus_in\ttable\tdelivered\tdelta\tsrc_kit_ist\tdst_lpad\tdst_kit_ist\tft\tlanding\tverdict\tclass\n")
            for r in recs:
                s, d = r.get("source", {}), r.get("receiver", {})
                f.write("\t".join(str(x) for x in (r["lane"], r["src_type"], r["bus_out"], r["dst_type"], r["bus_in"], r["table"],
                                                   r.get("delivered", ""), r.get("delta", ""), s.get("kit_ist", ""),
                                                   d.get("lpad", ""), d.get("kit_ist", ""), r.get("ft", ""), r.get("landing", ""),
                                                   r["verdict"], "+".join(r.get("class", [])))) + "\n")
    for e in errs:
        print(e)
    print("LANE_ASBUILT", json.dumps(sm))
    return 4 if errs else 5 if sm["unobserved"] else 0


if __name__ == "__main__":
    sys.exit(main())
