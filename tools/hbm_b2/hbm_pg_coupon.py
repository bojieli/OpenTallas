#!/usr/bin/env python3
"""HBM core-only PG feasibility coupon, using the source-pinned HEAD finite-pad tool.
No actual die plan is changed. PHYs are outside these windows and remain separate work.
"""
import argparse,sys,json,hashlib,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(a.tools)/'die_plan'))
import infra_pg as G, schema as S
from PIL import Image,ImageDraw
raw=json.loads(Path(a.plan).read_text());raw['die']['pg'].pop('domains',None)
P=S.Plan(raw,Path(a.plan));src=Path(a.plan).parent
model=G.load_model(P,src,core_watts=642.7)
density=model['core_w_mm2']
g=[dict(layer='M8',width_um=.48,pitch_um=4.32,offset_um=2.16,nets=['VDD','VSS']),dict(layer='M9',width_um=12.96,pitch_um=34.56,offset_um=17.28,nets=['VDD','VSS'])]
pg=dict(grid=g,core_w_mm2=density,bump_pitch_um=150,vdd=.7,budget_mv=35)
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
for name,rect in [('hub',[8000,6500,11000,9500]),('sm',[1300,12500,4300,15500])]:
 k=out/name;m=G.window_kit(P,src,pg,k,name,rect,tile=43.2,core_w_mm2=density,pad_um=70,nets=('VDD','VSS'))
 m.update(plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),tool_source='claude/infra-head5-1027@e5f4fb2cd1',power_basis='conservative historical642.7W envelope charged to non-PHY area; separately modelled PHY absent from this core-only coupon',not_release=True)
 (k/'irwin.json').write_text(json.dumps(m,indent=1)+'\n')
 # Detail of the repeated structure, 600um x600um; pads above M9 touch only same-net stripes.
 im=Image.new('RGB',(1000,800),'white');d=ImageDraw.Draw(im);W=600.;H=420.;ox,oy=70,70;sc=1.5
 for gg in g:
  pitch=gg['pitch_um'];w=gg['width_um'];vertical=gg['layer']=='M9';hi=W if vertical else H
  c=gg['offset_um'];j=0
  while c<hi:
   for z,net in enumerate(gg['nets']):
    cc=c+z*pitch/2
    color='#e99999' if net=='VDD' else '#99a9e9'
    if vertical:d.rectangle([ox+(cc-w/2)*sc,oy,ox+(cc+w/2)*sc,oy+H*sc],fill=color)
    else:d.line([ox,oy+cc*sc,ox+W*sc,oy+cc*sc],fill=color,width=1)
   c+=pitch
 for i in range(1,4):
  for j in range(1,3):
   x,y=i*150,j*150;color='red' if (i+j)%2==0 else 'blue'
   d.rectangle([ox+(x-35)*sc,oy+(y-35)*sc,ox+(x+35)*sc,oy+(y+35)*sc],outline=color,width=3)
 d.text((30,20),f'{name}: conservative {density:.4f} W/mm2 core coupon; 150um bumps / 70um pads',fill='black')
 d.text((30,735),'M8 .48@4.32; M9 12.96@34.56. Red VDD / blue VSS. Pads above M9.',fill='black')
 d.text((30,760),'This coupon does not claim PHY PG, lower-stack IR, actual power, or die freeze.',fill='black')
 im.save(k/'geometry.png')
 print(name,json.dumps({q:m[q] for q in ['window_um','power_w','bumps','est_worst_mv']}),flush=True)
