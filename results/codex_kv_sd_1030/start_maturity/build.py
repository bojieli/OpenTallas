import json
from pathlib import Path
r=Path(__file__).resolve().parent;ca=json.load(open(r/'bindbase/kv40/eW_sidecar_sd_r6w7_candidate.json'))['count_aligned']
regions=ca['regions'];names={n:'s'+str(i) for i,n in enumerate(regions)}
out=r/'start_maturity';out.mkdir(exist_ok=True)
sv=['`timescale 1ps/1ps','module tb;reg clk=0;always begin #416 clk=1;#417 clk=0;end reg rst=0;integer cyc=0;always @(posedge clk)cyc<=cyc+1;']
for n,v in regions.items():
 nn=names[n];sv+=['wire '+nn+';']
 if v['parent'] is None:sv+=['ot_dp_landing_root #(.SETTLE(64)) u'+nn+'(.clk(clk),.rst_raw_n(rst),.start('+nn+'),.start_d());']
 else:sv+=['ot_dp_landing_origin #(.PAD('+str(v.get('pad',0))+'),.EDGE_FALL('+str(int(v.get('edge_fall',False)))+')) u'+nn+'(.clk(clk),.rst_raw_n(rst),.p_start('+names[v['parent']]+'),.start('+nn+'));']
for n in ['hub_C','sys_SW','sys_SE','io_W2','io_E6']:sv+=['always @(posedge '+names[n]+')$display("START '+n+' cycle=%0d after_release=%0d",cyc,cyc-20);']
sv+=['initial begin repeat(20)@(negedge clk);rst=1;repeat(700)@(negedge clk);$display("COMPLETE");$finish;end endmodule']
(out/'tb.sv').write_text('\n'.join(sv))
