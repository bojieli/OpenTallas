#!/usr/bin/env python3
import re,json,itertools,math,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();root=Path(a.root)
def pins(path):
 text=path.read_text();out={}
 for n,b in re.findall(r'  PIN (\S+)\n(.*?)  END \S+',text,re.S):
  rect=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',b)
  if rect:x0,y0,x1,y1=map(float,rect.groups());out[n]=((x0+x1)/2,(y0+y1)/2)
 return out
m=pins(root/'physical/asap7_memory_macros/ot_sram_1r1w2c_16x546_m1/ot_sram_1r1w2c_16x546_m1.lef');l=pins(root/'physical/ref_tile/smh_tr_group_land_ref/views/ot_smh_tr_group_land/ot_smh_tr_group_land.lef')
text=(root/'physical/hbm_next/sm4/hnx_rp3lp3x_pins.tcl').read_text();ports={int(i):(float(x),float(y)) for i,x,y in re.findall(r'pin_name \{bin\[(\d+)\]\}.*?location \{([\d.]+) ([\d.]+)\}',text)}
def tr(q,xy,orient,w=176.904,h=81):
 x,y=q
 if orient in ('MY','R180'):x=w-x
 if orient in ('MX','R180'):y=h-y
 return x+xy[0],y+xy[1]
def dist(x,y):return abs(x[0]-y[0])+abs(x[1]-y[1])
cases={'original_no_growth':([(432,1598.4),(432,475.2),(129.6,1036.8),(345.6,1036.8)],(43.2,950.4)),'central_four_s129':([(129.6,1036.8),(345.6,1036.8),(129.6,1166.4),(345.6,1166.4)],(129.6,950.4)),'central_four_s43':([(129.6,1036.8),(345.6,1036.8),(129.6,1166.4),(345.6,1166.4)],(43.2,950.4)),'central_four_s388':([(129.6,1036.8),(345.6,1036.8),(129.6,1166.4),(345.6,1166.4)],(388.8,950.4)),'central_four_s345':([(129.6,1036.8),(345.6,1036.8),(129.6,1166.4),(345.6,1166.4)],(345.6,950.4))}
results={}
for label,(slots,land) in cases.items():
 costs={}
 for bank in range(4):
  for pos,xy in enumerate(slots):
   for orient in ('R0','MY','MX','R180'):
    read=[];write=[]
    for bit in range(bank*546,min((bank+1)*546,2069)):
     rd=tr(m[f'rd_out[{bit%546}]'],xy,orient);dst=tr(l[f'd[{bit}]'],land,'MX',216,43.2);wd=tr(m[f'wd_in[{bit%546}]'],xy,orient)
     read.append((dist(rd,dst),bit,rd,dst));write.append((dist(ports[bit],wd),bit,ports[bit],wd))
    costs[bank,pos,orient]=(max(read),max(write))
 best=None
 for perm in itertools.permutations(range(4)):
  for ori in itertools.product(('R0','MY','MX','R180'),repeat=4):
   cr=[costs[b,perm[b],ori[b]] for b in range(4)];obj=(max(c[0][0] for c in cr),max(c[1][0] for c in cr))
   if best is None or obj<best[0]:best=(obj,perm,ori,cr)
 obj,perm,ori,cr=best
 results[label]=dict(max_read_L1_um=obj[0],max_pin_to_write_L1_um=obj[1],register_to_macro_two_hop_write_necessary_um=obj[1]/2,read_405_pass=obj[0]<=405,write_two_hop_810_necessary_pass=obj[1]<=810,land_s_xy=land,bank_assignments=[dict(bank=b,slot=perm[b],xy=slots[perm[b]],orient=ori[b],read_worst_um=cr[b][0][0],read_worst_bit=cr[b][0][1],read_from=cr[b][0][2],read_to=cr[b][0][3],write_worst_um=cr[b][1][0],write_worst_bit=cr[b][1][1],write_from=cr[b][1][2],write_to=cr[b][1][3]) for b in range(4)])
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'matched_reach.json').write_text(json.dumps(results,indent=1)+'\n');print(json.dumps(results,indent=1),flush=True)
