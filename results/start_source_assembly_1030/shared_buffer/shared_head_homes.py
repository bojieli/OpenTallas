from pathlib import Path
import json,sys,math,collections
R=Path(__file__).parent;sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-s81-start-data-1030/tools/die_plan')
import schema as S,die_trial as DT
from start_data_emit import box,pin,overlaps,crosses,distance
p=json.load(open(R/'source_homes_candidatePG.json'));h=json.load(open(R/'shared_buffer/buffer_heads.json'));lib=json.load(open(R/'library_all.json'))['cell_library'];lib.update(json.load(open('/srv/opentallas-scratch/claude/wt/codex-s81-start-data-1030/results/start_data_emit_1030/actual_library_geometry.json'))['cell_library'])
site=DT.SiteMap(S.Plan(S.load(R/'candidate_pg_exclusion_plan_MODEL_ONLY.json')))
old=json.load(open('/srv/opentallas-scratch/claude/codex-flow-s81phy-1030/exactA/old_truth/tap_arrivals_TT.json'))['node_xy_um'];new=json.load(open('/srv/opentallas-scratch/claude/codex-flow-s81phy-1030/exactA/source_prep_contract.json'))['clock_nodes'];cp=dict(old);cp.update({k:v['xy']for k,v in new.items()})
occupied=[box(c,lib)for c in p['cells'].values()]+[(x-2.16,y-.54,x+2.16,y+.54)for x,y in cp.values()];idx=collections.defaultdict(list)
def add(r):
 for x in range(math.floor(r[0]/16),math.floor(r[2]/16)+1):
  for y in range(math.floor(r[1]/16),math.floor(r[3]/16)+1):idx[x,y].append(r)
for r in occupied:add(r)
def occ(r):return[b for x in range(math.floor(r[0]/16),math.floor(r[2]/16)+1)for y in range(math.floor(r[1]/16),math.floor(r[3]/16)+1)for b in idx[x,y]]
sources={(s['region'],s['signal']):s for s in p['source_records']};groups={g['region']:g for g in p['groups']};fails=[]
for hd in h['heads']:
 s=sources[hd['region'],hd['signal']];src=s['output_pin_um'];sx,sy=src;g=groups[hd['region']];x0,y0,X,Y=g['rect_um'];options=[]
 for xi in range(math.floor((sx-3)/.054),math.ceil((sx+3)/.054)+1):
  for yi in range(math.floor((sy-3)/.27),math.ceil((sy+3)/.27)+1):
   c=dict(instance=hd['instance'],master=hd['master'],xy_um=[round(xi*.054,6),round(yi*.27,6)],orient='R0'if yi%2==0 else'MX');r=box(c,lib);dst=pin(c,'A',lib);d=distance(src,dst)
   if d>3+1e-6:continue
   inside=x0-1e-6<=r[0]and r[2]<=X+1e-6 and y0-1e-6<=r[1]and r[3]<=Y+1e-6
   options.append((not inside,d,xi,yi,c,r,dst))
 found=None
 for outside,d,_,_,c,r,dst in sorted(options,key=lambda q:q[:4]):
  if any(overlaps(r,o)for o in occ(r)):continue
  if not all(site.legal(v)for v in [(r[0],r[1]),(r[2],r[1]),(r[0],r[3]),(r[2],r[3])]):continue
  for rt in [[src,[dst[0],src[1]],dst],[src,[src[0],dst[1]],dst]]:
   rt=[v for i,v in enumerate(rt)if i==0 or distance(v,rt[i-1])>1e-8]
   if not any(crosses(a,b,f[:4])for a,b in zip(rt,rt[1:])for f in site.forb):found=(c,r,rt,d,outside);break
  if found:break
 if not found:fails.append(dict(region=hd['region'],signal=hd['signal'],reason='no actualBUF8site/body/firstwire<=3um'));continue
 c,r,route,d,outside=found;add(r);hd.update(c);hd.update(source_pin_um=src,input_pin_um=pin(c,'A',lib),output_pin_um=pin(c,'Y',lib),first_route_um=route,first_wire_um=d,outside_original_capacity_tile=outside)
h.update(allocated_heads=sum(x['xy_um']is not None for x in h['heads']),unallocated=fails,max_first_wire_um=max(x.get('first_wire_um',0)for x in h['heads']),outside_capacity_tile=sum(x.get('outside_original_capacity_tile',False)for x in h['heads']),geometry_scope='proposed fullsource cells+all representedclockbody windows+candidatePGexclusions; unknown nativeSTDoccupancyheld')
(R/'shared_buffer/head_homes.json').write_text(json.dumps(h,indent=2)+'\n');print(json.dumps({k:h[k]for k in ['allocated_heads','unallocated','max_first_wire_um','outside_capacity_tile']}))
