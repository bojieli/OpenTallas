#!/usr/bin/env python3
"""Real source bit mapping and actual published LEF pin coordinates; missing views stay explicit."""
import argparse,gzip,hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'results/arch/qwen_vm_residual_1015/physical_inventory'
a=argparse.ArgumentParser();a.add_argument('--plan',default='regional_wide');args=a.parse_args()
x=json.loads((D/'inventory.json').read_text());plan=x['alternatives'][args.plan];rect={(b['region'],b['class'],b['n']):b for b in plan['rectangles']}
def pins(cls):
 row=x['inventory'][cls];data=subprocess.check_output(['git','show','HEAD:'+row['lef']],cwd=R).decode();res={}
 for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\bEND\s+\1(?:\s|$)',data,re.S):
  name,body=m.groups();sh=[]
  for z in re.finditer(r'LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',body):
   lay,*a=z.groups();a=list(map(float,a));sh.append({'layer':lay,'rect':a,'center':[(a[0]+a[2])/2,(a[1]+a[3])/2]})
  if sh:res[name]=sh
 return res
pbank=pins('qvm_su_bank_native');psu=pins('ot_qfd_vm_su1024_t')
rows=[];hops=[]
for c in range(3):
 for bank in range(16):
  rg,j=divmod(bank,2);bn=c*2+j;b=rect[rg,'qvm_su_bank_native',bn];s=rect[rg,'ot_qfd_vm_su1024_t',c]
  bpath=f'u_vm.g_tile.g_t[{rg}].u_t.g_c[{c}].g_j[{j}].g_nst.u_st';spath=f'u_vm.g_tile.g_t[{rg}].u_t.g_su_leaf[{c}].u_su'
  for bit in range(512):
   q=pbank[f'q[{bit}]'][0];si=psu[f'sx[{j*512+bit}]'][0];so=psu[f'so[{j*512+bit}]'][0]
   qxy=[b['x']+(b['w']-q['center'][0] if b['orient']=='MY' else q['center'][0]),q['center'][1]+b['y']];sxy=[si['center'][0]+s['x'],si['center'][1]+s['y']];oxy=[so['center'][0]+s['x'],so['center'][1]+s['y']]
   L=abs(qxy[0]-sxy[0])+abs(qxy[1]-sxy[1]);hops.append(L)
   plane=bit%32;word=bit//32;de=bank*16+word;dst=f'u_vm.g_cp[{c}].g_return_leaves.g_plane[{plane}].u_plane.d[{de}]'
   rows.append({'source':f'{bpath}.q[{bit}]','source_xy':qxy,'source_layer':q['layer'],'capture':f'{spath}.sx[{j*512+bit}]','capture_xy':sxy,'capture_layer':si['layer'],'bank_to_su1024_L1_um':L,'su1024_output':f'{spath}.so[{j*512+bit}]','su1024_output_xy':oxy,'su1024_output_layer':so['layer'],'current_region_return_register':f'u_vm.g_tile.g_t[{rg}].u_sr.q[{(c*2+j)*512+bit}]','current_region_return_has_physical_view':False,'target':dst,'target_xy':None,'target_pin_status':'Actual RTL port; leaf view/pin contract unassigned, do not invent coordinates','remaining_transport':'RO1 soft register then bitplane data pin; reach/cut/relay stages OPEN'})
assert len(rows)==24576
raw=json.dumps({'scope':'Actual source bit mapping, actual LEF local pins transformed through minimum wide packing screen; no clock/timing or routed fit qualification','rows':rows},separators=(',',':')).encode();blob=gzip.compress(raw,mtime=0);(D/('return_incident_graph_'+args.plan+'.json.gz')).write_bytes(blob)
r={'plan':args.plan,'edges':len(rows),'source_sha256':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in ['rtl/qwen_sys/vm_nox_20261014/ot_qfd_vm_region_nx.sv','rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv']},'graph_gzip_sha256':hashlib.sha256(blob).hexdigest(),'bank_q_to_su1024_sx_in_screen':{'over_500um':sum(h>500 for h in hops),'max_L1_um':max(hops),'min_L1_um':min(hops)},'missing_actual_views':['RO1 parent soft relay register','return-plane standard master'],'qualification':'Fail closed on missing target pin coordinates; selected packing is not qualified on remaining incident arcs/cuts/timing'};(D/('return_incident_summary_'+args.plan+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
