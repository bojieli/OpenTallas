"""Inventory explicit mesh clock/shield geometry against plan-specific PG phases.

This changes no plan or shared default. A clear mesh-only candidate still needs
complete tree/access/shield/via checks, PG continuity, IR/EM and routed timing.
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path
import die_clock_128 as C
import die_clock_mesh as D
import die_infra as I
import schema


def inventory(P,mesh,offset):
    grid=copy.deepcopy(C.pg_grid(P))
    for row in grid:
        if row['layer'] in ('M8','M9'):row['offset_um']=offset
    pg=C.pg_shapes(I.pg_rects(P,grid))
    nd=D.NDR[mesh.get('ndr','8w')]
    ix=C.MetalIndex(nd['space'])
    for shape in pg:ix.add(shape)
    segments=[('M8',s['x0'],s['y'],s['x1'],s['y'],'ck_mesh_explicit','mesh') for s in mesh['M8']]
    segments += [('M9',s['x'],s['y0'],s['x'],s['y1'],'ck_mesh_explicit','mesh') for s in mesh['M9']]
    counts=Counter();examples=[];affected=set()
    for i,s in enumerate(C.clock_shapes(segments,nd,'VSS')):
        for j,what in ix.hits(s):
            key=f'{s[0]}:{s[2]}:{what}'
            counts[key]+=1;affected.add(i)
            if len(examples)<32:examples.append(dict(kind=what,mesh=list(s),pg=list(ix.shapes[j])))
    return dict(offset_um=offset,grid=grid,segments=len(segments),shapes=3*len(segments),pg_shapes=len(pg),
                conflicts=sum(counts.values()),affected_shapes=len(affected),by_kind=dict(counts),examples=examples,
                verdict='MESH_ONLY_CLEAR' if not counts else 'FAIL')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan');ap.add_argument('mesh');ap.add_argument('out')
    ap.add_argument('--offsets',default='4.32,2.16');a=ap.parse_args()
    P=schema.Plan(schema.load(a.plan),Path(a.plan));mesh=json.loads(Path(a.mesh).read_text());mesh=mesh.get('mesh',mesh)
    rows=[inventory(P,mesh,float(x)) for x in a.offsets.split(',')]
    result=dict(schema='opentallas.qc_mesh_pg_phase.v1',plan=a.plan,mesh=a.mesh,rows=rows,
                scope='mesh metal and drawn VSS shields vs plan-specific PG only; phase alternatives do not edit source or qualify full clock/IR')
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('examples','grid')} for r in rows]))


if __name__=='__main__':main()
