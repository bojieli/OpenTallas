#!/usr/bin/env python3
"""Private source candidate only; no native view or registered-input adoption."""
import argparse
import hashlib
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('--rtl', required=True)
p.add_argument('--parent', required=True)
p.add_argument('--relay', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
text = Path(a.rtl).read_text()
match = re.search(r'module ot_s81sl_vn_b\s*#\(.*?\nendmodule', text, re.S)
assert match
body = match.group()
capture = '''    reg c_v_q; reg [30:0] c_s_q;
    always @(posedge clk or negedge rs_c) if (!rs_c) c_v_q <= 1'b0; else c_v_q <= c_v;
    always @(posedge clk) c_s_q <= c_s;'''
assert body.count(capture) == 1
candidate = body.replace('module ot_s81sl_vn_b #(', 'module ot_s81sl_vn_b_rin #(', 1)
candidate = candidate.replace('input  wire          c_v,', 'input  wire          c_v_q,', 1)
candidate = candidate.replace('input  wire [30:0]   c_s,', 'input  wire [30:0]   c_s_q,', 1)
candidate = candidate.replace('    output reg           p_v,', '    output wire          chain_rs_c, // exact reset feed for the lifted valid FF\n    output reg           p_v,', 1)
candidate = candidate.replace(capture, '    assign chain_rs_c = rs_c;')
assert 'reg c_v_q' not in candidate
assert candidate.count('input  wire          c_v_q,') == 1
(out/'ot_s81sl_vn_b_rin.sv').write_text(candidate+'\n')

parent = Path(a.parent).read_text()
assert parent.count('    ot_s81sl_vn_b #(.HW_STAGE(0), .LA(6), .LM(5)) u_u_vn_u_b (') == 1
assert 'vnb_chain_s_q' not in parent
start = parent.index('    ot_s81sl_vn_b #(.HW_STAGE(0), .LA(6), .LM(5)) u_u_vn_u_b (')
end = parent.index('\n    );', start)+len('\n    );')
old = parent[start:end]
assert old.count('.c_s(w_u_vn_u_a_c_s[30:0])') == 1
assert old.count('.c_v(w_u_vn_u_a_c_v[0])') == 1
new = old.replace('ot_s81sl_vn_b #', 'ot_s81sl_vn_b_rin #', 1)
new = new.replace('.c_s(w_u_vn_u_a_c_s[30:0]),', '.c_s_q(vnb_chain_s_q),')
new = new.replace('.c_v(w_u_vn_u_a_c_v[0]),', '.c_v_q(vnb_chain_v_q),\n        .chain_rs_c(vnb_chain_rs_c),')
lift = '''    // PRIVATE registered-input cut: same actual 32 flops, same edge/reset.
    wire vnb_chain_rs_c;
    reg vnb_chain_v_q; reg [30:0] vnb_chain_s_q;
    always @(posedge clk or negedge vnb_chain_rs_c)
        if (!vnb_chain_rs_c) vnb_chain_v_q <= 1'b0;
        else vnb_chain_v_q <= w_u_vn_u_a_c_v[0];
    always @(posedge clk) vnb_chain_s_q <= w_u_vn_u_a_c_s[30:0];
'''
(out/'parent_candidate.sv').write_text(parent[:start]+lift+new+parent[end:])
(out/'parent_instance_before.sv').write_text(old+'\n')
(out/'parent_instance_after.sv').write_text(lift+new+'\n')

relay = '''    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0];
'''
coupon = '''`timescale 1ns/1ps
module old_cut(input clk,rst_n,c_v,input [30:0] c_s,output c_v_o,output [30:0] c_s_o);
'''+relay+capture+'''
assign c_v_o=c_v_q; assign c_s_o=c_s_q;
endmodule
module new_child(input clk,rst_n,c_v_q,input [30:0] c_s_q, output chain_rs_c,c_v_o,output [30:0] c_s_o);
'''+relay+'''
assign chain_rs_c=rs_c; assign c_v_o=c_v_q; assign c_s_o=c_s_q;
endmodule
module new_composed(input clk,rst_n,c_v,input [30:0] c_s,output c_v_o,output [30:0] c_s_o);
wire chain_rs_c; reg c_v_q; reg [30:0] c_s_q;
`ifdef OT_VNB_RIN_MUT_RESET
wire reset_feed=rst_n;
`else
wire reset_feed=chain_rs_c;
`endif
always @(posedge clk or negedge reset_feed) if (!reset_feed) c_v_q<=1'b0; else c_v_q<=c_v;
always @(posedge clk) c_s_q<=c_s;
`ifdef OT_VNB_RIN_MUT_DATA
wire [30:0] child_data=c_s;
`else
wire [30:0] child_data=c_s_q;
`endif
new_child u_b(clk,rst_n,c_v_q,child_data,chain_rs_c,c_v_o,c_s_o);
endmodule
module tb;
reg clk=0; always #1 clk=~clk;
reg rst_n=1,c_v=0; reg [30:0] c_s=0;
wire ov,nv;wire [30:0] os,ns;
old_cut g(clk,rst_n,c_v,c_s,ov,os);
new_composed d(clk,rst_n,c_v,c_s,nv,ns);
integer cyc=0,checks=0,resets=0,xwords=0;
task check;
begin
checks=checks+1;
`ifdef OT_VNB_RIN_MUT_DATA
if (cyc > 12 && {ov,os} !== {nv,ns}) begin
`else
if ({ov,os} !== {nv,ns}) begin
`endif
$display("CUT DIFF cycle=%0d gold=%h gate=%h",cyc,{ov,os},{nv,ns});$fatal(1);
end
end endtask
always @(posedge clk) begin check;#0.01;check;end
always @(negedge rst_n) begin #0.01;check;end
initial begin
#0.2;rst_n=0;#0.4;rst_n=1;
for(cyc=0;cyc<6000;cyc=cyc+1) begin
@(negedge clk);c_v=$random;c_s={$random};
if(cyc%29==0) begin c_s[cyc%31]=1'bx;xwords=xwords+1;end
if(cyc%97==0) begin #0.2;rst_n=0;resets=resets+1;end
if(cyc%97==2) begin #0.2;rst_n=1;end
end
#1;$display("CUT PASS cycles=%0d checks=%0d resets=%0d xwords=%0d payload_cycles_added=0 valid_cycles_added=0",cyc,checks,resets,xwords);$finish;
end
endmodule
'''
(out/'cut_miter.sv').write_text(coupon)
(out/'ot_rst_relay.sv').write_text(Path(a.relay).read_text())
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
record = dict(status='PRIVATE_NOT_ADOPTED', actual_params=dict(LA=6,LM=5,HW_STAGE=0),
    rtl_sha256=sha(text), native_child_sha256=sha(body), parent_sha256=sha(parent),
    exact_capture_sha256=sha(capture), unchanged_downstream_body=True,
    changed_cut_bits=32, child_input_abi=['c_v_q:1','c_s_q:31'], new_reset_output='chain_rs_c:1',
    flops_moved_child_to_parent=32, total_functional_flop_delta=0, functional_cycle_delta=0,
    old_native_views_reusable=False, physical_status='NOT_RUN',
    wrapper_abi='Inherited native parent only; Types current 594/597 external width mismatch remains held',
    timing_contract='New explicit registered-input ABI requires ROOT review, new native qualification and hierarchical timing; no input-flop waiver')
(out/'impact.json').write_text(json.dumps(record,indent=2)+'\n')
print('PRIVATE_VNB_RIN_SOURCE PASS: actual capture processes moved, parent instance uniquely patched')
