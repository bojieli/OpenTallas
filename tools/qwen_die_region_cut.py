#!/usr/bin/env python3
"""Qwen ROM die: REPRESENTATIVE-REGION cut for the die-top detailed-route pilot (2026-10-06).

The flat full-die pilot (r20c, 3,334 macros, 3.98 M die nets) was killed by its 900 GB guard during global-route grid
setup (RSS 942 GB at GRT-0088), so the die-top flow is measured on one representative region and scaled:
one tile column (the column next to the spine, west column 31: 24 tiles + 24 corridor stations + its column head)
plus the whole spine/hub crossing (both spine slab columns, hub, constants sequencer, SU/SFU, vector memory, tree top,
link stations), full die height up to the IO row.  Everything else is removed; every die net that leaves the region
ends on a region boundary pin placed where the removed endpoint projects onto the region edge (clamped), on a
routing layer of the edge's preferred direction and on a free track, so the region still carries every wire that
crosses into the spine.  Rows and track grids are clipped keeping their absolute phase, and the r5 PDN is re-run on
the region (core-grid stripe offsets re-anchored so every stripe stays at its full-die position; macro grids filtered
to the kept instances).

  host:      python3 tools/qwen_die_region_cut.py stage --src CASE --out DIR [--x-lo 11280 --x-hi 13430 --y-top 31216]
  container: openroad -python -exit /work/qwen_die_region_cut.py    (env QDR_IN, QDR_OUT, QDR_REGION_JSON)
The stage step writes cut (python, this file), pdn.tcl, pilot.tcl and sta_{ss,ff}.tcl (tools/qwen_die_drt_pilot.py)
(launch start_region.sh inside tmux on the host: a docker-run client tied to an ssh session dies with it)
and start_region.sh.
"""
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------------------------- container side (odb)
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
    um = lambda v: int(round(v * dbu))
    xlo, xhi, ytop = um(reg['x_lo']), um(reg['x_hi']), um(reg['y_top'])
    insts = list(block.getInsts())
    keep, drop = set(), []
    for i in insts:
        b = i.getBBox()
        cx, cy = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
        (keep.add(i.getName()) if (xlo <= cx <= xhi and cy < ytop) else drop.append(i))
    kb = [i.getBBox() for i in insts if i.getName() in keep]
    x0, x1 = min(b.xMin() for b in kb), max(b.xMax() for b in kb)
    die = block.getDieArea()
    y0, y1 = die.yMin(), min([i.getBBox().yMin() for i in drop if i.getBBox().yMin() >= max(b.yMax() for b in kb)]
                              + [die.yMax()])
    intr = [i.getName() for i in drop if (lambda b: b.xMin() < x1 and b.xMax() > x0 and b.yMin() < y1 and b.yMax() > y0)(i.getBBox())]
    print(f'QDR region dbu=[{x0} {y0} {x1} {y1}] keep={len(keep)} drop={len(drop)} intruders={len(intr)} {intr[:5]}')
    assert not intr, 'a removed instance overlaps the region'
    tech_db = block.getDataBase().getTech()
    layers = {l.getName(): l for l in tech_db.getLayers() if l.getType() == 'ROUTING'}
    hdir = {n: l.getDirection() == 'HORIZONTAL' for n, l in layers.items()}
    # layers for boundary pins: M4..M9 by direction
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
                if px < x0:
                    edge = 'W'
                elif px > x1:
                    edge = 'E'
                elif py > y1:
                    edge = 'N'
                else:
                    edge = 'S'
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
                ln_len = max(4 * w, um(0.2))                          # on-track stub, 0.2 um (>= min area)
                if horiz:
                    c = min(max(py, y0 + 2 * w), y1 - 2 * w)
                else:
                    c = min(max(px, x0 + 2 * w), x1 - 2 * w)
                # one pin per (net, edge, layer) within 20 um
                if any(e == edge and l == ln and abs(cc - c) < um(20) for e, l, cc in placed):
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
            bb = bt.getBBox()
            if not (x0 <= bb.xMin() and bb.xMax() <= x1 and y0 <= bb.yMin() and bb.yMax() <= y1):
                print(f'QDR drop die bterm {bt.getName()}')
                odb.dbBTerm.destroy(bt)
    ndel = 0
    for n in list(block.getNets()):
        if n.getITermCount() == 0 and n.getBTermCount() == 0 and not n.isSpecial():
            odb.dbNet.destroy(n)
            ndel += 1
    print(f'QDR nets removed {ndel} kept {len(list(block.getNets()))}')
    # rows: clip keeping the absolute site phase
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
    # tracks: clip keeping the absolute phase
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
    out = {'region_dbu': [x0, y0, x1, y1], 'region_um': [x0 / dbu, y0 / dbu, x1 / dbu, y1 / dbu],
           'area_mm2': (x1 - x0) * (y1 - y0) / dbu / dbu / 1e6, 'die_mm2': die.dx() * die.dy() / dbu / dbu / 1e6,
           'kept_instances': len(keep), 'removed_instances': len(drop), 'boundary_pins': nbt, 'boundary_by_edge': stats,
           'region_nets': len(nets_seen), 'rows': nr, 'kept_masters': {}}
    out['kept_names'] = sorted(i.getName() for i in block.getInsts())
    for i in block.getInsts():
        m = i.getMaster().getName()
        out['kept_masters'][m] = out['kept_masters'].get(m, 0) + 1
    Path(os.environ['QDR_OUT'] + '.json').write_text(json.dumps(out, indent=1))
    odb.write_db(block.getDataBase(), os.environ['QDR_OUT'])
    print('QDR_CUT_DONE', json.dumps(out))


# ------------------------------------------------------------------------------------------------------- host side
def region_pdn(text, keep, x0, y0, vertical):
    """Filter the r5 pdn.tcl to the kept instances; re-anchor core-grid stripe offsets to the region origin."""
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
            new = (off - org) % pitch
            line = line.replace(f'-offset {s.group(3)}', f'-offset {new:.4f}')
        out.append(line)
    return '\n'.join(out) + '\n', sorted(dropped)


def stage(a):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import qwen_die_drt_pilot as P
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'region.json').write_text(json.dumps({'x_lo': a.x_lo, 'x_hi': a.x_hi, 'y_top': a.y_top}))
    (a.out / 'qwen_die_region_cut.py').write_text(Path(__file__).read_text())
    (a.out / 'pilot.tcl').write_text(P.pilot_tcl(a.threads, a.libs))
    for c in ('ss', 'ff'):
        (a.out / f'sta_{c}.tcl').write_text(P.sta_tcl(c, a.libs))
    (a.out / 'run_pdn.tcl').write_text(P.HEAD + """
step load { read_db /work/region.odb }
step pdn { source /work/pdn_region.tcl; pdngen }
foreach net {VDD VSS} { if {[catch {check_power_grid -net $net} err]} { puts "OT_PGCHECK $net FAIL $err" } else { puts "OT_PGCHECK $net PASS" } }
step write { write_db /work/floorplan_pdn.odb }
puts OT_PDN_DONE
""")
    (a.out / 'start_region.sh').write_text(f"""#!/bin/bash
# region pilot: cut (python odb) -> PDN (filtered r5) -> pilot (GRT/DPL/GRT/DRT/RCX) -> STA SS / FF
set -u
cd $(dirname $0)
S={a.src}
for f in floorplan.odb pdn.tcl elements.lef phy_ew.lef; do ln -f $S/$f . 2>/dev/null || cp -f $S/$f .; done
date -u +%FT%TZ > cut.log.start
docker run --rm --name qfd_region_cut --memory=200g -e QDR_IN=/work/floorplan.odb -e QDR_OUT=/work/region.odb \\
  -e QDR_REGION_JSON=/work/region.json -v $(pwd):/work -w /work ${{IMAGE:-openroad/orfs:asap7lock}} \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -python -exit /work/qwen_die_region_cut.py > /work/cut.log 2>&1; rc=\\$?; chmod -R a+rwX /work; exit \\$rc"
echo $? > cut.log.exit; date -u +%FT%TZ > cut.log.end
[ "$(cat cut.log.exit)" = 0 ] || exit 1
python3 qwen_die_region_cut.py pdnfilter --out $(pwd) || exit 1
./run_case.sh . run_pdn.tcl run_pdn.log 16 200 && ./run_case.sh . pilot.tcl pilot.log {a.threads} {a.mem} && \\
  ./run_case.sh . sta_ss.tcl sta_ss.log 16 300 && ./run_case.sh . sta_ff.tcl sta_ff.log 16 300
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
    s.add_argument('--x-lo', type=float, default=11280.0)
    s.add_argument('--x-hi', type=float, default=13430.0)
    s.add_argument('--y-top', type=float, default=31216.0)
    s.add_argument('--libs', default='qfd_elements')
    s.add_argument('--threads', type=int, default=64)
    s.add_argument('--mem', type=int, default=400)
    p = sub.add_parser('pdnfilter')
    p.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    stage(a) if a.cmd == 'stage' else pdnfilter(a)


if __name__ == '__main__':
    main()
