#!/usr/bin/env python3
"""Open actual PC/SVG hotspot using existing interior whitespace, unchanged RTL."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/planhM'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
actual=json.load(open(sys.argv[2]))['placement'];move={}
for i in [5,6]:
 for prefix in ['svg_SW','xc_SW','cp_svg_SW']:
  n=prefix+str(i);move[n]=dict(actual[n],y=round(actual[n]['y']+194.4,6))
move['wbk_SE']=dict(actual['wbk_SE'],y=round(actual['wbk_SE']['y']+432.,6))
for n in ['fs_SE','sfault_SE']:move[n]=dict(actual[n],x=14947.2)
new=dict(actual,**move);checks=[]
for name,r in move.items():
 bad=[]
 for n,b in new.items():
  if n==name:continue
  dx=min(r['x']+r['w'],b['x']+b['w'])-max(r['x'],b['x']);dy=min(r['y']+r['h'],b['y']+b['h'])-max(r['y'],b['y'])
  if dx>.001 and dy>.001:bad.append(n)
 assert not bad,(name,bad)
 checks.append(dict(name=name,before=actual[name],target=r,overlaps=bad))
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'))
# SVG follows its PC-band box directly; XC is placed inside that same region.
# Preserve box shape. Actual GEN, not a synthetic fixed XC home, decides placement.
for i in [5,6]:
 n='pc_SW'+str(i);p[n]['y']=round(p[n]['y']+194.4,6)
for name,r in move.items():
 sl=next((a for a in g['slots'] if a['name']==name),None)
 if sl:
  sl['origin'].update(x=r['x'],y=r['y']);sl['notes']=sl.get('notes','')+'; R16I interior PC/SVG escape'
 if name in p:p[name].update(x=r['x'],y=r['y'])
model=dict(status='GEOMETRY_MODEL_ONLY',base='09649a7bd/planhM',outline_um=g['floorplan']['die_um'],
 reason='Actual E1.880 worst window15400/1100 PHY+SVG6+XC6+PCctl; secondary1.059 SVG5window',
 placement_checks=checks,pc_region_dy_um=194.4,writeback_dy_um=432.,
 dynamic='XC remains normal first-fit inside moved PC region; actualGEN must confirm final boxes',
 rtl_source='unchanged',cycle_credit=0,remaining='Actual GEN/PINS/S4 required; no failedcapacity route')
g['floorplan']['r16i_pc_svg_escape']=model
(out/'grants_d4g.json').write_text(json.dumps(g,indent=1)+'\n');(out/'compact.P.json').write_text(json.dumps(p,indent=1)+'\n')
(out/'pc_svg_escape_model.json').write_text(json.dumps(model,indent=1)+'\n')
print('PC_SVG_ESCAPE_MODEL overlaps0 targets',len(checks),'die',model['outline_um'])
