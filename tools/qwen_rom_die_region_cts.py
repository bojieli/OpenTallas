#!/usr/bin/env python3
"""Qwen3-8B ROM die: clock-tree synthesis of one decision-C clock region on the real die geometry.

The die has no single synchronous tree (results/rtl/qwen_rom_fulldie_20261003 README (d)); decision C gives every
4 x 4-tile block, spine band, strip third and IO block its own tree, fed by a trunk, with mesochronous FIFOs at the
region boundaries.  This vehicle builds one region exactly as the die places it: every element abstract of the region
FIXED at its die position (the real-technology LEF of case (a)), standard-cell rows everywhere the elements leave free
(corridors, channels, gaps), and one clock sink flop at the clock entry of every element (the element's own tree
starts there; its internal insertion is measured in the element's closure).  OpenROAD TritonCTS builds the region tree
from the trunk tap on the region edge, the buffers are legalised, and OpenSTA reports, with the propagated clock at
the SS and FF libraries, the insertion and the skew between every pair of sinks whose elements exchange a die-level
bus (the pairs a die-level stage launches and captures across), against the measured wire stage's slack.

    python3 tools/qwen_rom_die_region_cts.py --region creg_t0_1 --work W  <plan args as qwen_rom_die_path_sta.py>
    # then on the compute host: run_case.sh W run.tcl run.log 8 32
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie_b3r2 as B   # noqa: E402

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
LIBS = {'SS': ['AO_RVT_SS_nldm_211120.lib.gz', 'INVBUF_RVT_SS_nldm_220122.lib.gz', 'OA_RVT_SS_nldm_211120.lib.gz',
               'SEQ_RVT_SS_nldm_220123.lib', 'SIMPLE_RVT_SS_nldm_211120.lib.gz'],
        'FF': ['AO_RVT_FF_nldm_211120.lib.gz', 'INVBUF_RVT_FF_nldm_220122.lib.gz', 'OA_RVT_FF_nldm_211120.lib.gz',
               'SEQ_RVT_FF_nldm_220123.lib', 'SIMPLE_RVT_FF_nldm_211120.lib.gz']}
SINK = 'DFFHQNx1_ASAP7_75t_R'
SITE_W, ROW_H = 0.054, 0.270


def region_insts(m, reg):
    x0, y0, x1, y1 = reg['rect']
    out = []
    for it in m['insts']:
        if it.x >= x0 - 1e-3 and it.y >= y0 - 1e-3 and it.x + it.w <= x1 + 1e-3 and it.y + it.h <= y1 + 1e-3:
            out.append(it)
    return out


def sink_xy(it, x0, y0):
    """the clock entry of an element: a point in the free routing space next to the face that carries its die bus
    (tile: corridor side at a quarter height, off the station; station/head: just north of it in the corridor;
    spine/strip blocks: their spine/strip-facing face at mid height)."""
    if it.kind == 'tile':
        return it.x + it.w + 6.0 - x0, it.y + it.h / 4 - y0
    if it.kind in ('station', 'head'):
        return it.x + it.w / 2 - x0, it.y + it.h + 3.0 - y0
    return it.x + it.w + 4.0 - x0, it.y + it.h / 2 - y0


def pairs(m, names):
    """element pairs joined by a die-level bus inside the region (the launch/capture pairs of die-level stages)"""
    P = set()
    for bid, cl, bits, eps in m['buses']:
        (a, _), (b, _) = eps[0], eps[1]
        if a in names and b in names and a != b:
            P.add(tuple(sorted((a, b))))
    return sorted(P)


def write_case(v, m, reg, work, tap='W', macros=True, dense=0):
    work.mkdir(parents=True, exist_ok=False)
    x0, y0, x1, y1 = reg['rect']
    W, H = x1 - x0, y1 - y0
    insts = region_insts(m, reg)
    names = {i.name for i in insts}
    P = pairs(m, names)
    # netlist: macros unconnected (FIXED obstructions), one sink flop per element on the region clock
    V = ['module qfd_region (clk);', '  input clk;']
    for it in (insts if macros else []):
        V.append(f'  {it.master} {it.name} ();')
    for it in insts:
        V.append(f'  {SINK} ck_{it.name} (.CLK(clk), .D(1\'b0), .QN());')
    # dense: the element's internal flops as extra sinks on a grid over its area (a flat tree sees every flop of the
    # region, so it balances a full sink population instead of 32 isolated points)
    extra = []
    if dense and not macros:
        for it in insts:
            # tiles: 2 x N; any other element larger than a station: one sink per ~(390 x 160 um), at most 64
            if it.kind == 'tile':
                nx_, ny_ = 2, max(1, dense)
            elif it.w * it.h > 0.02e6:
                nx_, ny_ = max(1, round(it.w / 390)), max(1, round(it.h / 160))
                while nx_ * ny_ > 64:
                    ny_ = max(1, ny_ // 2)
            else:
                continue
            for a_ in range(nx_):
                for b_ in range(ny_):
                    extra.append((f'd_{it.name}_{a_}_{b_}', it.x + it.w * (a_ + 0.5) / nx_, it.y + it.h * (b_ + 0.5) / ny_))
        for n_, *_ in extra:
            V.append(f'  {SINK} {n_} (.CLK(clk), .D(1\'b0), .QN());')
    V.append('endmodule')
    V = [x for x in V if x != 'endmodule'] + ['endmodule']
    (work / 'region.v').write_text('\n'.join(V) + '\n')
    pl = []
    for it in (insts if macros else []):
        pl.append(f'place_inst -name {it.name} -location {{{it.x - x0:.3f} {it.y - y0:.3f}}} -orientation {it.orient} '
                  '-status LOCKED')
    for it in insts:
        sx, sy = sink_xy(it, x0, y0)
        sx = min(max(sx, 1.0), W - 2.0)
        sy = min(max(sy, 1.0), H - 2.0)
        sx = round(math.floor(sx / SITE_W) * SITE_W, 3)
        sy = round(math.floor(sy / ROW_H) * ROW_H, 3)
        pl.append(f'place_inst -name ck_{it.name} -location {{{sx:.3f} {sy:.3f}}} -orientation R0 -status PLACED')
    for n_, ex, ey in (extra if dense and not macros else []):
        sx = round(math.floor(min(max(ex - x0, 1.0), W - 2.0) / SITE_W) * SITE_W, 3)
        sy = round(math.floor(min(max(ey - y0, 1.0), H - 2.0) / ROW_H) * ROW_H, 3)
        pl.append(f'place_inst -name {n_} -location {{{sx:.3f} {sy:.3f}}} -orientation R0 -status PLACED')
    (work / 'place.tcl').write_text('\n'.join(pl) + '\n')
    # trunk tap: the middle of the region's west edge (tile blocks: the trunk runs in the horizontal channel and
    # the spine; the tap is placed where the trunk enters), M5
    tx, ty = (0.0, H / 2) if tap == 'W' else (W / 2, 0.0)
    pr = '\n'.join(f'puts "OT_PAIR {a} {b}"' for a, b in P)
    libs_ss = '\n'.join(f'read_liberty -corner SS {PLAT}/lib/NLDM/asap7sc7p5t_{f}' for f in LIBS['SS'])
    libs_ff = '\n'.join(f'read_liberty -corner FF {PLAT}/lib/NLDM/asap7sc7p5t_{f}' for f in LIBS['FF'])
    tcl = f"""# decision-C region clock tree on the die geometry: {reg['name']} ({W:.1f} x {H:.1f} um, {len(insts)} elements)
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
define_corners SS FF
{libs_ss}
{libs_ff}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/elements.lef
read_verilog /work/region.v
link_design qfd_region
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
place_pin -pin_name clk -layer M5 -location {{{tx + 1.0:.3f} {ty:.3f}}} -force_to_die_boundary
source /work/place.tcl
cut_rows
# every element is a hard placement blockage for the region's clock buffers (TritonCTS obstruction-aware mode reads
# dbBlockages; without them it saw 2 of the 32 macros and buried buffers inside the tiles)
foreach inst [[ord::get_db_block] getInsts] {{
  if {{[[$inst getMaster] isBlock]}} {{
    set bb [$inst getBBox]
    set b [odb::dbBlockage_create [ord::get_db_block] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
  }}
}}
source {PLAT}/setRC.tcl
create_clock -name clk -period 0.833333 [get_ports clk]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
detailed_placement -max_displacement {{2000 4000}}
mem placed
set t0 [clock seconds]
clock_tree_synthesis -root_buf BUFx12f_ASAP7_75t_R -buf_list {{BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R}} \\
  {'-sink_clustering_enable ' if getattr(v, 'CTS_CLUSTER', True) else ''}-repair_clock_nets {getattr(v, 'CTS_ARGS', '')}
puts "OT_TIME cts_s=[expr {{[clock seconds]-$t0}}]"
set_propagated_clock [all_clocks]
detailed_placement -max_displacement {{2000 4000}}
check_placement -verbose
estimate_parasitics -placement
report_cts
foreach c {{SS FF}} {{
  puts "OT_CORNER $c"
  report_clock_skew -scene $c
  report_clock_latency -scene $c
}}
write_db /work/cts.odb
# propagated clock arrival at every sink: max over scenes = SS, min over scenes = FF
foreach p [get_pins -hierarchical ck_*/CLK] {{
  puts "OT_ARR [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise]"
}}
{pr}
mem done
"""
    (work / 'run.tcl').write_text(tcl)
    man = dict(region=reg['name'], rect=reg['rect'], extent_mm=reg['extent_mm'], elements=len(insts),
               kinds={k: sum(1 for i in insts if i.kind == k) for k in sorted({i.kind for i in insts})},
               bus_pairs=len(P), sink=SINK, tap=tap, macros=macros,
               mode='element abstracts FIXED (hierarchical)' if macros else
                    'flat-placement bound: the region tree may use the element interiors (no abstracts)')
    (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    return man


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--region', required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--lef', type=Path, required=True, help='elements.lef of the case (a) directory of this floorplan')
    ap.add_argument('--tap', default='W', choices=['W', 'S'])
    ap.add_argument('--rows', type=int, default=0, help='sub-region: only the first N tile rows of the region (extent sweep)')
    ap.add_argument('--cts-args', default='', help='extra clock_tree_synthesis arguments')
    ap.add_argument('--no-cluster', action='store_true', help='TritonCTS without sink clustering')
    ap.add_argument('--dense', type=int, default=0, help='flat bound: 2 x N extra sinks over every tile (its flops)')
    ap.add_argument('--no-macros', action='store_true', help='flat-placement bound: sinks only, no element abstracts')
    ap.add_argument('--slab-group-h', type=float, default=0.0)
    ap.add_argument('--cdc', default='')
    ap.add_argument('--r18', action='store_true')
    a = ap.parse_args(argv)
    v, m = B.selected(True, b3r3=True, b3r6=True, tree_cols=6, bw_align=True, bw_edge=True, io_faces=True,
                      bw_edge_inner=True, bw_sp=200, m6_strip=40, slab_group_h=a.slab_group_h, cdc=B._cdc_arg(a.cdc),
                      r18=a.r18)
    reg = dict(next(r for r in m['clock_regions'] if r['name'] == a.region))
    if a.rows:
        x0, y0, x1, y1 = reg['rect']
        y1 = m['geo']['row_y'][m['geo']['row_y'].index(min(m['geo']['row_y'], key=lambda y: abs(y - y0))) + a.rows - 1] \
            + v.TILE_SLOT[1]
        reg['rect'] = [x0, y0, x1, round(y1, 3)]
        reg['name'] = f"{reg['name']}_rows{a.rows}"
        reg['extent_mm'] = round(max(x1 - x0, y1 - y0) / 1000, 4)
    v.CTS_CLUSTER = not a.no_cluster
    v.CTS_ARGS = a.cts_args
    man = write_case(v, m, reg, a.work, a.tap, macros=not a.no_macros, dense=a.dense)
    (a.work / 'elements.lef').write_bytes(a.lef.read_bytes())
    print(json.dumps(man))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


def record(work, m=None):
    """insertion and skew of the region tree: all sinks, and the launch/capture pairs of die-level buses"""
    import re as _re
    log = (Path(work) / 'run.log').read_text()
    arr = {}
    for mm in _re.finditer(r'^OT_ARR ck_(\S+)/CLK (\S+) (\S+)', log, _re.M):
        arr[mm.group(1)] = (float(mm.group(2)), float(mm.group(3)))
    pairs = _re.findall(r'^OT_PAIR (\S+) (\S+)', log, _re.M)
    out = dict(sinks=len(arr), pairs=len(pairs))
    for k, c in ((0, 'SS'), (1, 'FF')):
        v = [a[k] for a in arr.values()]
        ps = sorted(((abs(arr[a][k] - arr[b][k]), a, b) for a, b in pairs if a in arr and b in arr), reverse=True)
        out[c] = dict(insertion_min_ps=round(min(v), 1), insertion_max_ps=round(max(v), 1),
                      skew_all_ps=round(max(v) - min(v), 1), pair_skew_max_ps=round(ps[0][0], 1) if ps else None,
                      pair_worst=list(ps[0][1:]) if ps else None,
                      pair_skew_p90_ps=round(ps[len(ps) // 10][0], 1) if ps else None,
                      pairs_over_25ps=sum(1 for x in ps if x[0] > 25.0), pairs_over_60ps=sum(1 for x in ps if x[0] > 60.0))
    mm = _re.search(r'Created (\d+) clock buffers', log)
    out['clock_buffers'] = int(mm.group(1)) if mm else None
    mm = _re.search(r'Path depth (\d+) - (\d+)', log)
    out['path_depth'] = [int(mm.group(1)), int(mm.group(2))] if mm else None
    out['legal'] = 'Violations remain' not in log.split('OT_TIME cts_s')[-1]
    return out
