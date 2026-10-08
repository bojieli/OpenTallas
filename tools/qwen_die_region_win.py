#!/usr/bin/env python3
"""Qwen ROM die: REPRESENTATIVE-WINDOW detail-route regions (owner steer 2026-10-07, academic validation).

The die-level evidence is a full-die global route (overflow 0) plus die STA on global-route parasitics; the error
bar on both comes from detail-routing a few representative windows (worst congestion, the SerDes / IO edge, the
longest spine links, one dense tile column) and correlating GRT against DRT (wire length per net, slack delta).

A window is any rectangle [x_lo, y_lo, x_hi, y_hi] (um).  Kept instances: centre inside the window.  The region box
is the window grown to the kept instances' bounding boxes.  A removed instance that still overlaps the region box
becomes a routing obstruction on its LEF OBS layers (M1-M7) over the overlap, so the router sees the same blockage
the full die has.  Every die net leaving the region ends on a boundary pin on the edge facing the removed endpoint
(projected, clamped, on a free track of a layer of the edge's preferred direction, nearest the endpoint's pin layer)
-- the qwen_die_region_cut.py (r20c pilot) rule, generalised from a full-height strip to any window.  Rows and track
grids are clipped keeping their absolute phase; the r5 pdn.tcl is filtered to the kept instances and its core-grid
stripe offsets re-anchored, so every PDN stripe stays at its full-die position.

  host:      python3 tools/qwen_die_region_win.py stage --src CASE --out DIR --win X0,Y0,X1,Y1 [--tile 4.8]
  container: openroad -python -exit /work/qwen_die_region_win.py    (env QDR_IN, QDR_OUT, QDR_REGION_JSON)
  then       python3 qwen_die_region_win.py pdnfilter --out DIR
The stage step writes start_region.sh: cut -> region PDN -> GRT (the full-die settings: M4-M9, tile 4.8 um,
M4/M5 0.30, M6-M9 0.05) -> DRT -> RCX -> GRT-vs-DRT wire length per net -> STA SS/FF on GRT and on RCX parasitics.
"""
import json
import os
import sys
from pathlib import Path


def cut():
    import bisect
    import odb
    from openroad import Design, Tech
    reg = json.loads(Path(os.environ['QDR_REGION_JSON']).read_text())
    tech = Tech()
    design = Design(tech)
    design.readDb(os.environ['QDR_IN'])
    block = design.getBlock()
    dbu = block.getDbUnitsPerMicron()
    um = lambda v: int(round(v * dbu))  # noqa: E731
    wx0, wy0, wx1, wy1 = (um(v) for v in reg['win'])
    insts = list(block.getInsts())
    keep, drop = set(), []
    for i in insts:
        b = i.getBBox()
        cx, cy = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
        (keep.add(i.getName()) if (wx0 <= cx <= wx1 and wy0 <= cy <= wy1) else drop.append(i))
    kb = [i.getBBox() for i in insts if i.getName() in keep]
    die = block.getDieArea()
    x0 = max(die.xMin(), min([wx0] + [b.xMin() for b in kb]))
    y0 = max(die.yMin(), min([wy0] + [b.yMin() for b in kb]))
    x1 = min(die.xMax(), max([wx1] + [b.xMax() for b in kb]))
    y1 = min(die.yMax(), max([wy1] + [b.yMax() for b in kb]))
    tech_db = block.getDataBase().getTech()
    layers = {l.getName(): l for l in tech_db.getLayers() if l.getType() == 'ROUTING'}
    # removed instances overlapping the region -> obstructions on their OBS layers over the overlap
    nobs, intr = 0, []
    for i in drop:
        b = i.getBBox()
        ox0, oy0, ox1, oy1 = max(b.xMin(), x0), max(b.yMin(), y0), min(b.xMax(), x1), min(b.yMax(), y1)
        if ox0 >= ox1 or oy0 >= oy1:
            continue
        intr.append(i.getName())
        obs_l = set()
        for ob in i.getMaster().getObstructions():
            if ob.getTechLayer() is not None and ob.getTechLayer().getType() == 'ROUTING':
                obs_l.add(ob.getTechLayer().getName())
        for ln in sorted(obs_l):
            odb.dbObstruction_create(block, layers[ln], ox0, oy0, ox1, oy1)
            nobs += 1
    print(f'QDR region dbu=[{x0} {y0} {x1} {y1}] keep={len(keep)} drop={len(drop)} intruders->obs={intr[:8]} obs={nobs}')
    hdir = {n: l.getDirection() == 'HORIZONTAL' for n, l in layers.items()}
    H = [n for n in ('M4', 'M6', 'M8') if n in layers]
    V = [n for n in ('M5', 'M7', 'M9') if n in layers]
    grids = {}
    for n in H + V:
        tg = block.findTrackGrid(layers[n])
        grids[n] = sorted(tg.getGridY() if hdir[n] else tg.getGridX())
    used = {}

    def pin_layer(lname, horizontal):
        pool = H if horizontal else V
        idx = int(lname[1:]) if lname and lname[0] == 'M' and lname[1:].isdigit() else 5
        return min(pool, key=lambda n: (abs(int(n[1:]) - idx), -int(n[1:])))

    def free_track(edge, lname, coord, lo, hi):
        g = grids[lname]
        s = used.setdefault((edge, lname), set())
        k = bisect.bisect_left(g, coord)
        for d in range(0, len(g)):
            for j in (k - d, k + d):
                if 0 <= j < len(g) and lo <= g[j] <= hi and j not in s:
                    s.add(j)
                    return g[j]
        raise RuntimeError(f'no free track {edge} {lname}')

    def edge_of(px, py):
        if x0 <= px <= x1 and y0 <= py <= y1:      # endpoint inside the box (on an obstructed intruder): nearest edge
            d = {'W': px - x0, 'E': x1 - px, 'S': py - y0, 'N': y1 - py}
            return min(d, key=d.get)
        dx = (x0 - px) if px < x0 else (px - x1) if px > x1 else 0
        dy = (y0 - py) if py < y0 else (py - y1) if py > y1 else 0
        if dx >= dy:
            return 'W' if px < x0 else 'E'
        return 'S' if py < y0 else 'N'

    nbt = 0
    stats = {'W': 0, 'E': 0, 'N': 0, 'S': 0}
    nets_seen = set()
    for i in insts:
        if i.getName() not in keep:
            continue
        for it in i.getITerms():
            net = it.getNet()
            if net is None or net.getSigType() in ('POWER', 'GROUND'):
                continue
            nn = net.getName()
            if nn in nets_seen:
                continue
            nets_seen.add(nn)
            placed = []
            for ot in list(net.getITerms()):
                if ot.getInst().getName() in keep:
                    continue
                b = ot.getBBox()
                px, py = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
                edge = edge_of(px, py)
                ol = None
                for mp in ot.getMTerm().getMPins():
                    for g in mp.getGeometry():
                        if g.getTechLayer() is not None:
                            ol = g.getTechLayer().getName()
                            break
                    if ol:
                        break
                horiz = edge in ('W', 'E')
                ln = pin_layer(ol, horiz)
                lay = layers[ln]
                w = lay.getWidth()
                ln_len = max(4 * w, um(0.2))
                c = min(max(py, y0 + 2 * w), y1 - 2 * w) if horiz else min(max(px, x0 + 2 * w), x1 - 2 * w)
                if any(e == edge and l_ == ln and abs(cc - c) < um(20) for e, l_, cc in placed):
                    continue
                t = free_track(edge, ln, c, (y0 if horiz else x0) + 2 * w, (y1 if horiz else x1) - 2 * w)
                placed.append((edge, ln, t))
                bt = odb.dbBTerm.create(net, f'{nn}__qdr{len(placed)}')
                bt.setIoType('INPUT' if ot.isOutputSignal() else 'OUTPUT' if ot.isInputSignal() else 'INOUT')
                bp = odb.dbBPin.create(bt)
                if edge == 'W':
                    odb.dbBox.create(bp, lay, x0, t - w // 2, x0 + ln_len, t + w // 2)
                elif edge == 'E':
                    odb.dbBox.create(bp, lay, x1 - ln_len, t - w // 2, x1, t + w // 2)
                elif edge == 'N':
                    odb.dbBox.create(bp, lay, t - w // 2, y1 - ln_len, t + w // 2, y1)
                else:
                    odb.dbBox.create(bp, lay, t - w // 2, y0, t + w // 2, y0 + ln_len)
                bp.setPlacementStatus('FIRM')
                nbt += 1
                stats[edge] += 1
    print(f'QDR boundary pins {nbt} {stats} region nets {len(nets_seen)}')
    for i in drop:
        odb.dbInst.destroy(i)
    for bt in list(block.getBTerms()):
        if '__qdr' not in bt.getName():
            odb.dbBTerm.destroy(bt)
    ndel = 0
    for n in list(block.getNets()):
        if n.getITermCount() == 0 and n.getBTermCount() == 0 and not n.isSpecial():
            odb.dbNet.destroy(n)
            ndel += 1
    print(f'QDR nets removed {ndel} kept {len(list(block.getNets()))}')
    rows = [(r.getName(), r.getSite(), r.getOrigin(), r.getOrient(), r.getDirection(), r.getSiteCount(), r.getSpacing())
            for r in block.getRows()]
    for r in list(block.getRows()):
        odb.dbRow.destroy(r)
    nr = 0
    for name, site, (ox, oy), orient, direc, cnt, sp in rows:
        h = site.getHeight()
        if oy < y0 or oy + h > y1:
            continue
        sx = ox + -(-(x0 - ox) // sp) * sp if x0 > ox else ox
        n = (min(x1, ox + cnt * sp) - sx) // sp
        if n > 0:
            odb.dbRow.create(block, name, site, sx, oy, orient, direc, n, sp)
            nr += 1
    for tg in list(block.getTrackGrids()):
        lay = tg.getTechLayer()
        px = [tg.getGridPatternX(k) for k in range(tg.getNumGridPatternsX())]
        py = [tg.getGridPatternY(k) for k in range(tg.getNumGridPatternsY())]
        odb.dbTrackGrid.destroy(tg)
        ng = odb.dbTrackGrid.create(block, lay)
        for pats, lo, hi, add in ((px, x0, x1, ng.addGridPatternX), (py, y0, y1, ng.addGridPatternY)):
            for o, c, s in pats:
                no = o + -(-(lo - o) // s) * s if lo > o else o
                cnt = (hi - no) // s + 1
                if cnt > 0:
                    add(no, cnt, s)
    block.setDieArea(odb.Rect(x0, y0, x1, y1))
    block.setCoreArea(odb.Rect(x0, y0, x1, y1))
    out = {'win_um': reg['win'], 'region_dbu': [x0, y0, x1, y1], 'region_um': [x0 / dbu, y0 / dbu, x1 / dbu, y1 / dbu],
           'area_mm2': (x1 - x0) * (y1 - y0) / dbu / dbu / 1e6, 'die_mm2': die.dx() * die.dy() / dbu / dbu / 1e6,
           'kept_instances': len(keep), 'removed_instances': len(drop), 'intruders_as_obstructions': intr,
           'obstructions': nobs, 'boundary_pins': nbt, 'boundary_by_edge': stats, 'region_nets': len(nets_seen),
           'rows': nr, 'kept_masters': {}}
    out['kept_names'] = sorted(i.getName() for i in block.getInsts())
    for i in block.getInsts():
        m = i.getMaster().getName()
        out['kept_masters'][m] = out['kept_masters'].get(m, 0) + 1
    Path(os.environ['QDR_OUT'] + '.json').write_text(json.dumps(out, indent=1))
    odb.write_db(block.getDataBase(), os.environ['QDR_OUT'])
    print('QDR_CUT_DONE', json.dumps({k: v for k, v in out.items() if k != 'kept_names'}))


def region_pdn(text, keep, x0, y0, vertical):
    """the r5 pdn.tcl filtered to the kept instances, core-grid stripe offsets re-anchored to the region origin."""
    import re
    out, dropped = [], set()
    for line in text.splitlines():
        m = re.match(r'define_pdn_grid -macro -instances \{([^}]*)\} .*-name (\S+)', line)
        if m:
            pats = [p for p in m.group(1).split() if p.strip('^$') in keep]
            if not pats:
                dropped.add(m.group(2))
                continue
            line = line.replace('{' + m.group(1) + '}', '{' + ' '.join(pats) + '}')
        g = re.search(r'-grid (\S+)', line)
        if g and g.group(1) in dropped:
            continue
        s = re.match(r'add_pdn_stripe -grid core -layer (\S+) .*-pitch (\S+) -offset (\S+)', line)
        if s:
            lay, pitch, off = s.group(1), float(s.group(2)), float(s.group(3))
            org = x0 if vertical[lay] else y0
            line = line.replace(f'-offset {s.group(3)}', f'-offset {(off - org) % pitch:.4f}')
        out.append(line)
    return '\n'.join(out) + '\n', sorted(dropped)


HEAD = r"""proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }
"""

LIBS = """read_liberty {N}/asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz
read_liberty {N}/asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz
read_liberty {N}/asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz
read_liberty {N}/asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib
read_liberty {N}/asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz
read_liberty /work/libs/qfd_etm_{c}.lib
read_liberty /work/libs/qfd_elements_{c}.lib
read_liberty /work/libs/ot_hbm3e_phy_{c}.lib
"""

CLOCKS = """create_clock -name stream -period 833.333 [get_ports -quiet n_clk_*__qdr*]
create_clock -name stream_i -period 833.333 [get_pins -quiet {hub_el/pll_r* io_collective/pll_stream}]
foreach c {ucie serdes} { create_clock -name $c -period 833.333 [get_pins -quiet io_collective/pll_$c] }
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
"""


def flow_tcl(threads, tile, drt_iters):
    return HEAD + f"""set_thread_count {threads}
step load {{ read_db /work/floorplan_pdn.odb }}
step coarse {{
  set b [ord::get_db_block]; set p [expr {{{tile}/15.0}}]
  foreach ln {{M2 M3}} {{ odb::dbTrackGrid_destroy [$b findTrackGrid [[ord::get_db_tech] findLayer $ln]]
    make_tracks $ln -x_offset 0.009 -x_pitch $p -y_offset 0.009 -y_pitch $p }}
  puts "OT_TILE dbu=[$b getGCellTileSize]"
}}
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.05
step special {{ set n 0; foreach net [[ord::get_db_block] getNets] {{
  if {{[regexp {{^n_(clk_|fck_|rst_)}} [$net getName]]}} {{ $net setSpecial; incr n }} }}; puts "OT_SPECIAL $n" }}
step grt {{ global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }}
step ckpt_grt {{ write_db /work/ckpt_grt.odb; write_guides /work/route.guide }}
step wl_grt {{ report_wire_length -net * -global_route -file /work/wl_grt.csv }}
step drt {{ detailed_route -output_drc /work/drt_drc.rpt -verbose 1 -droute_end_iter {drt_iters} }}
step write_odb {{ write_db /work/routed.odb }}
step wl_drt {{ report_wire_length -net * -detailed_route -file /work/wl_drt.csv }}
step rcx {{ define_process_corner -ext_model_index 0 X
  extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules }}
step write_spef {{ write_spef /work/routed.spef }}
puts OT_FLOW_DONE
"""


def sta_tcl(corner, para):
    """para: 'grt' (estimate_parasitics -global_routing on the GRT checkpoint) or 'rcx' (routed SPEF)."""
    c, C = corner, corner.upper()
    load = ('step load { read_db /work/ckpt_grt.odb }\nstep guides { read_guides /work/route.guide }\n'
            'set_routing_layers -signal M4-M9 -clock M4-M9\nsource /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl\n'
            'step est { estimate_parasitics -global_routing }\n') if para == 'grt' else \
        'step load { read_db /work/routed.odb }\nstep spef { read_spef /work/routed.spef }\n'
    chk = 'max' if c == 'ss' else 'min'
    return HEAD + 'step libs {\n' + LIBS.format(N='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM', C=C, c=c) + \
        '}\n' + load + CLOCKS + f"""step sta {{
  report_checks -path_delay {chk} -group_path_count 1000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/sta_{para}_{c}_ends.rpt
  report_checks -path_delay {chk} -group_path_count 5 -fields {{slew cap input_pins nets}} -digits 1 > /work/sta_{para}_{c}_paths.rpt
  report_worst_slack -{chk}; report_tns
}}
puts OT_STA_DONE
"""


def stage(a):
    a.out.mkdir(parents=True, exist_ok=True)
    win = [float(v) for v in a.win.split(',')]
    (a.out / 'region.json').write_text(json.dumps({'win': win, 'name': a.out.name}))
    (a.out / 'qwen_die_region_win.py').write_text(Path(__file__).read_text())
    (a.out / 'flow.tcl').write_text(flow_tcl(a.threads, a.tile, a.drt_iters))
    for c in ('ss', 'ff'):
        for p in ('grt', 'rcx'):
            (a.out / f'sta_{p}_{c}.tcl').write_text(sta_tcl(c, p))
    (a.out / 'run_pdn.tcl').write_text(HEAD + """
step load { read_db /work/region.odb }
step pdn { source /work/pdn_region.tcl; pdngen }
foreach net {VDD VSS} { if {[catch {check_power_grid -net $net} err]} { puts "OT_PGCHECK $net FAIL $err" } else { puts "OT_PGCHECK $net PASS" } }
step write { write_db /work/floorplan_pdn.odb }
puts OT_PDN_DONE
""")
    (a.out / 'start_region.sh').write_text(f"""#!/bin/bash
# representative window: cut -> region PDN -> GRT/DRT/RCX -> STA (GRT and RCX parasitics) SS / FF
set -u
cd $(dirname $0)
S={a.src}
for f in floorplan.odb pdn.tcl elements.lef phy_ew.lef; do ln -f $S/$f . 2>/dev/null || cp -f $S/$f .; done
N=qfd_win_$(basename $(pwd))
date -u +%FT%TZ > cut.log.start
docker run --rm --name ${{N}}_cut --memory=200g -e QDR_IN=/work/floorplan.odb -e QDR_OUT=/work/region.odb \\
  -e QDR_REGION_JSON=/work/region.json -v $(pwd):/work -w /work ${{IMAGE:-openroad/orfs:asap7lock}} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -python -exit /work/qwen_die_region_win.py > /work/cut.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"
echo $? > cut.log.exit; date -u +%FT%TZ > cut.log.end
[ "$(cat cut.log.exit)" = 0 ] || exit 1
python3 qwen_die_region_win.py pdnfilter --out $(pwd) || exit 1
./run_case.sh . run_pdn.tcl run_pdn.log 8 100 || exit 1
./run_case.sh . flow.tcl flow.log {a.threads} {a.mem}
for t in sta_grt_ss sta_grt_ff sta_rcx_ss sta_rcx_ff; do ./run_case.sh . $t.tcl $t.log 8 150; done
echo done > region.done
""")
    os.chmod(a.out / 'start_region.sh', 0o755)
    print(a.out)


def pdnfilter(a):
    reg = json.loads((a.out / 'region.odb.json').read_text())
    keep = set(reg['kept_names'])
    x0, y0 = reg['region_um'][0], reg['region_um'][1]
    vertical = {f'M{k}': k % 2 == 1 for k in range(1, 10)}          # asap7: odd metals vertical
    text, dropped = region_pdn((a.out / 'pdn.tcl').read_text(), keep, x0, y0, vertical)
    (a.out / 'pdn_region.tcl').write_text(text)
    print(f'pdn_region.tcl: {len(dropped)} macro grids dropped (no kept instance)')


def main():
    if 'odb' in sys.modules or os.environ.get('QDR_IN'):
        cut()
        return
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('stage')
    s.add_argument('--src', required=True, help='die case dir on the host (floorplan.odb, pdn.tcl, LEFs)')
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--win', required=True, help='x_lo,y_lo,x_hi,y_hi (um)')
    s.add_argument('--tile', type=float, default=4.8)
    s.add_argument('--threads', type=int, default=32)
    s.add_argument('--mem', type=int, default=300)
    s.add_argument('--drt-iters', type=int, default=64)
    p = sub.add_parser('pdnfilter')
    p.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    stage(a) if a.cmd == 'stage' else pdnfilter(a)


if __name__ == '__main__':
    main()
