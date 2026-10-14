#!/usr/bin/env python3
"""Actual native HC pin screen using explicit successor diagnostics and closed peers.

This never qualifies routed views. Successor tables must retain their actual
CTS Liberty models and clock references; closed peers are read directly.
"""
import argparse
import json
from pathlib import Path
import native_comb_seams as S
ROOT=Path(__file__).resolve().parents[2]

def screen(plan,models):
    geometries={}
    for leaf in plan['instances']:
        if not leaf.get('pin_assignment'):
            continue
        assignment=json.loads((ROOT/leaf['pin_assignment']).read_text())
        ox,oy=leaf['origin_um'];w,h=leaf['outline_um'];geom={}
        assert leaf['orient']=='R0', 'exact R0 pin transform required'
        for bus,port in assignment['ports'].items():
            assert not port.get('uniform'), 'actual per-bit assignment required'
            for bit,(face,layer,offset,depth) in enumerate(port['per_bit']):
                name=bus if port['bits']==1 else f'{bus}[{bit}]'
                x,y={'N':(offset,h-depth/2),'S':(offset,depth/2),
                     'W':(depth/2,offset),'E':(w-depth/2,offset)}[face]
                geom[name]=(ox+x,oy+y)
        geometries[leaf['instance']]=geom
    result=S.screen(plan,models,geometries)
    result.update(status='NOT_ADMITTED: provisional actual CTS successors and immutable closed peers; external/reset/source/chain joins remain',
                  actual_successor_sources={leaf['instance']:leaf['source_commit'] for leaf in plan['instances'] if leaf.get('source_commit')},
                  route_admission=False,price_ledger_claim=False)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--models',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=screen(json.loads(a.plan.read_text()),json.loads(a.models.read_text()))
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(len(r['seams']), 'actual seams:', r['fail_count'], 'setup failures,',r['hold_fail_count'],'hold failures,',r['missing_count'],'missing')
