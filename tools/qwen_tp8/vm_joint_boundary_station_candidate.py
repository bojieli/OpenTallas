#!/usr/bin/env python3
"""Necessary screens for two closed regional launch stations; no closure/adoption claim."""
import json,gzip,collections,re,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];BR=R.parent/'codex-qwen-vm-band';P=json.load(open(R/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json'));T=json.load(open(R/'results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json'));packet=json.load(gzip.open(BR/'results/arch/qwen_tp8_1012/vm_band_boundary_packet_codex.json.gz','rt'));bound=json.load(open(BR/'results/arch/qwen_tp8_1012/vm_band_boundary_extension_codex.json'));names=set(bound['necessary_geometry_bound']['scenarios'][0]['unreachable_launch_lane_names']);E=[e for e in packet['boundary_edges'] if e['lane'] in names];metrics={}
for e in packet['boundary_edges']:
 for side in ['launch','capture']:
  c=e['corner_budgets']['tt'][side];v=c['view'];n=c['pin'];metrics.setdefault(v,{})[n]={co:e['corner_budgets'][co][side] for co in ['tt','ff','ss']}
views={'E':'physical/ref_tile/qfd_vm_xrelay_t/views/ot_qfd_vm_xrelay_t','W':'physical/ref_tile/qfd_vm_xrelay_w/views/ot_qfd_vm_xrelay_w','P':'physical/ref_tile/qfd_vm_xpad2_t/views/ot_qfd_vm_xpad2_t'}
print({k:{p:sum(n.startswith(p+'[') for n in metrics[v]) for p in ['d','q']} for k,v in views.items()})
pins={}
for k,v in views.items():
 txt=next((R/v).glob('*.lef')).read_text();pins[k]={}
 for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s',txt,re.S):
  rr=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',m[2]);
  if rr:x,y,X,Y=map(float,rr.groups());pins[k][m[1]]=[(x+X)/2,(y+Y)/2]
C=P['children'];B={b['n']:b for b in P['x_relay_bays']};boxes=[]
for c in C:
 if c.get('region')==1:boxes.append((c['x'],c['y'],c['x']+c['w'],c['y']+c['h'],c['n']))
for bn,b in B.items():
 if b.get('region')==1:
  for t in T['bay_tiles'].get(bn,[]):
   x=b['x']+t['slot']*21.6;y=b['y'];txt=next((R/views[t['kind']]).glob('*.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',txt).groups());boxes.append((x,y,x+w,y+h,bn+'_t'+str(t['slot'])))
origin=P['slot']['region_origins']['1'];stations=[dict(n='g1_exit1',at=[origin[0]+868.32,origin[1]+879.12],kind='W'),dict(n='g1_exit2',at=[origin[0]+967.68,origin[1]+978.48],kind='W')]
for s in stations:
 x,y=s['at'];coll=[n for bx,by,BX,BY,n in boxes if x<BX+2.16-1e-6 and x+17.28>bx-2.16+1e-6 and y<BY+2.16-1e-6 and y+97.2>by-2.16+1e-6];print(s,'collisions',coll)
lanes=collections.defaultdict(list)
for e in E:lanes[e['lane']].append(e)
from scipy.optimize import linear_sum_assignment
for group,s in zip([7,8],stations):
 ll=[l for l,es in lanes.items() if ((es[0]['launch_stage']['bay'].endswith('_7') or es[0]['capture_stage']['bay']=='vm_pad_13_S0') if group==7 else (es[0]['launch_stage']['bay'].endswith('_8') and es[0]['capture_stage']['bay']!='vm_pad_13_S0'))];v=views[s['kind']];mat=[];cand={}
 for l in ll:
  costs=[]
  for q in range(64):
   worst=1e10;detail=[]
   for e in lanes[l]:
    i=8*q+e['bit'];n='d['+str(i)+']'
    if n not in metrics[v]:worst=-1e9;break
    xy=[a+b for a,b in zip(s['at'],pins[s['kind']][n])];L=sum(abs(a-b) for a,b in zip(e['launch_xy_um'],xy));tt=833.333-210-e['corner_budgets']['tt']['launch']['o_ps']-metrics[v][n]['tt']['s_ps']-.76*L;ss=833.333-210-e['corner_budgets']['ss']['launch']['o_ps']-metrics[v][n]['ss']['s_ps'];ff=e['corner_budgets']['ff']['launch']['l_ps']+.112*L-metrics[v][n]['ff']['h_ps']-100;worst=min(worst,tt,ss,ff,500-L);detail.append((e['bit'],i,L,tt,ss,ff))
   costs.append(-worst);cand[l,q]=detail
  mat.append(costs)
 row,col=linear_sum_assignment(mat);matches=[dict(lane=ll[i],station=s['n'],bit0=8*j,bits=cand[ll[i],j],worst_margin=-mat[i][j]) for i,j in zip(row,col)];print('group',group,'lanes',len(ll),'worst',min(m['worst_margin'] for m in matches),'bad',sum(m['worst_margin']<0 for m in matches));print(sorted(matches,key=lambda m:m['worst_margin'])[:1]);s['matches']=matches

out=dict(schema='opentallas.vm-joint-boundary-station-candidate.v1',status='FIRST_HOP_NECESSARY_SCREENS_PASS_NOT_QUALIFIED',core_masters_preserved=72,existing_region1_lane_tiles=len(boxes)-72,region=1,origin_um=origin,region_outline_um=P['slot']['region_um'][1],registered_payload_bits=688,lane_count=86,added_region_engine_edges=1,proposed_total_XPR=14,adoption='PROPOSED; requires second1ENGINE band stage and global all4096 lane equalization; no unitprice change.',setup_reserve_ps=210,hold_tree_ps=100,ss_policy='actual SS zero-wire budget only; no SS wire delay invented',existing_geometry_sha256={},stations=[])
import hashlib
for f in [R/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json',R/'results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json',BR/'results/arch/qwen_tp8_1012/vm_band_boundary_packet_codex.json.gz',BR/'results/arch/qwen_tp8_1012/vm_band_boundary_extension_codex.json']:out['existing_geometry_sha256'][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
for s in stations:
 sr=dict(name=s['n'],at_um=s['at'],outline_um=[17.28,97.2],view=views[s['kind']],registered_payload_bits=sum(len(m['bits']) for m in s['matches']),matches=[])
 for m in s['matches']:
  entries=[]
  for bit,regbit,L,tt,ss,ff in m['bits']:
   e=next(e for e in lanes[m['lane']] if e['bit']==bit);q='q['+str(regbit)+']';nq=[a+b for a,b in zip(s['at'],pins[s['kind']][q])];entries.append(dict(lane=m['lane'],bit=bit,region1_station_pin=q,new_launch_xy_um=nq,new_launch_corners={c:metrics[views[s['kind']]][q][c] for c in ['tt','ff','ss']},original_launch_stage=e['launch_stage'],original_launch_xy_um=e['launch_xy_um'],original_capture_stage=e['capture_stage'],original_capture_xy_um=e['capture_xy_um'],original_capture_corners={c:e['corner_budgets'][c]['capture'] for c in ['tt','ff','ss']},input_hop_manhattan_um=L,input_hop_tt_deep210_margin_ps=tt,input_hop_ss_zero_wire_margin_ps=ss,input_hop_ff_H100_margin_ps=ff))
  sr['matches'].append(dict(lane=m['lane'],bit0=int(m['bit0']),worst_input_necessary_margin=m['worst_margin'],bits=entries))
 out['stations'].append(sr)
(R/'results/arch/qwen_tp8_1012/vm_joint_g1_boundary_station_candidate.json').write_text(json.dumps(out,indent=1)+'\n')
print('WROTE joint station candidate')
