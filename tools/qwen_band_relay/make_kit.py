#!/usr/bin/env python3
"""q15 r13 BAND relay successor: kit inputs from the station plan.

Writes (repo-relative):
  tools/ref_tile/specs_q_compute_native/qfd_sp_band_lanes_relay.json   ref_tile source spec (lanes MX, 70 clock ports)
  physical/qwen_band_relay_1015/assigned_pins.tcl                    c17 data pins unchanged + clock entries
  physical/qwen_band_relay_1015/station_table.tcl                    planned station blocks (lane.group.stage -> x y)
  physical/qwen_band_relay_1015/station_place.tcl                    pre-GPL: station flops FIRM in their blocks
  physical/qwen_band_relay_1015/station_release.tcl                  post-GPL: release them (DPL legalises locally)
Clock entries: lanes at their (mirrored) child ck pin; std-cell roots at an interior free M5 point: station roots at the
member station nearest the cluster centroid, face roots next to their port segment, fault roots near their stages."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
plan = json.loads((ROOT / 'results/rtl/qwen_band_relay_1015/station_plan.json').read_text())
Q = ROOT / 'physical/ref_tile/qfd_sp_band_lanes_quarter'
qspec = json.loads((ROOT / 'tools/ref_tile/specs_q_compute_native/qfd_sp_band_lanes_quarter.json').read_text())
LANES = plan['lanes']; LW, LH = 259.2, 151.2; W, H = 881.28, 1131.84
lef = (ROOT / 'physical/ref_tile/qfd_bl_lane_rr/views/qfd_bl_lane/qfd_bl_lane.lef').read_text()
m = re.search(r'PIN ck\n.*?RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', lef, re.S)
ckx, cky = (float(m.group(1)) + float(m.group(3))) / 2, (float(m.group(2)) + float(m.group(4))) / 2
m = re.search(r'PIN f\n.*?RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', lef, re.S)
fx = (float(m.group(1)) + float(m.group(3))) / 2
def snap(v, g=0.048):            # M5 track lattice used by the existing entries (x 122.94 = 2561.25 * 0.048 ...)
    return round(round(v / g) * g, 4)
pins = [l for l in (Q / 'assigned_pins.tcl').read_text().splitlines()
        if l.startswith('place_pin') and not re.search(r'\{ck(_l\d+)?\}', l)]
clk = {}
for l, (x0, y0) in enumerate(LANES):           # MX: the child ck pin (LEF y = top face) lands on the lane's bottom edge
    clk[f'ck_l{l}'] = (round(x0 + ckx, 4), round(y0 + LH - cky, 4))
clk['ck'] = (snap(30.0), snap(8.0))           # S-face straps / reset pin flops (rst_n 20.0, b0 25.0, lnk 32.0 on S)
for s in range(4):                            # ty face quarters x 33.4..426.5, tw 453.4..846.5: entry 10 um inside
    clk[f'ck_fn[{s}]'] = (snap(33.42 + 98.28 * (s + 0.5)), snap(H - 10.0))
    clk[f'ck_fn[{4 + s}]'] = (snap(453.42 + 98.28 * (s + 0.5)), snap(H - 10.0))
clk['ck_fe0'] = (snap(W - 10.0), snap(435.0))  # pw 325..375, f 400, c 429, f_up 460, pw_l 495..545
clk['ck_fe1'] = (snap(W - 10.0), snap(750.0))  # tt 676..824
for r in plan['roots']:
    cx, cy = r['centroid']
    mem = [s['xy'] for s in plan['stations'] if s['root'] == r['root']]
    bx, by = min(mem, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))
    clk[f"ck_st[{r['root']}]"] = (snap(bx), snap(by))
for q in range(4):                            # quarter q4 stage: below lane 4q's f pin (lane bottom after MX)
    x0, y0 = LANES[4 * q]
    clk[f'ck_fq[{q}]'] = (snap(x0 + fx + 8.0), snap(y0 - 8.0))
clk['ck_fj'] = (snap(W - 14.0), snap(470.0))
for name, (x, y) in clk.items():
    pins.append(f'place_pin -pin_name {{{name}}} -layer M5 -location {{{x:.4f} {y:.4f}}}')
OUT = ROOT / 'physical/qwen_band_relay_1015'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'assigned_pins.tcl').write_text('\n'.join(pins) + '\n')
# ---- station blocks: each station's flops in a compact block at its planned point, kept off the lanes ----------------
GROUPS = {'TW': ['tw'], 'TY': ['ty'], 'TT': ['tt'], 'CP': ['c', 'pw'], 'S': ['st']}
WIDTH = {'TW': 256, 'TY': 256, 'TT': 98, 'CP': 58, 'S': 8}
COLS = 16; FW, RH = 1.296, 0.27              # block pitch: 16 flop columns x 1.296 um, rows 0.27 um
def inside_lane(x0, y0, x1, y1):
    return any(x1 > lx - 2 and x0 < lx + LW + 2 and y1 > ly - 2 and y0 < ly + LH + 2 for lx, ly in LANES)
used = []
def overlaps(r):
    return any(r[2] > u[0] and r[0] < u[2] and r[3] > u[1] and r[1] < u[3] for u in used)
tbl = []
for s in plan['stations']:
    n = WIDTH[s['group']]; rows = (n + COLS - 1) // COLS
    bw, bh = COLS * FW, rows * RH
    px, py = s['xy']
    best = None
    for d in range(0, 400):                   # spiral search on a 1.08 um step for a free, lane-clear block
        for dx, dy in ((0, 0),) if d == 0 else [(d, 0), (-d, 0), (0, d), (0, -d), (d, d), (-d, -d), (d, -d), (-d, d)]:
            x0 = px - bw / 2 + dx * 1.08; y0 = py - bh / 2 + dy * 1.08
            r = (x0, y0, x0 + bw, y0 + bh)
            if r[0] < 2 or r[1] < 2 or r[2] > W - 2 or r[3] > H - 2 or inside_lane(*r) or overlaps(r):
                continue
            best = r; break
        if best:
            break
    assert best, s
    used.append(best)
    tbl.append(f"dict set ::ot_band_st {s['lane']}.{s['group']}.{s['stage']} {{{best[0]:.3f} {best[1]:.3f}}}")
(OUT / 'station_table.tcl').write_text("# generated by tools/qwen_band_relay/make_kit.py from results/rtl/qwen_band_relay_1015/station_plan.json\n"
                                       "set ::ot_band_st [dict create]\n" + '\n'.join(tbl) + '\n')
(OUT / 'station_place.tcl').write_text(r'''# q15 r13 BAND relay: PRE_GLOBAL_PLACE (pin_hook_before_flops) -- every station flop FIRM in its planned block
# (station_table.tcl: lane.group.stage -> block lower-left; 16 columns x 1.296 um, rows of one site row), so the relay
# hop lengths are the planned ones (<= 666 um) instead of whatever a wirelength placer picks on a straight line.  The
# flops are released after global placement (station_release.tcl) and legalised by DPL inside their block.
source /src/physical/qwen_band_relay_1015/station_table.tcl
set ot_b [ord::get_db_block]
set ot_dbu [$ot_b getDbUnitsPerMicron]
set ot_row [lindex [$ot_b getRows] 0]
set ot_site [$ot_row getSite]
set ot_sw [$ot_site getWidth]; set ot_sh [$ot_site getHeight]
set ot_core [$ot_b getCoreArea]; set ot_cx [$ot_core xMin]; set ot_cy [$ot_core yMin]
set ot_gmap [dict create tw TW ty TY tt TT c CP pw CP st S]
set ot_n 0; set ot_miss 0; set ::ot_band_firm {}
foreach i [$ot_b getInsts] {
  set nm [string map {\\ {}} [$i getName]]
  if {![regexp {g_lane\[(\d+)\]\.(tw|ty|tt|c|pw|st)_s([12])\[(\d+)\]} $nm -> l g s bit]} continue
  if {![[$i getMaster] isSequential]} continue
  set key "$l.[dict get $ot_gmap $g].$s"
  if {![dict exists $::ot_band_st $key]} { incr ot_miss; continue }
  if {$g eq "pw"} { set bit [expr {$bit + 26}] }
  lassign [dict get $::ot_band_st $key] bx by
  set x [expr {int(round(($bx + ($bit % 16) * 1.296) * $ot_dbu))}]
  set y [expr {int(round($by * $ot_dbu)) + ($bit / 16) * $ot_sh}]
  set x [expr {$ot_cx + (($x - $ot_cx) / $ot_sw) * $ot_sw}]
  set y [expr {$ot_cy + (($y - $ot_cy) / $ot_sh) * $ot_sh}]
  $i setLocation $x $y
  $i setPlacementStatus FIRM
  lappend ::ot_band_firm $i
  incr ot_n
}
puts "OT_BAND_STATIONS placed $ot_n station flops FIRM ($ot_miss without a planned block)"
if {$ot_n != 16 * 2 * (256 + 256 + 98 + 58 + 8)} { error "OT_BAND_STATIONS expected [expr {16 * 2 * 676}] station flops, found $ot_n" }
''')
(OUT / 'station_release.tcl').write_text(r'''# q15 r13 BAND relay: POST_GLOBAL_PLACE -- release the FIRM station flops (station_place.tcl) for resize / DPL
set ot_b [ord::get_db_block]; set ot_n 0
foreach i [$ot_b getInsts] {
  set nm [string map {\\ {}} [$i getName]]
  if {![regexp {g_lane\[\d+\]\.(tw|ty|tt|c|pw|st)_s[12]\[\d+\]} $nm]} continue
  if {[$i getPlacementStatus] eq "FIRM"} { $i setPlacementStatus PLACED; incr ot_n }
}
puts "OT_BAND_STATIONS released $ot_n station flops"
''')
# ---- source spec --------------------------------------------------------------------------------------------------
sp = json.loads(json.dumps(qspec))
sp['name'] = 'qfd_sp_band_lanes_relay'
cports = ['ck'] + [f'ck_l{l}' for l in range(16)] + [f'ck_fn[{s}]' for s in range(8)] + ['ck_fe0', 'ck_fe1'] + \
         [f"ck_st[{r['root']}]" for r in plan['roots']] + [f'ck_fq[{q}]' for q in range(4)] + ['ck_fj']
sp['clock_ports'] = cports
roots = [c for c in cports if not c.startswith('ck_l')]
sp['clock_cts_roots'] = roots
sp['required_hybrid_roots'] = {'standard_cell_cts': roots,
                               'hard_child_entry': {f'ck_l{l}': f'u_core.g_lane[{l}].u_lane/ck' for l in range(16)}}
for c, (lx, ly) in zip(sp['children'], LANES):
    c['inst'] = c['inst'].replace('g_lane', 'u_core.g_lane'); c['orient'] = 'MX'
sp['sources'] = ['rtl/qwen_sys/band_fault_tree_20261015/ot_qfd_band_fault_tree3.sv', 'rtl/qwen_sys/band_relay_20261015/ot_qfd_band_relay.sv']
sp['defines'] = []
sp.pop('hard_define', None)
sp['io_tcl'] = 'physical/qwen_band_relay_1015/assigned_pins.tcl'
sp['pins'] = {f: [p for p in v if p != 'ck'] for f, v in sp['pins'].items()}
# clock entries are interior M5 points (assigned_pins.tcl); faces only book-keep the base names
sp['pins']['S'] += ['ck', 'ck_fq']; sp['pins']['N'] += ['ck_fn']; sp['pins']['E'] += ['ck_fe0', 'ck_fe1', 'ck_fj']; sp['pins']['W'] += ['ck_st']
sp['pin_ranges'] = {k: v for k, v in sp['pin_ranges'].items() if k != 'ck'}
sp['pin_hook_before_flops'] = ['physical/qwen_band_relay_1015/station_place.tcl']
sp['orfs_vars'] = {'POST_GLOBAL_PLACE_TCL': 'physical/qwen_band_relay_1015/station_release.tcl',
                   'POST_RESIZE_TCL': 'physical/common_flow/post_resize_relocate.tcl'}
sp['structural_change'] = (
    'q15 r13 BAND relay successor (claude/q15-band-successor). Measured predecessor failure: one std-cell root over 10,798 '
    'pin flops on three faces (TT 997..1756 ps) AND single-cycle port<->lane paths of 1.4-1.8 mm (c17 pins interleave each '
    "lane's 256 tw/ty bits over the whole face). Fix: lanes MX (tw/ty face toward N), two relay stations per lane per bus "
    'group (TW, TY, TT, CP, S) at planned points (worst planned hop 666 um), station flops on 42 local std-cell roots, '
    'face pin flops on 12 segment roots, Codex tree3 valid/fault (3 edges). Edges: lane inputs +2, round trip +2 LNK units '
    '(pw/f +4, returned tt +4), ty +8. Exact equivalence vs predecessor: rtl/test/qwen_band_relay (3 mutants fail).')
sp['reroute_reason'] = {'kind': 'rtl_change', 'source': 'results/rtl/qwen_band_relay_1015/station_plan.json', 'cell': 'qfd_sp_band_lanes',
                        'why': 'structural: relay stations + local roots replace the 10.8k-flop single root and 1.8 mm single-cycle paths'}
job = sp['job']
job['owner'] = 'Claude:q15_band_helper'; job['branch'] = 'claude/q15-band-successor'; job['tag'] = 'rl1'
job['purpose'] = 'BAND relay successor: 16 CLOSED lanes MX, 2 relay stations per lane/group, 70 clock entries'
job['extra_paths'] = sorted(set(job['extra_paths'] + ['rtl/test/qwen_band_relay', 'rtl/qwen_sys/band_relay_20261015',
                                                      'rtl/qwen_sys/band_fault_tree_20261015', 'physical/qwen_band_relay_1015']))
job['benches'] = [
    {'name': 'equiv_relay_vs_predecessor', 'cmd': 'bash rtl/test/qwen_band_relay/run_equiv.sh {RUN}/bench/equiv 0',
     'expect': 'pass', 'pass_regex': '^BAND_RELAY_EQUIV PASS', 'threads': 8, 'peak_ram_gb': 24, 'needs': ['verilator']},
    {'name': 'equiv_mut1_lnk_short', 'cmd': 'bash rtl/test/qwen_band_relay/run_equiv.sh {RUN}/bench/m1 1',
     'expect': 'fail', 'fail_regex': '^BAND_RELAY_EQUIV FAIL', 'threads': 8, 'peak_ram_gb': 24, 'needs': ['verilator']},
    {'name': 'equiv_mut2_station_skip', 'cmd': 'bash rtl/test/qwen_band_relay/run_equiv.sh {RUN}/bench/m2 2',
     'expect': 'fail', 'fail_regex': '^BAND_RELAY_EQUIV FAIL', 'threads': 8, 'peak_ram_gb': 24, 'needs': ['verilator']},
    {'name': 'equiv_mut3_fault_drop', 'cmd': 'bash rtl/test/qwen_band_relay/run_equiv.sh {RUN}/bench/m3 3',
     'expect': 'fail', 'fail_regex': '^BAND_RELAY_EQUIV FAIL', 'threads': 8, 'peak_ram_gb': 24, 'needs': ['verilator']},
    {'name': 'fault_tree3_formal', 'cmd': 'bash physical/qwen_band_fault_tree_1015/run_proofs.sh {RUN}/bench/tree3',
     'expect': 'pass', 'pass_regex': 'BAND_TREE PASS', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['yosys', 'iverilog']}]
job['extra_paths'] = sorted(set(job['extra_paths'] + ['physical/qwen_band_fault_tree_1015']))
job['views_to'] = 'physical/ref_tile/qfd_sp_band_lanes_relay/views'
job['record_to'] = 'results/rtl/ref_tile/qfd_sp_band_lanes_relay'
(ROOT / 'tools/ref_tile/specs_q_compute_native/qfd_sp_band_lanes_relay.json').write_text(json.dumps(sp, indent=1) + '\n')
print(f'clock ports {len(cports)} (std roots {len(roots)}), stations {len(tbl)}, pins {len(pins)}')
