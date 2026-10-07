#!/usr/bin/env python3
"""DIE CLOCK PLAN and its die-level clock-only CTS validation (CLAUDE BUDGETS, 2026-10-06).

Plan (both dies; option C of results/uarch/rom_die_clocking_decision_20261003: mesochronous regions + forwarded link
clocks):
  root      the PLL outputs on the collective block (S81 sp_collective pll_stream / pll_serial / pll_hbm; HBM hb_coll
            pll_stream / pll_serial / pll_hbm / pll_link)
  trunk     one balanced buffered H-tree per domain on M8/M9 from the PLL to every die-tree sink: the region roots of
            the field (S81: the 128 column FIFOs dsfd_cfifo, whose `co` output is the column clock root), the hub /
            spine / band / service partitions, and the common-clock hub stations
  regions   S81: one tree per field column (cfifo co -> every element, cfg ROM, sequencer, bank, relay, return node and
            slot station of the column) on M6/M7;  HBM: the die trunks are cut into the clock regions of
            hbm_accel_die_fp.clock_regions (G* SM groups, HUB-C, HUB-Q*, SVC*)
  links     forwarded clocks (S81 fclk, HBM station segments) travel with their data; not CTS trees
The partition clock pin is the CTS sink (abstract + clock pin only: a DFF stand-in at the pin), so the insertion this
run reports at a sink IS the planned arrival at the partition entry; the block's own internal insertion is added on top
by the block and priced per interface in the budget sheet.

Modes
  emit   --die-model X.json.gz --name N --out DIR [--group trunk|region|all]   OpenROAD case (netlist, placement, CTS
         Tcl, SS / FF measurement Tcl, run.sh for docker on the compute host)
  record --die-model X.json.gz --case DIR [--case DIR2 ...] --out plan.json         plan record from the measured trees
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
SINK_CELL = 'DFFHQNx1_ASAP7_75t_R'
ROOT_CELL = 'BUFx24_ASAP7_75t_R'
BUF_LIST = 'BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R'
LAYERS = dict(trunk='M8 M9', region='M6 M7', htop='M8 M9', hreg='M6 M7')


def esc(s):
    return re.sub(r'[^A-Za-z0-9_]', '_', s)


def plan_groups(d):
    trees = C.clock_trees(d)
    groups = dict(trunk=[], region=[])
    for t, tr in trees.items():
        groups['region' if tr['cls'] == 'col_clock' else 'trunk'].append(t)
    return trees, groups


MAX_MERGE_UM = 5250.0         # merged region limit: the measured 60 ps H-tree extent (rom_die_clocking_decision)
MAX_REGION_UM = 4000.0        # a region's sink bbox side (option C: <= 5.25 mm measured 60 ps H-tree extent)


def plan_regions(d, trees, max_ext=MAX_REGION_UM, max_merge=None):
    """die-trunk sinks -> clock regions: the generator's region rect (HBM clock_regions; S81 spine / svc / band), split
    along the long axis at the median until no region's sink bbox side exceeds max_ext.  {tree: {region: [(inst, port,
    x, y)]}}"""
    max_merge = max_merge or MAX_MERGE_UM
    reg = C.sink_regions(d, trees)
    out = defaultdict(dict)
    for t, tr in trees.items():
        if tr['cls'] == 'col_clock':
            continue
        groups = defaultdict(list)
        for inst, port in dict.fromkeys(tr['sinks']):
            (x, y), _ = C.port_xy(d, d['by'][inst], port)
            rect = reg.get(inst, (t, f'{t}:die'))[1].split(':', 1)[1]     # rect part (a block on two trees: per tree)
            groups[f'{t}:{rect}'].append((inst, port, x, y))
        work = list(groups.items())
        done = {}
        while work:
            name, l = work.pop()
            xs, ys = [p[2] for p in l], [p[3] for p in l]
            dx, dy = max(xs) - min(xs), max(ys) - min(ys)
            if max(dx, dy) <= max_ext or len(l) < 2:
                done[name] = l
                continue
            k = 2 if dx >= dy else 3
            l = sorted(l, key=lambda p: p[k])
            h = len(l) // 2
            work += [(name + '.0', l[:h]), (name + '.1', l[h:])]
        out[t] = merge_regions(d, done, max_merge)
    return out


def merge_regions(d, regs, max_merge):
    """merge regions joined by synchronous die nets while the merged sink bbox side stays <= max_merge (the most
    connected pair first): every merge turns region-boundary crossings into intra-region hops"""
    where = {}
    for r, l in regs.items():
        for inst, port, x, y in l:
            where[inst] = r
    links = defaultdict(int)
    for bid, cls, bits, eps in d['buses']:
        if cls in ('clock', 'col_clock', 'clock_trunk', 'reset', 'reset_tree', 'col_reset', 'fclk', 'top_in'):
            continue
        a = where.get(eps[0][0])
        for e in eps[1:]:
            b = where.get(e[0])
            if a and b and a != b:
                links[tuple(sorted((a, b)))] += 1
    regs = {r: list(l) for r, l in regs.items()}
    alias = {r: r for r in regs}

    def find(r):
        while alias[r] != r:
            r = alias[r]
        return r

    def side(l):
        xs, ys = [p[2] for p in l], [p[3] for p in l]
        return max(max(xs) - min(xs), max(ys) - min(ys))
    for (a, b), n in sorted(links.items(), key=lambda kv: -kv[1]):
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        if side(regs[ra] + regs[rb]) <= max_merge:
            regs[ra] += regs.pop(rb)
            alias[rb] = ra
    return {(r if '+' not in r else r): l for r, l in regs.items()}


FAMILY_ROOTS = [True]
# HBM VM early branch (OWNER 2026-10-07, VM-split fallback): the VM region's trunk tap arrives EARLY_PS earlier than the
# tree's padded root instant; every HUB-V sink gets that much die pad (the VM tiles' deeper trees use it, the face
# stations take it as die-side delay).  Applied when the region root pad covers it.
# HBM hub early branch (coordinator 2026-10-07, r23 2x hub): the hub quarters hfd_su / hfd_sfu / hfd_hc are 5.53 mm tall
# against the 900 ps block-insertion target; the serial trunk taps every HUB-C sub-region 500 ps early (prefix key: the
# key applies to the region and to its '.'-suffixed sub-regions).
EARLY_PS = {'clk_stream:HUB-V': 300.0, 'clk_serial:HUB-C': 500.0}


def early_ps(r):
    for k_, v_ in EARLY_PS.items():     # HBM: sibling regions share their family root point (see clock_nets)
        if r == k_ or r.startswith(k_ + '.'):
            return v_
    return 0.0


def clock_nets(d, trees, groups, group):
    """[(clock name, root xy, [(inst, port, x, y)])] for the case group"""
    nets = []
    if group in ('trunk', 'region'):
        for t in groups[group]:
            tr = trees[t]
            (rx, ry), _ = C.port_xy(d, d['by'][tr['root'][0]], tr['root'][1])
            l = []
            for inst, port in dict.fromkeys(tr['sinks']):
                (x, y), _ = C.port_xy(d, d['by'][inst], port)
                l.append((inst, port, x, y))
            nets.append((t, (rx, ry), l))
        return nets
    R = plan_regions(d, trees)
    fam_root = {}
    if d.get('die') == 'hbm' and FAMILY_ROOTS[0]:
        # HBM r23 (die 30.6 mm wide, stream trunk 3.1 ns: sibling regions of one SM group (G<q>w / G<q>e) or one scan
        # quadrant (HUB-Q<q> cuts) diverged near the PLL, 150-160 ps): sibling regions share one root point (their
        # family's sink bbox centre), so the trunk is common down to the family and only the region trees differ
        for t, regs in R.items():
            fam = defaultdict(list)
            for r, sl in regs.items():
                rect = r.split(':', 1)[1] if ':' in r else r
                fk = re.sub(r'^(G[NS][EW])[we]$', r'\1', rect.split('.')[0])
                fam[fk] += [(r, p) for p in sl]
            for fk, l in fam.items():
                xs, ys = [p[2] for _, p in l], [p[3] for _, p in l]
                c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
                for r in {r for r, _ in l}:
                    fam_root[r] = c
    for t, regs in R.items():
        tr = trees[t]
        (rx, ry), _ = C.port_xy(d, d['by'][tr['root'][0]], tr['root'][1])
        if group == 'htop':      # PLL -> every region root (family members share ONE trunk sink at the family root)
            l, seen = [], {}
            for r, sl in regs.items():
                xs, ys = [p[2] for p in sl], [p[3] for p in sl]
                cx, cy = fam_root.get(r, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
                if r in fam_root:
                    k_ = (round(cx, 3), round(cy, 3))
                    if k_ in seen:
                        seen[k_][0] += '|' + r
                        continue
                    seen[k_] = [f'REGION:{r}', '', cx, cy]
                    l.append(seen[k_])
                else:
                    l.append([f'REGION:{r}', '', cx, cy])
            nets.append((t, (rx, ry), [tuple(x) for x in l]))
        else:                    # hreg: one tree per region from its root
            for r, sl in regs.items():
                xs, ys = [p[2] for p in sl], [p[3] for p in sl]
                nets.append((f'REGION:{r}', fam_root.get(r, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)), sl))
    return nets


def emit(a):
    d = C.load_die(a.die_model)
    trees, groups = plan_groups(d)
    nets = clock_nets(d, trees, groups, a.group)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    W, H = d['outline_um']
    v, place, sdc, sinks = [], [], [], []
    v.append('module ckplan (ref);\n  input ref;')
    n = 0
    for k, (t, (rx, ry), l) in enumerate(nets):
        rn = f'root_{esc(t)}'
        v.append(f'  wire ck_{k};')
        v.append(f'  {ROOT_CELL} {rn} (.A(ref), .Y(ck_{k}));')
        place.append(f'place_inst -name {rn} -location {{{min(max(rx, 1.0), W - 2):.3f} {min(max(ry, 1.0), H - 2):.3f}}} -status FIRM')
        sdc.append(f'create_clock -name {esc(t)} -period 833.333 [get_pins {rn}/Y]')
        for inst, port, x, y in l:
            x = min(max(x, 1.0), W - 2.0)
            y = min(max(y, 1.0), H - 2.0)
            sn = f's{n}'
            v.append(f'  {SINK_CELL} {sn} (.CLK(ck_{k}));')
            place.append(f'place_inst -name {sn} -location {{{x:.3f} {y:.3f}}} -status FIRM')
            sinks.append([sn, t, inst, port, round(x, 3), round(y, 3), True])
            n += 1
    v.append('endmodule')
    (out / 'ckplan.v').write_text('\n'.join(v) + '\n')
    (out / 'place.tcl').write_text('\n'.join(place) + '\n')
    (out / 'clocks.sdc').write_text('\n'.join(sdc) + '\n')
    lay = LAYERS.get(a.group, LAYERS['trunk'])
    (out / 'sinks.json').write_text(json.dumps(dict(die=d['die'], group=a.group, layers=lay,
                                                    trees=[x[0] for x in nets], sinks=sinks)) + '\n')
    common = f"""foreach l [glob {PLAT}/lib/NLDM/*RVT_%C%*] {{ read_liberty $l }}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
"""
    (out / 'cts.tcl').write_text(common.replace('%C%', 'SS') + f"""read_verilog /work/ckplan.v
link_design ckplan
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source /work/place.tcl
read_sdc /work/clocks.sdc
source {PLAT}/setRC.tcl
set_wire_rc -clock -layers {{{lay}}}
set_wire_rc -signal -layers {{M4 M5}}
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
mem loaded
set t0 [clock seconds]
clock_tree_synthesis -root_buf {ROOT_CELL} -buf_list {{{BUF_LIST}}} -sink_clustering_enable \\
  -distance_between_buffers {a.buffer_um}
puts "OT_TIME cts_s=[expr {{[clock seconds]-$t0}}]"
mem cts
write_db /work/cts.odb
exit
""")
    meas = r"""read_db /work/cts.odb
read_sdc /work/clocks.sdc
source %PLAT%/setRC.tcl
set_wire_rc -clock -layers {%LAY%}
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set f [open /work/tree_%C%.txt w]
proc drv_of {pin} {
  set net [get_nets -quiet -of_objects [get_pins $pin]]
  if {$net eq ""} { return "-" }
  foreach p [get_pins -quiet -of_objects $net -filter "direction==output"] { return [regsub {/[^/]+$} [get_full_name $p] {}] }
  return "-"
}
foreach c [get_cells *] {
  set ref [get_property $c ref_name]
  set n [get_name $c]
  if {[string match BUF* $ref] || [string match CKINV* $ref] || [string match INV* $ref]} {
    set y [lindex [get_pins -of_objects $c -filter "direction==output"] 0]
    set ai [lindex [get_pins -of_objects $c -filter "direction==input"] 0]
    puts $f "B $n [drv_of [get_full_name $ai]] [get_property $y arrival_max_rise] [get_property $y arrival_min_rise] $ref"
  } elseif {[string match DFF* $ref]} {
    set cp [get_pins $n/CLK]
    puts $f "S $n [drv_of $n/CLK] [get_property $cp arrival_max_rise] [get_property $cp arrival_min_rise]"
  }
}
close $f
exit
"""
    for corner in ('SS', 'FF'):
        (out / f'meas_{corner}.tcl').write_text(common.replace('%C%', corner) + meas.replace('%PLAT%', PLAT)
                                               .replace('%LAY%', lay).replace('%C%', corner))
    (out / 'run.sh').write_text(f"""#!/bin/bash
# clock-only die CTS case {a.name} ({a.group}); docker on the compute host, admission guard if present
set -o pipefail
D=$(cd "$(dirname "$0")" && pwd)
IMG=${{IMG:-openroad/orfs:latest}}
CPUS=${{CPUS:-8}}
run() {{ docker run --rm --name ckplan_{esc(a.name)}_$1 --cpus=$CPUS -v $D:/work -w /work $IMG bash -lc \\
  "/usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads $CPUS -no_init -exit /work/$1.tcl > /work/$1.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"; }}
date -u +%FT%TZ > $D/start
run cts && run meas_SS && run meas_FF
echo $? > $D/exit
date -u +%FT%TZ > $D/end
""")
    (out / 'run.sh').chmod(0o755)
    print(json.dumps(dict(case=str(out), trees=len(nets), sinks=len(sinks))))


# ------------------------------------------------------------------------------------------------ record
def read_tree(path, pfx):
    """tree_<C>.txt -> (parent, arrival): names prefixed per case (CTS buffer names repeat across cases)"""
    par, arr = {}, {}
    for line in Path(path).read_text().splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        try:
            arr[pfx + p[1]] = (float(p[3]), float(p[4]))
        except ValueError:
            continue
        par[pfx + p[1]] = pfx + p[2] if p[2] != '-' else '-'
    return par, arr


def stats(v):
    return dict(n=len(v), mean=round(sum(v) / len(v), 1), min=round(min(v), 1), max=round(max(v), 1)) if v else None


class Forest:
    """measured clock trees of one die: every sink with (tree, region, arrival SS/FF, ancestor chain), the
    hierarchical cases (htop + hreg) joined at the region roots"""

    def __init__(self, cases):
        self.cases, self.sinks, self.meta = {}, {}, []
        for c in cases:
            c = Path(c)
            sj = json.loads((c / 'sinks.json').read_text())
            g = sj['group']
            pfx = g + ':'
            p1, a1 = read_tree(c / 'tree_SS.txt', pfx)
            p2, a2 = read_tree(c / 'tree_FF.txt', pfx)
            self.cases[g] = (sj, p1, a1, a2)
            log = (c / 'cts.log').read_text() if (c / 'cts.log').exists() else ''
            self.meta.append(dict(case=str(c), group=g, sinks=len(sj['sinks']), layers=sj['layers'],
                                  clock_buffers=sum(1 for k in a1 if not re.match(r'[a-z]+:s\d+$', k) and ':root_' not in k),
                                  cts_s=int(m.group(1)) if (m := re.search(r'OT_TIME cts_s=(\d+)', log)) else None,
                                  max_rss_mb=round(int(m.group(1)) / 1024) if (m := re.search(r'Maximum resident set size \(kbytes\): (\d+)', log)) else None))
        top, pad = {}, {}
        if 'hreg' in self.cases:          # planned pads: every region root of a tree reaches its sinks at the tree's
            sj, par, ass, aff = self.cases['hreg']       # slowest region-tree insertion (the trunk delivers the pad)
            mean = defaultdict(list)
            for sn, t, inst, port, x, y, ex in sj['sinks']:
                if 'hreg:' + sn in ass and 'hreg:' + sn in aff:
                    mean[t].append((ass['hreg:' + sn][0], aff['hreg:' + sn][1]))
            rm = {t: (sum(v[0] for v in l) / len(l), sum(v[1] for v in l) / len(l)) for t, l in mean.items()}
            tree_max = defaultdict(lambda: (0.0, 0.0))
            for t, (a1, a2) in rm.items():
                tt = t[len('REGION:'):].split(':')[0]
                tree_max[tt] = (max(tree_max[tt][0], a1), max(tree_max[tt][1], a2))
            for t, (a1, a2) in rm.items():
                tt = t[len('REGION:'):].split(':')[0]
                pad[t[len('REGION:'):]] = (tree_max[tt][0] - a1, tree_max[tt][1] - a2)
        self.tree_lift = defaultdict(float)
        for tt_ in sorted({r_.split(':')[0] for r_ in pad}):   # early branches: the trunk taps these regions
            early = {r_: early_ps(r_) for r_ in pad if r_.split(':')[0] == tt_ and early_ps(r_)}   # EARLY_PS[r] earlier
            if not early:              # (their sinks get that much die pad for deeper block trees; flop alignment unchanged)
                continue
            lift = max(0.0, max(e_ - pad[r_][0] for r_, e_ in early.items()))   # the root pads do not cover it: the
            if lift:                   # whole tree's flop instant moves by `lift` (every region padded `lift` later)
                for o_ in list(pad):
                    if o_.split(':')[0] == tt_:
                        pad[o_] = (pad[o_][0] + lift, pad[o_][1] + lift * 0.53)
                self.tree_lift[tt_] += lift
            for r_, e_ in early.items():
                pad[r_] = (max(0.0, pad[r_][0] - e_), max(0.0, pad[r_][1] - e_ * 0.53))
        self.pad = pad
        if 'htop' in self.cases:
            sj, par, ass, aff = self.cases['htop']
            for sn, t, inst, port, x, y, ex in sj['sinks']:
                k = 'htop:' + sn
                for r_ in inst[len('REGION:'):].split('|'):     # a family sink serves every member region
                    top[r_] = (t, k)
        for g, (sj, par, ass, aff) in self.cases.items():
            if g == 'htop':
                continue
            for sn, t, inst, port, x, y, ex in sj['sinks']:
                k = g + ':' + sn
                if k not in ass:
                    continue
                if g == 'hreg':
                    r = t[len('REGION:'):]
                    tree, tk = top[r]
                    _, tp, tass, taff = self.cases['htop']
                    p1, p2 = pad.get(r, (0.0, 0.0))
                    off = tass[tk][0] + p1
                    chain = [(n_, ass[n_][0] + off) for n_ in self._up(par, k)]
                    chain += [(n_, tass[n_][0]) for n_ in self._up(tp, tk)]
                    self.sinks[(inst, port)] = dict(tree=tree, region=r, ss=ass[k][0] + off,
                                                    ff=aff[k][1] + taff[tk][1] + p2, chain=chain, pin_ss=ass[k][0], pad_ss=p1)
                else:
                    region = t if g == 'region' else t + ':flat'
                    self.sinks[(inst, port)] = dict(tree=t, region=region, ss=ass[k][0], ff=aff[k][1],
                                                    chain=[(n_, ass[n_][0]) for n_ in self._up(par, k)])
        self.top = top

    @staticmethod
    def _up(par, n):
        out = []
        while n in par and par[n] != '-' and len(out) < 400:
            n = par[n]
            out.append(n)
        return out

    def skew(self, a, b):
        """CRPR setup skew bound: |nominal| + OCV x (non-shared insertion of both sinks below their common point)"""
        A, B = self.sinks[a], self.sinks[b]
        cb = {n_: t for n_, t in B['chain']}
        ac = next((t for n_, t in A['chain'] if n_ in cb), 0.0)
        return abs(A['ss'] - B['ss']) + C.OCV * ((A['ss'] - ac) + (B['ss'] - ac)), abs(A['ss'] - B['ss'])


def record(a):
    d = C.load_die(a.die_model)
    trees = C.clock_trees(d)
    F = Forest(a.case)
    by_inst = defaultdict(list)
    for (inst, port), s_ in F.sinks.items():
        by_inst[inst].append((inst, port))
    pairs = {}
    fb_ = set(d.get('fclk_buses', []))
    for bid, cls, bits, eps in d['buses']:
        if cls in ('clock', 'col_clock', 'clock_trunk', 'reset', 'reset_tree', 'col_reset', 'fclk', 'top_in'):
            continue
        if bid in fb_:      # a forwarded-clock segment: the capture clock travels with the data (no tree pair)
            continue
        for e in eps[1:]:
            for sa in by_inst.get(eps[0][0], []):
                for sb in by_inst.get(e[0], []):
                    if sa != sb and F.sinks[sa]['tree'] == F.sinks[sb]['tree']:
                        pairs.setdefault(tuple(sorted((sa, sb))), cls)
    intra, inter, worst = defaultdict(list), defaultdict(list), []
    for (sa, sb), cls in pairs.items():
        sk, nom = F.skew(sa, sb)
        ra, rb = F.sinks[sa]['region'], F.sinks[sb]['region']
        (intra[ra] if ra == rb else inter[tuple(sorted((ra, rb)))]).append(sk)
        worst.append((sk, nom, f'{sa[0]}/{sa[1]}', f'{sb[0]}/{sb[1]}', ra, rb, cls))
    regions = defaultdict(list)
    for k, s_ in F.sinks.items():
        regions[s_['region']].append(s_)
    out_regions = {}
    for r, l in sorted(regions.items()):
        ss, ff = stats([x['ss'] for x in l]), stats([x['ff'] for x in l])
        ib = max(intra.get(r, [0.0]))
        pin = stats([x['pin_ss'] for x in l if 'pin_ss' in x])
        out_regions[r] = dict(tree=l[0]['tree'], sinks=len(l), insertion_ss=ss, insertion_ff=ff, region_tree_ss=pin,
                              early_branch_ps=early_ps(r),
                              planned_root_pad_ss_ps=round(F.pad.get(r, (0.0, 0.0))[0], 1),
                              target_entry_insertion_ss_ps=round(ss['mean'], -1), target_entry_insertion_ff_ps=round(ff['mean'], -1),
                              target_tolerance_ps=round((ss['max'] - ss['min']) / 2, 1),
                              intra_pairs=len(intra.get(r, [])), intra_skew_bound_ss_ps=round(ib, 1),
                              intra_budget_ps=min(C.SKEW_INTRA_PS, math.ceil(ib + C.INTRA_MARGIN_PS)) if intra.get(r) else C.SKEW_INTRA_PS,
                              intra_ok=ib + C.INTRA_MARGIN_PS <= C.SKEW_INTRA_PS)
    out_inter = {f'{k[0]}|{k[1]}': dict(pairs=len(v), skew_bound_ss_ps=round(max(v), 1), ok=max(v) <= C.SKEW_INTER_PS)
                 for k, v in sorted(inter.items())}
    trees_out = {}
    for t in sorted({s_['tree'] for s_ in F.sinks.values()}):
        l = [s_ for s_ in F.sinks.values() if s_['tree'] == t]
        st = stats([x['ss'] for x in l])
        trees_out[t] = dict(cls=trees[t]['cls'], root=trees[t]['root'], sinks=len(l), insertion_ss=st,
                            insertion_ff=stats([x['ff'] for x in l]),
                            regions=len({x['region'] for x in l}),
                            ocv_wander_root_split_ps=round(C.OCV * 2 * st['max'], 1),
                            meso_window_ok=C.OCV * 2 * st['max'] <= C.T_PS / 2)
    worst.sort(reverse=True)
    viol_intra = [w for w in worst if w[4] == w[5] and w[0] + C.INTRA_MARGIN_PS > C.SKEW_INTRA_PS]
    viol_inter = [w for w in worst if w[4] != w[5] and w[0] > C.SKEW_INTER_PS]
    rec = dict(schema='opentallas.budgets.clock_plan.v1', die=d['die'], source_commit=d.get('source_commit'),
               s81_opts=d.get('s81_opts'), method=__doc__.split('\n\n')[1].strip(), cases=F.meta,
               max_region_um=MAX_REGION_UM, max_merge_um=MAX_MERGE_UM,
               policy=dict(inter_ps=C.SKEW_INTER_PS, intra_default_ps=C.SKEW_INTRA_PS, intra_margin_ps=C.INTRA_MARGIN_PS,
                           ocv=C.OCV, hold_io_ps=C.HOLD_IO_SKEW_PS),
               trees=trees_out, regions=out_regions, inter_region=out_inter,
               synchronous_pairs=len(pairs),
               violations=dict(intra=len(viol_intra), inter=len(viol_inter),
                               rows=[dict(skew_ps=round(w[0], 1), nominal_ps=round(w[1], 1), a=w[2], b=w[3], ra=w[4], rb=w[5], cls=w[6])
                                     for w in (viol_intra + viol_inter)[:200]]),
               worst_pairs=[dict(skew_ps=round(w[0], 1), nominal_ps=round(w[1], 1), a=w[2], b=w[3], ra=w[4], rb=w[5], cls=w[6])
                            for w in worst[:25]],
               sink_insertion={f'{k[0]}/{k[1]}': [round(s_['ss'], 1), round(s_['ff'], 1)] for k, s_ in F.sinks.items()},
               sink_region={f'{k[0]}/{k[1]}': s_['region'] for k, s_ in F.sinks.items()})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(json.dumps(dict(die=d['die'], regions=len(out_regions), pairs=len(pairs),
                          max_intra=max((r['intra_skew_bound_ss_ps'] for r in out_regions.values()), default=None),
                          max_inter=max((r['skew_bound_ss_ps'] for r in out_inter.values()), default=None),
                          viol_intra=len(viol_intra), viol_inter=len(viol_inter))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['emit', 'record'])
    ap.add_argument('--die-model', required=True)
    ap.add_argument('--name', default='case')
    ap.add_argument('--out', required=True)
    ap.add_argument('--group', default='trunk', choices=['trunk', 'region', 'htop', 'hreg'])
    ap.add_argument('--buffer-um', type=float, default=150.0)
    ap.add_argument('--case', action='append', default=[])
    a = ap.parse_args()
    emit(a) if a.mode == 'emit' else record(a)


if __name__ == '__main__':
    main()
