"""Render actual checkpoint coordinates; allocation is an outline only."""
import json,collections,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).resolve().parents[1];o=p/'output';j=json.loads((o/'native/positions.json').read_text());u=j['units']
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
W=1260;H=1390;pad=85;scale=1090/140.4
def xy(x,y):return (pad+x*scale,1250-y*scale)
def rect(draw,b,fill,outline=None):
 x0,y0=xy(b[0],b[3]);x1,y1=xy(b[2],b[1]);draw.rectangle([x0,y0,x1,y1],fill=fill,outline=outline)
for density in [False,True]:
 im=Image.new('RGB',(W,H),'white');dr=ImageDraw.Draw(im)
 dr.text((pad,20),'HIDX registered coupon — actual native placement checkpoint',font=font,fill='black')
 dr.text((pad,49),'11145 cells | 2904 FF | 140.4 x 140.4 um | all504 rows retained | NO CTS / ROUTE',font=small,fill='black')
 rect(dr,[0,0,140.4,140.4],None,'black');rect(dr,[2.16,2.16,138.24,138.24],'#f7f7f7','#555555')
 for r in j['rows']:
  x0,y0,x1,y1=[z/u for z in r];a=xy(x0,y0);b=xy(x1,y0);dr.line([a,b],fill='#eeeeee')
 if density:
  step=2.7;bins=collections.defaultdict(float)
  for z in j['insts'].values():
   x0,y0,x1,y1=[v/u for v in z['bbox']]
   for ix in range(int(x0/step),int(x1/step)+1):
    for iy in range(int(y0/step),int(y1/step)+1):
     bins[ix,iy]+=max(0,min(x1,(ix+1)*step)-max(x0,ix*step))*max(0,min(y1,(iy+1)*step)-max(y0,iy*step))
  for (ix,iy),area in bins.items():
   v=min(1,area/step**2);rect(dr,[ix*step,iy*step,(ix+1)*step,(iy+1)*step],(int(255*(1-v)),int(255*(1-v*.6)),255))
 else:
  for z in j['insts'].values():
   m=z['master'];c='#2b6cb0' if m.startswith('DFF') else ('#d97706' if m=='BUFx8_ASAP7_75t_R' else '#3a915f')
   rect(dr,[v/u for v in z['bbox']],c)
 rect(dr,[2.16,56.16,138.24,84.24],None,'#bc1b34')
 for n,bs in j['bterms'].items():
  if n in ['VDD','VSS']:continue
  for bp in bs:
   for layer,*b in bp['boxes']:rect(dr,[v/u for v in b],'#111111')
 x,y=xy(0,70.2);dr.ellipse([x-5,y-5,x+5,y+5],fill='#d7191c');dr.text((x+8,y-22),'CLK W(0,70.2)',font=small,fill='#b91c1c')
 dr.text((pad,1275),'Red outline:104-row allocation Y56.16..84.24um; every actual cell is inside.',font=font,fill='black')
 dr.text((pad,1305),'Blue FF / green logic / orange output BUF8. Density:2.7um bins, blue intensity = occupied fraction.',font=small,fill='black')
 dr.text((pad,1335),'Whole-core fill8.91676%; local band43.212%. Clock tree / wires / parent boundary OPEN.',font=font,fill='black')
 im.save(o/('checkpoint_density.png' if density else 'checkpoint_floorplan.png'))
