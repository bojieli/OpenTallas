#!/usr/bin/env python3
"""Qwen ROM near-HBM corridor routability gate (r2 floorplan, results/uarch/qwen_rom_floorplan_nearhbm_20261003).

r2 nets every corridor to 0.39-0.43 of its RAW same-direction tracks on the layers it is assigned, but the only routed
bus corridor in the repository passed at 0.225 and a 0.451 run never converged.  This tool builds two representative
routing test blocks with real structure and routes them through the pinned ORFS flow
(tools/run_abi3_physical_persistent.py -> tools/run_abi3_physical.py) at SS 1.2 GHz (60 ps setup) / FF hold (25 ps):

  A  link span   : one 504 um span (the SS reach) of a hub<->stack link, 1,056 signals registered at both ends by
                   station flop banks (96.768 x 8.64 um station slabs, r1 link endpoint), 4 BUFx4 repeaters per wire
                   (r2 7.71 buffers per wire-mm) in repeater slabs, long haul on M6/M8 only (r2 layer assignment).
  B  tile column : one tile pitch (1,291.68 um) of the tile-column corridor, 637 signals (636 downstream + ready),
                   stations every 430.56 um (r2: 3 stages per tile hop) with 3 BUFx4 repeaters per segment, the
                   entry station tapping a 637-pin tile-edge pin row on the east edge, long haul on M7/M9 only.

Layer assignment.  r2 counts only the assigned layers (A: M6+M8, B: M7+M9).  The other same-direction layers (A: M2/M4,
B: M3/M5) get zero global-route capacity between the station/repeater slabs (set_global_routing_region_adjustment
1.0), so long haul cannot leave the assigned layers; inside the slabs every layer is open for pin access.  All cells
(stations, repeaters, CTS and repair buffers) are confined to the slabs by placement blockages.  The routed DEF is
audited per layer after detail route (layer_audit) to prove the assignment held.

PG.  The repo die grid (tools/chip_assembly/tcl/pdn_die.tcl): M1/M2 follow-pins, M5 0.12/10.8 and M6 0.288/10.8
straps, M8/M9 mesh; the M8/M9 per-net coverage is the r2 region coverage (tile field 4.39%, strip 16.39%), built of
0.48 um stripes (below the ASAP7 M8/M9 0.49975 um wide-metal spacing class; MAXWIDTH 2.0 um forbids one 6.6 um strap)
at a track-aligned pitch rounded DOWN (coverage never below r2).  pdn_die's parallel M6-M8 connect is replaced by an
M6-M9 stack (through M7/M8) so the mesh really lands on the lower grid: this is harsher on M7/M8, never lighter.

    python3 tools/qwen_corridor_gate.py plan                       # variants, widths, ratios (json)
    python3 tools/qwen_corridor_gate.py write                      # RTL + hooks (committed sources)
    python3 tools/qwen_corridor_gate.py argv --variant A_strip_r2 --jobroot /home/ubuntu/otjobs/qcg
    python3 tools/qwen_corridor_gate.py record --variant A_strip_r2 --jobroot ... --out results/rtl/...
    python3 tools/qwen_corridor_gate.py die --out ...              # die-area statement from the routed records
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R2_REC = 'results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r2.json'
OUTDIR = 'results/rtl/qwen_corridor_gate_20261003'
RTL_DIR = 'rtl/chip/physical/qcg'
HOOK_DIR = 'physical/qwen_corridor_gate'

FLOP, BUF = 'DFFHQNx2_ASAP7_75t_R', 'BUFx4_ASAP7_75t_R'   # corridor-tool station flop; r2 repeater cell
SITE, ROW = 0.054, 0.270
PITCH = {'M2': 0.036, 'M3': 0.036, 'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064, 'M8': 0.080, 'M9': 0.080}
PERIOD_NS, UNC_SETUP_NS, UNC_HOLD_NS = 0.833, 0.060, 0.025
EDGE, STATION, REPSLAB = 2.16, 8.64, 4.32               # um: end margin, station slab (r1 link endpoint), repeater slab


def r2():
    return json.loads((ROOT / R2_REC).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def snap(v, q, up=True):
    n = v / q
    return round((math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)) * q, 6)


# ------------------------------------------------------------------ geometry
def tests():
    rec = r2()
    cor, lw = rec['corridors'], rec['long_wires']
    reach = lw['reach_um']
    bpm = lw['buffers_per_wire_mm']
    tile_h = 1291.68                                       # r1 tile slot height (long_wires row note)
    assert abs(reach - 504.0) < 1e-9
    a = dict(name='A', top='qcg_link_span', axis='x', demand=cor['horizontal_link']['demand_tracks'],
             layers=cor['horizontal_link']['layers'], blocked=['M2', 'M4'], width_r2=cor['horizontal_link']['width_r2_um'],
             seg_um=reach, segs=1, reps=round(bpm * reach / 1000), chains=cor['horizontal_link']['demand_tracks'])
    b = dict(name='B', top='qcg_tile_column', axis='y', demand=cor['tile_column']['demand_tracks'],
             layers=cor['tile_column']['layers'], blocked=['M3', 'M5'], width_r2=cor['tile_column']['width_r2_um'],
             seg_um=round(tile_h / math.ceil(tile_h / reach), 4), segs=math.ceil(tile_h / reach),
             reps=round(bpm * tile_h / math.ceil(tile_h / reach) / 1000), chains=cor['tile_column']['demand_tracks'])
    for t in (a, b):
        t['raw_per_um'] = sum(1 / PITCH[l] for l in t['layers'])
        t['zones'] = zones(t)
        t['length_um'] = round(t['zones'][-1][2] + EDGE, 4)
    return dict(A=a, B=b)


def zones(t):
    """[(name, lo, hi)] along the corridor axis; stations qs<k>, repeaters qr<k><j>."""
    grid = SITE if t['axis'] == 'x' else ROW
    out = []
    for k in range(t['segs'] + 1):
        c = EDGE + STATION / 2 + k * t['seg_um']
        out.append((f'qs{k}', snap(c - STATION / 2, grid, False), snap(c + STATION / 2, grid)))
        if k < t['segs']:
            for j in range(1, t['reps'] + 1):
                cr = c + j * t['seg_um'] / (t['reps'] + 1)
                out.append((f'qr{k}{j}', snap(cr - REPSLAB / 2, grid, False), snap(cr + REPSLAB / 2, grid)))
    return out


PG = dict(tile=0.0439, strip=0.1639)                    # r2 pg_coverage regions tile_field / strip (per net)
M6_PITCH, M6_PAIR = 10.8, (1.856, 2.528)                # pdn_die.tcl M6 straps (offset = first centreline): pair spans this per 10.8
PG_PITCH = dict(tile=10.8, strip=2.7)                   # M8/M9 pitch: divides the M6 pitch so every M6 pair sits in an
PG_OFFSET = 1.5                                         #   M8 gap (the M6->M9 stack never crosses an opposite-net M8)


def pg_pitch(cov_name):
    return PG_PITCH[cov_name]


def pg_width(cov_name):
    return math.ceil(PG[cov_name] * PG_PITCH[cov_name] * 500 - 1e-6) / 500    # 2 nm PDN width grid; realised >= r2


def plan():
    T = tests()
    rec = r2()
    assert abs(rec['pg_coverage']['regions']['tile_field']['m8m9_coverage_per_net'] - PG['tile']) < 1e-4
    assert abs(rec['pg_coverage']['regions']['strip']['m8m9_coverage_per_net'] - PG['strip']) < 1e-4
    ratios = [('r060', 0.60), ('r050', 0.50), ('r2', None), ('r0362', 0.362), ('r030', 0.30), ('r0225', 0.225)]
    V = {}
    for tname, pgs in (('A', ('strip', 'tile')), ('B', ('tile',))):
        t = T[tname]
        for pg in pgs:
            for tag, ratio in ratios:
                w = t['width_r2'] if ratio is None else snap(t['demand'] / ratio / t['raw_per_um'], 0.432)
                raw = {l: math.floor(w / PITCH[l] + 1e-8) for l in t['layers']}
                name = f'{tname}_{pg}_{tag}'
                V[name] = dict(variant=name, test=tname, top=t['top'], pg=pg, pg_cov_per_net=PG[pg],
                               pg_pitch_um=pg_pitch(pg), pg_stripe_um=pg_width(pg),
                               pg_cov_realised=round(pg_width(pg) / pg_pitch(pg), 4),
                               width_um=w, length_um=t['length_um'], demand=t['demand'], raw_tracks=raw,
                               ratio=round(t['demand'] / sum(raw.values()), 4), ratio_tag=tag)
    return dict(tests=T, variants=V)


# ------------------------------------------------------------------ RTL
def rtl_a(t):
    n, reps = t['chains'], t['reps']
    v = [f'// Generated by tools/qwen_corridor_gate.py: one {t["seg_um"]} um link span, {n} registered signals,',
         f'// {reps} {BUF} repeaters per wire between station banks qs0 -> qs1.  Do not edit.',
         'module qcg_link_span (input clk, input [%d:0] d, output [%d:0] q);' % (n - 1, n - 1)]
    for i in range(n):
        v.append(f'  wire w{i}_0; {FLOP} qs0_{i} (.CLK(clk), .D(d[{i}]), .QN(w{i}_0));')
        prev = f'w{i}_0'
        for j in range(1, reps + 1):
            v.append(f'  wire w{i}_{j}; {BUF} qr0{j}_{i} (.A({prev}), .Y(w{i}_{j}));')
            prev = f'w{i}_{j}'
        v.append(f'  {FLOP} qs1_{i} (.CLK(clk), .D({prev}), .QN(q[{i}]));')
    v.append('endmodule')
    return '\n'.join(v) + '\n'


def rtl_b(t):
    n, reps, segs = t['chains'], t['reps'], t['segs']
    nb = n - 1
    v = [f'// Generated by tools/qwen_corridor_gate.py: one tile pitch of the tile-column corridor, {n} signals',
         f'// ({nb} downstream + ready), stations qs0..qs{segs} every {t["seg_um"]} um, {reps} {BUF} per segment;',
         '// qs0 taps the tile-edge pin row (tq) and captures the tile ready (rdy_t).  Do not edit.',
         'module qcg_tile_column (input clk, input [%d:0] bd, input rdy_t, output [%d:0] bq, output [%d:0] tq);'
         % (nb - 1, n - 1, nb - 1)]
    for i in range(n):
        src = f'bd[{i}]' if i < nb else 'rdy_t'
        prev = None
        for k in range(segs + 1):
            out = f'bq[{i}]' if k == segs else f's{i}_{k}'
            if k < segs:
                v.append(f'  wire {out};')
            v.append(f'  {FLOP} qs{k}_{i} (.CLK(clk), .D({src if k == 0 else prev}), .QN({out}));')
            if k == 0 and i < nb:
                v.append(f'  assign tq[{i}] = {out};')
            prev = out
            if k < segs:
                for j in range(1, reps + 1):
                    v.append(f'  wire r{i}_{k}{j}; {BUF} qr{k}{j}_{i} (.A({prev}), .Y(r{i}_{k}{j}));')
                    prev = f'r{i}_{k}{j}'
    v.append('endmodule')
    return '\n'.join(v) + '\n'


# ------------------------------------------------------------------ hooks
TCL_LIB = r'''
# Generated by tools/qwen_corridor_gate.py.  Do not edit.
proc qcg_block {} { return [ord::get_db_block] }
proc qcg_dbu {} { return [[qcg_block] getDbUnitsPerMicron] }
proc qcg_um {v} { return [expr {int(round($v * [qcg_dbu]))}] }
# zone membership: instance name prefix before the first '_' (qs<k>, qr<k><j>)
proc qcg_zone_of {name} { return [lindex [split $name _] 0] }
proc qcg_chain_of {name} { return [lindex [split $name _] 1] }
'''


def hook_dont_touch():
    return TCL_LIB + r'''
# PRE_FLOORPLAN: the r2 repeaters are fixed BUFx4 cells; keep remove_buffers / unbuffer off them.
set n 0
foreach inst [[qcg_block] getInsts] {
  if {[string match "qr*" [$inst getName]]} { $inst setDoNotTouch 1; incr n }
}
puts "QCG dont_touch repeaters: $n"
'''


def hook_place(t):
    zl = ' '.join(f'{{{z} {lo} {hi}}}' for z, lo, hi in t['zones'])
    return TCL_LIB + f'''
# PRE_GLOBAL_PLACE_SKIP_IO: fixed station / repeater slabs + placement blockages between them.
set qcg_axis {t["axis"]}
set qcg_zones {{{zl}}}
set qcg_chains {t["chains"]}
set qcg_len {t["length_um"]}
''' + r'''
set block [qcg_block]
set dbu [qcg_dbu]
set die [$block getDieArea]
set W [$die xMax]; set H [$die yMax]
set site_w [qcg_um 0.054]
# rows
set rows {}
foreach row [$block getRows] {
  set o [$row getOrigin]
  lappend rows [list [lindex $o 1] [$row getOrient] [lindex $o 0] [expr {[lindex $o 0] + [$row getSiteCount]*$site_w}]]
}
set rows [lsort -integer -index 0 $rows]
set row_h [qcg_um 0.27]
# occupancy per row y: list of {x0 x1} (dbu), seeded with existing instances (tapcells)
array set occ {}
foreach r $rows { set occ([lindex $r 0]) {} }
foreach inst [$block getInsts] {
  if {[$inst getPlacementStatus] eq "NONE" || [$inst getPlacementStatus] eq "UNPLACED"} continue
  set b [$inst getBBox]
  set y [$b yMin]
  if {[info exists occ($y)]} { lappend occ($y) [list [$b xMin] [$b xMax]] }
}
proc qcg_free_near {y tx w lo hi} {
  # nearest site-aligned free interval of width w in row y to tx within [lo, hi]; -1 if none
  variable occ
  variable site_w
  set best -1; set bd 1e18
  set ivs [lsort -integer -index 0 $occ($y)]
  set cands [list $lo]
  foreach iv $ivs { lappend cands [lindex $iv 1] }
  set tx [expr {$lo + (($tx - $lo) / $site_w) * $site_w}]
  lappend cands $tx
  foreach c $cands {
    set x [expr {$lo + (($c - $lo + $site_w - 1) / $site_w) * $site_w}]
    # push right past any overlap
    set moved 1
    while {$moved} {
      set moved 0
      foreach iv $ivs {
        if {$x < [lindex $iv 1] && $x + $w > [lindex $iv 0]} {
          set x [expr {$lo + (([lindex $iv 1] - $lo + $site_w - 1) / $site_w) * $site_w}]; set moved 1
        }
      }
    }
    if {$x + $w > $hi} continue
    set d [expr {abs($x - $tx)}]
    if {$d < $bd} { set bd $d; set best $x }
  }
  return $best
}
# group instances by zone, ordered by chain index
array set members {}
foreach inst [$block getInsts] {
  set nm [$inst getName]
  if {![regexp {^q[sr][0-9]+_[0-9]+$} $nm]} continue
  lappend members([qcg_zone_of $nm]) [list [qcg_chain_of $nm] $inst]
}
set placed 0
set pad [expr {2 * $site_w}]
foreach z $qcg_zones {
  lassign $z zn lo_um hi_um
  set lo [qcg_um $lo_um]; set hi [qcg_um $hi_um]
  if {![info exists members($zn)]} { error "QCG zone $zn has no members" }
  set mem [lsort -integer -index 0 $members($zn)]
  set n [llength $mem]
  if {$qcg_axis eq "x"} {
    set zrows $rows; set xlo $lo; set xhi $hi
  } else {
    set zrows {}
    foreach r $rows { if {[lindex $r 0] >= $lo && [lindex $r 0] + $row_h <= $hi} { lappend zrows $r } }
    set xlo 0; set xhi $W
  }
  set nr [llength $zrows]
  if {$nr == 0} { error "QCG zone $zn has no rows" }
  set i 0
  foreach m $mem {
    set inst [lindex $m 1]
    set w [expr {[[$inst getMaster] getWidth] + $pad}]
    if {$qcg_axis eq "x"} {
      set tr [expr {int(($i + 0.5) * $nr / $n)}]; set tx $xlo
    } else {
      set tr [expr {$i % $nr}]; set tx [expr {$xlo + int(($i + 0.5) * ($xhi - $xlo) / $n)}]
    }
    set done 0
    for {set d 0} {$d < $nr && !$done} {incr d} {
      foreach rr [list [expr {$tr + $d}] [expr {$tr - $d}]] {
        if {$rr < 0 || $rr >= $nr} continue
        set r [lindex $zrows $rr]
        set y [lindex $r 0]
        set rlo [expr {max($xlo, [lindex $r 2])}]; set rhi [expr {min($xhi, [lindex $r 3])}]
        set x [qcg_free_near $y $tx $w $rlo $rhi]
        if {$x >= 0} {
          $inst setOrient [lindex $r 1]
          $inst setLocation $x $y
          $inst setPlacementStatus FIRM
          lappend occ($y) [list $x [expr {$x + $w}]]
          set done 1; break
        }
      }
    }
    if {!$done} { error "QCG could not place [$inst getName] in zone $zn" }
    incr placed; incr i
  }
}
puts "QCG placed $placed station/repeater cells in [llength $qcg_zones] slabs"
# placement blockages everywhere outside the slabs (CTS / repair buffers land in slabs)
set zs [lsort -real -index 1 $qcg_zones]
set prev 0
set nb 0
foreach z [concat $zs [list [list end [expr {($qcg_axis eq "x" ? $W : $H) / double($dbu)}] 0]]] {
  set a $prev; set b [qcg_um [lindex $z 1]]
  if {$b > $a} {
    if {$qcg_axis eq "x"} { odb::dbBlockage_create $block $a 0 $b $H } else { odb::dbBlockage_create $block 0 $a $W $b }
    incr nb
  }
  if {[lindex $z 0] ne "end"} { set prev [qcg_um [lindex $z 2]] }
}
puts "QCG placement blockages: $nb"
# well taps / end caps exist for cells; none can sit in a blockage, and DPL refuses fixed cells outside usable rows
set nd 0
foreach inst [$block getInsts] {
  if {![string match TAPCELL* [[$inst getMaster] getName]]} continue
  set b [$inst getBBox]
  foreach bl [$block getBlockages] {
    set bb [$bl getBBox]
    if {[$b xMin] < [$bb xMax] && [$b xMax] > [$bb xMin] && [$b yMin] < [$bb yMax] && [$b yMax] > [$bb yMin]} {
      odb::dbInst_destroy $inst; incr nd; break
    }
  }
}
puts "QCG removed $nd tap/endcap cells inside blockages"
'''


def hook_pins(t):
    if t['name'] == 'A':
        cons = ['set_io_pin_constraint -pin_names [qcg_ports {^d\\[}] -region left:*',
                'set_io_pin_constraint -pin_names [qcg_ports {^q\\[}] -region right:*',
                'set_io_pin_constraint -pin_names {clk} -region top:*']
    else:
        z0 = t['zones'][0]
        tap_hi = round(z0[2] + 40.0, 2)
        cons = ['set_io_pin_constraint -pin_names [qcg_ports {^bd\\[}] -region bottom:*',
                'set_io_pin_constraint -pin_names [qcg_ports {^bq\\[}] -region top:*',
                f'set_io_pin_constraint -pin_names [concat [qcg_ports {{^tq\\[}}] {{rdy_t}}] -region right:0-{tap_hi}',
                'set_io_pin_constraint -pin_names {clk} -region bottom:*']
    return TCL_LIB + r'''
# PRE_IO_PLACEMENT: bus ports on the corridor ends, tile-edge pin row on the east edge (B); no ordering is forced,
# so the placer matches each pin to its fixed station flop.
proc qcg_ports {pattern} {
  set names {}
  foreach bt [[qcg_block] getBTerms] { if {[regexp -- $pattern [$bt getName]]} { lappend names [$bt getName] } }
  if {[llength $names] == 0} { error "QCG no port matches $pattern" }
  return $names
}
''' + '\n'.join(cons) + '\n'


def hook_grt(t):
    zl = ' '.join(f'{{{z} {lo} {hi}}}' for z, lo, hi in t['zones'])
    return TCL_LIB + f'''
# PRE_GLOBAL_ROUTE: r2 layer assignment.  The non-assigned same-direction layers {t["blocked"]} get zero capacity
# between the slabs (kept {GRT_KEEP} um clear of every slab so pin access inside a slab is untouched).
set qcg_axis {t["axis"]}
set qcg_zones {{{zl}}}
set qcg_blocked {{{' '.join(t["blocked"])}}}
set qcg_keep {GRT_KEEP}
set qcg_margin {CORE_MARGIN}
''' + r'''
set die [[qcg_block] getDieArea]
set dbu [qcg_dbu]
set W [expr {[$die xMax] / double($dbu)}]; set H [expr {[$die yMax] / double($dbu)}]
set zs [lsort -real -index 1 $qcg_zones]
set n 0
for {set i 0} {$i < [llength $zs] - 1} {incr i} {
  set a [expr {[lindex [lindex $zs $i] 2] + $qcg_keep}]
  set b [expr {[lindex [lindex $zs [expr {$i + 1}]] 1] - $qcg_keep}]
  if {$b <= $a} continue
  foreach l $qcg_blocked {
    if {$qcg_axis eq "x"} {
      set_global_routing_region_adjustment [list $a 0 $b $H] -layer $l -adjustment 1.0
    } else {
      set_global_routing_region_adjustment [list 0 $a $W $b] -layer $l -adjustment 1.0
    }
    incr n
  }
}
puts "QCG region adjustments: $n"
# FastRoute leaves the gcells on the die margin outside the core unadjusted (measured: edge chains detoured on the
# blocked layers there), so the margin strips between slabs also get physical obstructions.  The margin lies outside
# the core, where no PG shape exists.
set tech [ord::get_db_tech]
set blk [qcg_block]
set m [qcg_um $qcg_margin]
set no 0
for {set i 0} {$i < [llength $zs] - 1} {incr i} {
  set a [qcg_um [lindex [lindex $zs $i] 2]]
  set b [qcg_um [lindex [lindex $zs [expr {$i + 1}]] 1]]
  foreach l $qcg_blocked {
    set L [$tech findLayer $l]
    if {$qcg_axis eq "x"} {
      odb::dbObstruction_create $blk $L $a 0 $b $m
      odb::dbObstruction_create $blk $L $a [expr {[$die yMax] - $m}] $b [$die yMax]
    } else {
      odb::dbObstruction_create $blk $L 0 $a $m $b
      odb::dbObstruction_create $blk $L [expr {[$die xMax] - $m}] $a [$die xMax] $b
    }
    incr no 2
  }
}
puts "QCG margin obstructions: $no"
'''


GRT_KEEP = 2.0
LONG_HAUL_UM = 10.0                                     # audit: a blocked-layer run longer than this is haul
ACCESS_UM = 10.0                                        # audit: pin-access band around each slab
CORE_MARGIN = 1.08                                      # um core inset: PG and rows stop short of the ports


def hook_def():
    return TCL_LIB + r'''
# POST_DETAIL_ROUTE: routed DEF for the per-layer audit (tools/qwen_corridor_gate.py layer_audit).
write_def /work/qcg_route.def
puts "QCG wrote /work/qcg_route.def"
'''


def pdn(cov_name):
    cov, p, w = PG[cov_name], pg_pitch(cov_name), pg_width(cov_name)
    sp = round(p / 2 - w, 3)
    lo, hi = M6_PAIR
    # the M6 pair must sit in the M8 gap between a VSS stripe end and the next VDD stripe (40 nm spacing each side)
    o = PG_OFFSET                                        # pdngen offset = first (VSS) stripe centreline
    gaps = [(o + w / 2, o + w / 2 + sp), (o + 1.5 * w + sp, o + p - w / 2)]
    assert any(g0 <= lo - 0.04 and g1 >= hi + 0.04 for g0, g1 in gaps), (cov_name, gaps)
    assert abs(M6_PITCH / p - round(M6_PITCH / p)) < 1e-9
    return f'''# Generated by tools/qwen_corridor_gate.py.  Do not edit.
# Repo die grid (tools/chip_assembly/tcl/pdn_die.tcl) with the r2 {cov_name} M8/M9 coverage {cov} per net:
# {w} um stripes at a {p} um pitch (realised {w / p:.4f} per net; MAXWIDTH 2.0 forbids one wide strap and stripes stay
# under the 0.49975 um wide-metal spacing class).  No core ring (the block is a strip of a die).  The M8/M9 pitch
# divides the M6 strap pitch (10.8) and is offset so every M6 VDD/VSS pair lies in an M8 gap; the mesh then lands on
# M6 through M6-M9 stacked vias (V6/V7/V8 through M7 and M8), which replace pdn_die's parallel M6-M8 connect (that
# connect cannot land without overlap; pdngen refuses it as an unrepaired channel).  Harsher on M7/M8, never lighter.
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name {{CORE}} -power {{VDD}} -ground {{VSS}}
define_pdn_grid -name {{top}} -voltage_domains {{CORE}}
add_pdn_stripe -grid {{top}} -layer {{M1}} -width {{0.018}} -pitch {{0.54}} -offset {{0}} -followpins
add_pdn_stripe -grid {{top}} -layer {{M2}} -width {{0.018}} -pitch {{0.54}} -offset {{0}} -followpins
add_pdn_stripe -grid {{top}} -layer {{M5}} -width {{0.12}} -spacing {{0.072}} -pitch {{10.8}} -offset {{1.5}}
add_pdn_stripe -grid {{top}} -layer {{M6}} -width {{0.288}} -spacing {{0.096}} -pitch {{10.8}} -offset {{2.0}}
add_pdn_stripe -grid {{top}} -layer {{M8}} -width {{{w}}} -spacing {{{sp}}} -pitch {{{p}}} -offset {{{PG_OFFSET}}}
add_pdn_stripe -grid {{top}} -layer {{M9}} -width {{{w}}} -spacing {{{sp}}} -pitch {{{p}}} -offset {{{PG_OFFSET}}}
add_pdn_connect -grid {{top}} -layers {{M1 M2}}
add_pdn_connect -grid {{top}} -layers {{M2 M5}}
add_pdn_connect -grid {{top}} -layers {{M5 M6}}
add_pdn_connect -grid {{top}} -layers {{M6 M9}}
add_pdn_connect -grid {{top}} -layers {{M8 M9}}
'''


def files(chains=None):
    T = tests()
    out = {}
    for t in T.values():
        if chains:
            t = dict(t, chains=chains)
        low = t['name'].lower()
        out[f'{RTL_DIR}/{t["top"]}.v'] = rtl_a(t) if t['name'] == 'A' else rtl_b(t)
        out[f'{HOOK_DIR}/{low}_place.tcl'] = hook_place(t)
        out[f'{HOOK_DIR}/{low}_pins.tcl'] = hook_pins(t)
        out[f'{HOOK_DIR}/{low}_grt.tcl'] = hook_grt(t)
    out[f'{HOOK_DIR}/dont_touch.tcl'] = hook_dont_touch()
    out[f'{HOOK_DIR}/write_def.tcl'] = hook_def()
    for k in list(out):
        if k.startswith(HOOK_DIR) and not k.split('/')[-1].startswith('pdn_'):
            # ORFS sources step hooks inside a proc: run them in a namespace so their variables are shared
            out[k] = 'namespace eval ::qcg {\n' + out[k] + '\n}\n'
    for c in PG:
        out[f'{HOOK_DIR}/pdn_{c}.tcl'] = pdn(c)
    return out


def write(root: Path, chains=None):
    for rel, text in files(chains).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return sorted(files(chains))


# ------------------------------------------------------------------ launch
def argv(v, jobroot: Path, src_root: Path):
    P = plan()
    var = P['variants'][v]
    t = P['tests'][var['test']]
    low = t['name'].lower()
    L, Wd = var['length_um'], var['width_um']
    die = [0, 0, L, Wd] if t['axis'] == 'x' else [0, 0, Wd, L]
    core = [CORE_MARGIN, CORE_MARGIN, round(die[2] - CORE_MARGIN, 4), round(die[3] - CORE_MARGIN, 4)]
    job = jobroot / v
    hor, ver = ('M6 M8', 'M7 M9') if t['name'] == 'A' else ('M4 M6', 'M7 M9')
    a = ['python3', str(src_root / 'tools/run_abi3_physical_persistent.py'),
         '--persistent-workdir', str(job / 'work'), '--launch-receipt', str(job / 'receipt.json'),
         '--view', 'asap7', '--top', t['top'], '--source', f'{RTL_DIR}/{t["top"]}.v', '--clock-port', 'clk',
         '--clock-period-ns', str(PERIOD_NS), '--clock-uncertainty-ns', str(UNC_SETUP_NS),
         '--clock-uncertainty-hold-ns', str(UNC_HOLD_NS), '--orfs-corner', 'WC', '--hold-corners', 'WC,BC',
         '--false-path-io', '--io-delay-fraction', '0', '--stages', 'pnr', '--purpose', 'signoff_target',
         '--die-area', *map(str, die), '--core-area', *map(str, core), '--routing-layers', 'M2', 'M9',
         '--step-tcl', f'PRE_FLOORPLAN={HOOK_DIR}/dont_touch.tcl',
         '--step-tcl', f'PRE_GLOBAL_PLACE_SKIP_IO={HOOK_DIR}/{low}_place.tcl',
         '--step-tcl', f'PRE_IO_PLACEMENT={HOOK_DIR}/{low}_pins.tcl',
         '--step-tcl', f'PRE_GLOBAL_ROUTE={HOOK_DIR}/{low}_grt.tcl',
         '--step-tcl', f'POST_DETAIL_ROUTE={HOOK_DIR}/write_def.tcl',
         '--orfs-var', f'PDN_TCL=/src/{HOOK_DIR}/pdn_{var["pg"]}.tcl',
         '--orfs-var', f'IO_PLACER_H={hor}', '--orfs-var', f'IO_PLACER_V={ver}',
         '--orfs-var', 'PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks',
         '--orfs-var', 'DONT_BUFFER_PORTS=1', '--orfs-var', 'PLACE_DENSITY_LB_ADDON=',
         '--keep-heavy-artifacts', '--nickname-tag', 'qcg_' + v.lower(),
         '--source-root', str(src_root), '--output', str(job / 'physical.json')]
    return a


# ------------------------------------------------------------------ record
def parse_def_layers(def_path: Path, var, t):
    """Signal wire length (um) per layer, split into slab vs between-slab along the corridor axis."""
    txt = def_path.read_text()
    m = re.search(r'UNITS DISTANCE MICRONS (\d+)', txt)
    dbu = int(m.group(1))
    nets = txt[txt.index('\nNETS '):txt.index('END NETS')]
    zs = [(lo, hi) for _, lo, hi in t['zones']]
    ax = 0 if t['axis'] == 'x' else 1

    slabs = [(lo - GRT_KEEP, hi + GRT_KEEP) for lo, hi in zs]
    access = [(lo - ACCESS_UM, hi + ACCESS_UM) for lo, hi in zs]

    def split(a, b):
        """(in slab, in access band beyond the slab, beyond both) along the corridor axis."""
        a, b = min(a, b), max(a, b)
        ins = sum(max(0.0, min(b, hi) - max(a, lo)) for lo, hi in slabs)
        acc_ = sum(max(0.0, min(b, hi) - max(a, lo)) for lo, hi in access) - ins
        return ins, acc_, (b - a) - ins - acc_
    acc = {}

    def add(layer, where, ln):
        if ln > 0:
            acc[(layer, where)] = acc.get((layer, where), 0.0) + ln
    longest = [0.0, None, None]
    for stmt in nets.split(';'):
        if 'ROUTED' not in stmt:
            continue
        mm_net = stmt.strip().split()[1] if stmt.strip().startswith('-') else None
        for seg in re.split(r'\b(?:ROUTED|NEW)\b', stmt)[1:]:
            mm = re.match(r'\s*(M\d+)\s+(.*)', seg, re.S)
            if not mm:
                continue
            layer, rest = mm.group(1), re.sub(r'RECT\s*\([^)]*\)|VIRTUAL\s*\([^)]*\)', ' ', mm.group(2))
            pts, last = [], None
            for x, y in re.findall(r'\(\s*(\S+)\s+(\S+)(?:\s+\S+)?\s*\)', rest):
                px = last[0] if x == '*' else int(x)
                py = last[1] if y == '*' else int(y)
                last = (px, py)
                pts.append(last)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                a0, a1 = (x0, x1) if ax == 0 else (y0, y1)
                p0, p1 = (y0, y1) if ax == 0 else (x0, x1)
                if a0 != a1:                                  # along the corridor
                    ins, near, out = split(a0 / dbu, a1 / dbu)
                    if layer in t['blocked'] and out > longest[0]:
                        longest[:] = [out, layer, mm_net]
                    add(layer, 'slab', ins)
                    add(layer, 'access', near)
                    add(layer, 'between', out)
                elif p0 != p1:                                # across the corridor
                    c = a0 / dbu
                    add(layer, 'slab' if any(lo <= c <= hi for lo, hi in slabs) else
                        'access' if any(lo <= c <= hi for lo, hi in access) else 'between', abs(p1 - p0) / dbu)
    per = {}
    for (layer, where), ln in sorted(acc.items()):
        per.setdefault(layer, {})[where] = round(ln, 1)
    between = sum(v.get('between', 0) for v in per.values())
    off = sum(v.get('between', 0) for l, v in per.items() if l in t['blocked'])
    near = sum(v.get('access', 0) for l, v in per.items() if l in t['blocked'])
    return dict(basis=f'routed DEF signal + clock wires; slab = slab +/- {GRT_KEEP} um (GRT keep), access = a further '
                      f'{ACCESS_UM - GRT_KEEP} um band (station / repeater pin access), between = the rest of the span',
                per_layer_um=per, between_slab_um=round(between, 1),
                between_slab_on_blocked_same_direction_layers_um=round(off, 1),
                access_band_on_blocked_same_direction_layers_um=round(near, 1),
                longest_blocked_layer_run_beyond_access=dict(um=round(longest[0], 2), layer=longest[1], net=longest[2]),
                assigned_share_of_between_slab=round(sum(per.get(l, {}).get('between', 0) for l in t['layers'])
                                                     / between, 4) if between else None)


def parse_logs(work: Path):
    logs = {p.name: p.read_text(errors='replace') for p in work.rglob('*.log') if p.is_file()}
    grt = next((v for k, v in logs.items() if k.startswith('5_1_grt')), '')
    drt = next((v for k, v in logs.items() if k.startswith('5_2_route')), '')
    out = {}
    tot = re.findall(r'Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', grt)
    if tot:
        out['grt_final_total'] = dict(resource=int(tot[-1][0]), demand=int(tot[-1][1]), usage_pct=float(tot[-1][2]),
                                      overflow=int(tot[-1][5]))
        out['grt_first_total'] = dict(usage_pct=float(tot[0][2]), overflow=int(tot[0][5]))
    lay = re.findall(r'^(M\d)\s+(Horizontal|Vertical)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', grt, re.M)
    if lay:
        last = {}
        for l in lay:
            last[l[0]] = dict(dir=l[1], resource=int(l[2]), demand=int(l[3]), usage_pct=float(l[4]), overflow=int(l[7]))
        out['grt_final_per_layer'] = last
    out['grt_congestion_iterations'] = len(re.findall(r'\[INFO GRT-0101\]|Running extra iterations|congestion iteration', grt))
    out['grt_errors'] = re.findall(r'\[ERROR GRT-\d+\].*', grt)[:3]
    viol = [int(x) for x in re.findall(r'Number of violations = (\d+)', drt)]
    out['drt_violations_by_iteration'] = viol
    out['drt_final_violations'] = viol[-1] if viol else None
    out['drt_errors'] = re.findall(r'\[ERROR DRT-\d+\].*', drt)[:3]
    out['drt_completed'] = 'Complete detail routing' in drt or bool(re.search(r'Total wire length = ', drt))
    return out


STA_TCL = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(QCG_LIBTAG)_*.lib*]] { read_liberty $f }
read_db $::env(QCG_ODB)
read_sdc $::env(QCG_SDC)
read_spef $::env(QCG_SPEF)
set_propagated_clock [all_clocks]
report_units
puts "QCGSTA setup"; report_worst_slack -max -digits 2
puts "QCGSTA hold";  report_worst_slack -min -digits 2
report_tns -digits 2
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded
set nv 0; set nh 0; set pins [get_pins -hierarchical qs*/D]
foreach p $pins {
  if {[get_property $p slack_max] < 0} { incr nv }
  if {[get_property $p slack_min] < 0} { incr nh }
}
puts "QCGSTA failing_D setup $nv hold $nh of [llength $pins]"
'''


def corner_sta(work: Path, nickname: str):
    hits = sorted(work.rglob(f'results/asap7/{nickname}/base'))
    if not hits:
        return dict(status='missing_results_dir')
    res = hits[0]
    work = res.parents[3]                                 # the ORFS case dir mounted as /work
    odb, sdc, spef = res / '6_final.odb', res / '6_final.sdc', res / '6_final.spef'
    if not (odb.is_file() and sdc.is_file() and spef.is_file()):
        return dict(status='missing_final_artifacts', have=[p.name for p in (odb, sdc, spef) if p.is_file()])
    (work / 'qcg_sta.tcl').write_text(STA_TCL)
    rel = lambda p: '/work/' + str(p.relative_to(work))
    cmd = ['docker', 'run', '--rm', '-v', f'{work}:/work', '-e', f'QCG_ODB={rel(odb)}', '-e', f'QCG_SDC={rel(sdc)}',
           '-e', f'QCG_SPEF={rel(spef)}', 'openroad/orfs:latest', 'bash', '-lc',
           'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/qcg_sta.tcl']
    out = dict(status='ran', basis='OpenSTA on 6_final.odb + RCX 6_final.spef, one liberty corner per run')
    for corner, tag in (('ss', 'SS'), ('ff', 'FF')):
        c = cmd[:3] + ['-e', f'QCG_LIBTAG={tag}'] + cmd[3:]
        p = subprocess.run(c, capture_output=True, text=True)
        (work / f'qcg_sta_{corner}.log').write_text(p.stdout + p.stderr)
        if p.returncode:
            out['status'] = f'{corner}_exit_{p.returncode}'
        tu = re.search(r'time\s+1(\S*)s', p.stdout)
        scale = {'p': 1e-3, 'n': 1.0}.get(tu.group(1) if tu else 'p', 1e-3)
        for k in ('setup', 'hold'):
            m = re.search(rf'QCGSTA {k}\s+worst slack (?:max|min) (\S+)', p.stdout)
            out[f'{corner}_{k}_ns'] = round(float(m.group(1)) * scale, 5) if m else None
        m = re.search(r'QCGSTA failing_D setup (\d+) hold (\d+) of (\d+)', p.stdout)
        if m:
            out[f'{corner}_station_D_pins'] = int(m.group(3))
            out[f'{corner}_failing_D_setup'] = int(m.group(1))
            out[f'{corner}_failing_D_hold'] = int(m.group(2))
    return out


def record(v, jobroot: Path, src_root: Path):
    P = plan()
    var = P['variants'][v]
    t = P['tests'][var['test']]
    job = jobroot / v
    work = job / 'work'
    phys = json.loads((job / 'physical.json').read_text()) if (job / 'physical.json').is_file() else None
    receipt = json.loads((job / 'receipt.json').read_text()) if (job / 'receipt.json').is_file() else None
    nick = f'opentallas_{t["top"]}_asap7_qcg_{v.lower()}'
    logs = parse_logs(work)
    dpath = next(iter(sorted(work.rglob('qcg_route.def'))), work / 'qcg_route.def')
    audit = parse_def_layers(dpath, var, t) if dpath.is_file() else dict(status='no routed DEF')
    sta = corner_sta(work, nick) if logs.get('drt_final_violations') is not None else dict(status='not routed')
    m = (phys or {}).get('place_and_route', {}).get('metrics', {}) if phys else {}
    grt_ovf = logs.get('grt_final_total', {}).get('overflow')
    drt = logs.get('drt_final_violations')
    routed_clean = bool(grt_ovf == 0 and drt == 0 and m.get('drc_errors', None) == 0)
    timing = dict(ss_setup_wns_ns=sta.get('ss_setup_ns'), ff_hold_wns_ns=sta.get('ff_hold_ns'))
    timing_met = (timing['ss_setup_wns_ns'] is not None and timing['ss_setup_wns_ns'] >= 0 and
                  timing['ff_hold_wns_ns'] is not None and timing['ff_hold_wns_ns'] >= 0)
    blk, btw = audit.get('between_slab_on_blocked_same_direction_layers_um'), audit.get('between_slab_um')
    run = (audit.get('longest_blocked_layer_run_beyond_access') or {}).get('um')
    # long haul stays on the assigned layers: blocked-layer wire beyond the access bands is <= 5% of the between-slab
    # wire and no single blocked-layer run exceeds LONG_HAUL_UM (short jogs around PG via stacks are routing, not haul)
    layer_ok = bool(btw) and blk is not None and blk <= 0.05 * btw and run is not None and run <= LONG_HAUL_UM
    verdict = ('ROUTED_CLEAN' if routed_clean else
               'GRT_OVERFLOW' if grt_ovf else
               'DRT_VIOLATIONS' if drt else 'INCOMPLETE')
    return dict(
        schema='opentallas.qwen-corridor-gate.v1', variant=v, test=t['name'], top=t['top'],
        question='does the r2 corridor route at its netted width (demand / raw same-direction tracks on the assigned '
                 'layers), with real stations, repeaters, CTS, PG and tile pins, and close SS setup / FF hold?',
        geometry=dict(width_um=var['width_um'], length_um=var['length_um'], axis=t['axis'], zones=t['zones'],
                      demand_tracks=var['demand'], assigned_layers=t['layers'], raw_tracks=var['raw_tracks'],
                      demand_over_raw=var['ratio'], ratio_tag=var['ratio_tag'],
                      r2_width_um=t['width_r2'], segment_um=t['seg_um'], repeaters_per_segment=t['reps'],
                      chains=t['chains'], gr_blocked_between_slabs=t['blocked']),
        pg=dict(region=var['pg'], r2_cov_per_net=var['pg_cov_per_net'], stripe_um=var['pg_stripe_um'],
                pitch_um=var['pg_pitch_um'], realised_cov_per_net=var['pg_cov_realised']),
        clock=dict(period_ns=PERIOD_NS, setup_uncertainty_ns=UNC_SETUP_NS, hold_uncertainty_ns=UNC_HOLD_NS,
                   primary_corner='WC (SS)', repair_corners=['WC', 'BC']),
        verdict=verdict, routed_clean=routed_clean, timing_met=timing_met,
        layer_assignment_held=layer_ok,
        grt=dict(final=logs.get('grt_final_total'), first=logs.get('grt_first_total'),
                 per_layer=logs.get('grt_final_per_layer'), errors=logs.get('grt_errors')),
        drt=dict(final_violations=drt, by_iteration=logs.get('drt_violations_by_iteration'),
                 errors=logs.get('drt_errors')),
        timing=dict(**timing, corner_sta=sta,
                    orfs_finish=dict(setup_wns_ns=m.get('setup_wns_ns'), hold_wns_ns=m.get('hold_wns_ns'),
                                     setup_violations=m.get('setup_violations'),
                                     hold_violations=m.get('hold_violations'))),
        orfs_metrics={k: m.get(k) for k in ('drc_errors', 'antenna_violating_nets', 'max_slew_violations',
                                            'max_cap_violations', 'standard_cell_count', 'instance_count',
                                            'routed_wirelength_um', 'vias', 'utilization_fraction')},
        driver_status=(phys or {}).get('status'), driver_flow_completed=(phys or {}).get('flow_completed'),
        layer_audit=audit,
        launch=dict(receipt_status=(receipt or {}).get('status'), driver_args=(receipt or {}).get('driver_args'),
                    git=(phys or {}).get('git'), elapsed_seconds=(phys or {}).get('elapsed_seconds')),
        sources_sha256={rel: sha(ROOT / rel) for rel in [R2_REC, 'tools/qwen_corridor_gate.py',
                                                          f'{RTL_DIR}/{t["top"]}.v'] +
                        [f'{HOOK_DIR}/{n}' for n in (f'{t["name"].lower()}_place.tcl', f'{t["name"].lower()}_pins.tcl',
                                                     f'{t["name"].lower()}_grt.tcl', 'dont_touch.tcl', 'write_def.tcl',
                                                     f'pdn_{var["pg"]}.tcl')]},
        claim_boundary='ASAP7 block-level strip of one corridor at its r2 width: the router sees only the tracks inside '
                       'the corridor width; neighbouring tiles, crossing corridors and the die-level clock are absent. '
                       'GRT capacity of the non-assigned same-direction layers is zeroed between slabs to enforce the '
                       'r2 layer assignment; detail route is audited per layer.')


# ------------------------------------------------------------------ die statement
def die_statement(ratios: dict):
    """Die outline at the measured routable ratio per corridor class (r2 build_frame, unchanged)."""
    sys.path.insert(0, str(ROOT / 'tools'))
    import qwen_rom_floorplan_nearhbm_r2 as R  # noqa
    F = R.F
    r1, _ = F.build()
    pr, cool = R.load(F.P['pricing']), R.load(F.P['cooling'])
    c17 = R.load(R.P2['credit17'])
    f1 = r1['floorplan']
    rp = R.region_power(r1, pr, cool, c17, None)
    cov = {reg: round(R.coverage_needed(max(rp['scenarios'][s][reg]['peak'] for s in ('A', 'B'))), 4)
           for reg in ('tile_field', 'hub', 'strip')}
    ev = R.corridor_evidence()
    link = r1['routes']['corridors']['per_link_tracks']
    cor = dict(
        tile_column=R.corridor('tile column corridor', f1['tile_slot']['corridor_um'], ('M7', 'M9'), cov['tile_field'],
                               F.NONFILL_CUT_TRACKS, 'tile_field'),
        horizontal_link=R.corridor('h', f1['link_channels']['horizontal_um'], ('M6', 'M8'), cov['tile_field'], link,
                                   'tile_field', clock_on='M6'),
        vertical_spine=R.corridor('v', f1['link_channels']['vertical_um'], ('M7', 'M9'), cov['hub'], 2 * link, 'hub',
                                  clock_on='M7'),
        in_strip_fan=R.corridor('s', f1['shoreline']['near_hbm_strip_um'], ('M7', 'M9'), cov['strip'], link, 'strip',
                                clock_on='M7'))
    kv = R.kv_reservation(pr)
    lw = R.long_wires(r1, dict(array_um=f1['array_um'], tile_corridor_um=f1['tile_slot']['corridor_um']), ev,
                      f1['tile_slot']['h_um'])
    areas = dict(row_engine_cells_mm2=r1['row_engine']['area_um2']['hi'] * 24 / 1e6,
                 hub_contents_mm2=f1['spine']['hub_contents_mm2'], kv_kept_mm2=kv['reservation_mm2'],
                 long_wire_mm2=lw['station_FF_mm2'] + lw['repeater_mm2'])
    cts0 = R.cts_plan(f1, r1, areas)
    base = R.build_frame(r1, pr, cor, kv['reservation_mm2'], lw, cts0)
    cc, widths = {}, {}
    for k, c in cor.items():
        d = ratios.get(k)
        per_um = sum(1 / R.PITCH_UM[l] for l in c['layers'])
        w = c['width_r2_um'] if d is None else max(c['width_r2_um'], R.snap_up(c['demand_tracks'] / d / per_um, F.SNAP_X))
        cc[k] = dict(c, width_r2_um=w)
        widths[k] = dict(r2_um=c['width_r2_um'], gated_um=w, density_used=d)
    fr = R.build_frame(r1, pr, cc, kv['reservation_mm2'], lw, cts0)
    return dict(r2_die_mm2=base['die_mm2'], gated_die_mm2=fr['die_mm2'], within_815=fr['within_815'],
                margin_to_815_mm2=fr['margin_to_815_mm2'], die_um=fr['die_um'], fits_26x33=fr['fits_26x33'],
                corridor_widths=widths)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'write', 'argv', 'record', 'die'])
    ap.add_argument('--variant')
    ap.add_argument('--jobroot', type=Path)
    ap.add_argument('--src-root', type=Path, default=ROOT)
    ap.add_argument('--chains', type=int, help='smoke only: fewer chains (never for evidence)')
    ap.add_argument('--ratios', help='die: json {corridor: density}')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    if a.mode == 'plan':
        print(json.dumps(plan(), indent=1))
    elif a.mode == 'write':
        print('\n'.join(write(ROOT, a.chains)))
    elif a.mode == 'argv':
        print(json.dumps(argv(a.variant, a.jobroot, a.src_root)))
    elif a.mode == 'record':
        rec = record(a.variant, a.jobroot, a.src_root)
        if a.out:
            if a.out.exists():
                raise SystemExit(f'{a.out} exists: records are never overwritten')
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
        print(json.dumps({k: rec[k] for k in ('variant', 'verdict', 'routed_clean', 'timing_met',
                                              'layer_assignment_held')} | dict(grt=rec['grt']['final'],
                                                                              drt=rec['drt']['final_violations'],
                                                                              timing=rec['timing']['ss_setup_wns_ns'])))
    elif a.mode == 'die':
        rec = die_statement(json.loads(a.ratios or '{}'))
        print(json.dumps(rec, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
