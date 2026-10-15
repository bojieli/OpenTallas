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


S81_LOCAL_FAMILIES = False    # opt-in measured SELECT/COLLECT/GATHER trunk sharing


def s81_clock_family(inst):
    if inst == "bk_selector" or inst.startswith(("xsix_", "hix_")):
        return "SELECT"
    if inst == "bk_collector" or inst.startswith(("xsco_", "hco_")):
        return "COLLECT"
    if inst == "sp_gather" or inst.startswith(("f_hr_", "g_hr_", "hr_")):
        return "GATHER"
    return None


MAX_MERGE_UM = 5250.0         # merged region limit: the measured 60 ps H-tree extent (rom_die_clocking_decision)
MAX_REGION_UM = 4000.0        # a region's sink bbox side (option C: <= 5.25 mm measured 60 ps H-tree extent)


def plan_regions(d, trees, max_ext=MAX_REGION_UM, max_merge=None):
    """die-trunk sinks -> clock regions: the generator's region rect (HBM clock_regions; S81 spine / svc / band), split
    along the long axis at the median until no region's sink bbox side exceeds max_ext.  {tree: {region: [(inst, port,
    x, y)]}}"""
    max_merge = max_merge or MAX_MERGE_UM
    reg = C.sink_regions(d, trees)
    # ds-1010/s81die 2026-10-10: a block on a column tree AND a die trunk (S81 --cfifo-colck: cfifo ck = stream trunk,
    # cr = its own column tree) is registered under whichever tree came first; its trunk region comes from its rect
    rects = [(r['name'], r['rect']) for r in d['regions'] if not r['name'].startswith('frame_')
             and r.get('kind') not in ('channel', 'soft_child_reservation')]

    def trunk_rect(inst, t):
        r_ = reg.get(inst)
        if r_ and r_[0] == t and ':' in r_[1]:
            return r_[1].split(':', 1)[1]
        if r_ is None:
            return 'die'
        it = d['by'][inst]
        c = (it[5] + it[7] / 2, it[6] + it[8] / 2)
        return next((n for n, rr in rects if C.in_rect(c, rr)), 'die')
    out = defaultdict(dict)
    for t, tr in trees.items():
        if tr['cls'] == 'col_clock':
            continue
        groups = defaultdict(list)
        for inst, port in dict.fromkeys(tr['sinks']):
            (x, y), _ = C.port_xy(d, d['by'][inst], port)
            rect = trunk_rect(inst, t)     # rect part (a block on two trees: per tree)
            if S81_LOCAL_FAMILIES and d.get('die', '').startswith('s81'):
                rect = s81_clock_family(inst) or rect
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


def clock_root_xy(d, root):
    """Resolve an explicit die input without inventing a root macro or PLL."""
    inst, port = root
    if inst == 'TOP':
        pin = d.get('top_input_ports', {}).get(port)
        if not pin or pin.get('use') != 'CLOCK' or pin.get('direction') != 'input':
            raise ValueError(f'missing physical clock input: TOP/{port}')
        xy = pin.get('center_um')
        if not xy or len(xy) != 2 or not all(math.isfinite(v) for v in xy):
            raise ValueError(f'invalid clock input center: TOP/{port}')
        if not all(0 <= v <= limit for v, limit in zip(xy, d['outline_um'])):
            raise ValueError(f'clock input outside die: TOP/{port}')
        return tuple(xy)
    xy, known = C.port_xy(d, d['by'][inst], port)
    if d.get('strict_clock_pins') and not known:
        raise ValueError(f'missing physical clock root: {inst}/{port}')
    return xy


def clock_period_ps(d, trees, name):
    """Keep a regional branch on its parent clock's real period."""
    tree = name.removeprefix('REGION:').split(':', 1)[0]
    tr = trees[tree]
    inst, port = tr['root']
    if inst == 'TOP':
        value = d['top_input_ports'][port].get('period_ns')
        if value is None or not math.isfinite(value) or value <= 0:
            raise ValueError(f'invalid clock period: TOP/{port}')
        return value * 1000
    # Retain historical cases, correcting their domain periods explicitly.
    if 'serial' in tree or 'serial' in port:
        return C.PERIODS['serial_0p9']
    if 'hbm' in tree or 'hbm' in port:
        return C.PERIODS['hbm']
    return C.PERIODS['stream_1p2']


def validate_clock_pins(d, trees):
    """A candidate must bind every sink; an outline-center fallback is not a pin."""
    missing = []
    for tree, tr in trees.items():
        clock_root_xy(d, tr['root'])
        clock_period_ps(d, trees, tree)
        for inst, port in tr['sinks']:
            if inst not in d['by'] or not C.port_xy(d, d['by'][inst], port)[1]:
                missing.append(f'{tree}:{inst}/{port}')
    if missing and d.get('strict_clock_pins'):
        raise ValueError('unbound clock sinks: ' + ', '.join(missing))
    return missing


def clock_nets(d, trees, groups, group):
    """[(clock name, root xy, [(inst, port, x, y)])] for the case group"""
    nets = []
    if group in ('trunk', 'region'):
        for t in groups[group]:
            tr = trees[t]
            rx, ry = clock_root_xy(d, tr['root'])
            l = []
            for inst, port in dict.fromkeys(tr['sinks']):
                (x, y), _ = C.port_xy(d, d['by'][inst], port)
                l.append((inst, port, x, y))
            nets.append((t, (rx, ry), l))
        return nets
    R = plan_regions(d, trees, max_ext=MAX_REGION_UM)
    fam_root = {}
    if (d.get('die') == 'hbm' and FAMILY_ROOTS[0]) or (S81_LOCAL_FAMILIES and d.get('die', '').startswith('s81')):
        # HBM r23 (die 30.6 mm wide, stream trunk 3.1 ns: sibling regions of one SM group (G<q>w / G<q>e) or one scan
        # quadrant (HUB-Q<q> cuts) diverged near the PLL, 150-160 ps): sibling regions share one root point (their
        # family's sink bbox centre), so the trunk is common down to the family and only the region trees differ
        for t, regs in R.items():
            fam = defaultdict(list)
            for r, sl in regs.items():
                rect = r.split(':', 1)[1] if ':' in r else r
                fk = re.sub(r'^(G[NS][EW])(?:[we]|c[0-9])$', r'\1', rect.split('.')[0])   # hbm-forks: 3 x 3 retile cuts c0-c2
                if d.get('die', '').startswith('s81') and fk not in ('SELECT', 'COLLECT', 'GATHER'):
                    fk = rect  # retain existing tree roots outside the local functional families
                fam[fk] += [(r, p) for p in sl]
            for fk, l in fam.items():
                xs, ys = [p[2] for _, p in l], [p[3] for _, p in l]
                c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
                for r in {r for r, _ in l}:
                    fam_root[r] = c
    for t, regs in R.items():
        tr = trees[t]
        rx, ry = clock_root_xy(d, tr['root'])
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
    missing_clock_pins = validate_clock_pins(d, trees)
    nets = getattr(a, '_nets', None) or clock_nets(d, trees, groups, a.group)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if getattr(a, 'shards', 0) and a.shards > 1 and not getattr(a, '_nets', None):
        # qwendie-1011: one CTS design per shard of region trees (independent clocks, no shared buffers), run in
        # parallel with a per-shard timeout; a single 265-region design hung > 3.5 h in CTS (H-tree level loop) with
        # no way to tell which region.  record takes every shard as a --case (names are prefixed per case).
        import copy
        k = -(-len(nets) // a.shards)
        names = []
        for i in range(0, len(nets), k):
            b = copy.copy(a)
            b.out, b._nets, b.name = str(out / f'sh{i // k:02d}'), nets[i:i + k], f'{a.name}_sh{i // k:02d}'
            emit(b)
            names.append(f'sh{i // k:02d}')
        (out / 'run.sh').write_text(f"""#!/bin/bash
# {a.name}: {len(names)} CTS shards in parallel (each: timeout, then H-tree variant retries)
D=$(cd "$(dirname "$0")" && pwd)
printf '%s\\n' {' '.join(names)} | xargs -P ${{SHARD_PAR:-{len(names)}}} -I{{}} bash $D/{{}}/run.sh
for s in {' '.join(names)}; do [ "$(cat $D/$s/exit 2>/dev/null)" = 0 ] || {{ echo "shard $s failed"; exit 1; }}; done
""")
        (out / 'run.sh').chmod(0o755)
        (out / 'shards.json').write_text(json.dumps(names) + '\n')
        print(json.dumps(dict(case=str(out), shards=len(names), trees=len(nets))))
        return
    W, H = d['outline_um']
    v, place, sdc, sinks = [], [], [], []
    v.append('module ckplan (ref);\n  input ref;')
    n = 0
    for k, (t, (rx, ry), l) in enumerate(nets):
        rn = f'root_{esc(t)}'
        v.append(f'  wire ck_{k};')
        v.append(f'  {ROOT_CELL} {rn} (.A(ref), .Y(ck_{k}));')
        place.append(f'place_inst -name {rn} -location {{{min(max(rx, 1.0), W - 2):.3f} {min(max(ry, 1.0), H - 2):.3f}}} -status FIRM')
        sdc.append(f'create_clock -name {esc(t)} -period {clock_period_ps(d, trees, t):.9f} [get_pins {rn}/Y]')
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
                                                    trees=[x[0] for x in nets], sinks=sinks,
                                                    missing_clock_pins=missing_clock_pins,
                                                    timing_scope='tree insertion after root driver output; external source, receiver and phase unqualified')) + '\n')
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
    ct = (out / 'cts.tcl').read_text()
    for v, o in (('sl1', '-num_static_layers 1'), ('sl3', '-num_static_layers 3'), ('wu50', '-wire_unit 50')):
        (out / f'cts_{v}.tcl').write_text(ct.replace(' -sink_clustering_enable', ' -sink_clustering_enable ' + o))
    for corner in ('SS', 'FF'):
        (out / f'meas_{corner}.tcl').write_text(common.replace('%C%', corner) + meas.replace('%PLAT%', PLAT)
                                               .replace('%LAY%', lay).replace('%C%', corner))
    (out / 'run.sh').write_text(f"""#!/bin/bash
# clock-only die CTS case {a.name} ({a.group}); docker on the compute host, admission guard if present
set -o pipefail
D=$(cd "$(dirname "$0")" && pwd)
IMG=${{IMG:-openroad/orfs:latest}}
CPUS=${{CPUS:-8}}
TO=${{CTS_TIMEOUT:-{max(300, int(0.04 * len(nets)))}}}   # H-DIE 1014: a die tree of 70k segment nets needs > 300 s (v13 34k: 601 s)
run() {{ docker run --rm --name ckplan_{esc(a.name)}_$1 --cpus=$CPUS -v $D:/work -w /work $IMG bash -lc \\
  "timeout -k 60 $TO /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads $CPUS -no_init -exit /work/$1.tcl > /work/$1.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"; }}
date -u +%FT%TZ > $D/start
# qwendie-1011: TritonCTS H-tree loops forever on some sparse ~60-sink region nets (r22ko4 e7: hangs after the
# 2-sinks-per-sub-region level with or without clustering / any buffer distance).  Each CTS that does not finish inside
# the timeout is retried with the next H-tree variant: -num_static_layers 1, -num_static_layers 3, -wire_unit 50.
{{ run cts || {{ echo "cts rc=$? -> sl1" >> $D/retry; run cts_sl1; }} || {{ echo "sl1 rc=$? -> sl3" >> $D/retry; run cts_sl3; }} || {{ echo "sl3 rc=$? -> wu50" >> $D/retry; run cts_wu50; }}; }} && run meas_SS && run meas_FF
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
            if g in self.cases:
                # qwendie-1011: emit --shards writes one case per shard of the same group; CTS cell / sink names repeat
                # across shards, so a shard's names get its directory as a prefix and the shards merge into one group
                sh = c.name + '.'
                sj['sinks'] = [[sh + x[0]] + list(x[1:]) for x in sj['sinks']]
                p1, a1 = read_tree(c / 'tree_SS.txt', g + ':' + sh)
                p2, a2 = read_tree(c / 'tree_FF.txt', g + ':' + sh)
                o_sj, o_p1, o_a1, o_a2 = self.cases[g]
                o_sj['sinks'] = o_sj['sinks'] + sj['sinks']
                o_p1.update(p1); o_a1.update(a1); o_a2.update(a2)
                sj = o_sj
            else:
                if (c / 'sinks.json').exists() and c.name.startswith('sh') and c.parent.joinpath('shards.json').exists():
                    sh = c.name + '.'
                    sj['sinks'] = [[sh + x[0]] + list(x[1:]) for x in sj['sinks']]
                    pfx = g + ':' + sh
                else:
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
               max_region_um=MAX_REGION_UM, max_merge_um=MAX_MERGE_UM, s81_local_families=S81_LOCAL_FAMILIES,
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


# ------------------------------------------------------------------------------------------------ balance
def lib_insertions(lib):
    """{cell: (min, max)} ETM clock_tree_path of every hard view in a liberty file (its own routed clock tree, ps)"""
    t = Path(lib).read_text()
    st = [m.start() for m in re.finditer(r'\n\s*cell\s*\(', t)]
    out = {}
    for i, a_ in enumerate(st):
        body = t[a_:st[i + 1] if i + 1 < len(st) else len(t)]
        v = {k: float(m.group(1)) for k in ('min', 'max')
             if (m := re.search(k + r'_clock_tree_path\s*;[^v]*values\("([0-9.]+)', body, re.S))}
        if len(v) == 2:
            out[re.search(r'cell\s*\(\s*"?(\w+)', body).group(1)] = (v['min'], v['max'])
    return out


def balance(a):
    """qwendie-1012 (CLOCK LATENCY ACROSS THE HIERARCHY).  Every ETM-bound hard view carries its own routed clock tree
    (min/max_clock_tree_path), so its registers clock at (die arrival at its clock pin) + (its insertion).  Two errors
    in the it1/it2 die STA: (1) OpenSTA reads a pin latency on a macro as the latency of its INTERNAL registers and
    subtracts the ETM tree ('macro clock tree delay -665.5'), so writing the plan's pin arrival put every view's pin
    one insertion early -- harmless between equal-depth relays (~95 ps cst ETMs), but qfd_d2d_rom's 665.5-767.2 ps
    tree made its pin ~570 ps early (it2: TT -273 on 787 endpoints); (2) the plan balanced pin arrivals only, and its
    synchronous pairs were same-tree only.  Fix: 'view_pin_insertion' (sta_tcl writes pin arrival + insertion,
    -early min / -late max) and target-latency balance: a view whose register instant is later than its bus partners'
    on OTHER trees, on a tree that holds only it and its own-tree partners (r22ko4 clk_d2d: d2d_rom + ucie_kv FDI +
    rs_bump on pll_d2d), has its tree tapped EARLY -- every other tree root gets the same TT lift L (one delay line
    per root, SS:FF 1 : 0.53 like the region pads) and the view's entry pad lands it on its partners.  TT is solved
    (setup sign-off); the FF residual is reported (hold is closed by the relay-input pads).  A late view on a shared
    tree is left as recorded and reported."""
    P = json.loads(Path(a.plan).read_text())
    d = C.load_die(a.die_model)
    lib = Path(a.libs)
    ins_tt, ins_ff = {}, {}
    if (lib / 'qfd_etm_tt.lib').exists():                  # Qwen ROM die: one ETM lib per corner (qwen_die_etm_map)
        ins_tt, ins_ff = lib_insertions(lib / 'qfd_etm_tt.lib'), lib_insertions(lib / 'qfd_etm_ff.lib')
    # per-master ETMs (bind_views.py: qfd_etm_<m>_tt.lib); HBM die cases (tools/hbm_die_views.py die): <master>_tt.lib
    for f in sorted(set(lib.glob('qfd_etm_*_tt.lib')) | {g for g in lib.glob('*_tt.lib') if not g.name.startswith('qfd_etm')}):
        ins_tt.update(lib_insertions(f))
        g = f.with_name(f.name[:-len('_tt.lib')] + '_ff.lib')
        if g.exists():
            ins_ff.update(lib_insertions(g))
    si, sr = P['sink_insertion'], P['sink_region']
    kss = 1.0 / ((1.0 + 0.53) / 2.0)          # a TT delay of x ps is x * kss in SS and 0.53 x kss in FF
    tree_of = lambda k: sr[k].split(':', 1)[0]
    m_of = lambda k: d['by'][k.rsplit('/', 1)[0]][1] if k.rsplit('/', 1)[0] in d['by'] else None
    vi = {k: (ins_tt[m_of(k)], ins_ff[m_of(k)]) for k in si if m_of(k) in ins_tt and m_of(k) in ins_ff}
    mid = lambda k, i: (sum(vi[k][i]) / 2) if k in vi else 0.0
    tt = lambda k, o=si: (o[k][0] + o[k][1]) / 2
    by_inst = defaultdict(list)
    for k in si:
        by_inst[k.rsplit('/', 1)[0]].append(k)
    fb_ = set(d.get('fclk_buses', []))
    partners = defaultdict(set)
    for bid, cls, bits, eps in d['buses']:
        if bid in fb_ or cls in ('clock', 'col_clock', 'clock_trunk', 'reset', 'reset_tree', 'col_reset', 'fclk', 'top_in'):
            continue
        insts = {e[0] for e in eps}
        for i_ in insts:
            for v in by_inst.get(i_, []):
                for o in insts - {i_}:
                    partners[v].update(by_inst.get(o, []))
    tsinks = defaultdict(set)
    for k in si:
        tsinks[tree_of(k)].add(k)
    flop = lambda k, o=si: tt(k, o) + mid(k, 0)
    # one STA clock per root instance (r22ko4: clk_rx/pll_* = 'stream'; io_collective/pll_serial etc. are async
    # groups): balance and lift only inside the early tree's own clock
    dom = {t: (P['trees'].get(t, {}).get('root') or ['?'])[0] for t in tsinks}
    deficit, need = {}, {}
    for t, ks in tsinks.items():
        deep = [k for k in ks if k in vi]
        for v in deep:
            oth = [p for p in partners[v] if tree_of(p) != t and dom.get(tree_of(p)) == dom[t]]
            if not oth:
                continue
            T = sum(flop(p) for p in oth) / len(oth)
            x = flop(v) - T
            if x > a.min_late_ps:
                deficit[v] = x
                need[v] = T - mid(v, 0)
    early, left = set(), []
    for t in {tree_of(v) for v in deficit}:
        ks = tsinks[t]
        own = {p for v in ks if v in deficit for p in partners[v] if tree_of(p) == t}
        if ks - {v for v in ks if v in deficit} - own:
            left += [v for v in ks if v in deficit]
        else:
            early.add(t)
    doms = {dom[t] for t in early}
    if len(doms) > 1:
        raise SystemExit(f'balance: early trees in several clocks {sorted(doms)}: one lift per clock not implemented')
    L = max([x for v, x in deficit.items() if tree_of(v) in early], default=0.0)
    lifted = lambda k: tree_of(k) not in early and dom.get(tree_of(k)) in doms
    out = {k: ([si[k][0] + L * kss, si[k][1] + 0.53 * L * kss] if lifted(k) else list(si[k])) for k in si}
    rows = {}
    for v in deficit:
        if tree_of(v) not in early:
            continue
        pad = max(0.0, need[v] + L - tt(v))
        out[v] = [si[v][0] + pad * kss, si[v][1] + 0.53 * pad * kss]
    # own-tree partners of an early view (r22ko4 rs_bump reset sync, ucie_kv FDI -> d2d_rom) moved early with the
    # tree but the view's registers sit one insertion later: pad their entries up to the view register instant
    # (it3: rs_bump -> d2d_rom FF hold -449.9, rs_bump -> lifted rly_rst_fwd -311.1)
    own_pad = {}
    for t in early:
        vs = [v for v in tsinks[t] if v in deficit]
        tgt = sum(flop(v, out) for v in vs) / len(vs)
        for k in tsinks[t]:
            if k not in deficit and tgt - flop(k, out) > 0:
                p_ = tgt - flop(k, out)
                out[k] = [out[k][0] + p_ * kss, out[k][1] + 0.53 * p_ * kss]
                own_pad[k] = round(p_, 1)
    for v in deficit:
        pt = [p for p in partners[v] if tree_of(p) != tree_of(v) and dom.get(tree_of(p)) == dom[tree_of(v)]]
        rows[v] = dict(master=m_of(v), view_insertion_tt=vi[v][0], view_insertion_ff=vi[v][1], early_tree=tree_of(v) in early,
                       partners=len(pt), late_before_tt=round(deficit[v], 1),
                       die_tt_before=round(tt(v), 1), die_tt_after=round(tt(v, out), 1),
                       flop_tt_minus_partners=round(flop(v, out) - sum(flop(p, out) for p in pt) / len(pt), 1),
                       flop_ff_minus_partners=round(out[v][1] + mid(v, 1) - sum(out[p][1] + mid(p, 1) for p in pt) / len(pt), 1))
    mixed = sorted(k for k in si if tree_of(k) in early and k not in deficit)
    tgt_rep = {}
    if getattr(a, 'sink_target', False):
        # qwendie-1012 per-sink TARGET LATENCY (supersedes the early-tree/lift result for every synchronous domain):
        # it3 left 196 deep views / relays on SHARED trees up to 527 ps late (port_tiles: 461-683 ps own trees;
        # rly_seq_coll_50 on clk_r101 vs its clk_r114 partner = tree-to-tree imbalance, TT -194.85).  One register
        # instant T_D per clock domain: every die clock pin k gets pin arrival p(k) = T_D - insertion(k) (relay /
        # plain sink: insertion 0 at die level beyond its ETM).  Realisation: k's region root BEFORE its planned
        # pad is the earliest tap (min_tt = recorded arrival - region pad, same branch depth as the recorded tree);
        # T_D = max_k(min_tt(k) + insertion(k)) is the earliest feasible instant; each region keeps ONE delay line
        # (its median need) and a sink whose need differs from it by > branch_tol_ps gets a dedicated branch from the
        # pre-pad region root with its own delay line (CTS pin insertion-delay target = the die contract's clock-
        # entry target latency).  SS : FF of every added delay 1 : 0.53 (as the region pads); FF residual reported.
        R_ = P.get('regions', {})
        padtt = lambda k: R_.get(sr[k], {}).get('planned_root_pad_ss_ps', 0.0) / kss
        def floor_(k):        # earliest tap: pre-pad region root + the region tree's shortest root->sink path
            r_ = R_.get(sr[k], {})
            ins_, rt_ = r_.get('insertion_ss') or {}, r_.get('region_tree_ss') or {}
            m_ = tt(k) - padtt(k)
            if ins_ and rt_:
                m_ = min(m_, (ins_['mean'] - r_.get('planned_root_pad_ss_ps', 0.0) - rt_['mean'] + rt_['min']) / kss)
            return max(0.0, m_)
        mn = {k: floor_(k) for k in si}
        byd = defaultdict(list)
        for k in si:
            if tt(k) > 0 or k in vi:           # clock source pins (pll outputs, tree roots) are not register sinks
                byd[dom.get(tree_of(k), '?')].append(k)
        nbr, worst_br = 0, 0.0
        for D_, ks in byd.items():
            T_ = max(mn[k] + mid(k, 0) for k in ks)
            need_ = {k: T_ - mid(k, 0) - mn[k] for k in ks}
            byr = defaultdict(list)
            for k in ks:
                byr[sr[k]].append(need_[k])
            med = {r_: sorted(l)[len(l) // 2] for r_, l in byr.items()}
            br = [k for k in ks if abs(need_[k] - med[sr[k]]) > a.branch_tol_ps]
            nbr += len(br)
            worst_br = max([worst_br] + [abs(need_[k] - med[sr[k]]) for k in br])
            for k in ks:
                dl = T_ - mid(k, 0) - tt(k)
                out[k] = [si[k][0] + dl * kss, si[k][1] + 0.53 * dl * kss]
            ffi = [out[k][1] + mid(k, 1) for k in ks]
            ocv_ = max([C.OCV * kss * (need_[v] + need_[p]) for v in ks for p in partners.get(v, ())
                        if p in need_ and sr[p] != sr[v]], default=0.0)
            tgt_rep[D_] = dict(sinks=len(ks), target_register_instant_tt_ps=round(T_, 1),
                               max_region_delay_line_tt_ps=round(max(med.values()), 1),
                               dedicated_branches=len(br), ff_register_instant_spread_ps=round(max(ffi) - min(ffi), 1),
                               worst_pair_added_ocv_ss_ps=round(ocv_, 1),
                               branches=sorted(br)[:400])
        print(json.dumps(dict(sink_target={D_: {k_: v_ for k_, v_ in r_.items() if k_ != 'branches'} for D_, r_ in tgt_rep.items()},
                              branches=nbr, worst_branch_offset_tt=round(worst_br, 1))))
    P['sink_insertion'] = {k: [round(x[0], 1), round(x[1], 1)] for k, x in out.items()}
    P['view_pin_insertion'] = {k: dict(tt=list(x[0]), ff=list(x[1])) for k, x in vi.items()}
    P['view_balance'] = dict(method=balance.__doc__.strip(), libs=str(lib), min_late_ps=a.min_late_ps,
                             lift_clock_roots=sorted(doms), lift_tt_ps=round(L, 1), lift_ss_ps=round(L * kss, 1), lift_ff_ps=round(0.53 * L * kss, 1),
                             early_trees=sorted(early), own_tree_partners_moved=mixed, own_tree_entry_pad_tt=own_pad, views=len(vi),
                             late_left_on_shared_trees={v: round(deficit[v], 1) for v in sorted(left)}, rows=rows,
                             sink_target=tgt_rep or None, branch_tol_ps=getattr(a, 'branch_tol_ps', None))
    Path(a.out).write_text(json.dumps(P, indent=1, default=str) + '\n')
    er = [r for r in rows.values() if r['early_tree']]
    print(json.dumps(dict(views=len(vi), late=len(deficit), lift_tt=round(L, 1), early=sorted(early), moved=len(mixed),
                          left=len(left), worst_left=max(deficit[v] for v in left) if left else None,
                          early_tt_residual=max((abs(r['flop_tt_minus_partners']) for r in er), default=None),
                          early_ff_residual=max((abs(r['flop_ff_minus_partners']) for r in er), default=None))))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['emit', 'record', 'balance'])
    ap.add_argument('--die-model', required=True)
    ap.add_argument('--name', default='case')
    ap.add_argument('--out', required=True)
    ap.add_argument('--plan', help='balance: recorded plan.json')
    ap.add_argument('--libs', help='balance: the STA libs dir (qfd_etm_{tt,ff}.lib [+ qfd_etm_<master>_{tt,ff}.lib])')
    ap.add_argument('--min-late-ps', type=float, default=60.0, help='balance: register-instant lateness vs partners that gets balanced (the setup uncertainty)')
    ap.add_argument('--sink-target', action='store_true', help='balance: one register instant per clock domain, per-sink pin target latency (region delay line + dedicated branches)')
    ap.add_argument('--branch-tol-ps', type=float, default=25.0, help='balance --sink-target: need offset from the region delay line that gets a dedicated branch')
    ap.add_argument('--group', default='trunk', choices=['trunk', 'region', 'htop', 'hreg'])
    ap.add_argument('--buffer-um', type=float, default=150.0)
    ap.add_argument('--shards', type=int, default=0, help='emit: split the trees into N independent CTS cases run in parallel')
    ap.add_argument('--case', action='append', default=[])
    ap.add_argument('--max-region-um', type=float, default=None,
                    help='region sink-bbox side limit (default MAX_REGION_UM 4000); qwendie-1011: the Qwen ROM die region '
                         'trees at 4 mm are ~650 ps deep, so 5%% OCV on unshared insertion breaks the intra budget')
    ap.add_argument('--max-merge-um', type=float, default=None,
                    help='merged-region sink-bbox side limit (default MAX_MERGE_UM 5250); die-gaps 2026-10-08: S81 r3 '
                         'serial spine merged to 5.23 mm gave a 65.2 ps intra bound (+25 margin > 90)')
    ap.add_argument('--s81-local-families', action='store_true', help='opt-in: selector/collector plus local crossing stages share band trunk roots')
    a = ap.parse_args()
    global MAX_MERGE_UM, MAX_REGION_UM, S81_LOCAL_FAMILIES
    S81_LOCAL_FAMILIES = a.s81_local_families
    if a.max_region_um:
        MAX_REGION_UM = a.max_region_um
    if a.max_merge_um:
        MAX_MERGE_UM = a.max_merge_um
    emit(a) if a.mode == 'emit' else record(a) if a.mode == 'record' else balance(a)


if __name__ == '__main__':
    main()
