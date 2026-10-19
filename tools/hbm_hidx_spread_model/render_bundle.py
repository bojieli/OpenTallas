"""Engineering plot of proposed native sites, explicitly not an actual placement."""
import json,gzip,collections
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];j=json.loads((P/'out/MODEL.json').read_text());plan=json.load(gzip.open(P/'out/site_plan.json.gz','rt'));native=json.load(gzip.open(P/'input/native_pin_geometry.json.gz','rt'));u=native['units']
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
pad=85;scale=1090/140.4
def xy(x,y):return pad+x*scale,1250-y*scale
def rect(d,b,fill,outline=None):
 x0,y0=xy(b[0],b[3]);x1,y1=xy(b[2],b[1]);d.rectangle([x0,y0,x1,y1],fill=fill,outline=outline)
for density in [False,True]:
 im=Image.new('RGB',(1260,1450),'white');d=ImageDraw.Draw(im)
 d.text((pad,17),'HIDX structural SOURCE MODEL — NO placement / ODB / CTS / route',font=font,fill='#a11924')
 d.text((pad,46),'11145 exact native cells | 27 real connectivity cohorts | all504 rows retained | central104 rows',font=small,fill='black')
 rect(d,[0,0,140.4,140.4],None,'black');rect(d,[2.16,2.16,138.24,138.24],'#fafafa','#555555')
 for row in range(505):d.line([xy(2.16,2.16+row*.27),xy(138.24,2.16+row*.27)],fill='#eeeeee')
 rect(d,[64.8,56.16,75.6,84.24],'#cccccc')
 if density:
  step=2.7;bins=collections.defaultdict(float)
  for c in plan.values():
   x0,y0,x1,y1=[v/u for v in c['bbox_dbu']]
   for ix in range(int(x0/step),int(x1/step)+1):
    for iy in range(int(y0/step),int(y1/step)+1):bins[ix,iy]+=max(0,min(x1,(ix+1)*step)-max(x0,ix*step))*max(0,min(y1,(iy+1)*step)-max(y0,iy*step))
  for (ix,iy),a in bins.items():
   v=min(1,a/step**2);rect(d,[ix*step,iy*step,(ix+1)*step,(iy+1)*step],(int(255*(1-v)),int(255*(1-v*.6)),255))
 else:
  for c in plan.values():
   m=c['master'];color='#2b6cb0' if m.startswith('DFF') else ('#d97706' if m=='BUFx8_ASAP7_75t_R' else '#3a915f');rect(d,[z/u for z in c['bbox_dbu']],color)
 for g,r in j['regions'].items():
  b=[2.16+r['x0']*.054,56.16+r['row0']*.27,2.16+r['x1']*.054,56.16+(r['row0']+r['rows'])*.27]
  rect(d,b,None,'#333333');x,y=xy(b[0]+.3,b[3]-.3);d.text((x,y),g,font=small,fill='#111111',stroke_width=1,stroke_fill='white')
 rect(d,[2.16,56.16,138.24,84.24],None,'#a11924')
 for p in native['ports']:
  if p['role'] not in ['POWER','GROUND']:
   for layer,b in p['shapes']:rect(d,[z/u for z in b],'black')
 x,y=xy(0,70.2);d.ellipse([x-5,y-5,x+5,y+5],fill='#d7191c');d.text((x+8,y-22),'CLK W(0,70.2)',font=small,fill='#a11924')
 d.text((pad,1275),'Gray10.8um clock space:303.264um2;265 all-BUF24 budget115.911um2,38.22% fill.',font=font,fill='black')
 d.text((pad,1305),'Exact maximum windows: '+ '; '.join(str(z['window_um'])+' '+format(z['maximum_fill']*100,'.2f')+'%' for z in j['density_windows'][:3]),font=font,fill='black')
 d.text((pad,1335),'Single-row maximum '+format(j['density_windows'][3]['maximum_fill']*100,'.2f')+'%; whole-band43.212%; clocks/hold/wires remain modeled.',font=small,fill='black')
 d.text((pad,1365),'Blue FF / green logic / orange output BUF8. All80fF external loads unchanged. Real clock/PG/access OPEN.',font=small,fill='black')
 d.text((pad,1395),'Native wire/cap/table checks and true parent boundary require actual implementation; source geometry only.',font=small,fill='#a11924')
 im.save(P/'out'/('SOURCE_DENSITY.png' if density else 'SOURCE_MODEL.png'))
