"""Read-only rendering of the completed SOURCE branch packet."""
import gzip,json,collections
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;O=P/'output'
rows=json.load(gzip.open(O/'branches.json.gz','rt'));s=json.load(open(O/'SUMMARY.json'));cells=json.load(gzip.open(P/'input/site_plan.json.gz','rt'))
im=Image.new('RGB',(1500,1710),'white');d=ImageDraw.Draw(im)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
def xy(x,y):return (80+x/1000*9.2,1430-y/1000*9.2)
d.text((70,20),'HIDX coupled branch SOURCE MODEL — no placement / CTS / router',font=font,fill='#a11924')
d.text((70,55),'11,145 unchanged native cells | actual fixed ports | 80 fF output loads | no added buffers / cycles',font=small,fill='black')
d.rectangle([xy(0,140400),xy(140400,0)],outline='black',width=2)
d.rectangle([xy(64800,84240),xy(75600,56160)],fill='#dddddd')
for c in cells.values():
 x0,y0,x1,y1=c['bbox_dbu'];d.rectangle([xy(x0,y1),xy(x1,y0)],fill='#d8e0e6')
colors={'M2':'#3e8caa','M3':'#56904d','M4':'#e88736','M5':'#9662a0'}
for r in rows:
 for edge in r['edges']:
  for l,axis,c,a,b in edge['segments_nm']:
   p,q=(xy(a,c),xy(b,c)) if axis=='H' else (xy(c,a),xy(c,b))
   d.line([p,q],fill=colors[l],width=1)
 for f in r['failures']:
  x,y=xy(*r['points_nm'][f['point_index']]);d.ellipse([x-3,y-3,x+3,y+3],fill='#bd1622')
d.text((70,1470),'Modeled branch graph contacts: '+str(s['counts']['connected_contacts'])+' / 31384; missing contacts shown red.',font=font,fill='black')
d.text((70,1505),'Complete / incomplete nets: '+str(s['counts'].get('nets_complete',0))+' / '+str(s['counts'].get('nets_incomplete',0)),font=font,fill='black')
d.text((70,1540),'TT / FF union-wire cap excess: '+str(s['counts']['cap_excess_TT'])+' / '+str(s['counts']['cap_excess_FF'])+'; unknown via fringe excluded.',font=font,fill='#a11924')
d.text((70,1575),'Native local M1 access, jog PG-clear, shared CUT union and enclosures remain HOLD.',font=font,fill='#a11924')
d.text((70,1610),'All waveform/setup/hold, real-clock phases and full PG proof remain HOLD. No physical PASS.',font=font,fill='#a11924')
d.text((70,1645),'M2 blue / M3 green / M4 orange / M5 purple. Gray center is unchanged candidate clock spine.',font=small,fill='black')
im.save(O/'COUPLED_SOURCE_MODEL.png')
