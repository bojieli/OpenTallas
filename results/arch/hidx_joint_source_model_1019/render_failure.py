import json
from pathlib import Path
P=Path(__file__).resolve().parent
regions=json.load(open(P/'STATIC_FAILURE.json'))['regions']
from PIL import Image,ImageDraw,ImageFont
im=Image.new('RGB',(1450,750),'white');d=ImageDraw.Draw(im);f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
d.text((30,20),'HIDX DISTINCT JOINT SOURCE MODEL — TERMINAL NATIVE PACKING FAIL',font=f,fill='#a00000')
d.text((30,52),'Cohort allocation only; no complete new site plan, placement, CTS or route',font=f,fill='black')
for g,r in regions.items():
 x0=45+r['x0']*.50;x1=45+r['x1']*.50;y0=120+r['row0']*4.3;y1=120+(r['row0']+r['rows'])*4.3
 col='#ffd2d2' if r['atom_reservation_ratio']>1 else '#dce8f5'
 d.rectangle((x0,y0,x1,y1),fill=col,outline='black');d.text((x0+4,y0+4),g,font=f,fill='black');d.text((x0+4,y0+29),format(r['ordinary_fill']*100,'.1f')+'% cells',font=f,fill='black');d.text((x0+4,y0+54),format(r['atom_reservation_ratio']*100,'.1f')+'% atoms',font=f,fill='#900000' if r['atom_reservation_ratio']>1 else 'black')
d.text((30,610),'First finite pack failure: pair[0], next genuine 39-site FF atom has no remaining interval.',font=f,fill='#a00000')
d.text((30,645),'All total atom areas fit; finite packing still fails. All 31,384 native contacts remain HOLD.',font=f,fill='black')
d.text((30,680),'Original actual checkpoint 70042afe and every predecessor failure are preserved unchanged.',font=f,fill='black')
im.save(P/'SOURCE_FAILURE.png')
