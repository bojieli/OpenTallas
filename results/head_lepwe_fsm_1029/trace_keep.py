import re,json
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/head-kits-3/diag/ot_s81hd_lep_pair_diag/run/results/asap7/hbc_ot_s81hd_lep_pair/base/1_2_yosys.v')
s=p.read_text();drivers={}
for m in re.finditer(r'^  (\S+)\s+(\S+)\s*\(\s*(.*?)\n  \);',s,re.M|re.S):
 typ,inst,body=m.groups();pins={a:b.strip().lstrip('\\').strip() for a,b in re.findall(r'\.(\w+)\((.*?)\)',body,re.S)}
 for out in ['Y','Q','QN','CON','SN']:
  if out in pins:drivers[pins[out]]=(typ,inst,out,pins)
for n in ['u_lane.u.u_ep.rdy_k[3]','u_lane.u.u_gb.g_pc[0].ps[5]','u_lane.u.u_gb.g_pc[11].ps[3]','u_lane.u.u_gb.g_pc[5].ps[4]']:
 chain=[];x=n
 for _ in range(12):
  d=drivers.get(x)
  if not d:break
  typ,inst,out,pins=d;chain.append(dict(net=x,type=typ,inst=inst,out=out))
  if not typ.startswith(('BUF','INV')):break
  x=pins['A']
 print(json.dumps(dict(kept=n,driver_chain=chain)))
