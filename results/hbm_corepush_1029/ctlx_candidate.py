#!/usr/bin/env python3
"""Emit a NON-ADOPTED die-local CTLX shrink proposal; never modifies source.
Requires the exact reviewed pin identities and old outline. Clock/reset/stations
are inventoried for the owning C25 event, not silently called requalified.
"""
import argparse,copy,hashlib,json,math,shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('out',type=Path);ap.add_argument('packet',type=Path);ap.add_argument('--paired-bfq',action='store_true');a=ap.parse_args()
assert a.source.resolve()!=a.out.resolve() and not a.out.exists()
read=lambda p:json.loads(p.read_text())
write=lambda p,d:p.write_text(json.dumps(d,indent=1)+'\n')
plan=read(a.source/'die_plan.json'); before=copy.deepcopy(plan)
packet=read(a.packet/'physical_contract_delta.json')
assert packet['outline_um']==[216.0,233.28]
newraw=read(a.packet/'m5_lowpins_pins.json')
newpins=[dict(name=q['bus']+(f"[{q['bit']}]" if q['bit'] is not None else ''),layer=q['layer'],x=q['x'],y=q['y'],**({k:q[k] for k in ('w','h') if k in q})) for q in newraw]
assert len({q['name'] for q in newpins})==len(newpins)==5782
np={q['name']:q for q in newpins}
report={'classification':'CANDIDATE ONLY; no bind/clock/reset/station/token/route qualification','source_plan_sha256':hashlib.sha256((a.source/'die_plan.json').read_bytes()).hexdigest(),'instances':[],'pin_deltas':[],'station_dependencies':[],'hard_collisions':[]}
shutil.copytree(a.source,a.out)
ce=read(a.out/'clock_entries.json')
for ty,t in plan['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h['module']!='ot_hgi_sm_xload_cl2_ctlx':continue
  assert h['outline_um']==[391.392,416.448],(ty,h)
  oldpins=read(a.source/h['pins_file']);op={q['name']:q for q in oldpins}
  assert op.keys()==np.keys(),(op.keys()-np.keys(),np.keys()-op.keys())
  old=copy.deepcopy(h);oldxy=list(h['origin_um']);h['origin_um']=[round(oldxy[0]+86.4,6),round(oldxy[1]+95.04,6)];h['outline_um']=[216.0,233.28]
  h['pins_file']='cores/ot_hgi_sm_xload_cl2_ctlx__candidate_216x233p28_m5.json';write(a.out/h['pins_file'],newpins)
  # Previous routed views have another outline and MUST NOT be reused.
  for k in ('lef','lib'):h.pop(k,None)
  h['note']=h.get('note','')+' | CANDIDATE CTLX locality shrink; fresh view required, lower-layer pin-access G2 pending'
  row={'type':ty,'inst':h['inst'],'old_origin_um':oldxy,'new_origin_um':h['origin_um'],'old_outline_um':old['outline_um'],'new_outline_um':h['outline_um'],'old_clock_taps':[],'new_clock_taps':[]}
  for tap in t.get('clock',{}).get('taps',[]):
   if tap.get('name')==h['inst']:
    row['old_clock_taps'].append(copy.deepcopy(tap));tap['xy']=[round(h['origin_um'][0]+108,6),round(h['origin_um'][1]+116.64,6)];tap['note']=tap.get('note','')+' | CANDIDATE clock coordinate; entire regional tree and CA must rebuild'
    row['new_clock_taps'].append(copy.deepcopy(tap))
  report['instances'].append(row)
  for name,q in np.items():
   z=op[name];report['pin_deltas'].append({'type':ty,'inst':h['inst'],'pin':name,'old':z,'new':q,'old_parent_um':[round(oldxy[0]+z['x'],6),round(oldxy[1]+z['y'],6)],'new_parent_um':[round(h['origin_um'][0]+q['x'],6),round(h['origin_um'][1]+q['y'],6)]})
  for j,s in enumerate(t.get('internal_stations',[])):
   if any('u_xl_Q_ctl' in s.get(k,'') for k in ('conn','launch','capture')):
    report['station_dependencies'].append({'type':ty,'index':j,'inst':h['inst'],'station':s,'required':'Rebuild source-bound per-bit endpoint paths; keep/price register counts in C25 event'})
  # Shrink rectangle must stay inside its prior lot, so neighbours cannot acquire overlap.
  nx,ny=h['origin_um'];ow,oh=old['outline_um'];assert oldxy[0]<=nx and oldxy[1]<=ny and nx+216<=oldxy[0]+ow and ny+233.28<=oldxy[1]+oh
 for ent in ce.get(ty,{}).values():
  if ent.get('module')=='ot_hgi_sm_xload_cl2_ctlx':
   ent['xy_um']=[108,116.64];ent['island_um']=[103.68,112.32,112.32,120.96];ent['source']='CANDIDATE CTLX216x233.28; same merged clock identities; native clk_cal198.72 requires fresh source tree'
if a.paired_bfq:
 report['bfq_moves']=[]
 for ty in ('q_hub_nw','q_hub_ne'):
  t=plan['partition_types'][ty]
  h=next(h for h in t['hard_cores'] if h['inst']=='u_xq_Q_p1_bfq3')
  oldxy=list(h['origin_um']);h['origin_um']=[oldxy[0],round(oldxy[1]+69.12,6)]
  for tap in t.get('clock',{}).get('taps',[]):
   if tap.get('name')==h['inst']:tap['xy']=[tap['xy'][0],round(tap['xy'][1]+69.12,6)]
  row={'type':ty,'inst':h['inst'],'old_origin_um':oldxy,'new_origin_um':h['origin_um'],'hard_collisions':[],'new_station_centre_hits':[],'station_dependencies':[]}
  x,y=h['origin_um'];w,z=h['outline_um']
  for o in t['hard_cores']:
   if o['inst']==h['inst']:continue
   ox,oy=o['origin_um'];ow,oh=o['outline_um']
   if x<ox+ow and ox<x+w and y<oy+oh and oy<y+z:row['hard_collisions'].append(o['inst'])
  for j,st in enumerate(t.get('internal_stations',[])):
   if h['inst'] in st.get('conn','') or h['inst'] in st.get('launch','') or h['inst'] in st.get('capture',''):row['station_dependencies'].append({'index':j,'station':st})
   for k,(rx,ry) in enumerate(st.get('regs_um',[])):
    inside_new=x<=rx<=x+w and y<=ry<=y+z
    inside_old=oldxy[0]<=rx<=oldxy[0]+w and oldxy[1]<=ry<=oldxy[1]+z
    if inside_new and not inside_old:row['new_station_centre_hits'].append({'index':j,'reg_index':k,'xy_um':[rx,ry],'conn':st.get('conn')})
  report['bfq_moves'].append(row)
 assert not any(q['hard_collisions']for q in report['bfq_moves']),report['bfq_moves']
assert len(report['instances'])==4
cm=read(a.out/'core_macros.json');m=cm['cores']['ot_hgi_sm_xload_cl2_ctlx'];oldm=copy.deepcopy(m);m.update(status='PLAN-TRIAL',outline_um=[216.0,233.28],basis='CANDIDATE native-area+pin-capacity, no new place')
assert len(m['macros'])==1
macro=m['macros'][0];r=macro['rect_um'];macro['rect_um']=[60.48,142.56,round(60.48+r[2]-r[0],6),round(142.56+r[3]-r[1],6)];m['replaces']=oldm
report['new_islands']=packet['islands'];report['required_before_PNR']=packet['before_any_PNR'];report['optional_bfq3']=packet['optional_bfq3_cotranslation'];report['data_or_core_cycles_added']=0;report['parent_cycles']='UNRESOLVED until per-bit station recompose; previous direct1024-bit BFQ path would need co-translation or a new stage'
write(a.out/'die_plan.json',plan);write(a.out/'clock_entries.json',ce);write(a.out/'core_macros.json',cm);write(a.out/'ctlx_candidate_report.json',report)
print(json.dumps({'instances':len(report['instances']),'pins_per_instance':len(np),'pin_records':len(report['pin_deltas']),'station_rows_requiring_recompose':len(report['station_dependencies']),'out':str(a.out)}))
