#!/usr/bin/env python3
"""Literal selected LEF pin graph; no placement, clock, or route qualification."""
import argparse, hashlib, json, pathlib, re
ap=argparse.ArgumentParser();ap.add_argument('--parent',required=True);ap.add_argument('--mapper-view',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
p=pathlib.Path(a.parent);mv=pathlib.Path(a.mapper_view)
b=p/'physical/ref_tile/sfu_lane_ring3_rt/views/ot_su12_sfu/ot_su12_sfu.lef';ml=mv/'ot_hgi_sfu_lane_map.lef';g=p/'rtl/hbm_accel/generic/peers/ot_hgi_sfu_arithmetic_grid.sv'
def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def pins(f):
 t=f.read_text();out={}
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',t,re.M|re.S):
  z=m.group(2);layer=None;rects=[]
  for ln in z.splitlines():
   q=re.search(r'LAYER (\S+) ;',ln)
   if q:layer=q[1]
   q=re.search(r'RECT\s+([\d. -]+)\s*;',ln)
   if q:rects.append({'layer':layer,'rect_um':list(map(float,q[1].split()))})
  d=re.search(r'DIRECTION (\S+)',z);u=re.search(r'USE (\S+)',z)
  out[m[1]]={'direction':d[1] if d else None,'use':u[1] if u else None,'rects':rects}
 return out
bp=pins(b);mp=pins(ml);text=g.read_text();widths={n:int(hi)+1 for hi,n in re.findall(r'wire \[(\d+):0\] (r_\w+);',text)}
passnames=re.search(r'\.i_pass\(\{(.*?)\}\)',text,re.S)[1].split(',');passnames=[x.strip() for x in passnames]
def pin(base,k,w):return base if w==1 else f'{base}[{k}]'
edges=[];offset=0
for name in reversed(passnames):
 w=widths[name];dst=name[2:]
 for k in range(w):
  s=f'o_pass[{offset+k}]';d=pin(dst,k,w)
  edges.append({'mapper_pin':s,'body_pin':d,'field':dst,'field_bit':k,'mapper_literal':mp.get(s),'body_literal':bp.get(d),'edge_count':0})
 offset+=w
for field,w in [('o_v',24),('i_v',24),('krow',24),('ls',4),('lvw',4),('emit',1),('ld_c',1200)]:
 for k in range(w):
  s=pin('o_'+field,k,w);d=pin(field,k,w)
  edges.append({'mapper_pin':s,'body_pin':d,'field':field,'field_bit':k,'mapper_literal':mp.get(s),'body_literal':bp.get(d),'constant_zero':field=='ld_c' and k%240>=24,'edge_count':0})
output={'schema':'opentallas.sfu.literal_source_pin_graph.v1','qualified':False,'instances':16,'source':str(g),'source_sha256':digest(g),'body_lef':str(b),'body_sha256':digest(b),'body_size_um':[216,330.48],'mapper_lef':str(ml),'mapper_sha256':digest(ml),'mapper_scope':'existing m2 exact view only; new 103.68x54 mapper has no inherited pin/timing qualification','body_pins':bp,'mapper_pins':mp,'mapper_to_body_bit_edges':edges,'controller_to_mapper':'grid_control1742 uniformly maps into 16 mapper input graphs. Only 480 coefficient bits are live; 720 padded bits never connect to mapper input. Dynamic bits total1022. No broadcast relay tree in source.','four_roots_to_controller':'ops_hi q/vo → ops_lo tail_d/v; meta_hi q/vo → meta_lo tail_d/v. Low roots reconstruct cws135 livebits (NONE bypass outside leaf), cws goes to original E1/E2 stages; all roots need literal CTS Q/P pin dump.','PG':'Selected body M6 VDD/VSS stripes, parent M7 straps. New controls M5. No PG corridor grant.','open':['literal control leaf CTS pins','new mapper pins and 26 setup defect closure','remaining real controller root/pin graph','full source/global quarter geography','registered broadcast topology and exact unchanged issue phase','native cache/owner group seam','die clock/PG/slot/cut/hold per pair']}
pathlib.Path(a.out).write_text(json.dumps(output,indent=2)+'\n')
