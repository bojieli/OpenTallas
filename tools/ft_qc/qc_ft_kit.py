#!/usr/bin/env python3
"""FT-QC (FT-PLAN, owner-approved 2026-10-23): derive a Qwen compute cluster kit under the NEW die contract from an
existing CB8/CB16 cluster kit (default qfd_c_b8_rgm_c1, the only cluster lineage that fits the 2445 x 5227 die slot).

Contract deltas (everything else -- RTL fabric, A0 children, stations, rings, ports, clocks, cycles -- unchanged):
  1. RESET: the per-region die reset pins rst_c<c>r<r> (8 on CB8, 16 on CB16) are replaced by ONE landed pin rst_n
     (S face, at the old rst_c0r0 pin).  An in-cluster registered reset tree (module qfd_c_ft_rst_tree, instance
     u_rst) carries it to every region's existing pin register u_fab.u_rpin_<q>: one chain per region, every hop
     <= HOP_UM pin to pin, each flop clocked by the region it sits in, ALL chains exactly D flops long (equal age).
     Region q therefore releases exactly D edges after rst_n where the die used to release all regions on one calendar
     edge: rst_n release age to every in-region sink = D + 1 (rpin) + the unchanged in-region tree.  The die carries
     one reset sink per cluster instead of 8/16 (no channel repeater/pad field; QDIE-R56 in-block reset plan item 3).
  2. LAYERS: signals M2-M7 (unchanged); PG top M7: the cluster's PG pins are its M7 stripes (pitch 10.8, offset 1.0);
     NO M8 stripes, no M7->M8 child strap.  The hard children's own M7 PG stripes are exported as cluster PG pins and
     strapped by the die M8 grid directly (pg_contract "m7_passthrough"); M8/M9 are the die's (die + ft wires).
  3. FEEDTHROUGH: none needed for data on the Qwen compute die (results/arch/ft_qc_1023/r50_lane_stages_1000.json:
     45 of 48 clusters carry 0 ft bits; the column bus bc->bco / rs_i->rs_o is already an in-cluster registered
     feedthrough).  The kit records the per-cluster ft census it was derived from.

Outputs: RTL (rtl/physical/qcluster/<top>_cf.sv), site file (physical/qcluster/<top>_sites.tsv), regions SDC
(physical/qcluster/<top>_regions.sdc), kit spec (physical/ref_tile/<name>/spec.json) and a reset-tree record
(results/arch/ft_qc_1023/<name>_reset_tree.json).  Run tools/ref_tile/ref_tile.py gen on the kit afterwards.
"""
import argparse
import json
import math
import re
from pathlib import Path

HOP_UM = 400.0          # in-cluster reach (signals <= M7: the 405-um M4-M7 reach rule)


A0_W, A0_H = 820.8, 907.2


def region_of(x, y, tiles, ncol):
    """clock region (c, r) of a point: column = nearest A0 tile-column centre, row = A0 tile-row band (boundaries
    halfway through each inter-row gap).  Works for CB8 (2 x 4) and CB16 (4 x 4)."""
    cols = sorted({t[0] for t in tiles})
    c = min(range(len(cols)), key=lambda i: (abs(cols[i] + A0_W / 2 - x), i))
    rows = sorted({t[1] for t in tiles})
    bounds = [(rows[i] + A0_H + rows[i + 1]) / 2 for i in range(len(rows) - 1)]
    return c, sum(1 for b in bounds if y >= b)


def chain_points(path, n):
    """n points evenly along a polyline (excluding the start, including the end)."""
    seg = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    L = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in seg)
    out = []
    for k in range(1, n + 1):
        t = L * k / n
        for a, b in seg:
            l = abs(b[0] - a[0]) + abs(b[1] - a[1])
            if t <= l + 1e-9:
                f = t / l if l else 0.0
                out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                break
            t -= l
    return out, L


def plan_tree(rpins, land, corridor_x, edge_x, H, tiles, ncol):
    """per region an L/U path in the std-cell corridors: S band -> (W edge | E edge | nearest inter-column corridor)
    -> region pin.  corridor_x: list of inter-column corridor centre lines."""
    plans = {}
    sband_y = land[1]
    for q, (x, y) in sorted(rpins.items()):
        if y < 400:                                    # S band regions: straight along the S band
            path = [land, (x, sband_y)]
        elif x < 200:                                  # W edge regions
            path = [land, (edge_x[0], sband_y), (edge_x[0], y), (x, y)]
        elif x > edge_x[1] - 100:                      # E edge regions
            path = [land, (edge_x[1], sband_y), (edge_x[1], y), (x, y)]
        else:                                          # interior / N band: up the nearest inter-column corridor
            cx = min(corridor_x, key=lambda c: abs(c - x))
            path = [land, (cx, sband_y), (cx, y), (x, y)]
        plans[q] = path
    lens = {q: sum(abs(p[i + 1][0] - p[i][0]) + abs(p[i + 1][1] - p[i][1]) for i in range(len(p) - 1))
            for q, p in plans.items()}
    D = max(max(1, math.ceil(L / HOP_UM)) for L in lens.values())
    tree = {}
    for q, path in plans.items():
        need = max(1, math.ceil(lens[q] / HOP_UM))
        pts, _ = chain_points(path, need)
        # never on the region pin register's own site (its compact block): step 4.32 um aside
        x, y = rpins[q]
        pts = [(px + 4.32, py) if abs(px - x) < 1 and abs(py - y) < 1 else (px, py) for px, py in pts]
        # equal depth: the D - need extra stages sit at the destination (same region clock, 1-um apart)
        # (offset 4.32 um in x from the region pin register so the stacks never share its compact block)
        pts += [(pts[-1][0] + 4.32, pts[-1][1] + 0.27 * (k + 1)) for k in range(D - need)]
        tree[q] = [dict(k=k, x=round(p[0], 3), y=round(p[1], 3), clk=f"ck_c{region_of(p[0], p[1], tiles, ncol)[0]}"
                        f"r{region_of(p[0], p[1], tiles, ncol)[1]}") for k, p in enumerate(pts)]
        # the last stage must sit in the destination region (it feeds that region's pin register)
        tree[q][-1]['clk'] = f"ck_{q}"
    return D, plans, lens, tree


def gen_tree_rtl(regions, tree, D, modname):
    L = [f"// GENERATED by tools/ft_qc/qc_ft_kit.py -- do not edit.  FT-QC in-cluster reset tree (FT-PLAN item 4):",
         f"// rst_n -> one registered chain per clock region, every chain exactly D = {D} flops (equal release age),",
         "// each flop on the clock of the region it sits in (neighbour-region hops are ordinary XCLK paths, STA-timed).",
         f"module {modname} (",
         "    input  wire rst_n,"]
    L += [f"    input  wire ck_{q}," for q in regions]
    L += [f"    output wire rst_{q}{',' if i < len(regions) - 1 else ''}" for i, q in enumerate(regions)]
    L += [");"]
    L.append("    // pin register (FT-PLAN pin-register rule): rst_n lands once on the S-face region clock")
    L.append(f"    wire r_land;  qfd_q3h_stn #(.W(1), .N(1)) u_land (.ck(ck_{regions[0]}), .d(rst_n), .q(r_land));")
    for q in regions:
        prev = "r_land"
        for st in tree[q]:
            n = f"r_{q}_{st['k']}"
            L.append(f"    wire {n};  qfd_q3h_stn #(.W(1), .N(1)) u_{q}_{st['k']} (.ck({st['clk']}), .d({prev}), .q({n}));"
                     f"   // ({st['x']:.1f}, {st['y']:.1f})")
            prev = n
        L.append(f"    assign rst_{q} = {prev};")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default='.')
    ap.add_argument('--src-kit', default='physical/ref_tile/qfd_c_b8_rgm_c1')
    ap.add_argument('--name', default='qfd_c_b8_ft1')
    ap.add_argument('--top', default='qfd_c_b8_ft')
    ap.add_argument('--tag', default='ft1')
    a = ap.parse_args()
    R = Path(a.repo)
    src = json.loads((R / a.src_kit / 'spec.json').read_text())
    old_top = src['top']
    rtl_src = [p for p in src['sources'] if p.endswith('_cf.sv')][0]
    rtl = (R / rtl_src).read_text()
    regions = [p[len('rst_'):] for p in src['reset_ports']]          # c0r0 ...
    regions = sorted(regions, key=lambda q: (int(q[1]), int(q[3])))
    ncol = 1 + max(int(q[1]) for q in regions)
    tiles = [tuple(c['at']) for c in src['children'] if re.fullmatch(r'u_t_\d+_\d+', c['inst'])]
    W, H = src['outline']['w'], src['outline']['h']
    # region pin-register sites from the source site file
    sites_src = R / src['orfs_vars']['OT_QC_SITES']
    sites_txt = sites_src.read_text()
    rpins = {}
    for ln in sites_txt.splitlines():
        m = re.match(r'u_fab\.u_rpin_(c\dr\d)\t([\d.]+)\t([\d.]+)', ln)
        if m:
            rpins[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    assert set(rpins) == set(regions), (sorted(rpins), regions)
    land = rpins['c0r0']
    land = (land[0] + 21.6, land[1])                                  # beside the old c0r0 pin register
    xs = sorted({t[0] for t in tiles})
    corridor_x = [(xs[i] + A0_W + xs[i + 1]) / 2 for i in range(len(xs) - 1)]   # inter-column corridor centres
    edge_x = (86.4, W - 86.4)
    D, plans, lens, tree = plan_tree(rpins, land, corridor_x, edge_x, H, tiles, ncol)

    # ---- RTL: rename the top, rst_<q> ports -> rst_n + u_rst tree
    tree_mod = f"{a.top}_rst_tree"
    new = rtl.replace(f"module {old_top} (", f"module {a.top} (", 1)
    assert new != rtl
    for i, q in enumerate(regions):
        pat = f"    input  wire rst_{q},\n"
        assert new.count(pat) >= 2, q                                # fabric + top
        # only the TOP's port list (second occurrence)
        first = new.index(pat)
        second = new.index(pat, first + 1)
        new = new[:second] + ("    input  wire rst_n,\n" if i == 0 else "") + new[second + len(pat):]
    top_start = new.index(f"module {a.top} (")
    body_start = new.index(");\n", top_start) + 3
    decl = "".join(f"    wire rst_{q};\n" for q in regions)
    inst = (f"    {tree_mod} u_rst (.rst_n(rst_n), " + ", ".join(f".ck_{q}(ck_{q})" for q in regions) + ", "
            + ", ".join(f".rst_{q}(rst_{q})" for q in regions) + ");\n")
    new = new[:body_start] + "    // FT-QC: in-cluster reset tree (one landed rst_n per cluster)\n" + decl + inst + new[body_start:]
    hdr = (f"// FT-QC 2026-10-23: derived from {rtl_src} by tools/ft_qc/qc_ft_kit.py -- do not edit.\n"
           f"// Top {old_top} -> {a.top}: per-region die reset pins replaced by one rst_n + {tree_mod} (D = {D}).\n")
    new = hdr + new + "\n" + gen_tree_rtl(regions, tree, D, tree_mod)
    out_rtl = Path('rtl/physical/qcluster') / f"{a.top}_cf.sv"
    (R / out_rtl).write_text(new)

    # ---- sites: source sites + one compact block per tree flop (5-column line: prefix x y xlo xhi)
    lines = [f"# FT-QC qc_ft_kit.py: {sites_src.name} + in-cluster reset tree flops (u_rst.u_land + u_rst.u_<q>_<k>, D = {D})"]
    lines += [ln for ln in sites_txt.splitlines()]
    lines.append(f"u_rst.u_land\t{land[0]:.3f}\t{land[1]:.3f}\t{land[0] - 15:.3f}\t{land[0] + 15:.3f}")
    for q in regions:
        for st in tree[q]:
            lines.append(f"u_rst.u_{q}_{st['k']}\t{st['x']:.3f}\t{st['y']:.3f}\t{max(0.0, st['x'] - 15):.3f}\t"
                         f"{min(W, st['x'] + 15):.3f}")
    out_sites = Path('physical/qcluster') / f"{a.top}_sites.tsv"
    (R / out_sites).write_text("\n".join(lines) + "\n")

    # ---- regions SDC: drop the per-region reset port constraints (rst_n is timed by the kit's reset_ports rule)
    sdc_src = [p for p in src['sdc_extra'] if p.endswith('_regions.sdc')][0]
    sdc = (R / sdc_src).read_text()
    out = []
    for ln in sdc.splitlines():
        if re.search(r'get_ports \{rst_c\dr\d\}', ln):
            continue
        ln = re.sub(r'(?<=[{ ])rst_c\dr\d in ck_c\dr\d ?', '', ln)
        out.append(ln)
    out_sdc = Path('physical/qcluster') / f"{a.top}_regions.sdc"
    (R / out_sdc).write_text(f"# FT-QC: {sdc_src} minus the per-region reset ports (one rst_n per cluster)\n"
                             + "\n".join(out) + "\n")

    # ---- spec
    s = json.loads(json.dumps(src))
    s['name'], s['top'] = a.name, a.top
    s['sources'] = [str(out_rtl) if p == rtl_src else p for p in s['sources']]
    s['sdc_extra'] = [str(out_sdc) if p == sdc_src else p for p in s['sdc_extra']]
    s['orfs_vars'] = dict(s['orfs_vars'], OT_QC_SITES=str(out_sites))
    s['reset_ports'] = ['rst_n']
    old_rst = [f"rst_{q}" for q in regions]
    for f in s['pins']:
        s['pins'][f] = [('rst_n' if p == 'rst_c0r0' else p) for p in s['pins'][f] if p == 'rst_c0r0' or p not in old_rst]
    s['pin_layers'] = {('rst_n' if k == 'rst_c0r0' else k): v for k, v in s['pin_layers'].items() if k not in old_rst[1:]}
    s['pin_ranges'] = {('rst_n' if k == 'rst_c0r0' else k): v for k, v in s['pin_ranges'].items() if k not in old_rst[1:]}
    s['pg_contract'] = 'm7_passthrough'
    s['reset_landing'] = {"enable": False, "reason": f"FT-QC: rst_n lands in u_rst (qfd_q3h_stn on ck_c0r0) and fans out "
                          f"through equal-depth D={D} region chains to the existing u_fab.u_rpin_<q> registers"}
    s['structural_change'] = (
        f"FT-QC 10-23 {a.name} = {src['name']} under the FT-PLAN die contract: (1) reset: {len(regions)} die reset pins "
        f"-> 1 rst_n + in-cluster equal-depth tree (pin landing + D={D} hops <= {HOP_UM:.0f} um, per-region clocks; release age D+2); (2) PG top M7 "
        "pins (m7_passthrough: no M8 stripes, children M7 PG exported for the die M8 grid), signals M2-M7, M8/M9 die-only; "
        "(3) no data feedthrough needed (column bus already in-cluster registered ft). Same fabric RTL, A0 stand-ins, "
        "stations, rings, ports (minus resets), clocks and data cycles. Base: " + src['structural_change'][:600])
    s['job'] = dict(s['job'], owner='Claude:FT-QC', branch='claude/ft-qc-1023', tag=a.tag,
                    purpose=f"FT-QC pilot (FT-PLAN): {src['name']} + one-pin in-cluster reset tree + PG<=M7 contract; "
                            "diagnostic A0 stand-ins (as the base); gate only, no submit",
                    submit=False, hold_merge='FT-QC pilot: diagnostic A0 STAND-IN, CB8/CB16 ruling pending COORD')
    kit = R / 'physical/ref_tile' / a.name
    kit.mkdir(parents=True, exist_ok=True)
    (kit / 'spec.json').write_text(json.dumps(s, indent=1) + "\n")
    rec = dict(schema='opentallas.ft_qc.reset_tree.v1', kit=a.name, base=src['name'], top=a.top, D=D, hop_um=HOP_UM,
               landing=land, region_pins=rpins, path_um={q: round(v, 1) for q, v in lens.items()},
               stages={q: len(tree[q]) for q in regions}, tree=tree,
               release_age_edges=f"rst_n -> landing (1) + chain (D) + region pin register (1) = {D + 2} edges, equal for every region; in-region trees unchanged",
               die_reset_sinks_per_cluster=dict(before=len(regions), after=1))
    out_rec = Path('results/arch/ft_qc_1023') / f"{a.name}_reset_tree.json"
    (R / out_rec).parent.mkdir(parents=True, exist_ok=True)
    (R / out_rec).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(D=D, path_um=rec['path_um'], rtl=str(out_rtl), sites=str(out_sites), sdc=str(out_sdc),
                          kit=str(kit))))


if __name__ == '__main__':
    main()
