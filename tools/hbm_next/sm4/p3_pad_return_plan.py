#!/usr/bin/env python3
"""Geometry-only prototype: central SRAM, rl1 on native XS3 N face, fixed3-edge pad.
Run the matched pin/region checks on the fleet; no route or timing claim.
"""
import argparse,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
r=Path(a.root);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
def pins(path):
 p={}
 for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \S+',path.read_text(),re.S):
  m=re.search(r'\bRECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',body)
  if m:x0,y0,x1,y1=map(float,m.groups());p[name]=((x0+x1)/2,(y0+y1)/2)
 return p

def tr(p,rect):
 x,y=p;ori=rect['orient'];w=rect['w'];h=rect['h']
 if ori in ('MY','R180'):x=w-x
 if ori in ('MX','R180'):y=h-y
 return x+rect['x'],y+rect['y']

def l1(x,y):return abs(x[0]-y[0])+abs(x[1]-y[1])
def snap(x):return round(round((x-.012)/.048)*.048+.012,3)
base=json.loads((r/'results/arch/hbm_next_1019/die/safe_sm_pack/central_candidate.json').read_text())
pads={0:(302.4,302.4,'MX'),1:(302.4,345.6,'R0'),2:(302.4,259.2,'MX'),3:(302.4,388.8,'R0'),4:(302.4,432,'R0'),5:(432,604.8,'R0'),6:(518.4,604.8,'R0')}
for x in base['rects']:
 if x['name'].startswith('new_pad_'):
  b=int(x['name'].rsplit('_',1)[1]);x['x'],x['y'],x['orient']=pads[b];x['region']='s'
(base_path:=out/'candidate.json').write_text(json.dumps(base,indent=1)+'\n')
# New native N-face allocation keeps shared W and each lane X local. Actual RTL is unchanged.
native={}
for bit in range(532):native[f'o_iwb[{bit}]']=(snap(4.020+.168*bit),289.44)
for lane,start in enumerate((100.020,352.020,448.020)):
 for bit in range(532):native[f'o_ixb[{lane*532+bit}]']=(snap(start+.168*bit),289.44)
for bit in range(818):
 x=196.020+.168*bit
 if x>=309.984:x+=11.52
 native[f'rl1[{bit}]']=(snap(x),289.44)
old=json.loads((r/'results/arch/hbm_next_1019/sm4/p3/sram_landing/xs3_gate_pins.json').read_text())
others=sorted(p[0] for p in old['pins'] if p[5]>=289.439 and not p[0].startswith(('o_iwb[','o_ixb[','VDD','VSS')) and p[0]!='clk')
assert len(others)==47,len(others)
for j,name in enumerate(others):native[name]=(snap(542.028+.36*j),289.44)
native['clk']=(315.372,289.44)
assert len(native)==2994 and len(set(native.values()))==2994
(out/'xs3_rl1n_native_pins.json').write_text(json.dumps(native,indent=1)+'\n')
lines=['# Prototype geometry only; exact RTL and native clocks unchanged.']
for name,(x,y) in native.items():lines.append(f'place_pin -pin_name {{{name}}} -layer M5 -location {{{x:.3f} {y:.3f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
(out/'xs3_rl1n_pins.tcl').write_text('\n'.join(lines)+'\n')
row=pins(r/'physical/ref_tile/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w/ot_smh_tr_group_row_w.lef')
mem=pins(r/'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.lef')
rs={x['name']:x for x in base['rects']};src=rs['u_row1'];dst=rs['u_lf1.g_xs3.u_xs']
proof=[];regions=[];half=(5.4,4.05)
for group,lo in enumerate(range(0,818,32)):
 hi=min(lo+32,818)
 if group<20:center=(275.4+(group%2)*10.8,310.5+(group//2)*10.8)
 elif group<24:center=(500,585+(group-20)*10.8)
 else:center=(589.2+(group-24)*10.8,632.88)
 tests=[]
 for bit in range(lo,hi):
  bank=rs[f'new_pad_{bit//128}'];s=tr(row[f'first[{bit}]'],src)
  w=tr(mem[f'wd_in[{bit%128}]'],bank);q=tr(mem[f'rd_out[{bit%128}]'],bank)
  z=tr(native[f'rl1[{bit}]'],dst)
  tests.append((l1(s,center)+sum(half),l1(center,w)+sum(half),l1(q,z)))
 worst=[max(v[j] for v in tests) for j in range(3)]
 # Captures must occupy actual whitespace, not a hard block/halo.
 box=(center[0]-half[0],center[1]-half[1],2*half[0],2*half[1]);overlap=[]
 for x in base['rects']:
  if box[0]<x['x']+x['w']+10.8-1e-6 and x['x']<box[0]+box[2]+10.8-1e-6 and box[1]<x['y']+x['h']+10.8-1e-6 and x['y']<box[1]+box[3]+10.8-1e-6:overlap.append(x['name'])
 regions.append({'bits':[lo,hi-1],'center':center,'region_um':[10.8,8.1]})
 proof.append({'bits':[lo,hi-1],'source_capture_um':worst[0],'capture_write_um':worst[1],'read_xs3_um':worst[2],'overlap':overlap,'pass':max(worst)<=405 and not overlap})
transport=[]
for label,inst,cy,cx,port_y in [('n','u_row0',1756.08,190.0,1565.0),('s','u_row1',632.88,194.4,440.0)]:
 child=rs[inst]
 for group,lo in enumerate(range(0,818,32)):
  hi=min(lo+32,818);center=(cx+6.48*group,cy);cost=[]
  for bit in range(lo,hi):
   pp=(0,snap(port_y+.243*bit));dd=tr(row[f'd[{bit}]'],child)
   cost.append((l1(pp,center)+sum(half),l1(center,dd)+sum(half)))
  worst=[max(x[j] for x in cost) for j in range(2)]
  # Overlapping placement REGIONS are permitted for separate cell sets; actual cell packing remains mandatory.
  overlaps=[]
  for x in base['rects']:
   if center[0]-half[0]<x['x']+x['w']+10.8-1e-6 and x['x']<center[0]+half[0]+10.8-1e-6 and center[1]-half[1]<x['y']+x['h']+10.8-1e-6 and x['y']<center[1]+half[1]+10.8-1e-6:overlaps.append(x['name'])
  transport.append({'region':label,'bits':[lo,hi-1],'center':center,'region_um':[10.8,8.1], 'face':'W', 'parent_pin_capture_um':worst[0],'capture_row_input_um':worst[1],'macro_overlap':overlaps,'pass':max(worst)<=405 and not overlaps})
(out/'transport_regions.json').write_text(json.dumps(transport,indent=1)+'\n')
result={'status':'PASS' if all(x['pass'] for x in proof+transport) else 'FAIL','groups':proof,'capture_regions':regions,'maxima_um':[max(x[k] for x in proof) for k in ['source_capture_um','capture_write_um','read_xs3_um']], 'latency':'One input capture plus native2-edge SRAM ring = existing3edge pad; zero extra data edges, II1', 'native_face_density_per_um':{'N':2994/561.6,'S':2085/561.6,'W':787/289.44,'E':531/289.44},'transport_maxima_um':[max(x[k] for x in transport) for k in ['parent_pin_capture_um','capture_row_input_um']], 'physical_gate_pass':False,'remaining':['materialize transport W/E y retarget and overlapping bounded capture regions in legal placement','all row/bk1/strap/control/clock endpoint checks','actual stdcell area in capture regions','fresh XS3 N-face gate and native clock audit','final parent synthesis/gate']}
(out/'pad_reach.json').write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['groups','capture_regions']},indent=1))
raise SystemExit(result['status']!='PASS')
