#!/usr/bin/env python3
"""Source-pinned native bulk control DMR; shadow excludes all data storage."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv'
s=src.read_text().split('// A W-bit register synthesis keeps')[0]
s=s.replace('module ot_hbm_accel_bulk_copy #(', '(* keep_hierarchy = "yes", dont_touch = "yes" *)\nmodule ot_hbrom_bulk_control_lane #(\n    parameter integer CTRL_ONLY = 0,')
s=s.replace('    input  wire                  clk,','    input wire permit,\n    output wire [8191:0] control_state,\n    input  wire                  clk,',1)
s=s.replace('ot_hbm_accel_bc_kreg','ot_hbrom_bulk_ctl_kreg')
s=s.replace('    assign d_ready = (q_cnt < DQ);','    assign d_ready = permit && (q_cnt < DQ);')
s=s.replace('wire [NG-1:0] issue_c = act_c & free_c & cred_c & {NG{req_ready}};', 'wire [NG-1:0] issue_c = act_c & free_c & cred_c & {NG{req_ready && permit}};')
s=s.replace('assign req_v = act_c[0] && free_c[0] && cred_c[0];','assign req_v = permit && act_c[0] && free_c[0] && cred_c[0];')
s=s.replace('wire [NT-1:0] take_c = hf_c & (rok_c | {NT{pop_o}});','wire [NT-1:0] take_c = hf_c & (rok_c | {NT{pop_o}}) & {NT{permit}};')
s=s.replace('wire [NG-1:0] load_c = ~act_c & {NG{qne}};', 'wire [NG-1:0] load_c = ~act_c & {NG{qne && permit}};')
s=s.replace('assign s_valid = head_full;','assign s_valid = permit && head_full;').replace('assign s_valid = oq_n != 0;','assign s_valid = permit && oq_n != 0;')
# Invalid input tags carry no ownership; do not clock them into protected state.
s=s.replace('rsp_q <= rsp_v; rsp_tag_q <= rsp_tag;', 'rsp_q <= rsp_v; if (rsp_v) rsp_tag_q <= rsp_tag;')
s=s.replace('rsp_qq <= rsp_q; rsp_tag_qq <= rsp_tag_q;', 'rsp_qq <= rsp_q; if (rsp_q) rsp_tag_qq <= rsp_tag_q;')
s=s.replace('set_lo[k] <= (rsp_tag[LO-1:0] == k);', 'set_lo[k] <= rsp_v && (rsp_tag[LO-1:0] == k);')
# Stored descriptor slots have defined reset state so unused entries can be checked.
s=s.replace('    always @(posedge clk) begin\n        if (d_valid && d_ready) begin q_base', '''    integer qi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (qi=0;qi<DQ;qi=qi+1) begin
                q_base[qi]<=0; q_len[qi]<=0; q_base_hinc[qi]<=0; q_len_hdec[qi]<=0;
            end
            q_nz<=0; q_one<=0;
        end else if (d_valid && d_ready) begin q_base''')
# Data memory and output data flops exist only in primary, while ALL control
# registers (including parity, output WE domain copies) exist independently.
s=s.replace('        reg [LINE_BITS-1:0] ring [0:DEPTH-1];','        if (!CTRL_ONLY) begin : g_payload\n        reg [LINE_BITS-1:0] ring [0:DEPTH-1];')
s=s.replace('        assign idle = !act && (q_cnt == 0) && (outstanding == 0) && !rsp_q && (used == 0);', '''        end else begin : g_no_payload
            assign s_valid = permit && head_full;
            assign s_data = 0;
            assign pop_o = s_valid && s_ready;
            assign rok_c = {NT{1'b0}};
        end
        assign detail_state = 0;
        assign idle = !act && (q_cnt == 0) && (outstanding == 0) && !rsp_q && (used == 0);''',1)
s=s.replace('        reg [NB*256-1:0] oq0, oq1, oq2;', '        wire [NB*256-1:0] oq0, oq1, oq2;')
s=s.replace('                ot_sram_1r1w_1024x256_m2_r2c2 u_ring (', '                if (!CTRL_ONLY) begin : g_payload\n                ot_sram_1r1w_1024x256_m2_r2c2 u_ring (')
s=s.replace('                    ot_sram_1r1w_512x256_m1_r2c2 u_ring (', '                    if (!CTRL_ONLY) begin : g_payload\n                    ot_sram_1r1w_512x256_m1_r2c2 u_ring (')
# close macro guards at exact ports
# Close each payload guard by matching the complete surrounding macro block.
import re
s=re.sub(r"(ot_sram_1r1w_1024x256_m2_r2c2 u_ring \(.*?cr_sel\(16'd0\)\);)", r"\1\n                end else assign rd[0][256*mb +: 256] = 0;", s, flags=re.S)
s=re.sub(r"(ot_sram_1r1w_512x256_m1_r2c2 u_ring \(.*?cr_sel\(16'd0\)\);)", r"\1\n                    end else assign rd[gg][256*mb +: 256] = 0;", s, flags=re.S)
# Source oq declarations replaced by wires; per64 domains drive payload flops.
s=s.replace('''            always @(posedge clk) begin
                if (we0[mb]) oq0[64*mb +: 64] <= qin[64*mb +: 64];
                if (we1[mb]) oq1[64*mb +: 64] <= qin[64*mb +: 64];
                if (we2[mb]) oq2[64*mb +: 64] <= qin[64*mb +: 64];
            end''','''            if (!CTRL_ONLY) begin : g_payload
                reg [63:0] q0, q1, q2;
                always @(posedge clk) begin
                    if (permit && we0[mb]) q0 <= qin[64*mb +: 64];
                    if (permit && we1[mb]) q1 <= qin[64*mb +: 64];
                    if (permit && we2[mb]) q2 <= qin[64*mb +: 64];
                end
                assign oq0[64*mb+:64]=q0; assign oq1[64*mb+:64]=q1; assign oq2[64*mb+:64]=q2;
            end else begin
                assign oq0[64*mb+:64]=0; assign oq1[64*mb+:64]=0; assign oq2[64*mb+:64]=0;
            end''')
s=s.replace('        genvar mb, gg;', '''        genvar mb, gg;
        wire [NW:0] parity_state;
        assign detail_state = {parity_state, we0,we1,we2,oq_n,res,oq_wp,oq_rp,rd_v,rd_v2};''')
s=s.replace('        if (RING_MACRO == 0) begin : g_m1', '        if (RING_MACRO == 0) begin : g_m1\n            assign parity_state = 0;')
s=s.replace('            reg par1;', '            reg par1;\n            assign parity_state = {par1,par2};')
# Export all control storage. Detail includes queue enables/parity registers.
anchor='    integer k, kf;'
s=s.replace(anchor,'''    wire [2047:0] detail_state;
    wire [DQ*(2*AW+32)-1:0] descriptor_state;
    for (genvar z=0;z<DQ;z=z+1) begin : g_desc_image
        assign descriptor_state[z*(2*AW+32)+:(2*AW+32)] = {q_base[z],q_len[z],q_base_hinc[z],q_len_hdec[z]};
    end
    wire [NBK*(TW-BB)-1:0] bank_pointer_state;
    for (genvar z=0;z<NBK;z=z+1) begin : g_bank_image
        assign bank_pointer_state[z*(TW-BB)+:(TW-BB)] = bank_ptr[z];
    end
    assign control_state = {detail_state, descriptor_state, bank_pointer_state,
        q_cnt,q_wp,q_rp,a_addr,a_left,last_q,full,alloc_p,cons_p,used,outstanding,
        act_c,free_c,cred_c,hf_c,rok_c,addr_hi_inc,left_hi_dec,q_nz,q_one,
        next_full,next_slot,next2_slot,rsp_q,rsp_tag_q,set_hi,clr_hi,set_lo,clr_lo,
        bank_full,rsp_qq,rsp_tag_qq,hi_lo1,hi_hi1,load_d1};
    integer k, kf;''')
# Original off branch unsupported inside protected lanes: controller always ENABLE1.
s=s.replace('    generate if (ENABLE == 0) begin : g_original','    generate if (ENABLE == 0) begin : g_original\n        assign control_state = 0;')
wrapper='''`timescale 1ns/1ps
// Default-off dual independent native controls; one payload SRAM/queue path.
// Global state comparison is deliberately explicit, pending contextual SS/FF.
// Any mismatch blocks all native side effects immediately and latches fault.
module ot_hbrom_bulk_copy_control_protected #(
 parameter integer PROTECT=0, ENABLE=0, LINE_BITS=1024, DEPTH=1024,
 MAX_OUT=512, AW=32, DQ=4, SRAM_RING=0, RING_MACRO=0
)(input wire clk,rst_n,input wire d_valid,output wire d_ready,
 input wire[AW-1:0] d_base,input wire[23:0] d_lines,
 output wire req_v,input wire req_ready,output wire[AW-1:0] req_addr,
 output wire[$clog2(DEPTH)-1:0] req_tag,input wire rsp_v,
 input wire[$clog2(DEPTH)-1:0] rsp_tag,input wire[LINE_BITS-1:0] rsp_data,
 output wire s_valid,input wire s_ready,output wire[LINE_BITS-1:0] s_data,
 output wire[$clog2(MAX_OUT+1)-1:0] outstanding,output wire idle,
 output wire control_fault);
 generate if(!PROTECT) begin : g_original
  assign control_fault=0;
  ot_hbm_accel_bulk_copy #(.ENABLE(ENABLE),.LINE_BITS(LINE_BITS),.DEPTH(DEPTH),
   .MAX_OUT(MAX_OUT),.AW(AW),.DQ(DQ),.SRAM_RING(SRAM_RING),.RING_MACRO(RING_MACRO)) original
   (.clk(clk),.rst_n(rst_n),.d_valid(d_valid),.d_ready(d_ready),.d_base(d_base),.d_lines(d_lines),
    .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
    .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.s_valid(s_valid),.s_ready(s_ready),
    .s_data(s_data),.outstanding(outstanding),.idle(idle));
 end else begin : g_protected
  wire[8191:0] image0,image1;
  (* keep="true",dont_touch="yes" *) reg fault0,fault1;
  wire mismatch=|(image0^image1);
  wire permit=rst_n && !mismatch && !fault0 && !fault1;
  assign control_fault=mismatch || fault0 || fault1;
  always @(posedge clk or negedge rst_n)
   if(!rst_n) begin fault0<=0;fault1<=0;end
   else begin fault0<=fault0||mismatch;fault1<=fault1||mismatch;end
  ot_hbrom_bulk_control_lane #(.CTRL_ONLY(0),.ENABLE(1),.LINE_BITS(LINE_BITS),.DEPTH(DEPTH),
   .MAX_OUT(MAX_OUT),.AW(AW),.DQ(DQ),.SRAM_RING(SRAM_RING),.RING_MACRO(RING_MACRO)) primary
   (.permit(permit),.control_state(image0),.clk(clk),.rst_n(rst_n),.d_valid(d_valid&&permit),
    .d_ready(d_ready),.d_base(d_base),.d_lines(d_lines),.req_v(req_v),.req_ready(req_ready&&permit),
    .req_addr(req_addr),.req_tag(req_tag),.rsp_v(rsp_v&&permit),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
    .s_valid(s_valid),.s_ready(s_ready&&permit),.s_data(s_data),.outstanding(outstanding),.idle(idle));
  ot_hbrom_bulk_control_lane #(.CTRL_ONLY(1),.ENABLE(1),.LINE_BITS(LINE_BITS),.DEPTH(DEPTH),
   .MAX_OUT(MAX_OUT),.AW(AW),.DQ(DQ),.SRAM_RING(SRAM_RING),.RING_MACRO(RING_MACRO)) shadow
   (.permit(permit),.control_state(image1),.clk(clk),.rst_n(rst_n),.d_valid(d_valid&&permit),
    .d_ready(),.d_base(d_base),.d_lines(d_lines),.req_v(),.req_ready(req_ready&&permit),
    .req_addr(),.req_tag(),.rsp_v(rsp_v&&permit),.rsp_tag(rsp_tag),.rsp_data({LINE_BITS{1'b0}}),
    .s_valid(),.s_ready(s_ready&&permit),.s_data(),.outstanding(),.idle());
 end endgenerate
endmodule
'''
kreg=src.read_text().split('// A W-bit register synthesis keeps')[1]
kreg='// A W-bit register synthesis keeps'+kreg.replace('ot_hbm_accel_bc_kreg','ot_hbrom_bulk_ctl_kreg')
out=ROOT/'rtl/hbrom/ot_hbrom_bulk_copy_control_protected.sv'
out.write_text(wrapper+'\n'+s+'\n'+kreg)
print(out)
