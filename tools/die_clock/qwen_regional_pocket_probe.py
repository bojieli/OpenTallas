#!/usr/bin/env python3
"""Readonly exact-bay model for inherited long regional leaf connections.

Uses actual full-shape source floorplan occupancy and actual legacy output
pins. Candidate leaves are whole-footprint reserved, but not a complete tree
placement, physical row/PDN proof, timing result, or phase certificate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from qwen_exact_corridor import ExactBayGrid,XP,YP


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main(a):
    from openroad import Tech,Design
    tech=Tech();floor=Design(tech);floor.readDb(a.floorplan)
    block=floor.getBlock();u=block.getDbUnitsPerMicron();die=block.getDieArea()
    rows=[];physical_rows=[]
    for obj in block.getInsts():
        if not (obj.getMaster().isBlock() or obj.isPlaced()):continue
        q=obj.getBBox();rows.append((obj.getName(),(q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u)))
    for row in block.getRows():
        q=row.getBBox();physical_rows.append((q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u))
    g=ExactBayGrid(die.xMax()/u,die.yMax()/u,rows)
    oldtech=Tech();legacy=Design(oldtech);legacy.readDb(a.legacy_odb)
    old=legacy.getBlock();ou=old.getDbUnitsPerMicron()
    m=json.loads(Path(a.legacy_manifest).read_text());models=[];other=[]
    def xy(pin):
        q=pin.getBBox();return ((q.xMin()+q.xMax())/2/ou,(q.yMin()+q.yMax())/2/ou)
    for name,*_ in m['cells']:
        if m['cell_tree'].get(name)=='spine':continue
        obj=old.findInst(name);out=obj.findITerm('Y') if obj else None
        if out is None or out.getNet() is None:continue
        p=xy(out);loads=[it for it in out.getNet().getITerms() if it.getIoType()=='INPUT']
        coords=[xy(it) for it in loads]
        lengths=[sum(abs(p[i]-q[i]) for i in (0,1)) for q in coords]
        if not lengths or max(lengths)<=405:continue
        if not re.search(r'_L[0-9]+$',name):
            other.append(dict(source=name+'/Y',max_old_direct_um=max(lengths)));continue
        center=tuple(sorted(q[i] for q in coords)[len(coords)//2] for i in (0,1))
        cell=g.nearest_free(*center);site=g.reserve(cell)
        # Whole real output pin lies within the1.62x.27 reserved footprint.
        bound=max(sum(abs(site[i]-q[i]) for i in (0,1))+XP+YP for q in coords)
        has_row=any(r[0]<=site[0] and r[1]<=site[1] and r[2]>=site[0]+XP and r[3]>=site[1]+YP for r in physical_rows)
        models.append(dict(source=name+'/Y',old_output_xy_um=p,new_leaf_origin_um=site,
                           loads=[dict(pin=it.getInst().getName()+'/'+it.getMTerm().getName(),xy_um=q)
                                  for it,q in zip(loads,coords)],
                           old_max_direct_um=max(lengths),new_max_direct_bound_um=bound,
                           required_containing_row_missing=not has_row,reach_pass=bound<=405))
    result=dict(schema='opentallas.qwen.regional_pocket_model.v1',floorplan_sha256=sha(a.floorplan),
                legacy_odb_sha256=sha(a.legacy_odb),legacy_manifest_sha256=sha(a.legacy_manifest),
                modeled_long_leaf_sources=len(models),model_reach_failures=sum(not m['reach_pass'] for m in models),
                other_long_regional_sources=other,leaf_models=models,
                full_tree_placement_proven=False,physical_rows_created=False,power_qualified=False,
                timing_qualified=False,production_admitted=False,
                remaining=['Place all region and spine buffers with global whole-footprint reservations',
                           'Prove actual physical rows/rails/PDN and every actual routed stage<=405um',
                           'Native clock references/TTFF+SS sensitivity and programme-bound phase replay'])
    Path(a.out).write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('leaf_models','other_long_regional_sources')},indent=1),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('floorplan','legacy-odb','legacy-manifest','out'):p.add_argument('--'+arg,required=True)
    main(p.parse_args())
