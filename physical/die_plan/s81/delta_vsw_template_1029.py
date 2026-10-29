#!/usr/bin/env python3
"""Explicit fresh VSW edge-pin template; old routed table/view remain historical.
The old native M3/M5 access rectangles are 0.02..1.76 um inside the body,
which cannot be used as the canonical pins of a new core kit. Keep each pin's
N/S face and x order, choose its nearest legal M5 track, and publish the exact
edge rectangle (no generator projection, no logic/cycle/outline changes).
"""
import json,hashlib,re,argparse
from pathlib import Path
S=Path(__file__).resolve().parent; ROOT=S.parents[2]
OLD='inputs/core_pins/ot_s81sl_vsw.json'; NEW='inputs/core_pins/ot_s81sl_vsw_tpl.json'
LEF='physical/die_plan/s81/cores/leaf/lef/ot_s81sl_vsw_tpl.lef'
def apply(plan_paths):
 old=json.loads((S/OLD).read_text());new=json.loads((S/OLD).read_text());W=H=224.64
 source=(ROOT/old['lef']).read_text();dirs={m.group(1):m.group(2) for m in re.finditer(r'  PIN (\S+)\n\s+DIRECTION (\w+) ;',source)}
 seen=set();moved=[];lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','MACRO ot_s81sl_vsw','  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {W:.3f} BY {H:.3f} ;']
 for a,b in zip(old['pins'],new['pins']):
  if a['name']=='clk':x,y=a['x'],a['y'];pw,ph=.048,.48
  else:
   x=round(.012+.048*round((a['x']-.012)/.048),6);y=H-.042 if a['y']>H/2 else .042;pw,ph=.024,.084
  b.update(layer='M5',x=x,y=round(y,6));site=(x,y);assert site not in seen,(a['name'],site);seen.add(site)
  assert 0<=x-pw/2<x+pw/2<=W and -1e-8<=y-ph/2<y+ph/2<=H+1e-8
  moved.append(dict(name=a['name'],old=[a['layer'],a['x'],a['y']],new=['M5',x,y],move_um=round(abs(x-a['x'])+abs(y-a['y']),6)))
  lines.extend([f'  PIN {a["name"]}',f'    DIRECTION {dirs[a["name"]]} ;','    USE SIGNAL ;','    PORT','      LAYER M5 ;',f'        RECT {x-pw/2:.6f} {y-ph/2:.6f} {x+pw/2:.6f} {y+ph/2:.6f} ;','    END',f'  END {a["name"]}'])
 # Keep the real existing connectable PG ports exactly; no invented supply abstract.
 for name in ['VDD','VSS']:
  m=re.search(r'  PIN '+name+r'\n.*?  END '+name+r'\n',source,re.S);assert m,name
  lines.extend(m.group(0).rstrip().splitlines())
 lines.append('  OBS')
 for i in range(1,6):lines.extend([f'    LAYER M{i} ;',f'      RECT 0 0 {W:.3f} {H:.3f} ;'])
 lines.extend(['  END','END ot_s81sl_vsw','END LIBRARY'])
 (ROOT/LEF).write_text('\n'.join(lines)+'\n');new['lef']=LEF;new['pinhash']=hashlib.sha256(json.dumps(new['pins'],sort_keys=True).encode()).hexdigest()[:12];new['source']='S81 fresh VSW template 2026-10-29: explicit N/S M5 edge contract; nearest existing x track, preserved faces/order/clock/outline; old routed view and old input table retained. No logic/cycle change.'
 (S/NEW).write_text(json.dumps(new,indent=1)+'\n')
 counts={}
 for f in plan_paths:
  text=Path(f).read_text();p=json.loads(text);n=0
  for t in p['partition_types'].values():
   for h in t.get('hard_cores',[]):
    if h['module']=='ot_s81sl_vsw':h['pins_file']=NEW;h['lef']=LEF;n+=1
  # Only these exact strings change, retaining all surrounding source bytes.
  text=text.replace(OLD,NEW).replace(old['lef'],LEF)
  assert json.loads(text)==p
  Path(f).write_text(text);counts[str(f)]=n
 return dict(pins=len(moved),max_move_um=max(z['move_um'] for z in moved),clock_next=next(z for z in moved if z['name']=='clk'),plan_rows=counts,pins_changed=moved)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--plan',action='append',required=True);a.add_argument('--receipt',required=True);x=a.parse_args();r=apply(x.plan);Path(x.receipt).write_text(json.dumps(r,indent=1)+'\n');print({k:v for k,v in r.items() if k!='pins_changed'})
