#!/usr/bin/env python3
"""Copy frozen actual NE7b2 host fixture and override only query successor/test."""
import argparse,json,hashlib,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--out',required=True);p.add_argument('--root',default='.');a=p.parse_args();out=Path(a.out);shutil.copytree(a.freeze,out,dirs_exist_ok=False)
source=Path(a.root)/'rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch_partitioned.sv'
compat='''
module ot_hbm_attn_query_prefetch #(parameter integer FILL_LAT=8,MUT=0)(
 input wire clk,rst_n,input wire fetch_v,fetch_epoch,input wire[3:0]fetch_head,
 input wire[2:0]fetch_burst,input wire[15:0]fetch_base_sector,
 output wire[135:0]rq,input wire[2055:0]rr,
 input wire read_v,read_epoch,input wire[3:0]read_head,
 output wire q_v,output wire[8191:0]q_w,output wire fault
);
 ot_hbm_attn_query_prefetch_partitioned #(.FILL_LAT(FILL_LAT),.MUT(MUT))u_partition(
 .clk(clk),.rst_n(rst_n),.fetch_v(fetch_v),.fetch_epoch(fetch_epoch),.fetch_head(fetch_head),
 .fetch_burst(fetch_burst),.fetch_base_sector(fetch_base_sector),.rq(rq),.rr(rr),.read_v(read_v),
 .read_epoch(read_epoch),.read_head(read_head),.q_v(q_v),.q_w(q_w),.field_q_w(),.fault(fault));
endmodule
'''
q=out/'rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch.sv';q.write_text(source.read_text()+compat)
tb=out/'rtl/test/hbm_accel/generic/tb_hbm_attn_QP_host_front.sv';text=tb.read_text();needle='    heads++;'
checks='''    for(integer tile=0;tile<32;tile++)for(integer x=0;x<32;x++)begin
     if(dut.u_front.u_query.u_partition.field_q_w[(tile%4)*2048+((tile%16)/4)*512+x*16+:16]!==word(profile/2,heads,(tile%16)*32+x))
      $fatal(1,"ATT_QPART physical field/SL mismatch tile%0d word%0d",tile,x);
    end
'''
assert needle in text;tb.write_text(text.replace(needle,checks+needle))
runner=out/'tools/hbm_static_attention/run_QP_host_front.sh';header=runner.read_text().split('for profile in')[0]
# Build a separate exact DUT mutant, then native coldboot QK profile0 must fail.
for m in [1,2]:
 d=out/f'qpart_mut{m}';d.mkdir();mut=q.read_text().replace('FILL_LAT=8,MUT=0',f'FILL_LAT=8,MUT={m}');(d/'query.sv').write_text(mut)
 build=header.replace('rtl/hdc/v41x/static/ot_hbm_attn_query_prefetch.sv',f'qpart_mut{m}/query.sv')
 build+='''set +e
"$out/obj/sim" +DIR="$out/vectors" +MUT=0 +PROFILE=0 > "$out/mutant.log" 2>&1
rc=$?
set -e
test "$rc" != 0
grep -qE 'ATT_FRONT query payload mismatch|ATT_QPART physical field/SL mismatch' "$out/mutant.log"
'''
 (d/'run.sh').write_text(build)
files={str(t.relative_to(out)):hashlib.sha256(t.read_bytes()).hexdigest() for t in out.rglob('*') if t.is_file()}
(out/'query_partition_source_manifest.json').write_text(json.dumps({'scope':'actualfrozenNE7b2hostsourcewith64SRAMquerypartition successor, nativefieldchecks and2DUTmutants','files':files},indent=2)+'\n')
print(out)
