#!/usr/bin/env python3
"""Qwen ROM die: GUIDED representative-window detail route -- the error bar of the full-die global route.

Cut from the FULL-DIE GRT checkpoint (placed macros + physical PDN + every net's global-route guides), not from the
floorplan: a projected-pin window (qwen_die_region_win.py, r22 win2_col: region GRT overflow 22,249 against 0 for
the same nets in the full-die GRT) re-routes the window's nets from pins piled where the removed endpoints project,
which the die never does.  Here every die net that leaves the window gets its boundary pin where ITS full-die
global route crosses the window edge, on that guide's layer, on a free track inside the guide; the guides are
clipped to the window and kept, so the detail router follows the full-die global route.  The PDN special wires are
clipped to the window (no PDN re-run).  The DRT result vs those guides (per-net wire length, slack on GRT vs RCX
parasitics) is the GRT-vs-DRT correlation the owner asked for (steer 2026-10-07).

Kept instances: centre inside the window; region box = window grown to them; removed instances overlapping the
box become obstructions on their LEF OBS layers.  Nets with no full-die guide crossing a used edge fall back to the
projected pin.

  host:      python3 tools/qwen_die_region_guided.py stage --ckpt CKPT_GRT.odb --out DIR --win X0,Y0,X1,Y1
  container: openroad -python -exit /work/qwen_die_region_guided.py   (env QDR_IN, QDR_OUT, QDR_REGION_JSON)
"""
import json
import os
import sys
from pathlib import Path


def cut():
    import bisect
    import odb
    reg = json.loads(Path(os.environ['QDR_REGION_JSON']).read_text())
    db = odb.dbDatabase.create()          # Design.readDb segfaults on the 6 GB GRT checkpoint (OpenROAD 26Q3-1510)
    odb.read_db(db, os.environ['QDR_IN'])
    block = db.getChip().getBlock()
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
    tech = block.getDataBase().getTech()
    layers = {l.getName(): l for l in tech.getLayers() if l.getType() == 'ROUTING'}
    hdir = {n: l.getDirection() == 'HORIZONTAL' for n, l in layers.items()}
    nobs, intr = 0, []
    for i in drop:
        b = i.getBBox()
        ox0, oy0, ox1, oy1 = max(b.xMin(), x0), max(b.yMin(), y0), min(b.xMax(), x1), min(b.yMax(), y1)
        if ox0 >= ox1 or oy0 >= oy1:
            continue
        intr.append(i.getName())
        for ln in sorted({ob.getTechLayer().getName() for ob in i.getMaster().getObstructions()
                          if ob.getTechLayer() is not None and ob.getTechLayer().getType() == 'ROUTING'}):
            odb.dbObstruction_create(block, layers[ln], ox0, oy0, ox1, oy1)
            nobs += 1
    print(f'QDR region dbu=[{x0} {y0} {x1} {y1}] keep={len(keep)} drop={len(drop)} intruders={len(intr)} obs={nobs}',
          flush=True)
    grids = {}
    for n in ('M4', 'M5', 'M6', 'M7', 'M8', 'M9'):
        tg = block.findTrackGrid(layers[n])
        grids[n] = sorted(tg.getGridY() if hdir[n] else tg.getGridX())
    stats = dict(guided=0, projected=0, nets=0, guides_kept=0, guides_clipped=0, guides_dropped=0, no_track=0,
                 track_blocked=0, guides_floating=0, nets_bbox_guide=0, guides_lifted=0)
    used = {}
    # ON-TRACK ACCESS CHECK (2026-10-08, gw_cong DRT-0255 at x 10,599.552 = the region box grown to a kept macro: the
    # boundary pin sat on that macro's OBS, so the maze router had no way out).  A boundary pin goes only on a track
    # whose pin box + access stub (depth ACC from the edge), grown by half the wire width + min spacing, is clear of
    # every same-layer blocker in the edge strip: kept-instance bodies with OBS/pins on that layer, the intruder
    # obstructions, and the PDN special wires.
    ACC = um(1.0)
    strips = {'W': (x0, y0, x0 + ACC, y1), 'E': (x1 - ACC, y0, x1, y1), 'S': (x0, y0, x1, y0 + ACC),
              'N': (x0, y1 - ACC, x1, y1)}
    blk = {}

    def add_blocker(ln, bx0, by0, bx1, by1):
        if ln not in grids:
            return
        for edge, (sx0, sy0, sx1, sy1) in strips.items():
            if hdir[ln] != (edge in ('W', 'E')) or bx0 >= sx1 or bx1 <= sx0 or by0 >= sy1 or by1 <= sy0:
                continue
            blk.setdefault((edge, ln), []).append((by0, by1) if edge in ('W', 'E') else (bx0, bx1))

    for i in insts:
        if i.getName() not in keep:
            continue
        m = i.getMaster()
        lays = {ob.getTechLayer().getName() for ob in m.getObstructions() if ob.getTechLayer() is not None}
        for mt in m.getMTerms():
            for mp in mt.getMPins():
                lays |= {g.getTechLayer().getName() for g in mp.getGeometry() if g.getTechLayer() is not None}
        b = i.getBBox()
        for ln in lays:
            add_blocker(ln, b.xMin(), b.yMin(), b.xMax(), b.yMax())
    for ob in block.getObstructions():
        b = ob.getBBox()
        add_blocker(b.getTechLayer().getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax())
    for n in block.getNets():
        if not n.isSpecial():
            continue
        for sw in n.getSWires():
            for sb in sw.getWires():
                if sb.isVia():
                    continue
                if sb.xMax() <= x0 or sb.xMin() >= x1 or sb.yMax() <= y0 or sb.yMin() >= y1:
                    continue
                add_blocker(sb.getTechLayer().getName(), sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax())
    blk_iv = {}
    for key, iv in blk.items():
        lay = layers[key[1]]
        g = lay.getWidth() // 2 + max(lay.getSpacing(), 0)
        merged = []
        for a_, b_ in sorted((a_ - g, b_ + g) for a_, b_ in iv):
            if merged and a_ <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b_)
            else:
                merged.append([a_, b_])
        blk_iv[key] = ([a_ for a_, _ in merged], [b_ for _, b_ in merged])
    print('QDR access blockers', json.dumps({f'{e}/{ln}': len(v[0]) for (e, ln), v in sorted(blk_iv.items())}),
          flush=True)

    def blocked(edge, ln, t):
        iv = blk_iv.get((edge, ln))
        if not iv:
            return False
        k = bisect.bisect_right(iv[0], t) - 1
        return k >= 0 and t <= iv[1][k]

    def free_track(edge, ln, coord, lo, hi):
        g = grids[ln]
        s = used.setdefault((edge, ln), set())
        k = bisect.bisect_left(g, coord)
        for d in range(0, len(g)):
            for j in (k - d, k + d):
                if 0 <= j < len(g) and lo <= g[j] <= hi and j not in s:
                    if blocked(edge, ln, g[j]):
                        stats['track_blocked'] += 1
                        continue
                    s.add(j)
                    return g[j]
        return None

    def make_pin(net, edge, ln, t, k):
        lay = layers[ln]
        w = lay.getWidth()
        ln_len = max(4 * w, um(0.2))
        bt = odb.dbBTerm.create(net, f'{net.getName()}__qdr{k}')
        bt.setIoType('INOUT')
        bp = odb.dbBPin.create(bt)
        if edge == 'W':
            r = (x0, t - w // 2, x0 + ln_len, t + w // 2)
        elif edge == 'E':
            r = (x1 - ln_len, t - w // 2, x1, t + w // 2)
        elif edge == 'N':
            r = (t - w // 2, y1 - ln_len, t + w // 2, y1)
        else:
            r = (t - w // 2, y0, t + w // 2, y0 + ln_len)
        odb.dbBox.create(bp, lay, *r)
        bp.setPlacementStatus('FIRM')
        return (ln, *r)

    lvl = {n: l.getRoutingLevel() for n, l in layers.items()}
    MIN_LVL, MAX_LVL = lvl['M4'], lvl['M9']          # the region routes M4-M9 (drt_tcl / sta set_routing_layers)

    def low_same_dir(ln):
        return 'M4' if hdir[ln] == hdir['M4'] else 'M5'
    TOUCH = um(2.0)

    def connected_guides(net, boxes, pins):
        """DRT-0218 fix (gw_io / gw_col 2026-10-08: 'Guide is not connected to design'): the clipped guides of a net
        that leaves and re-enters the window fall into pieces.  Pieces touching no pin (boundary pin on the same layer,
        or an in-window ITerm within TOUCH) are dropped; a net still in several pinned pieces gets a bounding-box guide
        on every routing layer (its pieces are joined only outside the window)."""
        if not boxes:
            return boxes
        n = len(boxes)
        par = list(range(n))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        def touch(p, q, g=0):
            return p[1] <= q[3] + g and q[1] <= p[3] + g and p[2] <= q[4] + g and q[2] <= p[4] + g
        for a_ in range(n):
            for b_ in range(a_ + 1, n):
                p, q = boxes[a_], boxes[b_]
                if abs(lvl.get(p[0], 0) - lvl.get(q[0], 0)) <= 1 and touch(p, q):
                    par[find(a_)] = find(b_)
        its = [('', it.getBBox()) for it in net.getITerms() if it.getInst().getName() in keep]
        its = [('', r.xMin(), r.yMin(), r.xMax(), r.yMax()) for _, r in its]
        live = set()
        for a_ in range(n):
            if any(pn[0] == boxes[a_][0] and touch(pn, boxes[a_]) for pn in pins) or \
                    any(touch(it, boxes[a_], TOUCH) for it in its):
                live.add(find(a_))
        dropped = sum(1 for a_ in range(n) if find(a_) not in live)
        stats['guides_floating'] += dropped
        boxes = [boxes[a_] for a_ in range(n) if find(a_) in live]
        if len(live) <= 1:
            return boxes
        stats['nets_bbox_guide'] += 1
        allr = [b[1:] for b in boxes] + [p[1:] for p in pins] + [i[1:] for i in its]
        bx0 = max(x0, min(r[0] for r in allr) - TOUCH)
        by0 = max(y0, min(r[1] for r in allr) - TOUCH)
        bx1 = min(x1, max(r[2] for r in allr) + TOUCH)
        by1 = min(y1, max(r[3] for r in allr) + TOUCH)
        return [(ln, bx0, by0, bx1, by1) for ln in sorted(layers, key=lambda v: lvl[v]) if MIN_LVL <= lvl[ln] <= MAX_LVL]

    def inside(r):
        return r.xMin() >= x0 and r.xMax() <= x1 and r.yMin() >= y0 and r.yMax() <= y1

    def overlaps(r):
        return r.xMin() < x1 and r.xMax() > x0 and r.yMin() < y1 and r.yMax() > y0

    gwrite = []
    nets_seen = set()
    for i in insts:
        if i.getName() not in keep:
            continue
        for it in i.getITerms():
            net = it.getNet()
            if net is None or net.getSigType() in ('POWER', 'GROUND') or net.getName() in nets_seen:
                continue
            nets_seen.add(net.getName())
            stats['nets'] += 1
            outside = [ot for ot in net.getITerms() if ot.getInst().getName() not in keep]
            guides = list(net.getGuides())
            kept_boxes = []
            pins = []
            k = 0
            for g in guides:
                r = g.getBox()
                ln = g.getLayer().getName()
                if lvl.get(ln, 99) < MIN_LVL:
                    # die-gaps 2026-10-08 (HBM r25 hub DRT-0155: a die guide of n_clk_serial on M3, below the region's
                    # M4-M9 routing range): a guide below M4 is lifted to the lowest allowed layer of its direction
                    # (M2 -> M4, M3 -> M5) plus M4 so the lifted box still touches the net's M4 guides; DRT reaches
                    # the M1-M3 pins through its via access.
                    ln = low_same_dir(ln)
                    stats['guides_lifted'] += 1
                    if ln != 'M4' and overlaps(r):
                        kept_boxes.append(('M4', max(r.xMin(), x0), max(r.yMin(), y0), min(r.xMax(), x1),
                                           min(r.yMax(), y1)))
                elif lvl.get(ln, 0) > MAX_LVL:
                    ln = 'M9'
                    stats['guides_lifted'] += 1
                if inside(r):
                    kept_boxes.append((ln, r.xMin(), r.yMin(), r.xMax(), r.yMax()))
                    stats['guides_kept'] += 1
                    continue
                if not overlaps(r) or ln not in grids:
                    stats['guides_dropped'] += 1
                    continue
                cr = (max(r.xMin(), x0), max(r.yMin(), y0), min(r.xMax(), x1), min(r.yMax(), y1))
                kept_boxes.append((ln, *cr))
                stats['guides_clipped'] += 1
                if not outside:
                    continue
                # the guide leaves the window: a pin on each crossed edge whose direction matches the layer
                for edge, crossed in (('W', r.xMin() < x0), ('E', r.xMax() > x1), ('S', r.yMin() < y0),
                                      ('N', r.yMax() > y1)):
                    if not crossed or hdir[ln] != (edge in ('W', 'E')):
                        continue
                    lo, hi = (cr[1], cr[3]) if edge in ('W', 'E') else (cr[0], cr[2])
                    w = layers[ln].getWidth()
                    t = free_track(edge, ln, (lo + hi) // 2, lo + w, hi - w)
                    if t is None:
                        stats['no_track'] += 1
                        continue
                    k += 1
                    pins.append(make_pin(net, edge, ln, t, k))
                    stats['guided'] += 1
            if outside and k == 0:
                # no guide crosses an edge in its preferred direction: projected pin (the win tool's rule)
                b = outside[0].getBBox()
                px, py = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
                dx = (x0 - px) if px < x0 else (px - x1) if px > x1 else 0
                dy = (y0 - py) if py < y0 else (py - y1) if py > y1 else 0
                edge = ('W' if px < x0 else 'E') if dx >= dy else ('S' if py < y0 else 'N')
                ln = 'M8' if edge in ('W', 'E') else 'M9'
                w = layers[ln].getWidth()
                c = min(max(py, y0 + 2 * w), y1 - 2 * w) if edge in ('W', 'E') else min(max(px, x0 + 2 * w), x1 - 2 * w)
                t = free_track(edge, ln, c, (y0 if edge in ('W', 'E') else x0) + 2 * w,
                               (y1 if edge in ('W', 'E') else x1) - 2 * w)
                if t is not None:
                    pins.append(make_pin(net, edge, ln, t, 1))
                    stats['projected'] += 1
            for g in guides:
                odb.dbGuide_destroy(g)
            kept_boxes = connected_guides(net, kept_boxes, pins)
            for ln, a, b_, c, d in kept_boxes:
                gwrite.append((net.getName(), ln, a, b_, c, d))
    print('QDR pins/guides', json.dumps(stats), flush=True)
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
    # clip the physical PDN to the box (wires clipped, vias outside or on the border removed)
    psb = dict(kept=0, clipped=0, removed=0)
    for n in block.getNets():
        if not n.isSpecial():
            continue
        for sw in n.getSWires():
            for sb in list(sw.getWires()):
                r = odb.Rect(sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax())
                if inside(r):
                    psb['kept'] += 1
                    continue
                if sb.isVia() or not overlaps(r):
                    odb.dbSBox_destroy(sb)
                    psb['removed'] += 1
                    continue
                lay, st = sb.getTechLayer(), sb.getWireShapeType()
                cx0, cy0, cx1, cy1 = max(r.xMin(), x0), max(r.yMin(), y0), min(r.xMax(), x1), min(r.yMax(), y1)
                odb.dbSBox_destroy(sb)
                odb.dbSBox_create(sw, lay, cx0, cy0, cx1, cy1, st)
                psb['clipped'] += 1
    print(f'QDR nets removed {ndel}; pdn {psb}', flush=True)
    rows = [(r.getName(), r.getSite(), r.getOrigin(), r.getOrient(), r.getDirection(), r.getSiteCount(), r.getSpacing())
            for r in block.getRows()]
    for r in list(block.getRows()):
        odb.dbRow.destroy(r)
    for name, site, (ox, oy), orient, direc, cnt, sp in rows:
        if oy < y0 or oy + site.getHeight() > y1:
            continue
        sx = ox + -(-(x0 - ox) // sp) * sp if x0 > ox else ox
        n = (min(x1, ox + cnt * sp) - sx) // sp
        if n > 0:
            odb.dbRow.create(block, name, site, sx, oy, orient, direc, n, sp)
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
    # clipped full-die guides: a guide file (DRT read_guides, GRT read_guides for the GRT-parasitics STA)
    out_dir = Path(os.environ['QDR_OUT']).parent
    with open(out_dir / 'route.guide', 'w') as f:
        cur = None
        for nn, ln, a, b_, c, d in sorted(gwrite, key=lambda t: t[0]):
            if nn != cur:
                if cur is not None:
                    f.write(')\n')
                f.write(f'{nn}\n(\n')
                cur = nn
            f.write(f'{a} {b_} {c} {d} {ln}\n')
        if cur is not None:
            f.write(')\n')
    out = {'win_um': reg['win'], 'region_um': [x0 / dbu, y0 / dbu, x1 / dbu, y1 / dbu],
           'area_mm2': (x1 - x0) * (y1 - y0) / dbu / dbu / 1e6, 'kept_instances': len(keep),
           'intruders_as_obstructions': intr, 'obstructions': nobs, 'pins_guides': stats, 'pdn_clip': psb,
           'region_nets': len(nets_seen), 'kept_masters': {}}
    for i in block.getInsts():
        m = i.getMaster().getName()
        out['kept_masters'][m] = out['kept_masters'].get(m, 0) + 1
    Path(os.environ['QDR_OUT'] + '.json').write_text(json.dumps(out, indent=1))
    odb.write_db(block.getDataBase(), os.environ['QDR_OUT'])
    print('QDR_CUT_DONE', json.dumps(out))


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
CLOCKS = """set roots {}
foreach bt [[ord::get_db_block] getBTerms] {
  set n [[$bt getNet] getName]
  if {![regexp {^n_(clk|fck)_} $n] || [info exists seen($n)]} { continue }
  set seen($n) 1; lappend roots [get_ports [$bt getName]] }
foreach p [get_pins -quiet {hub_el/pll_r* io_collective/pll_*}] { lappend roots $p }
# every region / link clock is the 1.2 GHz stream clock at the die level (ideal roots; the clock plan's skew is the
# setup / hold uncertainty below)
create_clock -name stream -period 833.333 $roots
puts "OT_CLOCK_ROOTS [llength $roots]"
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
"""


def drt_tcl(threads, iters):
    return HEAD + f"""set_thread_count {threads}
step load {{ read_db /work/region.odb }}
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
step guides {{ read_guides /work/route.guide }}
step wl_grt {{ report_wire_length -net * -global_route -file /work/wl_grt.csv }}
step drt {{ detailed_route -output_drc /work/drt_drc.rpt -verbose 1 -droute_end_iter {iters} }}
step write_odb {{ write_db /work/routed.odb }}
step wl_drt {{ report_wire_length -net * -detailed_route -file /work/wl_drt.csv }}
step rcx {{ define_process_corner -ext_model_index 0 X
  extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules }}
step write_spef {{ write_spef /work/routed.spef }}
puts OT_FLOW_DONE
"""


def sta_tcl(corner, para):
    c, C = corner, corner.upper()
    load = ('step load { read_db /work/region.odb }\nset_routing_layers -signal M4-M9 -clock M4-M9\n'
            'source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl\n'
            # read_guides cannot feed estimate_parasitics (GRT-0008: the 'GRT' slacks of regions21g had no wire RC);
            # re-route the cut region globally (M4-M9, default adjustments) instead
            'step grt { global_route -congestion_iterations 30 -allow_congestion }\n'
            'step est { estimate_parasitics -global_routing }\n') if para == 'grt' else \
        'step load { read_db /work/routed.odb }\nstep spef { read_spef /work/routed.spef }\n'
    chk = 'max' if c == 'ss' else 'min'
    return HEAD + 'step libs {\n' + LIBS.format(N='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM', C=C, c=c) + \
        '}\n' + load + CLOCKS + f"""step sta {{
  report_checks -path_delay {chk} -group_path_count 1000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/sta_{para}_{c}_ends.rpt
  report_checks -path_delay {chk} -group_path_count 3 -fields {{slew cap input_pins}} -digits 1 > /work/sta_{para}_{c}_paths.rpt
  report_worst_slack -{chk}; report_tns
}}
puts OT_STA_DONE
"""


def stage(a):
    a.out.mkdir(parents=True, exist_ok=True)
    win = [float(v) for v in a.win.split(',')]
    (a.out / 'region.json').write_text(json.dumps({'win': win, 'name': a.out.name, 'ckpt': a.ckpt}))
    (a.out / 'qwen_die_region_guided.py').write_text(Path(__file__).read_text())
    (a.out / 'drt.tcl').write_text(drt_tcl(a.threads, a.drt_iters))
    for c in ('ss', 'ff'):
        for p in ('grt', 'rcx'):
            (a.out / f'sta_{p}_{c}.tcl').write_text(sta_tcl(c, p))
    (a.out / 'start_region.sh').write_text(f"""#!/bin/bash
# guided window: cut from the full-die GRT checkpoint -> DRT on the clipped full-die guides -> RCX -> STA GRT / RCX
set -u
cd $(dirname $0)
ln -f {a.ckpt} ckpt_grt.odb 2>/dev/null || cp -f {a.ckpt} ckpt_grt.odb
N=qfd_gw_$(basename $(pwd))
date -u +%FT%TZ > cut.log.start
docker run --rm --name ${{N}}_cut --memory=300g -e QDR_IN=/work/ckpt_grt.odb -e QDR_OUT=/work/region.odb \\
  -e QDR_REGION_JSON=/work/region.json -v $(pwd):/work -w /work ${{IMAGE:-openroad/orfs:asap7lock}} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -python -exit /work/qwen_die_region_guided.py > /work/cut.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"
echo $? > cut.log.exit; date -u +%FT%TZ > cut.log.end
rm -f ckpt_grt.odb
[ "$(cat cut.log.exit)" = 0 ] || exit 1
for t in sta_grt_ss sta_grt_ff; do ./run_case.sh . $t.tcl $t.log 8 120; done
./run_case.sh . drt.tcl drt.log {a.threads} {a.mem}
for t in sta_rcx_ss sta_rcx_ff; do ./run_case.sh . $t.tcl $t.log 8 120; done
echo done > region.done
""")
    os.chmod(a.out / 'start_region.sh', 0o755)
    print(a.out)


def main():
    if 'odb' in sys.modules or os.environ.get('QDR_IN'):
        cut()
        return
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('stage')
    s.add_argument('--ckpt', required=True, help='full-die GRT checkpoint on the host (ckpt_grt.odb)')
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--win', required=True, help='x_lo,y_lo,x_hi,y_hi (um)')
    s.add_argument('--threads', type=int, default=24)
    s.add_argument('--mem', type=int, default=250)
    s.add_argument('--drt-iters', type=int, default=64)
    a = ap.parse_args()
    stage(a)


if __name__ == '__main__':
    main()
