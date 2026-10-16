#!/usr/bin/env python3
"""Expose the eight real NT bottom roots without changing arithmetic or storage."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
p=root/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv'
s=p.read_text();start=s.index('module ot_s81_hc_cnbot #(');end=s.index('\nendmodule',start)+len('\nendmodule')
t=s[start:end].replace('module ot_s81_hc_cnbot #(','module ot_s81_hc_cnbot_roots #(',1)
a='    input  wire                 sk,'
assert t.count(a)==1
t=t.replace(a,a+'\n    input wire [7:0] sk_leaf,',1)
# Each selected connection occurs exactly once in this wires-only parent.
for old,new in [('u_a (.sk(sk)','u_a (.sk(sk_leaf[2*c])'),('u_b (.sk(sk)','u_b (.sk(sk_leaf[2*c+1])'),('.sk(sk), .srs(srs), .w_rvt','.sk(sk_leaf[6]), .srs(srs), .w_rvt'),('u_rsq (.sk(sk)','u_rsq (.sk(sk_leaf[7])')]:
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
o=root/'rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_cnbot_roots.sv'
o.write_text('// Candidate wires-only parent; all existing child arithmetic and stages preserved.\n'+t+'\n')
paths=[f'g_c[{c}].u_{h}' for c in range(3) for h in ('a','b')]+['u_tr','u_rsq']
receipt={'scope':'additive NT bottom independent root source candidate; no inherited parent/clock/native physical closure','source':str(p.relative_to(root)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(o.read_bytes()).hexdigest(),'roots':[{'index':i,'child':x,'type':(['ot_s81_hc_cncla','ot_s81_hc_cnclb'][i%2] if i<6 else ['ot_s81_hc_cntree','ot_s81_hc_cnrsq'][i-6])}for i,x in enumerate(paths)],'new_payload_FF':0,'new_control_FF':0,'new_data_cycles':0,'child_tuple':{'NG':256,'D':5120,'NCOL':3,'GS':8,'S_RD':2,'S_RT':4,'ML':5,'AL':4,'NT_K':67,'cntree':{'HALF':1,'RLY':2,'RF':4,'DW':6}},'residual_roots_total_including_previous53':61,'open':['source equality and stopped-real-root checks','per-root sink census/current real clock pins','actual native views and compact parent homes','current die TAIL_SPLIT1 lacks NT lane joins']}
(root/'results/arch/s81_hc_current_1016/cnbot_prebuild.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('CNBOT8_GENERATED')
