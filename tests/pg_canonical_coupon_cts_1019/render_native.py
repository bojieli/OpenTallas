from pathlib import Path
import json,sys,hashlib
root=Path.cwd();sys.path.insert(0,str(root/'tools/ref_tile'));from layout_png import Canvas
p=root/'output/default/analysis';j=json.loads((p/'native_geometry.json').read_text());raw=json.loads((p/'raw.json').read_text());m=raw['modules']['ot_pg_canonical_xor16_1019'];dbu=j['dbu'];assert dbu==1000
clocknets={int(k) for k,v in m['net_metadata'].items() if v['signal_type']=='CLOCK'}
clockcells={n for n,c in m['cells'].items() if any(c['port_directions'][pin]=='output' and any(b in clocknets for b in bs) for pin,bs in c['connections'].items())}
c=Canvas(1600,1330)
c.text(50,25,'ACTUAL DEFAULT CTS - DIAGNOSTIC HOLD: 16 OUTPUT SLEW / 202 UNBOUND PG',scale=2)
c.text(50,53,'NATIVE ODB '+j['sha256'][:40],scale=2)
def panel(bounds,rect,zoom=False):
 x0,y0,x1,y1=bounds;left,top,right,bottom=rect
 def xy(x,y):return left+(x/dbu-x0)/(x1-x0)*(right-left),bottom-(y/dbu-y0)/(y1-y0)*(bottom-top)
 def draw(bb,color,outline=False):
  a,b=xy(bb[0],bb[1]);d,e=xy(bb[2],bb[3]);(c.box if outline else c.fill)(a,e,d,b,color)
 c.box(left,top,right,bottom,(0,0,0),2)
 for row in j['rows']:draw(row,(230,240,245))
 if not zoom:
  draw([2160,2160,41040,41040],(135,135,135),True)
  for s in j['pg_shapes']:
   if s['layer']=='M5':draw(s['box'],(245,216,216) if s['net']=='VDD' else (215,220,242))
 for x in j['cells']:
  if 'DFF' in x['master']:color=(50,115,220)
  elif x['name'] in clockcells:color=(240,145,25)
  elif 'TIE' in x['master']:color=(140,140,140)
  elif 'TAP' in x['master']:color=(20,20,20)
  else:color=(40,165,95)
  draw(x['bbox'],color)
  if zoom:draw(x['bbox'],(255,255,255),True)
 for k in range(6):
  x=x0+(x1-x0)*k/5;px,_=xy(x*dbu,y0*dbu);c.text(px-15,bottom+8,f'{x:.2f}',scale=1)
 if not zoom:
  for pin in j['pins']:
   if pin['role'] in ('POWER','GROUND'):continue
   bb=pin['box'];x,y=xy((bb[0]+bb[2])/2,(bb[1]+bb[3])/2);color=(220,0,0) if pin['name']=='clk' else (110,20,170) if pin['name']=='rst_n' else (50,50,50);c.fill(x-3,y-3,x+3,y+3,color)
   if pin['name']=='clk':c.text(x+10,y+8,'CLK X8.700 Y43.158',color,1)
  for k in range(6):
   y=y0+(y1-y0)*k/5;_,py=xy(x0*dbu,y*dbu);c.text(left-45,py-4,f'{y:.2f}',scale=1)
 else:
  for k,row in enumerate(j['rows']):
   _,y=xy(row[0],(row[1]+row[3])/2);c.text(left-80,y-4,f'{row[1]/dbu:.2f}',scale=1)
panel([0,0,43.2,43.2],[100,120,900,920])
c.text(100,955,'FULL OUTLINE: BOTH AXES IN UM, 1:1 ASPECT',scale=2)
text=['255 NATIVE CELLS / 51 FF','16 XOR / 52 TIES / 16 TAP','6 FULL ROWS: Y20.79..22.41','BAND X2.16..41.04','STD AREA 33.65064 UM2','BAND AREA 62.98560 UM2','BAND FILL 53.43%','WHOLE OUTLINE FILL 1.803%','CORE FILL 2.226%','BLUE FF / ORANGE CLOCK','GREEN COMB / GRAY TIE','BLACK TAP','CLOCK PIN (8.700,43.158)','RESET PIN (8.796,43.158)','ACTUAL PIN PLACEMENT:','NORTH PINS ARE NOT CENTERED','SOURCE PLAN DIFFERENCE OPEN','TT CLOCK SPREAD <=7.97 PS','FF CLOCK SPREAD <=4.54 PS','PLACEMENT RC ONLY / NO ROUTE']
for k,line in enumerate(text):c.text(960,140+30*k,line,scale=2 if len(line)<29 else 1)
c.text(100,1010,'EXACT SIX-ROW ZOOM: X IN UM, Y EXAGGERATED; EACH RECTANGLE IS A NATIVE CELL',scale=2)
panel([2.16,20.79,41.04,22.41],[100,1060,1500,1260],True)
c.text(100,1300,'NO DENSITY OR CLOCK-PIN WAIVER; ROOT MUST REVIEW ACTUAL GEOMETRY',scale=2)
o=p/'layout_native';o.mkdir(exist_ok=True);c.save(o/'full_and_band.png')
(o/'provenance.json').write_text(json.dumps({'odb_sha256':j['sha256'],'native_geometry_sha256':hashlib.sha256((p/'native_geometry.json').read_bytes()).hexdigest(),'dbu':dbu,'native_cell_count':len(j['cells']),'actual_rows':j['rows'],'clock_pin_um':[8.7,43.158],'fill_band_percent':33.65064/62.9856*100,'fill_whole_outline_percent':33.65064/(43.2**2)*100,'fill_core_percent':33.65064/(38.88**2)*100,'notes':'Full panel 1:1; row zoom exaggerates Y explicitly. Draws actual native coordinates and actual pins, not model locations.'},indent=2)+'\n')
