#!/usr/bin/env python3
"""Candidate spare P2 targets with exact TT source/P2/band pin constraints.
Outgoing boundary only; placement and region predecessors remain unqualified.
"""
import argparse,collections,gzip,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=('P','E','W'),default='P');args=ap.parse_args();kind=args.kind
 s=json.loads((A/'vm_band_boundary_packet_codex.json').read_text());p=json.load(gzip.open(ROOT/s['packet']['path'],'rt'));plan=json.loads((A/'vm_leaf_plan_claude.json').read_text());bays={b['n']:b for b in plan['x_relay_bays']};groups=collections.defaultdict(list)
 selected={(e['launch_stage']['bay'],e['launch_stage']['slot'])for e in p['boundary_edges']if e['must_move_launch_constraint']}
 for e in p['boundary_edges']:
  k=(e['launch_stage']['bay'],e['launch_stage']['slot'])
  if k in selected:groups[k].append(e)
 def reach(l,c):return min(500,(833.3333333333-210-l['o_ps']-c['s_ps'])/.76)-.2
 records=[]
 for (bay,slot),es in sorted(groups.items()):
  es=sorted(es,key=lambda e:(e['lane'],e['bit']));ox=bays[bay]['x']+21.6*slot;oy=bays[bay]['y'];u0=ox+oy;v0=ox-oy;targets=[]
  for target in s['spare_slots']:
   tx,ty=target['at'];ulo=vlo=-math.inf;uhi=vhi=math.inf;exitworst=math.inf;exitfails=0
   for pb,e in enumerate(es):
    pin_table=p['P2_actual_pins'] if kind=='P' else p['one_stage_relay_actual_pins'][kind];dp=pin_table['d'][pb];qp=pin_table['q'][pb];ls=e['corner_budgets']['tt']['launch'];cs=e['corner_budgets']['tt']['capture'];bx,by=e['capture_xy_um'];qx,qy=qp['xy_um']
    outgoing=abs(tx+qx-bx)+abs(ty+qy-by);er=reach(qp['corners']['tt'],cs);exitworst=min(exitworst,er-outgoing)
    if outgoing>er:exitfails+=1
    px=e['launch_xy_um'][0]-ox;py=e['launch_xy_um'][1]-oy;dx,dy=dp['xy_um'];r=reach(ls,dp['corners']['tt']);u=tx+dx+ty+dy-px-py;v=tx+dx-ty-dy-px+py
    ulo=max(ulo,u-r);uhi=min(uhi,u+r);vlo=max(vlo,v-r);vhi=min(vhi,v+r)
   if exitfails or ulo>uhi or vlo>vhi:continue
   u=min(max(u0,ulo),uhi);v=min(max(v0,vlo),vhi);x=(u+v)/2;y=(u-v)/2;origins=[]
   for ix in range(math.floor(x/2.16)-2,math.ceil(x/2.16)+3):
    for iy in range(math.floor(y/2.16)-2,math.ceil(y/2.16)+3):
     xx=ix*2.16;yy=iy*2.16
     if ulo<=xx+yy<=uhi and vlo<=xx-yy<=vhi:origins.append((abs(xx-ox)+abs(yy-oy),xx,yy))
   if not origins:continue
   distance,x,y=min(origins)
   targets.append(dict(target=target,source_origin_um=[round(x,4),round(y,4)],source_delta_um=[round(x-ox,4),round(y-oy,4)],source_L1_move_um=round(distance,4),P2_to_band_worst_reach_margin_um=round(exitworst,4),source_u_interval=[ulo,uhi],source_v_interval=[vlo,vhi]))
  targets.sort(key=lambda z:(z['source_L1_move_um'],-z['P2_to_band_worst_reach_margin_um']))
  records.append(dict(bay=bay,slot=slot,bits=len(es),relay_bit_mapping=[dict(relay_bit=i,lane=e['lane'],bit=e['bit'])for i,e in enumerate(es)],feasible_outgoing_candidate_count=len(targets),best_targets=targets[:8]))
 out=dict(schema='opentallas.qwen.vm-band-spare-P2-candidates.v1',qualification=False,status='EXACT_TT_OUTGOING_PINS_ONLY_NOT_ASSIGNED',
  source_packet_sha256=s['packet']['sha256'],candidate_relay_kind=kind,added_enabled_edges=2 if kind=='P' else 1,latency_adoption='proposed only; other lanes would need equalization to same XPR',candidates=records,
  constraints=['Stable sorted lane+bit mapping is explicit; no existing source indices or phase order changed.','Uses conservative deep entry210ps totalsetup reserve; no predecessor/internal region links, whole-geometry, hold, SS route wire or combined cut checked.','Targets are alternatives, not simultaneous occupancy grants; source origins may overlap cores or each other.','Loader/load_step cannot be paused by core_step; fill-fire consumes each held valid/token once.'])
 (A/('vm_band_boundary_staging_codex.json' if kind=='P' else f'vm_band_boundary_staging_{kind}_codex.json')).write_text(json.dumps(out,indent=1)+'\n')
 for r in records:print(r['bay'],r['slot'],r['feasible_outgoing_candidate_count'],r['best_targets'][:1])
if __name__=='__main__':main()
