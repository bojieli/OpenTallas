import json,copy,shutil,hashlib,sys
from pathlib import Path
base=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists();shutil.copytree(base,out,symlinks=False)
r=json.load(open(out/'die_plan.json'));rep={'base':str(base),'base_sha':hashlib.sha256((base/'die_plan.json').read_bytes()).hexdigest(),'rtl_cycles_added':0,'changes':[]}
old='cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__440.64x207.36__d31s.json';new='cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__414.72x207.36__d34e.json'
pins=json.load(open(out/old));source=copy.deepcopy(pins)
# The native clock inputs all remain separate ports; reset/control aliases are never folded.
clks=[p for p in pins if p['name'].startswith('clk')];rst=[p for p in pins if p['name'].startswith('rst')]
north=[p for p in pins if p['y']>207 and p not in clks and p not in rst]
south=[p for p in pins if p['y']<.2 and p not in rst]
for p in pins:
 if p['x']>440: p['x']=round(p['x']-25.92,6)
# Repack the N bus sequence on the existing M5 tracks; fixed .048 pitch grid, >1um separation.
for i,p in enumerate(north):p['x']=round(2.328+1.44*i,6)
for i,p in enumerate(south):p['x']=round(2.328+1.056*i,6)
clock_xy=[(0,0)]+[(x,y) for y in [-1,0,1,2] for x in [-2,-1,0,1,2] if (x,y)!=(0,0)]
for i,p in enumerate(clks):
 dx,dy=clock_xy[i];p.update(x=round(207.384+1.44*dx,6),y=round(103.68+1.08*dy,6),w=.048,h=.48)
for i,p in enumerate(rst):p.update(x=round(207.384+1.44*(i+3),6),y=103.68,w=.048,h=.48)
assert len(north)==275
assert max(p['x'] for p in pins)<414.72
assert sorted(p['name'] for p in pins)==sorted(p['name'] for p in source)
assert len({(p['layer'],p['x'],p['y']) for p in pins})==len(pins)
json.dump(pins,open(out/new,'w'),indent=1)
for tn,t in r['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('pins_file')==old:
   rep['changes'].append({'type':tn,'inst':c['inst'],'old_outline':c['outline_um'],'new_outline':[414.72,207.36],'old_pins':old,'new_pins':new})
   c.update(outline_um=[414.72,207.36],pins_file=new);c['note']+=' | D34e approved2:1outline; clock/reset centre cluster, unchanged port set and SRAM sites'
# Superset-face collar: current actual root drives logical c_done, selected physical alias was W.
for tn,t in r['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!='ot_hbm_static_cfg_collar_idx256r':continue
  oldc=c['pins_file'];pinrows=json.load(open(out/oldc));found=[p for p in pinrows if p.get('name',p.get('bus')) in ('c_done','c_done__W')]
  print('collar found',found)
  # Native table is bus/bit; remove historical N input and rename selected W alias.
  fixed=[]
  for p in pinrows:
   n=p.get('name',p.get('bus'))
   if n=='c_done':continue
   if n=='c_done__W':
    p=copy.deepcopy(p);p['name' if 'name' in p else 'bus']='c_done'
   fixed.append(p)
  assert len(fixed)==len(pinrows)-1
  newc='cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d34e.json';json.dump(fixed,open(out/newc,'w'),indent=1)
  c['pins_file']=newc;c.pop('pin_select',None);c.pop('unused_pins',None);c.pop('unused_pins_policy',None)
  c['note']+=' | D34e sole native c_done input at selected W face; stale unused N alternate removed'
  rep['changes'].append({'type':tn,'inst':c['inst'],'old_pins':oldc,'new_pins':newc,'removed_stale_N_c_done':1,'selected_W_named_native':'c_done'})
# Clock sidecars and actual type/die taps must follow the new centred entry.
import sys as _sys
_sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-hbm-1030/tools/die_plan')
import schema as S
P=S.Plan(r)
ce=json.load(open(out/'clock_entries.json'))
for tn,t in r['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('pins_file')!=new:continue
  if tn in ce and c['inst'] in ce[tn]:
   en=ce[tn][c['inst']];en['xy_um']=[207.36,103.68];en['island_um']=[203.04,99.36,211.68,108.0]
  ox,oy=c['origin_um'];orient=c.get('orient','R0');xx=207.36;yy=103.68
  if orient in ('MY','R180'):xx=414.72-xx
  if orient in ('MX','R180'):yy=207.36-yy
  for tap in t.get('clock',{}).get('taps',[]):
   if tap.get('name','').split('.')[0]==c['inst'] or tap.get('name')==c['inst']:
    tap['xy']=[round(ox+xx,6),round(oy+yy,6)]
json.dump(ce,open(out/'clock_entries.json','w'),indent=1)
en=json.load(open(out/'entries.json'));en['ot_hbm_su_static_pgslice_lg__lane_exp0_id']['xy']=[207.36,103.68];json.dump(en,open(out/'entries.json','w'),indent=1)
# Recompute every die tap from its declared type tap and placed orientation, no estimate offsets.
P=S.Plan(r);dt=json.load(open(out/'clock_taps_die.json'));changed=0
for tap in dt:
 part=tap.get('part');name=tap.get('tap','')
 if part not in P.parts or 'lane_exp0' not in name:continue
 tt=P.ptype(part);ttap=next((x for x in tt.get('clock',{}).get('taps',[]) if x.get('name')==name),None)
 if ttap is not None:tap['xy_die_um']=list(P.to_die(part,ttap['xy']));changed+=1
json.dump(dt,open(out/'clock_taps_die.json','w'),indent=1);rep['clock_sidecar_die_taps_updated']=changed
r['note']='CODEX D34e unsigned core interface fixes | '+r.get('note','');json.dump(r,open(out/'die_plan.json','w'),indent=1)
rep['sha']=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest();json.dump(rep,open(out/'d34e_event.json','w'),indent=1);print(json.dumps(rep))
