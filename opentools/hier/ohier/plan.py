"""Build a hierarchical plan: regions, pins, budgets (shared plan schema)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import budget as B
from . import emit as E
from . import partition as P
from . import pins as PI
from . import schema as S


@dataclass
class Options:
    k: int = 4
    cap_cells: int = 400_000
    unit_max_cells: int = 0          # 0 -> total / (3k)
    balance_eps: float = 0.3
    max_net_degree: int = 64
    clock_ports: tuple = ("clk",)
    period_ps: float = 1000.0
    latency_ps: float = 100.0        # common partition clock insertion target
    io_budget_ps: float = 0.0        # chip IO: external portion (from the design SDC)
    util: float = 0.55               # std-cell utilization inside a partition
    macro_pad: float = 0.25          # extra area per macro (halo / channels)
    channel_um: float = 4.0          # top-level channel between partitions
    macro_halo_um: float = 4.0       # macro halo (fit check and partition MACRO_PLACE_HALO)
    die_margin_um: float = 5.0       # top core margin (IO ring, top PDN ring)
    grid_um: float = 1.08            # snap region corners (ASAP7: 4 x 0.27 rows, 20 x 0.054 sites)
    pin_pitch_um: float = 0.192
    pin_margin_um: float = 1.2
    ps_per_um: float = 1.0           # repeated-wire delay estimate
    setup_margin_ps: float = 0.0
    max_aspect: float = 3.0          # slot aspect limit while growing the core
    block_margin_um: float = 1.08    # partition core margin inside its outline (macro fit check)


def _snap_dn(v, g):
    return math.floor(v / g + 1e-9) * g


def _snap_up(v, g):
    return math.ceil(v / g - 1e-9) * g


def leaf_groups(nl, region_map):
    """Longest-prefix match of each leaf's hierarchical name against the region members."""
    pref = sorted(((m, gi) for gi, r in enumerate(region_map) for m in r["members"]),
                  key=lambda t: -len(t[0]))
    out = []
    for lf in nl.leaves:
        g = None
        for m, gi in pref:
            if lf.name == m or lf.name.startswith(m + "."):
                g = gi
                break
        out.append(g)
    return out


def build_plan(nl, libcells, lef_macros, o: Options, design=None, region_map=None, die_wh=None):
    """region_map: [dict(name, rect|None, partition|None, members[])] from schema.region_map();
    each map region becomes one partition (1 clock region == 1 partition).  Without it the
    regions come from connectivity clustering (K = o.k)."""
    total = len(nl.leaves)
    k_req = len(region_map) if region_map else o.k
    unit_max = o.unit_max_cells or max(1, total // (3 * k_req))
    lgroup = leaf_groups(nl, region_map) if region_map else None
    items, leaf_item = P.build_items(nl, libcells, unit_max, lgroup)
    clock_nets = set()
    for cp in o.clock_ports:
        if cp in nl.ports:
            clock_nets.update(b for b in nl.ports[cp]["bits"] if isinstance(b, int))
    adj, _ = P.item_graph(nl, leaf_item, clock_nets, o.max_net_degree)
    n_glue = 0
    if region_map:
        assign, n_glue = P.assign_from_map(items, adj, lgroup, k_req)
        moved = 0
        for g in range(k_req):
            c = sum(items[i]["cells"] for i, a in enumerate(assign) if a == g)
            if c > o.cap_cells:
                raise ValueError(f"region {region_map[g]['name']}: {c} cells > cap {o.cap_cells}")
    else:
        assign = P.cluster(items, adj, o.k, o.cap_cells, o.balance_eps)
        assign, moved = P.refine(items, adj, assign, o.k, o.cap_cells, o.balance_eps)
    leaf_part = [assign[leaf_item[li]] for li in range(total)]
    k = k_req if region_map else max(assign) + 1
    cut = P.cut_report(nl, leaf_item, assign, k, clock_nets)

    # region areas
    parts = []
    for p in range(k):
        std = sum(items[i]["area"] for i in range(len(items)) if assign[i] == p)
        mac = [li for i in range(len(items)) if assign[i] == p for li in items[i]["macros"]]
        mac_dims = []
        mac_area = 0.0
        for li in mac:
            m = lef_macros.get(nl.leaves[li].type)
            if m:
                mac_dims.append((m.width, m.height))
                mac_area += m.width * m.height
        halo = o.macro_halo_um
        mac_fp = sum((w + 2 * halo) * (h + 2 * halo) for w, h in mac_dims)
        area = std / o.util + mac_fp * (1 + o.macro_pad)
        # the channel is carved out of each region: add it back
        side = math.sqrt(area)
        area_ch = (side + o.channel_um) ** 2
        parts.append({"id": p, "area_um2": area_ch, "std_area": std, "macro_area": mac_area,
                      "macro_dims": mac_dims, "macros": mac,
                      "cells": sum(items[i]["cells"] for i in range(len(items)) if assign[i] == p)})
    conn = {}
    for key, v in cut["pairs"].items():
        a, b = map(int, key.split("-"))
        conn[(a, b)] = v
    m = _snap_up(o.die_margin_um, o.grid_um)
    if region_map and all(r.get("rect") for r in region_map):
        # the map's rectangles are binding (die coordinates); only snap them inward
        if not die_wh:
            raise ValueError("region map with rects needs die {w, h}")
        die = (0.0, 0.0, float(die_wh[0]), float(die_wh[1]))
        regions = {}
        for p, r in enumerate(region_map):
            x0, y0, x1, y1 = r["rect"]
            regions[p] = (round(_snap_up(x0, o.grid_um), 3), round(_snap_up(y0, o.grid_um), 3),
                          round(_snap_dn(x1, o.grid_um), 3), round(_snap_dn(y1, o.grid_um), 3))
        feasible = all(P.shelf_fit(parts[p]["macro_dims"], regions[p], 2 * o.block_margin_um,
                                   o.macro_halo_um) for p in range(k))
    else:
        # grow the core until every hard macro fits its region and no slot is skinnier than
        # max_aspect (max 3x side)
        base = math.sqrt(sum(p["area_um2"] for p in parts)) * 1.05
        for step in range(41):
            core = _snap_up(base * (1 + 0.05 * step), o.grid_um)
            rects, feasible = P.floorplan(parts, conn, core, core,
                                          channel=o.channel_um + 2 * o.grid_um + 2 * o.block_margin_um,
                                          halo=o.macro_halo_um)
            asp = max(max((r[2] - r[0]) / max(r[3] - r[1], 1e-6), (r[3] - r[1]) / max(r[2] - r[0], 1e-6))
                      for r in rects.values())
            if feasible and asp <= o.max_aspect:
                break
        rects, _ = P.floorplan(parts, conn, core, core, channel=o.channel_um)
        die = (0.0, 0.0, core + 2 * m, core + 2 * m)
        regions = {}
        for p, (x0, y0, x1, y1) in rects.items():
            regions[p] = (round(_snap_up(x0 + m, o.grid_um), 3), round(_snap_up(y0 + m, o.grid_um), 3),
                          round(_snap_dn(x1 + m, o.grid_um), 3), round(_snap_dn(y1 + m, o.grid_um), 3))

    # ports and pins
    part_ports, net_parts, port_names = E.partition_ports(nl, leaf_part, k)
    pnets = nl.port_nets()
    clock_names = set()
    targets = {}
    for p in range(k):
        for net, (nm, d) in part_ports[p].items():
            t = [q for q in net_parts[net] if q != p]
            if net in pnets:
                t.append("IO")
            targets[(p, nm)] = t
            if net in clock_nets:
                clock_names.add(nm)
    pins = PI.assign_pins(regions, targets, die, pitch=o.pin_pitch_um, margin=o.pin_margin_um,
                          clock_ports=clock_names)
    pin_xy = {(d["region"], d["port"]): d["xy_um"] for d in pins}
    for d in pins:
        d["net"] = None
    name_net = {nm: net for net, nm in port_names.items()}
    for d in pins:
        d["net"] = name_net.get(d["port"])

    # budgets
    arr, req, driver = B.levelize(nl, libcells)
    crossings = {}
    for net, parts_of in net_parts.items():
        if len(parts_of) < 2 or net in clock_nets:
            continue
        li = driver.get(net)
        if li is None:
            continue          # driven by chip input: IO budget
        src = leaf_part[li]
        crossings[net] = (src, [q for q in parts_of if q != src])

    def wire_ps(net):
        src, dsts = crossings[net]
        nm = port_names[net]
        a = pin_xy.get((src, nm))
        worst = 0.0
        for q in dsts:
            b = pin_xy.get((q, nm))
            if a and b:
                worst = max(worst, abs(a[0] - b[0]) + abs(a[1] - b[1]))
        return worst * o.ps_per_um

    budgets = B.make_budgets(crossings, arr, req, o.period_ps, o.latency_ps, wire_ps,
                             o.setup_margin_ps)
    for b in budgets:
        b["port"] = port_names[b["net"]]

    plan = S.new_plan(design or nl.top)
    plan["die"] = {"bbox_um": list(die), "core_margin_um": m}
    plan["clocks"] = [{"name": "clk", "port": cp, "period_ps": o.period_ps,
                       "region_latency_target_ps": o.latency_ps} for cp in o.clock_ports
                      if cp in nl.ports]
    plan["macros"] = [{"inst": nl.leaves[li].name, "master": nl.leaves[li].type, "region": p["id"]}
                      for p in parts for li in p["macros"]]
    for p in parts:
        rid = p["id"]
        rm = region_map[rid] if region_map else {}
        plan["regions"].append({
            "id": rid, "kind": "partition", "clock_region": rid,
            "region_name": rm.get("name") or S.region_name(rid),
            "module": rm.get("partition") or f"{nl.top}_P{rid}", "bbox_um": list(regions[rid]),
            "cells": p["cells"], "std_area_um2": round(p["std_area"], 3),
            "macro_area_um2": round(p["macro_area"], 3),
            "macros": [nl.leaves[li].name for li in p["macros"]],
            "items": [items[i]["name"] for i in range(len(items)) if assign[i] == rid][:200],
            "n_items": sum(1 for a in assign if a == rid),
            "ports": len(part_ports[rid]),
            "util": round(p["std_area"] / max(1e-9, (regions[rid][2] - regions[rid][0]) *
                                              (regions[rid][3] - regions[rid][1]) - p["macro_area"]), 3),
        })
    plan["pins"] = pins
    plan["budgets"] = budgets
    plan["metrics"] = {"cells": total, "items": len(items), "unit_max_cells": unit_max,
                       "refine_moves": moved, "floorplan_macro_fit": feasible,
                       "mode": "region_map" if region_map else "cluster", "glue_items": n_glue, **cut}
    return plan, leaf_part, part_ports


def partition_sdcs(plan, part_ports, o: Options):
    """Return {rid: sdc text} from the plan budgets."""
    by_net = {b["net"]: b for b in plan["budgets"]}
    clock_ports = {d for c in plan["clocks"] for d in [c["port"]]}
    out = {}
    for r in plan["regions"]:
        rid = r["id"]
        bp = {}
        clock_port = None
        for net, (nm, d) in part_ports[rid].items():
            if nm in clock_ports or nm == "clk":
                clock_port = nm
                continue
            b = by_net.get(net)
            bp[nm] = ("in" if d == "input" else "out", b)
        out[rid] = B.partition_sdc(rid, clock_port or "clk", o.period_ps, o.latency_ps, bp,
                                   o.io_budget_ps)
    return out
