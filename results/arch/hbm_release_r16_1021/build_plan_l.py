#!/usr/bin/env python3
"""Actual failed-capacity repair: northern service band and SW delivery geometry."""
import copy,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/plankM';out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
m=json.load(open(sys.argv[2]));actual=m['placement']
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'));sm=dict(x.split('=') for x in (out/'slot_map.txt').read_text().strip().split(','));slots={s['name']:s for s in g['slots']};moves={}
for i in range(8):
 p['pc_NW'+str(i)]['y']=round(p['pc_NW'+str(i)]['y']-194.4,6)
 for n in ['grid_svg_NW'+str(i),'cp_svg_NW'+str(i)]:slots[n]['origin']['y']=round(slots[n]['origin']['y']-194.4,6)
for n in ['wbk_NW','wbk_NE']:
 slots[n]['origin']['y']=round(slots[n]['origin']['y']-432.,6);moves[n]=dict(actual[n],y=slots[n]['origin']['y'])
for n in ['fs_NW','sfault_NE']:slots[n]['origin']['y']=round(slots[n]['origin']['y']-194.4,6)
# FS_NE cannot follow Y into the SM frame; give the existing tiny leaf real side whitespace.
slots['fs_NE']['origin']['x']=14968.8
xs=[11793.6,12101.4,12403.8,12711.6];ys=[11415.6,11566.8]
for i,col,row in [(2,0,0),(0,1,0),(1,2,0),(3,3,0),(4,0,1),(6,1,1),(7,2,1),(5,3,1)]:
 n='vmdel_SW'+str(i);a=actual[n];sn='pack_'+n
 sl=dict(name=sn,cell=a['m'],kind='tile',parent='die',outline=dict(w=a['w'],h=a['h']),origin=dict(x=xs[col],y=ys[row],orient=a['o']),pins=[],pin_status='FACES_ONLY',notes='Source-identical actual delivery leaf, dedicated physicalhome; no edge or width change. Actual S4 prices every new path.')
 g['slots'].append(sl);sm[n]=sn;moves[n]=dict(a,x=xs[col],y=ys[row])
new=dict(actual,**moves);checks=[]
for n,r in moves.items():
 bad=[]
 for k,b in new.items():
  if k==n:continue
  dx=min(r['x']+r['w'],b['x']+b['w'])-max(r['x'],b['x']);dy=min(r['y']+r['h'],b['y']+b['h'])-max(r['y'],b['y'])
  if dx>.001 and dy>.001:bad.append(k)
 assert not bad,(n,bad)
 checks.append(dict(name=n,before=actual[n],after=r,overlaps=bad))
model=dict(status='ACTUAL_FAILURE_GEOMETRY_REPAIR_MODEL',base_source='5e0e107d5/Kcolh',why='I/J max2.122/2.460 northSVG/WBK window9900/30800 plus VMflag1080/1120 hops across split rows',
 die_um=g['floorplan']['die_um'],northern_PC_and_CP_dy_um=-194.4,northern_WBK_dy_um=-432.,
 actual10box_checks=checks,SW_VMDEL='Eight actual leaves dedicated2x4 aboveVMS;3 lowerrow leaves moved. Same actual shapes/source/ports/clocks',
 north='SVG/XC/VMKS normal regionplacement plus8matching reservedSVGframes; smallleaves keepout handled explicitly. Actual GEN channelaware legality mandatory',
 WBK='OLD CURRENT SOURCE475.2 only; mandatory c9a189d12 newbody native/area/functional pending. Never reuse this box as qualified newbody.',
 WBK_newbody_selected=False,rtl_changes=0,extra_cycle_credit=0,remaining='FreshactualsourceGEN/P/Q/S4; no failedgeometryroute. RequirednewWBK source/realmeasuredframe must be adopted later explicitly')
g['floorplan']['r16l_north_vmpack']=model
(out/'grants_d4g.json').write_text(json.dumps(g,indent=1)+'\n');(out/'compact.P.json').write_text(json.dumps(p,indent=1)+'\n');(out/'slot_map.txt').write_text(','.join(k+'='+v for k,v in sorted(sm.items()))+'\n');(out/'north_vmpack_model.json').write_text(json.dumps(model,indent=1)+'\n')
print('NORTH_VM_MODEL actual10boxchecks0overlap; actualGENrequired; WBKoldbodyonly')
