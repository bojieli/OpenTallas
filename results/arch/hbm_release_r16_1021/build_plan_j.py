#!/usr/bin/env python3
"""Reserve real relay grids in shared-region SYNTH blocks; retain usable area."""
import copy,importlib.util,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/planiM';out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
actual=json.load(open(sys.argv[2]))['placement'];actual=copy.deepcopy(actual)
for f,t in [('plangM/pg_centering_model.json','after'),('planhM/xload_corridor_model.json','after'),('planiM/pc_svg_escape_model.json','target')]:
 for c in json.load(open(ROOT/'results/arch/hbm_release_r16_1021'/f))['placement_checks']:actual[c['name']]=c[t]
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'));slotmap={};records=[]
for name,a in sorted(actual.items()):
 if not(name.startswith('svg_') or name=='hb_vms_SW'):continue
 w,h=round(a['w']+43.2,6),round(a['h']+43.2,6)
 if name.startswith('svg_'):
  box=p['pc_'+name[4:]];north=box['y']>g['floorplan']['die_um'][1]/2
  x=round(round((box['x']+(box['w']-w)/2)/.216)*.216,3)
  y=round(box['y']+4.32,3) if north else round(box['y']+box['h']-h-4.32,3)
 else:x,y=round(a['x']-21.6,3),round(a['y']-21.6,3)
 # One column + one row. Solid area exactly equals the prior uncarved frame.
 assert abs((w-43.2)*(h-43.2)-a['w']*a['h'])<.001
 cx=round((w-43.2)/2,3);cy=round((h-43.2)/2,3)
 channels=[dict(kind='feedthrough_relay_column',x_um=[cx,round(cx+43.2,3)],y_um=[0,h],owner='die',master_keepout='hard placement + M5/M6 route'),dict(kind='feedthrough_relay_row',x_um=[0,w],y_um=[cy,round(cy+43.2,3)],owner='die',master_keepout='hard placement + M5/M6 route')]
 sn='grid_'+name;slotmap[name]=sn
 g['slots'].append(dict(name=sn,cell=a['m'],kind='tile',parent='die',outline=dict(w=w,h=h),origin=dict(x=x,y=y,orient=a['o']),pins=[],pin_status='FACES_ONLY',reserved_channels=channels,notes='R16J dedicated physical SYNTH slot; exact existing source; grew43.2 each axis to preserve usablearea with real relay cross. Future hardened master MUST reserve identical keepout; no CLOSED view claim.'))
 records.append(dict(instance=name,slot=sn,master=a['m'],before=[a['x'],a['y'],a['w'],a['h']],after=[x,y,w,h],old_usable_um2=a['w']*a['h'],new_usable_um2=(w-43.2)*(h-43.2),segments_um=[(w-43.2)/2,(h-43.2)/2],reserved_channels=channels))
model=dict(status='GEOMETRY_MODEL_ONLY',reason='Actual E VMS_SW uncarved428square blocks 1080um flaghop; SVG uncarved430square spans worst1.880 PCwindow',base='88ba1e4de/planiM',die_um=g['floorplan']['die_um'],slots=records,rtl_source='unchanged',usable_area_change_um2=0,hard_view_alias=False,dynamic_relocation='Normal GEN first-fit rehomes XC/VMKS/smallfaults around grownSVG. Actual GEN placementcheck mandatory; not a static placementPASS.',physical_obligation='Real hardened component must implement identical cross keepout and source/clock/latency; no synthetic CLOSED claim',remaining='ActualGEN/P/Q/S4; no failedgeometry route')
g['floorplan']['r16j_shared_grid']=model
(out/'grants_d4g.json').write_text(json.dumps(g,indent=1)+'\n');(out/'slot_map.txt').write_text(','.join(n+'='+v for n,v in sorted(slotmap.items()))+'\n');(out/'shared_grid_model.json').write_text(json.dumps(model,indent=1)+'\n')
print('SHARED_GRID_MODEL',len(records),'dedicated slots; usable area unchanged; actualGEN required')
