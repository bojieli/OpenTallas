#!/usr/bin/env python3
"""Replace provisional stage rows with ALL mapped FF bodies and exact pin pairs.
Geometry uses actual LEF pins at legally planned coordinates; actual fresh ODB
application is a separate gate. Conservative whole-stage failures are retained.
"""
import argparse,collections,json
from pathlib import Path

def union(rr):
 return [min(r[0] for r in rr),min(r[1] for r in rr),max(r[2] for r in rr),max(r[3] for r in rr)] if rr else None
def dist(r,s):return max(abs(x-u)+abs(y-v) for x in [r[0],r[2]] for y in [r[1],r[3]] for u in [s[0],s[2]] for v in [s[1],s[3]])
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--placements',required=True);p.add_argument('--constraints',required=True);p.add_argument('--reach',required=True);p.add_argument('--native-boundary-pins');p.add_argument('--out',required=True);a=p.parse_args();inv=json.load(open(a.inventory));pl=json.load(open(a.placements));g=json.load(open(a.constraints));reach=json.load(open(a.reach));assert not pl['failed'];D=pl['dbu'];cs={c['inst']:c for c in inv['cells']};pos={c['inst']:c for c in pl['cells']};stages={s['stage']:dict(ff=[],origin_ff=[],reset_ff=[],start_launch={},start_capture={},reset_launch={},reset_capture={}) for s in inv['stages']};pin_cache={}
 def body(n):return[v/D for v in pos[n]['bbox_dbu']]
 def pin(n,p):
  key=n,p
  if key not in pin_cache:
   c=cs[n];q=pos[n];assert q['orient']=='R0';x,y=q['xy_dbu'];rr=g['masters'][c['master']]['pins'][p]['rects_dbu'];assert rr
   pin_cache[key]=[(x+min(r[1] for r in rr))/D,(y+min(r[2] for r in rr))/D,(x+max(r[3] for r in rr))/D,(y+max(r[4] for r in rr))/D]
  return pin_cache[key]
 for n,c in cs.items():
  if c['sequential']:
   z=stages[c['stage']];z['ff'].append(n);z['reset_ff' if c.get('role','origin')=='reset' else 'origin_ff'].append(n)
 edges=collections.defaultdict(list)
 for arc in reach['arcs']:
  src,dst=cs[arc['src_inst']],cs[arc['dst_inst']];kind='reset' if src.get('role')=='reset' or dst.get('role')=='reset' else 'start';sb=pin(src['inst'],arc['src_pin']);db=pin(dst['inst'],arc['dst_pin']);stages[src['stage']][kind+'_launch'][src['inst']+'/'+arc['src_pin']]=sb;stages[dst['stage']][kind+'_capture'][dst['inst']+'/'+arc['dst_pin']]=db
  if src['stage']!=dst['stage']:edges[src['stage'],dst['stage'],kind].append(dict(src_inst=src['inst'],src_pin=arc['src_pin'],src_pin_bbox_um=sb,dst_inst=dst['inst'],dst_pin=arc['dst_pin'],dst_pin_bbox_um=db,um=arc['um']))
 outst={}
 for name,z in stages.items():
  r=dict(all_ff_bbox_um=union([body(n) for n in z['ff']]),all_ff_count=len(z['ff']),origin_ff_bbox_um=union([body(n) for n in z['origin_ff']]),origin_ff_count=len(z['origin_ff']),reset_ff_bbox_um=union([body(n) for n in z['reset_ff']]),reset_ff_count=len(z['reset_ff']))
  for kind in ['start_launch','start_capture','reset_launch','reset_capture']:r[kind+'_pin_bbox_um']=union(list(z[kind].values()));r[kind+'_ff_pin_boxes']=z[kind]
  outst[name]=r
 edgeout=[]
 for (src,dst,kind),pairs in edges.items():
  whole=dist(outst[src]['all_ff_bbox_um'],outst[dst]['all_ff_bbox_um']);srcu=union([r['src_pin_bbox_um'] for r in pairs]);dstu=union([r['dst_pin_bbox_um'] for r in pairs]);actual=max(q['um'] for q in pairs);edgeout.append(dict(src_stage=src,dst_stage=dst,kind=kind,whole_stage_anycorner_um=whole,whole_stage_over405=whole>405+1e-9,endpoint_union_anycorner_um=dist(srcu,dstu),actual_registered_pair_max_um=actual,actual_registered_pair_over405=actual>405+1e-9,registered_pairs=pairs))
 native=json.load(open(a.native_boundary_pins)) if a.native_boundary_pins else {};outputs=[]
 for q in inv['outputs']:
  rec=dict(net=q['net'],dst_part=q['dst_part'],stage=q['stage'],actual_final_driver=dict(inst=q['source_inst'],pin=q['source_pin'],bbox_um=pin(q['source_inst'],q['source_pin'])),actual_launch_ff=dict(inst=q['launch_inst'],pin=q['launch_pin'],bbox_um=pin(q['launch_inst'],q['launch_pin'])))
  target=native.get(q['net']) or native.get(q['port'])
  if target:
   rec['native_target']=target;rec['native_target_geometry_kind']=target.get('geometry_kind','UNVERIFIED');r=target.get('rect_um')
   if r:rec['whole_stage_to_native_pin_anycorner_um']=dist(outst[q['stage']]['all_ff_bbox_um'],r);rec['actual_launch_to_native_pin_anycorner_um']=dist(rec['actual_launch_ff']['bbox_um'],r);rec['final_driver_to_native_pin_anycorner_um']=dist(rec['actual_final_driver']['bbox_um'],r)
  else:rec['native_target']='UNRESOLVED_NO_ACTUAL_NATIVE_PIN_BINDING'
  outputs.append(rec)
 result=dict(schema='ot_provider_actual_ff_boxes/1',scope='Actual mapped LEF FF bodies/pins at legal proposal positions; actual fresh OpenDB import NOT yet run',ODB_imported=False,stages=outst,interstage_edges=edgeout,outputs=outputs,summary=dict(stages=len(stages),all_ff=sum(s['all_ff_count'] for s in outst.values()),interstage_edges=len(edgeout),whole_stage_over405=sum(q['whole_stage_over405'] for q in edgeout),exact_registered_pair_over405=sum(q['actual_registered_pair_over405'] for q in edgeout),whole_stage_max_um=max((q['whole_stage_anycorner_um'] for q in edgeout),default=0),actual_registered_pair_max_um=max((q['actual_registered_pair_max_um'] for q in edgeout),default=0),native_outputs_unresolved=sum(isinstance(q['native_target'],str) for q in outputs),native_outputs_actual_ODB_bound=sum(isinstance(q['native_target'],dict) and q['native_target'].get('actual_ODB_bound') is True for q in outputs),declared_native_whole_stage_over405=sum(q.get('whole_stage_to_native_pin_anycorner_um',0)>405+1e-9 for q in outputs),declared_native_actual_launch_over405=sum(q.get('actual_launch_to_native_pin_anycorner_um',0)>405+1e-9 for q in outputs)))
 Path(a.out).write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps(result['summary'],indent=2))
if __name__=='__main__':main()
