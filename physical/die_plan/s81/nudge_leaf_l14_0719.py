#!/usr/bin/env python3
"""Reserve 2um for station D/Q access on two t56 scalar-control chains (0 cycles).

Original points are outside the same hard-core halos. Move the first station
1.2um north and final station3.6um west, leaving every stage count unchanged.
This is planned geometry; actual placed D/Q reach still gates G3.
"""
import json,sys
from pathlib import Path
OLD={'u_lf.u_vq.m_q':[[777.708,907.198],[828.697,656.652]],
     'u_lf.u_vq.m_b':[[777.708,907.19],[829.035,656.652]]}
NEW={k:[[v[0][0],round(v[0][1]+1.2,3)],[round(v[1][0]-3.6,3),v[1][1]]] for k,v in OLD.items()}

def apply(raw):
    t=raw['partition_types']['ot_s81sl_leaf__t56'];found=set()
    for e in t['internal_stations']:
        cap=e.get('capture')
        if cap not in OLD:continue
        assert e['regs_um'] in (OLD[cap],NEW[cap]),(cap,e['regs_um'])
        e['regs_um']=NEW[cap];e['note']='LEAF0719: unchanged 2-stage scalar chain, <=402um planned legs plus2um station pin allowance'
        pts=[e['from_um'],*e['regs_um'],e['to_um']]
        assert max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(pts,pts[1:]))<=402.0
        found.add(cap)
    assert found==set(OLD),found

if __name__=='__main__':
    p=Path(sys.argv[1]);d=json.loads(p.read_text());apply(d);p.write_text(json.dumps(d,separators=(',',':'))+'\n');print('t56 scalar stations nudged: 0 cycles; planned leg<=402um, actual placed D/Q proof required')
