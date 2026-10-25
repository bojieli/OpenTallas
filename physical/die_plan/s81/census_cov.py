#!/usr/bin/env python3
"""S81 census coverage (GEOM-REVIEW2 06:34 rule): as-built inter-partition bits vs planned lane bits.

As-built source = the FT census of the bound die netlist (s81_lanes.tsv: one row per driver bus -> sink bus, endpoints
traced through relays/landing cells by tools/die_feedthrough).  Landing cells (ld_*) are collapsed onto their source.
Every as-built endpoint instance is mapped to its plan GROUP (the as-built block the plan partitions re-derive: a frame,
a slice half, an svc column = rsv pair + ctrl pair + etap pair + irg, a unit, a SerDes, the PHY).  A census row whose two
groups differ must be carried by plan lanes between the two groups with >= the as-built width.
dropped = sum over group pairs of max(0, as-built bits - planned bits); clock/reset rows are replaced by the plan's
spine + per-partition reset sync and are reported, not counted.  Rows whose endpoint maps to no partition are ERRORS
(every instance maps to a partition).

usage: census_cov.py PLAN.json INSTANCE_MAP.json CENSUS.tsv [--out OUT.json]
"""
import argparse
import os
import collections
import csv
import json
import re
import sys


def group_of_inst(inst):
    """as-built instance -> plan group name (None if unmapped)."""
    if inst.startswith("u_"):
        b = inst[2:]
    else:
        return None
    m = re.match(r"(rsv|ctrl|etap)_(\d+)$", b)
    if m:
        return "svc_%d" % (int(m.group(2)) // 2)
    m = re.match(r"irg_(\d+)$", b)
    if m:
        return "svc_%d" % int(m.group(1))
    return b          # f_0L01, s_0N, seqhost, lk_WN0, phy_hbm, gunit, ...


IMAP = {}


def node_of_inst(inst, bus):
    """v3 plans (instance_map has inst_part/slice_part): the PARTITION an as-built endpoint lands in (finer than its
    group: the svc pair is two partitions, a slice's external lanes end at its hub C, lep SerDes rx/tx at LP)."""
    if "inst_part" not in IMAP:
        return group_of_inst(inst)
    if inst in IMAP["inst_part"]:
        return IMAP["inst_part"][inst]
    if inst in IMAP["slice_part"]:
        sp = IMAP["slice_part"][inst]
        if sp["LP"] and re.match(IMAP.get("lp_bus_re", r"(rx|tx)\d$"), bus or ""):
            return sp["LP"]
        return sp["C"]
    return group_of_inst(inst)


def group_of_part(part, fmap):
    if "inst_part" in IMAP and not re.match(r"f[WE]\d_p\d_b\d$", part):
        return part
    m = re.match(r"(f[WE]\d_p\d)_b\d$", part)
    if m:
        return "f_" + fmap[m.group(1)][2:] if fmap[m.group(1)].startswith("f_") else fmap[m.group(1)]
    m = re.match(r"(s_\d[NS])_g\d+$", part)
    if m:
        return m.group(1)
    m = re.match(r"(svc_\d)_q\d$", part)
    if m:
        return m.group(1)
    return part


def collapse_landing(rows):
    """census rows with ld_* endpoints -> source-to-sink rows (a landing cell repeats its single source)."""
    into = collections.defaultdict(list)
    for r in rows:
        if r["dst"].startswith("ld_") and r["kind"] != "reset":
            into[r["dst"]].append(r)
    out, unresolved = [], []
    for r in rows:
        if r["dst"].startswith("ld_"):
            continue
        s = r["src"]
        seen = 0
        while s.startswith("ld_") and seen < 16:
            ins = into.get(s, [])
            srcs = {i["src"] for i in ins}
            if len(srcs) != 1:
                unresolved.append((r["src"], r["dst"], r["bits"], sorted(srcs)))
                break
            s = srcs.pop()
            seen += 1
        rr = dict(r)
        if s != r["src"]:
            rr["src_bus"] = "%s/%s" % (r["src"], r["kind"])   # every ld output is "o": key by landing cell + kind
        rr["src"] = s
        out.append(rr)
    return out, unresolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("imap")
    ap.add_argument("census")
    ap.add_argument("--out")
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    IMAP.update(json.load(open(a.imap)))
    fmap = IMAP["frames"]
    rows = list(csv.DictReader(open(a.census), delimiter="\t"))
    ports = {p["id"]: p for p in plan["ports"]}
    parts = {p["name"] for p in plan["partitions"]}
    groups_planned = {group_of_part(p, fmap) for p in parts}
    # planned bits per (src group, dst group); lanes inside a group are the split's own traffic
    planned = collections.Counter()
    cls_of, retopo = {}, {}
    internal = collections.Counter()
    for ln in plan["lanes"]:
        if not ln["ports"]:
            continue
        p0, p1 = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        gs, gd = group_of_part(p0["src"]["part"], fmap), group_of_part(p1["dst"]["part"], fmap)
        if gs == gd:
            internal[gs.split("_")[0] if not gs.startswith("s_") else "slice"] += p0["width"]
            continue
        if "inst_part" in IMAP and re.match(r"(dn|up|kd|ku)_", ln["id"]):
            internal["slice_split"] += p0["width"]      # C <-> leaf / LP lanes: the slice's own band split
            continue
        wb = int(ln.get("word_bits", p0["width"])) if ln.get("beats") else p0["width"]   # DEC12 2-beat lanes
        planned[(gs, gd)] += wb
        cls_of[ln["id"]] = (gs, gd, wb)
    # re-topologised broadcast: the plan chains x through the frame relay port xo (u_xo0..3 relay x -> xo in
    # col_h9/h10_l4_lp); as-built drives frame p2 from the slice directly.  x content reaching fB over a planned
    # xo lane fA -> fB counts as delivered from the slice that feeds fA (extra hop is in the latency table).
    xin = collections.defaultdict(collections.Counter)
    for lid, (gs, gd, w) in cls_of.items():
        if lid.startswith("x_"):
            xin[gd][gs] += w
    for _ in range(4):
        for lid, (gs, gd, w) in cls_of.items():
            if lid.startswith("xo_"):
                for s_, w_ in list(xin[gs].items()):
                    if s_.startswith("s_") and xin[gd][s_] < w_:
                        xin[gd][s_] = w_
    for fB, src in xin.items():
        for s_, w_ in src.items():
            if (s_, fB) not in planned:
                retopo[(s_, fB)] = w_
    for k, w_ in retopo.items():
        planned[k] += w_
    rows2, unresolved = collapse_landing(rows)
    # S81/H4 10-24: retired V-rung units (gen_plan_v4.RETIRED_RUNG: bk_col) -> the direct slice <-> slice rung
    retired = {"u_bk_col": {"vo_n": "u_s_1S", "vo_s": "u_s_1N"}}
    rows2 = [dict(r, src=retired[r["src"]][r["src_bus"]], src_bus="vo") if r["src"] in retired else r
             for r in rows2 if r["dst"] not in retired]
    asb = collections.Counter()
    seen_bus = {}
    clkrst = collections.Counter()
    unmapped = collections.Counter()
    die_io = collections.Counter()
    for r in rows2:
        b = int(r["bits"])
        if r["kind"] == "reset" or r["src"] == "PORT" and r["src_bus"] in ("rst_n", "clk"):
            clkrst[r["kind"]] += b
            continue
        if r["src"] == "PORT" or r["dst"] == "PORT":
            die_io[r["kind"]] += b
            continue
        gs, gd = node_of_inst(r["src"], r["src_bus"]), node_of_inst(r["dst"], r["dst_bus"])
        if gs is None or gd is None or gs not in groups_planned or gd not in groups_planned:
            unmapped[(r["src"], r["dst"])] += b
            continue
        if gs == gd:
            continue
        # the census tracer emits a src-bus x dst-bus cross product when several buses share one relay bundle
        # (e.g. seqhost t_host/t_kd/mu_c/mu_rc -> s_7N): count each driver bus once per sink instance
        key = (r["src"], r["src_bus"], r["dst"])
        if b > seen_bus.get(key, 0):
            asb[(gs, gd)] += b - seen_bus.get(key, 0)
            seen_bus[key] = b
    # S81-P6 10-23: frame-band lanes vs the band RTL census (inputs/frame_band_census.json, frame_band_census.py)
    fbc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "frame_band_census.json")
    fbc = json.load(open(fbc_path))["masters"] if os.path.exists(fbc_path) else None
    ptype = {p["name"]: p["type"] for p in plan["partitions"]}
    fband = collections.defaultdict(dict)
    for ln in plan["lanes"]:
        if not ln["id"].startswith("fi_") or not ln["ports"]:
            continue
        p0 = ports[ln["ports"][0]]
        sp, dp = p0["src"]["part"], ports[ln["ports"][-1]]["dst"]["part"]
        mod = plan["partition_types"][ptype[sp]]["contents"][0]["module"]          # col_h10_l4_lp.r0
        m = re.match(r"col_(h\d+)_l4_lp[._]r(\d)", mod).group(1)   # col_h10_l4_lp.r0 (v4.2) or col_h10_l4_lp_r0[_nx] (v4.3 plan contents)
        fband[(sp.rsplit("_b", 1)[0], m)]["r%s->r%s" % (sp[-1], dp[-1])] = p0["width"]
    fb_drop = []
    for (fr, m), got in sorted(fband.items()):
        for k, need in (fbc or {}).get(m, {}).items():
            if got.get(k, 0) < need:
                fb_drop.append(dict(frame=fr, master=m, pair=k, band_rtl=need, planned=got.get(k, 0)))
    pairs = []
    dropped = sum(x["band_rtl"] - x["planned"] for x in fb_drop)
    for k, b in asb.items():
        p = planned.get(k, 0)
        d = max(0, b - p)
        dropped += d
        pairs.append(dict(src=k[0], dst=k[1], asbuilt=b, planned=p, dropped=d))
    extra = {"%s->%s" % k: v for k, v in planned.items() if k not in asb}
    pairs.sort(key=lambda x: -x["dropped"])
    res = dict(
        asbuilt_inter_group_bits=sum(asb.values()), planned_inter_group_bits=sum(planned.values()),
        covered_bits=sum(asb.values()) - dropped, dropped_bits=dropped,
        dropped_pairs=[p for p in pairs if p["dropped"]],
        clock_reset_replaced=dict(clkrst), die_io_bits=dict(die_io),
        unmapped=[dict(src=k[0], dst=k[1], bits=v) for k, v in unmapped.items()],
        unresolved_landing=unresolved,
        planned_only_pairs=extra, retopo_x_via_xo_bits=sum(retopo.values()), retopo_pairs=len(retopo), split_internal_lane_bits=dict(internal),
        census_rows=len(rows), group_pairs=len(asb),
        frame_band=dict(source=fbc_path if fbc else None, frames=len(fband), dropped=fb_drop[:50], dropped_bits=sum(x["band_rtl"] - x["planned"] for x in fb_drop)))
    js = json.dumps(res, indent=1)
    if a.out:
        open(a.out, "w").write(js)
    print(json.dumps({k: v for k, v in res.items() if k not in ("dropped_pairs", "planned_only_pairs")}, indent=1)[:4000])
    print("dropped pairs (top 25):")
    for p in res["dropped_pairs"][:25]:
        print("  %-12s -> %-12s asbuilt %6d planned %6d dropped %6d" % (p["src"], p["dst"], p["asbuilt"], p["planned"],
                                                                        p["dropped"]))
    print("planned-only pairs:", len(extra))
    return 0 if dropped == 0 and not unmapped else 1


if __name__ == "__main__":
    sys.exit(main())
