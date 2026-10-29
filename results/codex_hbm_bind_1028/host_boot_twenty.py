"""Emit exact native HOST320 source chain:20 named planned hops,18NW_hub +2root.
transport20 means provider consumer sees a launched tuple on edge21 (direct caseedge1).
The plan/binder must account separately for any boundary or CA stages it adds.
usage host_boot_twenty.py INPUT_TOP OUTPUT_TOP OUT_MAP_DELTA
"""
from pathlib import Path
import json,re,sys,argparse
PORTS=[('cfg_v',1),('cfg_target',8),('cfg_addr',12),('cfg_data',256),('desc_v',1),('desc_base',12),('desc_limit',13),('desc_loops',16),('launch_v',1)]
ap=argparse.ArgumentParser();ap.add_argument('input_top');ap.add_argument('output_top');ap.add_argument('out_map');ap.add_argument('--host-boot-hops',type=int,default=20);ap.add_argument('--nw-hops',type=int,default=18);a=ap.parse_args();N=a.host_boot_hops;NW=a.nw_hops;assert 1<=NW<N
top=Path(a.input_top).read_text();assert top.count('\nendmodule')==1;assert 'u_host_boot_hop00' not in top
block=re.search(r'  ot_hnx_fused_host_program #\(.*?\) u_mu_fused_programme \(.*?\n  \);',top,re.S);assert block
text=block[0];offset=320;fields=[]
for pn,w in PORTS:
 offset-=w;old=f'hleaf_NW__a_{pn}[{w-1}:0]';assert f'.{pn}({old})' in text
 text=text.replace(f'.{pn}({old})',f'.{pn}(host_boot_{N:02d}[{offset+w-1}:{offset}])')
 fields.append(dict(port=pn,source=old,lsb=offset,width=w))
assert offset==0
top=top[:block.start()]+text+top[block.end():]
insert=f'\n// C25c exact HOST320 planned transport.{N}core edges, provider consumes at{N+1}.\n'
for i in range(N+1):insert+=f' wire [319:0] host_boot_{i:02d};\n'
insert+=' assign host_boot_00={'+','.join(x['source'] for x in fields)+'};\n'
parts={};hops=[]
for i in range(N):
 name=f'u_host_boot_hop{i:02d}';part='NW_hub' if i<NW else 'root';parts[name]=[part,name]
 insert+=f' ot_hnx_host_boot_hop {name} (.clk(hb_ckgen__pll_stream[0]),.rst_n(hb_ckgen__por_stream[0]),.d(host_boot_{i:02d}),.q(host_boot_{i+1:02d}));\n'
 hops.append(dict(instance=name,partition=part,module='ot_hnx_host_boot_hop',data_width=320,reset_valid_bits=[319,42,0]))
top=top.replace('\nendmodule',insert+'\nendmodule',1);Path(a.output_top).write_text(top)
Path(a.out_map).write_text(json.dumps(dict(parts=parts,hops=hops,fields=fields,transport_cycles=N,producer_to_consumer_edges=N+1,added_boot_cycles=N,added_token_cycles=0,source=f'hleaf_NW output →{N}named planned hops→u_mu_fused_programme',note='Existing regional CA wrapper remains external and its Kmustbeincluded by final binder, not waived'),indent=2)+'\n')
print(f'HOST320{N}hops emitted;{N}bootcyclesadded;{N+1}producer-to-consumeredges;0token-cyclechange')
