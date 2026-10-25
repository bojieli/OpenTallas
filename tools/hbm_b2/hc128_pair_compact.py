#!/usr/bin/env python3
"""Compact pair-cut scalar ports and reuse one structurally identical tile master.
The following composition miter, not this transformation, decides exactness.
"""
import argparse,collections,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('split',type=Path);ap.add_argument('--top',default='ot_hbm_hc_bankq_static');ap.add_argument('--master',default='ot_hbm_hc_bank128_pair_core');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);j=json.loads(a.split.read_text());mods=j['modules'];top=mods[a.top];master=a.master
base_names={'clk':'clk','u_c.u_b.x_re':'x_read','u_c.u_b.w_re':'weight_read','u_c.u_b.u_st.rst_n':'rst_n','u_c.u_b.u_st.g_lg.ov_r':'go','u_c.u_b.wa_q':'write_addr','u_c.u_b.u_st.g_lg.sss':'square','u_c.u_b.wd_q':'write_data','u_c.u_b.u_st.sum_out':'sum_out','u_c.u_b.u_st.sum_in':'sum_in','sum_in':'sum_in','sum_out':'sum_out','u_c.u_b.w_addr':'weight_addr','u_c.u_b.x_addr':'x_addr','u_c.u_b.u_st.g_lg.lfg':'fault','u_c.u_b.u_st.g_lg.lvs':'lane_valid'}
all_maps={};counts={}
for k in range(8):
 name=f'ot_hbm_hc_bank128_pair{k}';m=mods[name];groups=collections.defaultdict(list)
 read={b for c in m['cells'].values() for pn,bs in c['connections'].items() if c['port_directions'][pn]=='input' for b in bs if isinstance(b,int)}
 drive={b for c in m['cells'].values() for pn,bs in c['connections'].items() if c['port_directions'][pn]=='output' for b in bs if isinstance(b,int)}
 for pn,p in m['ports'].items():
  mm=re.match(r'^(.*)\[(\d+)\]$',pn);base=mm[1] if mm else pn;ix=int(mm[2]) if mm else -1
  label=base_names.get(base)
  if label is None:
   wm=re.match(r'u_c\.u_b\.g_w\[(\d+)\]\.we$',base);xm=re.match(r'u_c\.u_b\.g_x\[(\d+)\]\.we$',base)
   if wm:label=f'weight_we{int(wm[1])-2*k}'
   elif xm:label='x_write'
   else:raise AssertionError(('unknown port',pn))
  for z,b in enumerate(p['bits']):
   di='output' if b in drive else 'input' if b in read else None
   if di is None:continue
   groups[label].append((ix if len(p['bits'])==1 else z,pn,z,b,di))
 ports={};connections={};mapping={};cell=top['cells'][name]
 for label,group in sorted(groups.items()):
  group.sort(key=lambda x:x[0]);directions={v[4] for v in group};assert len(directions)==1
  ports[label]=dict(direction=next(iter(directions)),bits=[v[3] for v in group])
  connections[label]=[cell['connections'][v[1]][v[2]] for v in group]
  mapping[label]=[(v[1],v[2]) for v in group]
 if k==0:
  canonical=json.loads(json.dumps(m));canonical['ports']=ports;canonical['attributes'].pop('hdlname',None);mods[master]=canonical
 else:
  assert {n:(p['direction'],len(p['bits'])) for n,p in ports.items()}==counts
 counts={n:(p['direction'],len(p['bits'])) for n,p in ports.items()}
 cell['type']=master;cell['connections']=connections;cell['port_directions']={n:p['direction'] for n,p in ports.items()};all_maps[name]=mapping
for k in range(8):del mods[f'ot_hbm_hc_bank128_pair{k}']
(a.out/'compact128.json').write_text(json.dumps(j))
(a.out/'compact_port_map.json').write_text(json.dumps(dict(master=master,ports=counts,instances=all_maps),indent=2)+'\n')
(a.out/'export.ys').write_text(f'read_json {a.out.resolve()}/compact128.json\nselect {master}\nwrite_verilog -selected {a.out.resolve()}/{master}.sv\n')
print(master,counts)
