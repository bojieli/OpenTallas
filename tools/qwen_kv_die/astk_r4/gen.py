#!/usr/bin/env python3
"""Same-cycle ASTK Z read-control replicas; canonical masters remain untouched."""
from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
for rel,name in [('rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv','qkd_astk_zn'),('rtl/qwen_sys/kv_plan_leaves_1023/qkd_astk_zn_head_p.sv','qkd_astk_zn_head_p')]:
 s=(a.root/rel).read_text();i=s.index('module '+name);s=s[i:s.index('endmodule',i)+9]
 if name.endswith('head_p'):s=s.replace('parameter [3:0] ZC = 0','parameter [3:0] ZC = 0, parameter integer READ_MUT = 0',1)
 else:s=s.replace('module '+name+' (','module '+name+' #(parameter integer READ_MUT = 0) (',1)
 s=s.replace('module '+name,'module '+name+'_r4',1)
 old='        oa <= slot[0] ? sd[k] : d;'
 assert s.count(old)==1;s=s.replace(old,'')
 anchor='    always @(posedge ck) begin\n        if (put)'
 replica="    // Replicas capture the same input bits on the same edge as zq, with no pipeline stage.\n    genvar rg;\n    generate for (rg=0;rg<4;rg=rg+1) begin : g_read_ctl\n        (* keep = 1 *) reg [4:0] read_ctl_q;\n        always @(posedge ck) read_ctl_q <= zi[6:2];\n        wire [3:0] read_k = read_ctl_q[3:0] ^ ((READ_MUT && rg==0) ? 4'd1 : 4'd0);\n        always @(posedge ck) oa[32*rg +: 32] <= read_ctl_q[4] ? sd[read_k][32*rg +: 32] : d[32*rg +: 32];\n    end endgenerate\n"
 assert s.count(anchor)==1;s=s.replace(anchor,replica+anchor)
 (a.out/(name+'_r4.sv')).write_text(s+'\n')
(a.out/'model.json').write_text(json.dumps(dict(status='CANDIDATE',added_data_cycles=0,added_registers_per_Z=20,reason='four same-edge address/slot replicas limit read-mux fanout',canonical_masters_changed=False),indent=1)+'\n')
