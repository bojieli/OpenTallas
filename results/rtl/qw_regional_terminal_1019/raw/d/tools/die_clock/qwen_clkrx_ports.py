#!/usr/bin/env python3
"""Q-CLK 10-18: complete the qfd_clkrx root ports in a Qwen compute die ODB (stand-in for the GEN fix).

Finding (dv2f14bi): the GEN's qfd_clkrx LEF abstract has 46 pll_r* pins, but die.v connects 65 (pll_r55, pll_r89..r106
missing: 'STA-0201 instance clk_rx port pll_rNN not found' x19 in the case run.log).  Those 19 region trunks (~900 die
clock entry pins: 6 c_b16, all 12 dv slices, native59, landings, ~750 reset repeaters) have NO driver in the physical
die.  This script rebuilds clk_rx on a master with every port die.v connects, each pll_r<k> pin at the GEN's own stable
slot (tools/qwen_kv_die/rom_r22k.py: 3.2 um grid, x0 = 180.668 + (k % 16) * 3.2, y0 = 180.576 + (k // 16) * 3.2 for a
412.536 macro), and connects the trunk nets.  Nothing else changes.  The real fix is in the GEN (Q-DIE15).

  openroad -python -no_init -exit qwen_clkrx_ports.py --odb IN.odb --die-v die.v --out OUT.odb
"""
import argparse
import re


def main():
    import odb
    ap = argparse.ArgumentParser()
    ap.add_argument('--odb', required=True)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--inst', default='clk_rx')
    a = ap.parse_args()
    line = next(ln for ln in open(a.die_v) if re.match(rf'\s*qfd_clkrx\s+{a.inst}\s*\(', ln))
    conns = re.findall(r'\.(\w+)\((\w+)\)', line)
    db = odb.dbDatabase.create(); odb.read_db(db, a.odb)
    blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron(); tech = db.getTech()
    inst = blk.findInst(a.inst); old = inst.getMaster()
    have = {m.getName() for m in old.getMTerms()}
    missing = [(p, n) for p, n in conns if p + '[0]' not in have and p not in have]
    print('QCLK_CLKRX die.v ports', len(conns), 'lef pins', len(have), 'missing', len(missing), [p for p, _ in missing])
    if not missing:
        odb.write_db(db, a.out); return
    lib = odb.dbLib.create(db, 'qclk_clkrx_fix', tech, ',')
    m = odb.dbMaster.create(lib, old.getName() + '_qclk')
    m.setWidth(old.getWidth()); m.setHeight(old.getHeight()); m.setType(old.getType())
    m.setSymmetryX(); m.setSymmetryY()
    m8 = tech.findLayer('M8')
    for mt in old.getMTerms():
        nt = odb.dbMTerm.create(m, mt.getName(), mt.getIoType(), mt.getSigType())
        for mp in mt.getMPins():
            np_ = odb.dbMPin.create(nt)
            for bx in mp.getGeometry():
                odb.dbBox.create(np_, bx.getTechLayer(), bx.xMin(), bx.yMin(), bx.xMax(), bx.yMax())
    for p, _ in missing:
        k = int(re.fullmatch(r'pll_r(\d+)', p).group(1))
        x0, y0 = 180.668 + (k % 16) * 3.2, 180.576 + (k // 16) * 3.2
        nt = odb.dbMTerm.create(m, p + '[0]', 'OUTPUT', 'SIGNAL')
        odb.dbBox.create(odb.dbMPin.create(nt), m8, int(round(x0 * u)), int(round(y0 * u)),
                         int(round((x0 + 0.4) * u)), int(round((y0 + 0.04) * u)))
    for ob in old.getObstructions():
        odb.dbBox.create(m, ob.getTechLayer(), ob.xMin(), ob.yMin(), ob.xMax(), ob.yMax())
    m.setFrozen()
    loc, orient, st = inst.getLocation(), inst.getOrient(), inst.getPlacementStatus()
    nets = {it.getMTerm().getName(): it.getNet() for it in inst.getITerms() if it.getNet()}
    odb.dbInst.destroy(inst)
    ni = odb.dbInst.create(blk, m, a.inst)
    ni.setOrient(orient); ni.setLocation(loc[0], loc[1]); ni.setPlacementStatus(st)
    made = 0
    for it in ni.getITerms():
        nm = it.getMTerm().getName()
        net = nets.get(nm)
        if net is None and nm.endswith('[0]'):
            dv = dict(conns).get(nm[:-3])
            net = blk.findNet(dv) or blk.findNet(dv + '[0]') if dv else None
            if net is not None:
                made += 1
        if net is not None:
            it.connect(net)
    loads = {}
    for p, n in missing:
        it = ni.findITerm(p + '[0]'); net = it.getNet() if it else None
        loads[p] = (len([x for x in net.getITerms() if x.getIoType() == 'INPUT']) if net else None)
    print('QCLK_CLKRX connected', made, 'of', len(missing), 'loads', loads)
    if made != len(missing):
        raise SystemExit('QCLK_CLKRX FAIL: trunk nets missing in the ODB')
    odb.write_db(db, a.out)


if __name__ == '__main__':
    main()
