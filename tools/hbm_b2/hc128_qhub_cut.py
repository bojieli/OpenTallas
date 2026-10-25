#!/usr/bin/env python3
"""Cut a native W128 qcen into four exact32-input/five-level subtrees.
Three upper adders and original control remain untouched; no registered level is
added, removed or re-associated. The original per-node error indicators leave
through31bits/subtree, preserving ps_f's cycle-exact OR across every level.
"""
import argparse,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('netlist',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);j=json.loads(a.netlist.read_text());top='ot_hbm_hc_qhub_static';qn=j['modules'][top]['cells']['u_cen']['type'];q=j['modules'][qn];cells=q['cells'];ne=q['netnames']['ne']['bits'];assert len(ne)==127
bybit={}
for n,c in cells.items():
 for p,d in c['port_directions'].items():
  if d=='output':
   for b in c['connections'][p]:
    if isinstance(b,int):bybit.setdefault(b,[]).append(n)
pieces=[];used=set()
for k in range(4):
 names=[];nodes=[]
 for n,c in cells.items():
  m=re.fullmatch(r'g_lvl\[(\d+)\]\.g_n\[(\d+)\]\.u_a',n)
  if not m:continue
  l,i=map(int,m.groups());N=128>>l
  if l<=5 and k*(N//4)<=i<(k+1)*(N//4):names.append(n);nodes.append(128-((2*128)>>l)+i)
 assert len(names)==31
 for ni in nodes:
  drv=bybit[ne[ni]];assert len(drv)==1;dn=drv[0];names.append(dn)
  for p,d in cells[dn]['port_directions'].items():
   if d!='input':continue
   for b in cells[dn]['connections'][p]:
    for nn in bybit.get(b,[]):
     if cells[nn]['type']=='$reduce_or':names.append(nn)
 names=sorted(set(names));assert not (set(names)&used);used.update(names)
 pieces.append(dict(index=k,module=f'ot_hbm_hc_subtree32_{k}',cells=names,fp32_adders=31,tree_levels=5,error_nodes=sorted(nodes)))
s=[f'read_json {a.netlist.resolve()}',f'select {qn}','splitnets','select -clear',f'cd {qn}']
for p in pieces:
 s+=['select -set CUT '+' '.join('c:'+n.replace('\\','?').replace('[','?').replace(']','?') for n in p['cells']),f'submod -name {p["module"]} @CUT']
s+=['cd ..',f'write_json {a.out.resolve()}/qhub_split128.json',f'write_verilog {a.out.resolve()}/qhub_split128.v','stat']
(a.out/'cut.ys').write_text('\n'.join(s)+'\n');(a.out/'physical_contract.json').write_text(json.dumps(dict(schema='opentallas.hbm.hc128.qhub_cut.v1',source_sha='591bcf802',status='CANDIDATE_NOT_ROUTED',W=128,subtree_replicas=4,subtree_inputs=32,subtree_levels=5,upper_levels=2,upper_fp32_adders=3,total_fp32_adders=127,split_cycle_delta=0,remainder_cells=len(cells)-len(used),pieces=pieces,model=dict(measured_W128_qcen_cells=534816,measured_W128_qcen_std_area_um2=55806.21846,estimated_subtree_cells=131000,estimated_subtree_outline_um=[220.32,220.32],estimate_only=True),pending=['exact composition miter+mutant','actual core pins/synthesis/floorplan integration','face shell latency adoption and timing']),indent=2)+'\n');print('four32input subtrees;',len(cells)-len(used),'remainder word cells;',len(used),'selected word cells')
