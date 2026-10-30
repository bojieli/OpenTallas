#!/usr/bin/env python3
"""Prepare one unadopted KEYBUF face/locality candidate from an existing die event."""
import argparse, collections, copy, hashlib, json, math, re, shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('base',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--output-face',choices=['E','S'],default='E');ap.add_argument('--row-spread-um',type=float,default=0.0);ap.add_argument('--macro-lef',type=Path);a=ap.parse_args()
assert a.base.is_dir() and not a.out.exists()
# Every file is copied, never hard-linked: earlier event report aliases corrupted base metadata.
shutil.copytree(a.base,a.out,copy_function=shutil.copy2,symlinks=False)
read=lambda p:json.loads(p.read_text());write=lambda p,d:p.write_text(json.dumps(d,indent=1)+'\n')
plan=read(a.out/'die_plan.json');old_plan=copy.deepcopy(plan)
cores=[(tn,c) for tn,t in plan['partition_types'].items() for c in t.get('hard_cores',[]) if c['module']=='ot_hnx_idxn_keybuf_slice']
assert len(cores)==16
changed=[]
for src in sorted({c['pins_file'] for _,c in cores}):
 pins=read(a.out/src);before=copy.deepcopy(pins);W,H=cores[0][1]['outline_um'];names={p['name'] for p in pins};assert len(names)==len(pins)
 out=sorted((p for p in pins if p['name'].startswith('key_out[')),key=lambda p:int(re.search(r'\[(\d+)\]',p['name'])[1]));assert len(out)==1099
 clockreset=[copy.deepcopy(p) for p in pins if p['name'] in ('clk','rst_n')]
 west=[p for p in pins if p not in out and p['name'] not in ('clk','rst_n')]
 def slots(n,reserved=()):
  pitch=.240;first=.024+.048*math.ceil(((H-(n-1)*pitch)/2-.024)/.048)
  result=[];k=0
  while len(result)<n:
   y=round(first+k*pitch,3);k+=1
   if any(abs(y-q)<.096-1e-7 for q in reserved):continue
   assert 4.32<y<H-4.32,(n,y)
   result.append(y)
  return result
 if a.output_face=='E':
  for p,y in zip(out,slots(len(out))):p.update(layer='M4',x=round(W-.096,3),y=y)
 else:
  # Metadata bits0..10 remain near static tags/control at W; data bits11..1098
  # reverse on S so the upper SRAM's read bits stay >=31.704um from W.
  for i,p in enumerate(out):
   x=17.304+.192*i if i<11 else 31.704+.192*(1098-i)
   p.update(layer='M5',x=round(x,3),y=.096)
  assert all(abs((p['x']-.024)/.048-round((p['x']-.024)/.048))<1e-6 for p in out)
 for p,y in zip(west,slots(len(west),[p['y'] for p in clockreset if p['layer']=='M4'])):p.update(layer='M4',x=.096,y=y)
 assert {p['name'] for p in pins}==names
 assert [p for p in pins if p['name'] in ('clk','rst_n')]==clockreset
 assert all(abs((p['y']-.024)/.048-round((p['y']-.024)/.048))<1e-6 for p in pins if p['layer']=='M4')
 physical=[(p['layer'],p['x'],p['y']) for p in pins];assert len(physical)==len(set(physical))
 density={}
 for face in (('W','E') if a.output_face=='E' else ('W','S')):
  ys=sorted(p['x'] if face=='S' else p['y'] for p in pins if (face=='S' and p['layer']=='M5' and p['y']<.2) or (face!='S' and p['layer']=='M4' and(p['x']<W/2)==(face=='W')));peak=0;j=0
  for i,y in enumerate(ys):
   while y-ys[j]>10:j+=1
   peak=max(peak,(i-j+1)/10)
  density[face]=peak
 assert max(density.values())<=6.0,density
 dst=str(Path(src).with_name(Path(src).stem+'__keybuf_'+a.output_face.lower()+'w1030.json'));write(a.out/dst,pins)
 for _,c in cores:
  if c['pins_file']==src:c['pins_file']=dst
 changed.append(dict(before=src,after=dst,pins=len(pins),key_in=1099,key_out=1099,peak_pins_per_um_10um=density,clock_reset_unchanged=True))
cm=read(a.out/'core_macros.json');entry=cm['cores']['ot_hnx_idxn_keybuf_slice'];oldmac=copy.deepcopy(entry['macros']);assert len(oldmac)==5
for i,m in enumerate(entry['macros']):
 m['orient']='MY'
 if a.macro_lef:
  mw,mh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',a.macro_lef.read_text()).groups())
  x,y=m['rect_um'][:2];y=round(y+i*a.row_spread_um,3)
  m['rect_um']=[x,y,round(x+mw,3),round(y+mh,3)]
 else:assert a.row_spread_um==0
if not a.macro_lef:assert [m['rect_um'] for m in entry['macros']]==[m['rect_um'] for m in oldmac]
entry['basis']+='; KEYBUF '+a.output_face+'-output/W-input locality candidate: MY heavy read edge faces E, identical sites/outline'
cm['plan']=str(a.out/'die_plan.json');write(a.out/'core_macros.json',cm);write(a.out/'die_plan.json',plan)
write(a.out/'keybuf_event_report.json',dict(status='PREP_UNADOPTED',base=str(a.base),base_sha256=hashlib.sha256((a.base/'die_plan.json').read_bytes()).hexdigest(),instances=[dict(type=n,inst=c['inst']) for n,c in cores],changed_pin_tables=changed,macro_orientations_changed=5,macro_rectangles_unchanged=not bool(a.macro_lef),macro_row_spread_um=a.row_spread_um,macro_lef_sha256=hashlib.sha256(a.macro_lef.read_bytes()).hexdigest() if a.macro_lef else None,source_cycles_added=0,output_face=a.output_face,outline_unchanged=True,clock_reset_pins_unchanged=True,station_sidecars='UNCHANGED; full G0C/parent internal station reconciliation required before adoption',warning='No P&R release; review and batched parent approval remain required'))
print(json.dumps(changed))
