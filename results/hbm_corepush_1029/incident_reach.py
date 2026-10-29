#!/usr/bin/env python3
"""Source-bound per-bit reach estimate for a CTLX/BFQ physical proposal.
Direct selected-source links only; absent providers and station materialization
are failures/dependencies, not invented paths or new-cycle claims.
"""
import argparse,json,math,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('old',type=Path);ap.add_argument('new',type=Path);ap.add_argument('graph',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
r=lambda p:json.loads(p.read_text())
g=r(a.graph);old=r(a.old/'die_plan.json');new=r(a.new/'die_plan.json');affected={'u_xl_Q_ctl__q0','u_xl_Q_ctl__q1','u_xq_Q_p1_bfq3'};cache={}
def point(root,plan,part,inst,port,bit):
 key=(str(root),part,inst);ty=next(q['type'] for q in plan['partitions'] if q['name']==part);t=plan['partition_types'][ty]
 if key not in cache:
  hs=[h for h in t.get('hard_cores',[]) if h['inst']==inst]
  if len(hs)!=1:raise ValueError(f'{part}/{inst}: expected1hardcorefound{len(hs)}')
  h=hs[0];pins=r(root/h['pins_file']);cache[key]=(h,{q['name']:q for q in pins})
 h,ps=cache[key];name=f'{port}[{bit}]';q=ps.get(name)
 if q is None and bit==0:q=ps.get(port)
 if q is None:raise ValueError(f'{part}/{inst}: missingpin{name}')
 x,y=q['x'],q['y'];W,H=h['outline_um'];ori=h.get('orient','R0')
 if ori in ('MY','R180'):x=W-x
 if ori in ('MX','R180'):y=H-y
 if ori not in ('R0','MX','MY','R180'):raise ValueError(f'unsupportedorient{ori}')
 off=h.get('track_offset_um') or [0,0]
 return [round(h['origin_um'][0]+off[0]+x,6),round(h['origin_um'][1]+off[1]+y,6)]
rows=[];missing=[];bits=[]
for e in g['edges']:
 if e['src_plan_instance'] not in affected and e['dst_plan_instance'] not in affected:continue
 if e['src_partition']!=e['dst_partition']:
  missing.append({'edge':e,'error':'crosspartitioncoordinateframe needsdieplacement'});continue
 local=[];err=None
 for sb,db in e['bit_pairs']:
  try:
   aa=point(a.old,old,e['src_partition'],e['src_plan_instance'],e['src_port'],sb);bb=point(a.old,old,e['dst_partition'],e['dst_plan_instance'],e['dst_port'],db)
   cc=point(a.new,new,e['src_partition'],e['src_plan_instance'],e['src_port'],sb);dd=point(a.new,new,e['dst_partition'],e['dst_plan_instance'],e['dst_port'],db)
  except (ValueError,KeyError,StopIteration,FileNotFoundError)as ex:err=str(ex);break
  od=sum(abs(x-y)for x,y in zip(aa,bb));nd=sum(abs(x-y)for x,y in zip(cc,dd));oz=max(0,math.ceil((od-1e-7)/405)-1);nz=max(0,math.ceil((nd-1e-7)/405)-1)
  local.append({'source_bit':sb,'capture_bit':db,'old_source_um':aa,'old_capture_um':bb,'new_source_um':cc,'new_capture_um':dd,'old_dist_um':round(od,6),'new_dist_um':round(nd,6),'old_min_station_count':oz,'new_min_station_count':nz})
 if err:missing.append({'edge':e,'error':err});continue
 rows.append({'edge':{k:v for k,v in e.items()if k!='bit_pairs'},'checked_bits':len(local),'old_max_um':max(q['old_dist_um']for q in local),'new_max_um':max(q['new_dist_um']for q in local),'bits_gaining_min_hop':sum(q['new_min_station_count']>q['old_min_station_count']for q in local),'actual_station_realization':'NOTQUALIFIED; bindcurrent_transport+streetrouter required'})
 bits.append({'edge':rows[-1]['edge'],'bits':local})
summary={'classification':'ESTIMATE exactselectedsource directbitlinks; notstations/clock/tokenclosure','graph_sha256':hashlib.sha256(a.graph.read_bytes()).hexdigest(),'groups_checked':len(rows),'bits_checked':sum(q['checked_bits']for q in rows),'groups_missing':len(missing),'groups_gaining_min_hop':sum(q['bits_gaining_min_hop']>0for q in rows),'bits_gaining_min_hop':sum(q['bits_gaining_min_hop']for q in rows),'rows':rows,'missing':missing}
a.out.mkdir(parents=True,exist_ok=False);(a.out/'summary.json').write_text(json.dumps(summary,indent=1)+'\n');(a.out/'perbit.json').write_text(json.dumps(bits,indent=1)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in ('rows','missing')}))
