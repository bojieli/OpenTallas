#!/usr/bin/env python3
"""Derivative of exact historical a7/r6 leaf; defaults/pipeline ages preserved."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[3]
p=r/'rtl/qwen_sys/host_cluster_20261017/qkd_hr_core_peer.v'
s=p.read_text();assert s.count('module qkd_hr_core_peer(')==1;assert s.count('qkd_host_peer_link_rr u_rank__u_peer')==1
q=r/'rtl/qwen_sys/host_cluster_20261017/qkd_hr_core_peer_sram.v'
q.write_text(s.replace('module qkd_hr_core_peer(', 'module qkd_hr_core_peer_sram(').replace('qkd_host_peer_link_rr u_rank__u_peer','qkd_host_peer_link_rr_sram u_rank__u_peer'))
a=r/'rtl/qwen_sys/host_cluster_20261017/peer_rr/qkd_host_peer_link_rr.sv'
s=a.read_text();assert s.count('module qkd_host_peer_link_rr #(')==1;assert s.count('qkd_host_peer_link #(.MUT(MUT))')==1
b=r/'rtl/qwen_sys/host_cluster_20261017/peer_rr/qkd_host_peer_link_rr_sram.sv'
b.write_text(s.replace('module qkd_host_peer_link_rr #(', 'module qkd_host_peer_link_rr_sram #(').replace('qkd_host_peer_link #(.MUT(MUT))','qkd_host_peer_link #(.MUT(MUT),.SAFE_SRAM(1))'))
d=json.loads((r/'physical/ref_tile/qkd_hr_core_peer/spec.json').read_text())
d['name']=d['top']='qkd_hr_core_peer_sram'
d['sources']=[str(q.relative_to(r)) if x==str(p.relative_to(r)) else str(b.relative_to(r)) if x==str(a.relative_to(r)) else x for x in d['sources']]
n='ot_sram_1r1w_32x546_m1_p192_mir';d['sources']+=['rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_sram_head.sv','physical/asap7_memory_macros/'+n+'/'+n+'_bb.v']
d['reset_landing'].update(copies={'por_n':64,'host_rst_n':64},first_copies={'por_n':2,'host_rst_n':2});d['reset_relay_split']['max_loads']=32
(r/'rtl/test/host_peer_safe_1020/leaf_spec.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({str(x.relative_to(r)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [p,q,a,b]},indent=2))
