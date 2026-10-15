#!/usr/bin/env python3
"""Actual VM bank face exposure under structural eight-bank arrangements.

A blocked straight escape means a real neighboring macro requires a turn; it
is not a routing failure verdict. No arbitrary remote client point is scored.
"""
import argparse,hashlib,json
from pathlib import Path

INPUT='/home/ubuntu/wt/hbm-vm-static-1014/results/arch/hbm_vm_bank_static_1015/native_pin_pg_diagnostic/native_bank_actual_pin_pg.json'

def analyse():
 p=Path(INPUT);m=json.loads(p.read_text());W,H=m['die'][2:];gap=43.2;halo=5.4
 pins={}
 for name,_,use,_,shapes in m['bterms']:
  if use in ('POWER','GROUND') or not shapes:continue
  layer,r=shapes[0];x=(r[0]+r[2])/2;y=(r[1]+r[3])/2
  face=min([(x,'W'),(W-x,'E'),(y,'S'),(H-y,'N')])[1]
  pins[name]=(x,y,face,layer)
 critical=lambda n:n.split('[')[0] in ('rq3','rr3','wq1','wq_done1')
 assert sum(critical(n) for n in pins)==556
 cases=[]
 for name,cols,outward in [('column8_R0',1,False),('two_columns_R0',2,False),('two_columns_outward_R0_MY',2,True),('four_columns_R0',4,False)]:
  rows=8//cols;boxes=[]
  for b in range(8):
   col,row=divmod(b,rows);boxes.append(dict(bank=b,x=col*(W+gap),y=row*(H+gap),w=W,h=H,orient='MY' if outward and col==1 else 'R0'))
  counts={f:dict(total=0,requires_turn=0) for f in 'NSEW'};att={'pins':0,'requires_turn':0,'minimum_neighbour_detour_sum_um':0.,'max_minimum_neighbour_detour_um':0.};blocked_clock=[]
  for b in boxes:
   for n,(px,py,face,layer) in pins.items():
    if b['orient']=='MY':px=W-px;face={'W':'E','E':'W'}.get(face,face)
    x=b['x']+px;y=b['y']+py;obstacles=[]
    for o in boxes:
     if o is b:continue
     hit=(face=='W' and o['x']+W<x and o['y']<y<o['y']+H) or (face=='E' and o['x']>x and o['y']<y<o['y']+H) or (face=='N' and o['y']>y and o['x']<x<o['x']+W) or (face=='S' and o['y']+H<y and o['x']<x<o['x']+W)
     if hit:obstacles.append(o)
    counts[face]['total']+=1;counts[face]['requires_turn']+=bool(obstacles)
    if critical(n):
     att['pins']+=1;att['requires_turn']+=bool(obstacles)
     # Across aligned columns, all neighboring bank rectangles share the same
     # top/bottom; passing either requires this exact extra vertical distance.
     detour=2*min(py+halo,H-py+halo) if obstacles and face in ('W','E') else 0.
     att['minimum_neighbour_detour_sum_um']+=detour;att['max_minimum_neighbour_detour_um']=max(att['max_minimum_neighbour_detour_um'],detour)
    if n=='clk' and obstacles:blocked_clock.append(b['bank'])
  cases.append(dict(name=name,banks=boxes,outline_um=[cols*W+(cols-1)*gap,rows*H+(rows-1)*gap],all_actual_signal_face_exposure=counts,canonical_NE_ATT_RG3_WG1_face=att,clock_entries_requiring_turn=blocked_clock,qualified=False))
 return dict(schema='opentallas.hbm.vm_system.actual_face_exposure.v1',input=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()),bank_outline_um=[W,H],signal_pins_per_bank=len(pins),cases=cases,limits=['Actual native bank BTerm rectangles; source and CTS remain unqualified.','43.2um streets are a comparative reservation, not a bus cut proof.','R0/MY are H-DIE-admitted candidate orientations; transform all face groups and clock together.','No outside ATT/SU/IDX/COLL/HBM consumer pins are invented. Face obstruction is not a route failure; a turn/escape corridor may resolve it.','All signal faces and physical clock entries reported so ATT improvement cannot hide other client effects.','Final objective requires production transfer activity and real outside endpoints; these cases are not globally ranked.'])

def draw(r,path):
 raw=json.loads(Path(INPUT).read_text());W,H=r['bank_outline_um'];scale=.135;pw=480;ph=520;svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1140">','<rect width="100%" height="100%" fill="white"/>','<style>text {font-family:Arial,sans-serif}</style>','<text x="16" y="25" font-size="19" font-weight="bold">HBM system placement: actual NE VM bank faces toward attention</text>','<text x="16" y="47" font-size="12">Eight real bank outlines per panel, same scale. Representative actual pin centres; metrics use every pin. All clients and clocks move with a flip.</text>']
 for i,c in enumerate(r['cases']):
  px=16+(i%2)*pw;py=70+(i//2)*ph;x0=px+15;y0=py+70;FH=c['outline_um'][1];att=c['canonical_NE_ATT_RG3_WG1_face'];svg += [f'<rect x="{px}" y="{py}" width="470" height="510" fill="#fafafa" stroke="#aaa"/>',f'<text x="{px+10}" y="{py+20}" font-size="14" font-weight="bold">{c["name"]}</text>',f'<text x="{px+10}" y="{py+40}" font-size="12">{c["outline_um"][0]:.1f} × {FH:.1f} µm; ATT pins needing a turn: {att["requires_turn"]}/4448</text>']
  for b in c['banks']:
   x=x0+b['x']*scale;y=y0+(FH-b['y']-H)*scale;svg.append(f'<rect x="{x}" y="{y}" width="{W*scale}" height="{H*scale}" fill="#eee5cf" stroke="#444" stroke-width=".7"/>');svg.append(f'<text x="{x+3}" y="{y+17}" font-size="10">b{b["bank"]} {b["orient"]}</text>')
   for pin_index,(n,_,use,_,shapes) in enumerate(raw['bterms']):
    if use in ('POWER','GROUND') or not shapes:continue
    is_att=n.split('[')[0] in ('rq3','rr3','wq1','wq_done1')
    if n!='clk':
     if is_att and '[' in n and int(n.split('[')[1].split(']')[0])%4:continue
     if not is_att and pin_index%64:continue
    _,a=shapes[0];xx=(a[0]+a[2])/2;yy=(a[1]+a[3])/2
    if b['orient']=='MY':xx=W-xx
    color='#168b39' if n.startswith(('rq3[','rr3[')) else '#cc2879' if n.startswith('wq1[') or n=='wq_done1' else '#707070';rad=1.1 if color!='#707070' else .45
    if n=='clk':color='#1957c2';rad=2.4
    svg.append(f'<circle cx="{x0+(b["x"]+xx)*scale}" cy="{y0+(FH-b["y"]-yy)*scale}" r="{rad}" fill="{color}"><title>b{b["bank"]} {n}, {b["orient"]}; actual BTerm centre transformed</title></circle>')
  txtx=x0+max(140,c['outline_um'][0]*scale+20);txty=y0+100
  if c['outline_um'][0]*scale>180:txtx=x0;txty=y0+FH*scale+35
  svg += [f'<text x="{txtx}" y="{txty}" font-size="12">Clock entries requiring a turn: {len(c["clock_entries_requiring_turn"])}/8</text>',f'<text x="{txtx}" y="{txty+20}" font-size="12">ATT RG3 query and WG1 output share</text>',f'<text x="{txtx}" y="{txty+37}" font-size="12">the original W face; MY exposes it east.</text>',f'<text x="{txtx}" y="{txty+64}" font-size="12">Other RG / write / service groups also</text>',f'<text x="{txtx}" y="{txty+81}" font-size="12">need reserved escape and real routing.</text>']
 svg += ['<circle cx="20" cy="1120" r="3" fill="#168b39"/><text x="29" y="1124" font-size="12">ATT RG3 query</text>','<circle cx="155" cy="1120" r="3" fill="#cc2879"/><text x="164" y="1124" font-size="12">ATT WG1 output</text>','<circle cx="310" cy="1120" r="3" fill="#1957c2"/><text x="319" y="1124" font-size="12">Actual clock</text>','<circle cx="450" cy="1120" r="3" fill="#707070"/><text x="459" y="1124" font-size="12">Other actual pins</text>','<path d="M650,1120 h135" stroke="black" stroke-width="3"/><text x="795" y="1124" font-size="12">1000 µm</text>','</svg>'];Path(path).write_text('\n'.join(svg))

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();r=analyse();Path(a.out).write_text(json.dumps(r,indent=2)+'\n');draw(r,Path(a.out).with_suffix('.svg'));print(json.dumps([{k:v for k,v in c.items() if k!='banks'} for c in r['cases']]))
if __name__=='__main__':main()
