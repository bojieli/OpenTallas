#!/usr/bin/env python3
"""DIE-CLOCK (2026-10-16): dump a die ODB's geometry needed by the die clock builder, once, to small TSVs.

  openroad -python -no_init -exit die_clock_geom_dump.py --odb floorplan.odb --out DIR [--roots inst/pin,...]
Writes DIR/blocks.tsv   (inst, master, x0, y0, x1, y1 um; every block master instance = hard obstacle)
       DIR/clknets.tsv  (root pin, load inst/pin, master, x, y) for every PLL output and every cfifo co/rf output
       DIR/die.json     (die size, dbu, row origin).
"""
import argparse, json
from pathlib import Path


def main():
    import odb
    ap = argparse.ArgumentParser()
    ap.add_argument('--odb', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--roots', default='')
    ap.add_argument('--pairs', action='store_true', help='also write DIR/pairs.tsv: P instA instB net for every signal net '
                    'joining 2..--max-fanout block instances (die_clock_check P rows: the communicating tile pairs)')
    ap.add_argument('--max-fanout', type=int, default=8)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    db = odb.dbDatabase.create(); odb.read_db(db, a.odb)
    blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron(); die = blk.getDieArea()
    rows = blk.getRows()
    r0 = rows[0].getOrigin() if rows else (0, 0)
    roots = [r for r in a.roots.split(',') if r]
    with open(a.out / 'blocks.tsv', 'w') as fb:
        for inst in blk.getInsts():
            m = inst.getMaster()
            if not m.isBlock():
                continue
            b = inst.getBBox()
            fb.write(f'{inst.getName()}\t{m.getName()}\t{b.xMin()/u:.3f}\t{b.yMin()/u:.3f}\t{b.xMax()/u:.3f}\t{b.yMax()/u:.3f}\n')
            mn = m.getName()
            if mn.startswith('dsfd_cfifo'):
                for p in ('co', 'rf'):
                    it = inst.findITerm(p) or inst.findITerm(p + '[0]')
                    if it and it.getNet():
                        roots.append(inst.getName() + '/' + it.getMTerm().getName())
            if inst.getName() == 'sp_collective':
                for it in inst.getITerms():
                    if it.getMTerm().getName().startswith('pll_') and it.getNet():
                        roots.append(inst.getName() + '/' + it.getMTerm().getName())
    with open(a.out / 'clknets.tsv', 'w') as fc:
        for r in roots:
            it = blk.findITerm(r)
            if (not it or not it.getNet()) and blk.findITerm(r + '[0]'):
                r = r + '[0]'     # 1-bit bus pins (pll/pll_c[0]); the dump names the literal pin
                it = blk.findITerm(r)
            if not it or not it.getNet():
                print('GEOM_DUMP_ROOT_MISSING', r)
                continue
            for ld in it.getNet().getITerms():
                if ld.getIoType() != 'INPUT':
                    continue
                b = ld.getBBox()
                fc.write(f'{r}\t{ld.getInst().getName()}/{ld.getMTerm().getName()}\t{ld.getInst().getMaster().getName()}\t'
                         f'{(b.xMin()+b.xMax())/2/u:.3f}\t{(b.yMin()+b.yMax())/2/u:.3f}\n')
    if a.pairs:
        clk = set()
        for r in roots:
            it = blk.findITerm(r) or blk.findITerm(r + '[0]')
            if it and it.getNet():
                clk.add(it.getNet().getName())
        n_p = 0
        with open(a.out / 'pairs.tsv', 'w') as fp:
            for net in blk.getNets():
                if net.getSigType() in ('POWER', 'GROUND', 'CLOCK') or net.getName() in clk:
                    continue
                its = net.getITerms()
                if len(its) < 2 or len(its) > 4 * a.max_fanout:
                    continue
                ins = sorted({x.getInst().getName() for x in its if x.getInst().getMaster().isBlock()})
                if not 2 <= len(ins) <= a.max_fanout:
                    continue
                for i in range(len(ins)):
                    for j in range(i + 1, len(ins)):
                        fp.write(f'P\t{ins[i]}\t{ins[j]}\t{net.getName()}\n'); n_p += 1
        print('GEOM_DUMP_PAIRS', n_p)
    (a.out / 'die.json').write_text(json.dumps(dict(w=die.xMax()/u, h=die.yMax()/u, dbu=u, row0=[r0[0]/u, r0[1]/u] if rows else None,
                                                    rows=len(rows), roots=len(roots))) + '\n')
    print('GEOM_DUMP_DONE', len(roots))


if __name__ == '__main__':
    main()
