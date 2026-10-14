"""c5 diagnosis, cut check (2026-10-13), step 1 of 2: dump what the cut check needs from a die GRT checkpoint.

Run inside the ORFS container, the run's grt dir mounted READ-ONLY at /in and a scratch dir at /out:
  openroad -python -exit /out/c5diag_cut_dump.py
Writes (dbu = nm):
  /out/gcell.json           gcell grid lines (GRIDX, GRIDY), layers, array shape
  /out/gcell_<L>_{cap,use}.f32   per-GCELL GRT capacity / usage of M4..M9, row-major [ny][nx] float32.  As GRT stores
                            them: cap = the layer's undiminished tracks per gcell; use = net usage + every reduction
                            (layer adjustment, macro OBS, PG, pre-routes).  The cut check recovers the net part from
                            route.guide, so supply = cap - (use - guide usage) is GRT's own free capacity per edge.
  /out/nets.tsv             one line per signal net:  name \t ndrv \t drv_inst \t drv_master \t drv_pin \t dx \t dy \t
                            nsink \t sink0_inst \t sink0_master \t sx,sy;sx,sy;...   (pin-shape centres, placed netlist)
"""
import json
import sys
from array import array

import odb
from openroad import Design, Tech

IN, OUT = '/in', '/out'
src = sys.argv[1] if len(sys.argv) > 1 else 'ckpt_grt.odb'
ortech = Tech()          # keep the reference: Design(Tech()) frees the Tech and readDb segfaults
design = Design(ortech)
design.readDb(f'{IN}/{src}')
block = design.getBlock()
tech = block.getDb().getTech()
grid = block.getGCellGrid()
gx, gy = list(grid.getGridX()), list(grid.getGridY())
nx, ny = len(gx), len(gy)
layers = ['M4', 'M5', 'M6', 'M7', 'M8', 'M9']
if grid is not None and '--no-gcell' not in sys.argv:
    for ln in layers:
        lay = tech.findLayer(ln)
        cap, use = array('f'), array('f')
        gc, gu = grid.getCapacity, grid.getUsage
        for j in range(ny):
            for i in range(nx):
                cap.append(gc(lay, i, j))
                use.append(gu(lay, i, j))
        with open(f'{OUT}/gcell_{ln}_cap.f32', 'wb') as f:
            cap.tofile(f)
        with open(f'{OUT}/gcell_{ln}_use.f32', 'wb') as f:
            use.tofile(f)
        print('OT_CUTDUMP layer', ln, 'cap', sum(cap), 'use', sum(use), flush=True)
    json.dump(dict(GRIDX=gx, GRIDY=gy, nx=nx, ny=ny, layers=layers, dbu_per_um=block.getDbUnitsPerMicron(),
                   die=[block.getDieArea().xMin(), block.getDieArea().yMin(), block.getDieArea().xMax(),
                        block.getDieArea().yMax()]), open(f'{OUT}/gcell.json', 'w'))

n = bad = 0
with open(f'{OUT}/nets.tsv', 'w') as f:
    for net in block.getNets():
        if net.getSigType() in ('POWER', 'GROUND') or net.isSpecial():
            continue
        drv, sinks, s0, ndrv = None, [], ('', ''), 0
        for it in net.getITerms():
            r = it.getAvgXY()
            if r[0]:
                x, y = r[1], r[2]
            else:
                bb = it.getInst().getBBox()
                x, y = (bb.xMin() + bb.xMax()) // 2, (bb.yMin() + bb.yMax()) // 2
                bad += 1
            inst = it.getInst()
            if it.isOutputSignal():
                ndrv += 1
                if drv is None:
                    drv = (inst.getName(), inst.getMaster().getName(), it.getMTerm().getName(), x, y)
                    continue
            if not sinks:
                s0 = (inst.getName(), inst.getMaster().getName())
            sinks.append(f'{x},{y}')
        for bt in net.getBTerms():
            bb = bt.getBBox()
            x, y = (bb.xMin() + bb.xMax()) // 2, (bb.yMin() + bb.yMax()) // 2
            if bt.getIoType() == 'INPUT' and drv is None:
                ndrv += 1
                drv = ('PIN', 'PIN', bt.getName(), x, y)
            else:
                if not sinks:
                    s0 = ('PIN', 'PIN')
                sinks.append(f'{x},{y}')
        if drv is None:
            drv = ('', '', '', -1, -1)
        f.write('\t'.join([net.getName(), str(ndrv), drv[0], drv[1], drv[2], str(drv[3]), str(drv[4]), str(len(sinks)),
                           s0[0], s0[1], ';'.join(sinks)]) + '\n')
        n += 1
        if n % 1000000 == 0:
            print('OT_CUTDUMP nets', n, flush=True)
print('OT_CUTDUMP done nets', n, 'iterms_without_shape', bad, 'nx', nx, 'ny', ny, flush=True)
