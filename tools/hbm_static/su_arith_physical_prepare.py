#!/usr/bin/env python3
"""Source-pinned SU physical admission model, before mapping/CTS."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
O=R/'results/arch/hbm_su_f2_static_1014/arithmetic/physical';O.mkdir(exist_ok=True)
leaf='rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane.sv'
bank='rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_pinned_bank.sv'
def ports(path,env):
 s=re.sub(r'//[^\n]*','',(R/path).read_text());s=s[s.index(') (')+3:s.index(');',s.index(') ('))] if ') ('in s else s[s.index(')(\n')+2:s.index(');')]
 s=re.sub(r'//[^\n]*','',s);out=[]
 for m in re.finditer(r'\b(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s*([^;]+?)(?=,\s*(?:input|output)\b|$)',s,re.S):
  dr,rg,names=m.groups();w=1
  if rg:
   a,b=rg[1:-1].split(':');w=abs(eval(a,{'__builtins__':{}},env)-eval(b,{'__builtins__':{}},env))+1
  for n in names.strip().rstrip(',').split(','):
   n=n.strip()
   if n:out.append(dict(name=n,direction=dr,bits=w))
 return out
lp=ports(leaf,dict(AW=24,CW=24,LN=7));bp=ports(bank,dict(READERS=6,RB=9))
read={'rd_q','vi_q','side_y'};outputs={p['name']for p in lp if p['direction']=='output'}
faces={'N':['clk_stage','clk_insert','ld_c'],'W':sorted(read),'E':sorted(outputs),'S':[p['name']for p in lp if p['name']not in read|outputs|{'clk_stage','clk_insert','ld_c'}]}
macro='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
ls=(R/macro).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',ls).groups()); obs=ls.split('OBS',1)[1] if 'OBS'in ls else ''
layout=[dict(reader=i,x_um=22.464+(i%3)*114.912,y_um=23.76+(i//3)*62.64,orientation='R0')for i in range(6)]
c=json.loads((R/'results/arch/hbm_su_f2_static_1014/arithmetic/clock_census.json').read_text())
report=dict(schema='hbm.su.physical_admission.v1',qualified=False,clock_period_ns=1.111111111,clock_policy='serial target; related1:1 logical phase0; routed insertion and phi-R delivery unmeasured',corners='TT setup pathfinding, FF hold, SS sensitivity; unchanged60ps/25ps',leaf_ports=lp,leaf_raw_pin_bits=sum(p['bits']for p in lp),leaf_faces=faces,leaf_face_bits={f:sum(p['bits']for p in lp if p['name']in ns)for f,ns in faces.items()},kinds=[dict(kind=k,replicas=[384,127,1][k],register_census=c['records'][k],outline_um=[216,216] if k==0 else [302.4,302.4],outline_status='independent geometry prototype only',mapping='pending',CTS='pending')for k in range(3)],bank=dict(ports=bp,pin_bits=sum(p['bits']for p in bp),replicas=512,real_macros=6,macro_size_um=[w,h],macro_OBS_layers=sorted(set(re.findall(r'LAYER\s+(\w+)',obs))),candidate_outline_um=[369.36,151.2],candidate_placement=layout,intermacro_channel_um=20,macro_core_edge_margin_um=20,core_margin_um=2.16,standard_cell_FF=330,clock_loads='boundary register root plus six distinct provider roots (each one SRAM and word-select flops)',macro_clock_roots=6,boundary_clock_roots=1,geometry_status='candidate only; needs pin/PG/channel and source-qualified mapping',read_edges=2,write_commit_edges=1),whole_parent=dict(operand_network_implemented=False,arithmetic_roots=3970,broadcast_roots=64,bank_roots=3584,side_roots=6,leaf_clock_slots=6144,active_arithmetic_broadcast_bank_side_roots=7624),source_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest()for p in [leaf,bank,macro]})

for k in range(3):
 p=O/f'kind{k}_map/result.json'
 if p.exists():
  a=json.loads(p.read_text())['synthesis'];report['kinds'][k]['mapping']=dict(area_um2=a['cell_area_um2'],cells=a['cell_count'],mappedFF=a['sequential_cell_count'],status='sourcequalified mapping only; noCTS')
report['geometry_assignment']='/home/ubuntu/wt/geometry-hbm-1015/results/arch/hbm_system_geometry_1015/physical_assignments/SU_actual_arithmetic.json'
report['bank']['prior_die_edge_model_compliant']=False
assert report['leaf_raw_pin_bits']==1921 and report['bank']['pin_bits']==308
(O/'admission_model.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['leaf_raw_pin_bits','leaf_face_bits','bank']}))
