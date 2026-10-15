#!/usr/bin/env python3
"""Freeze literal per-bit clock-safe bank pin plans before source shipment."""
import json, math, argparse
from pathlib import Path
r=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*');a=ap.parse_args()

def snap(z):return .012+round((z-.012)/.048)*.048

def coordinates(n,pg=False):
 allowed=[]
 for k in range(math.ceil((5.4-.012)/.048),math.floor((59.4-.012)/.048)+1):
  x=.012+.048*k
  if pg and any(abs(x-(2.46+5.4*j+d))<.120-1e-9 for j in range(12) for d in [0,.192]):continue
  allowed.append(round(x,6))
 out=[]
 for b in range(n):
  target=5.4+54*b/(n-1)
  valid=[x for x in allowed if not out or x>=out[-1]+.096-1e-8]
  out.append(min(valid,key=lambda x:abs(x-target)))
 assert out[-1]<=59.4 and len(set(out))==n
 return out

for width in [263,256]:
 for orient in ['H','V']:
  name=f'qkh_packet_{orient.lower()}{width}'
  if a.only is not None and name not in a.only: continue
  kit=r/'physical/ref_tile'/name;kit.mkdir(parents=True,exist_ok=True)
  outline=[64.8,15.12] if orient=='H' else [15.12,64.8]
  positions={};tcl=[];points=coordinates(width,pg=orient=='H')
  for port in ['d','q']:
   entries=[]
   for b,z in enumerate(points):
    x,y=(z,.096 if port=='d' else outline[1]-.096) if orient=='H' else (.096 if port=='d' else outline[0]-.096,z)
    layer='M5' if orient=='H' else 'M4';entries.append([x,y])
    tcl.append(f'place_pin -pin_name {{{port}[{b}]}} -layer {layer} -location {{{x:.6f} {y:.6f}}}')
   positions[port]=dict(layer=layer,xy_um=entries)
  for port,z in [('clk',snap(5.4) if orient=='H' else 4.968),('rst_n',snap(9.7))]:
   if orient=='H': x,y,layer=.096,z,'M4'
   elif port=='clk': x,y,layer=.096,1.308,'M4'
   else: x,y,layer=z,.096,'M5'
   positions[port]=dict(layer=layer,xy_um=[[x,y]])
   tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.6f} {y:.6f}}}')
  (kit/'assigned_pins.tcl').write_text('\n'.join(tcl)+'\n')
  (kit/'assigned_pins.json').write_text(json.dumps(dict(schema='opentallas.qkh-packet-bank-pins.v1',name=name,width_bits=width,outline_um=outline,positions=positions,pg_rule='H M5 coordinates exclude 0.12um around actual PG stripe centers2.46/2.652 mod5.4; V M4 pins are below M5PG; all bit centers use0.012+0.048k grid, >=0.096pitch'),indent=2)+'\n')
  s=json.load(open(r/'physical/qwen_head_bank_pins_1015/packet_template.json'));s['name']=name;s['top']=name;s['params']={};s['sources'].append('rtl/qwen_sys/head_staging_20261015/qkh_packet_masters.sv');s['outline']=dict(zip(['w','h'],outline));s['pins']={'S':['d'],'N':['q'],'W':['clk','rst_n']} if orient=='H' else {'W':['d'],'E':['q'],'S':['clk','rst_n']}
  if orient=='V': s['pins']={'W':['d','clk'],'E':['q'],'S':['rst_n']}
  s['io_tcl']=f'physical/ref_tile/{name}/assigned_pins.tcl';s['pin_ranges']={'d':[points[0],points[-1]],'q':[points[0],points[-1]]}
  if orient=='V': s['route']['m5_pg_pitch']=2.7
  s['job']['tag']='bp1' if orient=='H' else 'pg3';s['job']['views_to']=f'physical/ref_tile/{name}/views';s['job']['record_to']=f'results/rtl/ref_tile/{name}'
  # Use only the original primitive bench, retaining exact full-width transfer and mutants.
  for b in s['job']['benches']:
   b['cmd']=b['cmd'].replace(' 256 ',' '+str(width)+' ')+ ' '+name
   for k in ['pass_regex','fail_regex']:
    if k in b:b[k]=b[k].replace('W=256 ','W='+str(width)+' ')
  s['structural_change']='Actual Q519 split into263b metadata+lowerQ and256b upperQ banks at SAMEfixededge, eachrealownclockroot. LiteralspreadM4/M5pins+PGavoidance frozen beforeCTS. H519failedrecipe2posthookarea755.7>core653.2; bitbanking preservesallQbits/throughput, no density or timing waiver.'
  if orient=='V': s['structural_change']+=' Actual bp2 export failed child_lint PG spread36percent: double M5 stripe density to2.7um pitch, moving clk pin5.388to4.968um away from newstripe5.352; all data pins/outline/RTL/data edges unchanged. PG2 actualroutes failed DRT-0255 at S-M5clk access. Moveclk to W-M4(.096,1.308), belowfirstdata5.436 andbelowPG; all d/q/rst remain unchanged. Coordinatescheckedon.012+.048k tracks. Expected PG span53.6percent must be measured in exported actual LEF; no waiver.'
  out=r/'tools/ref_tile/specs_q_compute_native'/(name+'.json');out.write_text(json.dumps(s,indent=2)+'\n');print(name,points[0],points[-1])

for width in [34,16]:
 name=f'qkh_packet_v{width}'
 if a.only is not None and name not in a.only: continue
 p=r/'tools/ref_tile/specs_q_compute_native'/(name+'.json');s=json.load(open(r/'physical/qwen_head_bank_pins_1015/packet_template.json'));s['name']=name;s['top']=name;s['params']={};s['outline']={'w':21.6,'h':21.6};s['pins']={'W':['d'],'E':['q'],'S':['clk','rst_n']};s['sources'].append('rtl/qwen_sys/head_staging_20261015/qkh_packet_masters.sv')
 for b in s['job']['benches']:
  b['cmd']=b['cmd'].replace(' 256 ',' '+str(width)+' ')+ ' '+name
  for k in ['pass_regex','fail_regex']:
   if k in b:b[k]=b[k].replace('W=256 ','W='+str(width)+' ')
 s['job']['tag']='bp1';s['job']['views_to']='physical/ref_tile/'+name+'/views';s['job']['record_to']='results/rtl/ref_tile/'+name;p.write_text(json.dumps(s,indent=2)+'\n')
