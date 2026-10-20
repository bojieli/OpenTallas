"""Extract the actual stationary-control/write RTL for an equal-state step proof.

This cut excludes arithmetic, SRAM delays, and the mapped graph. The SAT harness
assumes only equal stationary state at step 2 and proves equality at step 3;
controls, payload, group, bank, gid, and reset stay unrestricted.
"""
import argparse
from pathlib import Path
import hashlib
p=argparse.ArgumentParser(__doc__)
p.add_argument('--source',default='rtl/hdc/v41x/ot_s81svc8_hgrp_s81.sv')
p.add_argument('--out',default='write_cut.v')
options=p.parse_args()
s=Path(options.source).read_text()
a=s.index('            wire [BW-1:0] r_ld_bank;');b=s.index('            // products',a)
ctrl=s[a:b]
a=s.index('                reg [NBANK*16-1:0] ab;',b);b=s.index('                wire [BW-1:0] bk =',a)
write=s[a:b]
ports='''input clk, rst_n, input [7:0] gid,ld_grp, input ld_v,ld_mode,ld_w2v,
input [2:0] ld_bank, input [1023:0] ld_w, input [255:0] ld_wp,
output [10239:0] weights'''
cut='''module write_cut #(parameter WRITE_PREDECODE=0) ('''+ports+''');
localparam HG=4,TD=32,R=2,BW=3,PWORDS=2,NBANK=5;
wire rst_l=rst_n;
wire [7:0] gid_m=gid;
genvar gh,gk;
generate for(gh=0;gh<4;gh=gh+1) begin:g_h
'''+ctrl+'''for(gk=0;gk<TD;gk=gk+1) begin:g_m
'''+write+'''assign weights[(gh*TD+gk)*NBANK*16+:NBANK*16]=ab;
end end endgenerate
endmodule
'''
miter='''module write_miter ('''+ports.replace('output [10239:0] weights','output same_state')+''');
wire[10239:0] a,b;
write_cut #(.WRITE_PREDECODE(0)) gold (.clk(clk),.rst_n(rst_n),.gid(gid),.ld_grp(ld_grp),.ld_v(ld_v),.ld_mode(ld_mode),.ld_w2v(ld_w2v),.ld_bank(ld_bank),.ld_w(ld_w),.ld_wp(ld_wp),.weights(a));
write_cut #(.WRITE_PREDECODE(1)) cand (.clk(clk),.rst_n(rst_n),.gid(gid),.ld_grp(ld_grp),.ld_v(ld_v),.ld_mode(ld_mode),.ld_w2v(ld_w2v),.ld_bank(ld_bank),.ld_w(ld_w),.ld_wp(ld_wp),.weights(b));
assign same_state=a==b;
endmodule
'''
Path(options.out).write_text(cut+miter)
print('CUT_SOURCE_SHA256',hashlib.sha256(s.encode()).hexdigest())
print('CUT_CONTROL_SHA256',hashlib.sha256(ctrl.encode()).hexdigest())
print('CUT_WRITES_SHA256',hashlib.sha256(write.encode()).hexdigest())
