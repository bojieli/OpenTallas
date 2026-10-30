#!/usr/bin/env python3
"""Physical feasibility of exact scorer row1 source split: 1088+1088+570b. Plan-only; no routing claim."""
import sys,json,copy,time
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import lane_add as L;import schema as S
src=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=False)
r=json.loads((src/'die_plan.json').read_text())
east=['NW_hub','NW_b000','NW_b010','NW_b001','NW_b011','NW_b002','NW_b012','NW_b003','NW_b013','NW_b102']
top=['NW_hub','NW_spu0','NW_su01','NW_b010']+east[3:]
north=['NW_hub','NW_spu0','NW_su01','NW_su00','NW_b113','NW_b013','NW_b102']
paths={'east':east,'top':top,'north':north}
variants=[('east2176_top570',[(2176,'east'),(570,'top')]),('east1088_twice_top570',[(1088,'east'),(1088,'east'),(570,'top')]),('top2176_east570',[(2176,'top'),(570,'east')]),('east1088_top1088_north570',[(1088,'east'),(1088,'top'),(570,'north')])]
report=[]
for name,feeds in variants:
 B=L.Builder(copy.deepcopy(r),near_um=20000,max_hops=16,require_cycle_match=False,first_id=850);B.shared=set();rows=[]
 for bits,pn in feeds:
  chain=paths[pn]
  assert all(L.shared_edge(B.P,a,b) for a,b in zip(chain,chain[1:]))
  t=time.time();result=B.build_one(chain[0],chain[-1],bits,chain,'path',None,record=False)
  row=dict(bits=bits,path=pn,chain=chain,seconds=round(time.time()-t,3),pass_construction=result is not None,result=result,why=None if result else B._why)
  rows.append(row);print(name,json.dumps(row),flush=True)
  if result is None:break
 solved=len(rows)==len(feeds)and all(x['pass_construction']for x in rows)
 report.append(dict(variant=name,all_solved=solved,feeds=rows))
 if solved:
  d=out/name;d.mkdir();(d/'die_plan.json').write_text(json.dumps(B.raw,indent=1)+'\n')
(out/'corridor_report.json').write_text(json.dumps(report,indent=1)+'\n')
