#!/usr/bin/env python3
"""RP4b: real hard output cells next to parent pins; no RTL/edge change."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
from child_lint import parse_lef
sys.path.insert(0,str(Path(__file__).resolve().parent))
from repack import stats,draw
s=json.loads((ROOT/'physical/ref_tile/smh_tile_rp4/spec.json').read_text())
s.update(name='smh_tile_rp4b',outline={'w':406.08,'h':1434.24},io_tcl='physical/ref_tile_specs/smh/smh_tile_rp4b_pins.tcl')
s['job'].update(tag='rp4b',structural_change='RP4 exact CTS failed global hard-clock repair (shared66eeff fix). Independently row_e parent-output stub229um exceeded available native launch margin30.3ps. Move actual Erow masters to x336.96 and Ebeat to x336.96/y717.12; upper5children shift112.32 to preserve21.6um channel. Match W/E busbit stations exactly to actual hard output LEF. SameRTL/dataedges. Width406.08 unchanged, height1434.24 fits1800SMframe; XC home must moveY1455.84 beforeparentadoption.')
boxes=[];mods={}
for c in s['children']:
 if c['at'][1]>=842.4:c['at'][1]=round(c['at'][1]+112.32,3)
 if c['inst'] in ['u.u_pte.u_row0','u.u_pte.u_row1']:c['at'][0]=336.96
 if c['inst']=='u.u_pte.u_beat':c['at']=[336.96,717.12]
 v=ROOT/c['view'];m=parse_lef((v/(v.name+'.lef')).read_text());mods[c['inst']]=(c,m)
 boxes.append(('row' if 'row' in c['inst'] else 'tile',c['inst'],*c['at'],m['W'],m['H']))
st=stats(406.08,1434.24,boxes)
assert not st['overlaps'] and not st['slivers_um'],st
# All 3705 externally launched bits are an exact translated hard-output shape.
pins={};used=[];links=[]
for inst,base,count,outp,inp in [('u.u_pte.u_row0',0,818,'rout','rin'),('u.u_pte.u_row1',818,818,'rout','rin'),('u.u_pte.u_beat',0,2069,'bout','bin')]:
 c,m=mods[inst]
 for bit in range(count):
  rr=[r for r in m['pins'][f'last[{bit}]']['rects'] if r[3]>=m['W']-0.001]
  assert len(rr)==1,(inst,bit,rr)
  layer,x0,y0,x1,y1=rr[0];assert layer=='M4'
  y=round(c['at'][1]+(y0+y1)/2,6)
  assert abs((y-0.012)/0.048-round((y-0.012)/0.048))<1e-4
  for port,x in [(outp,406.08),(inp,0)]:pins[f'{port}[{base+bit}]']=(layer,x,y)
  used.append(y);links.append({'parent':f'{outp}[{base+bit}]','child':inst+f'/last[{bit}]','layer':layer,'y_um':y,'horizontal_stub_um':25.92})
blocked={round((y-.012)/.048)+d for y in used for d in range(-2,3)}
lines=[]
pat=re.compile(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([^ ]+) ([^}]+)\}')
for line in (ROOT/'physical/ref_tile_specs/smh/smh_tile_rp4_pins.tcl').read_text().splitlines():
 m=pat.search(line)
 if not m:lines.append(line);continue
 port,layer,x,y=m[1],m[2],float(m[3]),float(m[4])
 if port in pins:layer,x,y=pins[port]
 elif port.startswith(('clk_hard[','clk_pin[','clk_oper[','clk_region[')):
  if y>=842.4:y+=112.32
  # Keep existing root locality, avoiding every actual M4 data pin by >=3tracks.
  candidates=[k for k in range(3,int((1434.24-.2)/.048)) if k not in blocked]
  k=min(candidates,key=lambda k:abs(.012+.048*k-y));y=.012+.048*k
  blocked.update(k+d for d in range(-2,3))
 elif abs(y-1321.92)<.001:y=1434.24
 lines.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary' if layer=='M4' else line.replace('1321.92}', '1434.24}'))
(ROOT/s['io_tcl']).write_text('\n'.join(lines)+'\n')
(ROOT/'physical/ref_tile_specs/smh/smh_tile_rp4b.json').write_text(json.dumps(s,indent=1)+'\n')
out=ROOT/'results/arch/hbm_sm_repack_1015/rp4b_boundary';out.mkdir(exist_ok=True,parents=True)
(out/'plan.json').write_text(json.dumps(dict(schema='opentallas.rp4b_boundary.v1',outline=s['outline'],geometry=st,children=s['children'],output_links=links,normal_edges_added=0,scope='Geometry/bitpin candidate only. Actual CTS/native boundary/route open.',tile_area_delta_mm2=406.08*112.32/1e6,sm_frame_area_delta_mm2=0,xc_required_home_um=[3788.64,1455.84]),indent=2)+'\n')
draw(out/'floorplan.png',406.08,1434.24,boxes,'RP4b hard output cells adjacent to actual parent bus pins; CTS/native OPEN')
print(json.dumps(st))
