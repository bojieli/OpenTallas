#!/usr/bin/env python3
"""Distinct native identity candidate: no modification to legacy helper/controller."""
from pathlib import Path
import hashlib
base=Path('rtl/physical/ot_qfd_seq_su_bi_native8_candidate.sv').read_text()
assert hashlib.sha256(base.encode()).hexdigest()=='d4fcfff07bbeb45ad40a659034172ba348d6fe3763ed45b777fd16cdc46d3db7'
shared=Path('rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv').read_text()
a=shared.index('module ot_qwen_tp_seq_w12_vrl #(')
h=shared[a:shared.index('endmodule',a)+len('endmodule')]
h=h.replace('module ot_qwen_tp_seq_w12_vrl #(', 'module ot_qwen_tp_seq_w12_vrl_native59 #(')
h=h.replace('parameter integer TAGW = 32,','parameter integer TAGW = 59,')
h=h.replace('    input  wire              start,','    input wire [15:0] tag_epoch,\n    input wire [5:0] tag_stage,\n    input wire [58:0] r_tag,\n    input  wire              start,')
h=h.replace('    assign c_tag      = {tok_r, pos_r[7:0], {(8 - DAW){1\'b0}}, seg};', '''    reg [15:0] epoch_r; reg [5:0] stage_r;
    initial if (NW!=18 || TAGW!=59 || DAW!=6 || RB!=3 || N!=8) $error("native59 fixed identity ABI");
    assign c_tag = {epoch_r, stage_r, tok_r, pos_r[12:0], seg};
    wire identity_valid = token <= 18'd151935 && pos <= 18'd8191 && tag_stage <= 6'd37;
    wire return_match = r_tag == c_tag;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin epoch_r<=0;stage_r<=0;end
      else if (start && st==S_IDLE && identity_valid) begin epoch_r<=tag_epoch;stage_r<=tag_stage;end''')
h=h.replace('            case (st)','''            // Reject before receive counters, vector writes or argmax updates.
            if (r_valid && (st != S_COLL || !return_match)) fault <= 1'b1;
            if (CRED!=0 && c_ready && c_cred==CRED && !c_fire) fault <= 1'b1;
            case (st)''')
h=h.replace('S_IDLE: if (start) begin','S_IDLE: if (start && !identity_valid) fault <= 1\'b1; else if (start) begin')
h=h.replace('if (r_valid) begin','if (r_valid && return_match) begin')
h=h.replace('else if (st == S_COLL && r_valid && kind == K_AR)', 'else if (st == S_COLL && r_valid && return_match && kind == K_AR)')
# Cap invalid extra returned credits in distinct helper, with protocol fault above.
h=h.replace('else if (CRED != 0) c_cred <= c_cred - (c_fire ? 8\'d1 : 8\'d0) + (c_ready ? 8\'d1 : 8\'d0);', 'else if (CRED != 0) c_cred <= c_cred - (c_fire ? 8\'d1 : 8\'d0) + ((c_ready && (c_cred < CRED || c_fire)) ? 8\'d1 : 8\'d0);')
assert 'pos_r[7:0]' not in h
Path('rtl/physical/ot_qwen_tp_seq_w12_vrl_native59.sv').write_text('`timescale 1ns/1ps\n// Distinct functional prototype; allocator and transport must supply actual TAG59.\n'+h+'\n')
s=base.replace('module ot_qfd_seq_su_bi_native8_candidate','module ot_qfd_seq_su_bi_native8_tag59_candidate')
s=s.replace('    input  wire [5:0] cb_st_rdy_stage,','    input  wire [5:0] cb_st_rdy_stage,\n    input wire [NW-1:0] cb_st_rdy_tpos,\n    input wire [15:0] coll_epoch,\n    input wire [58:0] r_tag,')
s=s.replace('wire [32-1:0] c_tag','wire [59-1:0] c_tag').replace('wire [32-1:0] b_c_tag','wire [59-1:0] b_c_tag')
s=s.replace('ot_hdc_delay #(.W(32), .D(OS)) u_o_c_tag','ot_hdc_delay #(.W(59), .D(OS)) u_o_c_tag')
marker='    wire [1-1:0] q_r_valid;'
s=s.replace(marker,'''    wire [58:0] q_r_tag; wire [15:0] q_coll_epoch;
    ot_hdc_delay #(.W(59), .D(IS)) u_i_r_tag (.clk(clk), .rst_n(rsv[5]), .d(r_tag), .q(q_r_tag));
    ot_hdc_delay #(.W(16), .D(IS)) u_i_coll_epoch (.clk(clk), .rst_n(rsv[6]), .d(coll_epoch), .q(q_coll_epoch));
'''+marker)
s=s.replace('    wire [5:0] q_stage_in, q_cb_st_rdy_stage; wire q_cb_st_rdy;', '''    wire [NW-1:0] q_cb_st_rdy_tpos;
    ot_hdc_delay #(.W(NW), .D(IS)) u_i_cbtpos (.clk(clk), .rst_n(rsv[6]), .d(cb_st_rdy_tpos), .q(q_cb_st_rdy_tpos));
    reg [15:0] sg_epoch;
    always @(posedge clk or negedge rsv[7]) if (!rsv[7]) sg_epoch<=0; else if(q_h_start) sg_epoch<=q_coll_epoch;
    wire [5:0] q_stage_in, q_cb_st_rdy_stage; wire q_cb_st_rdy;''')
s=s.replace('ot_qfd_stage_gate #(.SW_(6), .NW(NW))','ot_qfd_stage_gate_native_epoch #(.SW_(6), .NW(NW), .NG(1))')
s=s.replace('.st_rdy_stage(q_cb_st_rdy_stage), .go(sg_go)', '.st_rdy_stage(q_cb_st_rdy_stage), .st_rdy_tpos(q_cb_st_rdy_tpos), .go(sg_go)')
s=s.replace('ot_qwen_tp_seq_w12_vrl #(', 'ot_qwen_tp_seq_w12_vrl_native59 #(').replace('.TAGW(32)', '.TAGW(59)')
s=s.replace('.start(sg_go),', '.tag_epoch(sg_epoch), .tag_stage(sg_stage), .r_tag(q_r_tag), .start(sg_go),')
assert 'u_i_r_tag' in s and '.tag_epoch(sg_epoch)' in s
Path('rtl/physical/ot_qfd_seq_su_bi_native8_tag59_candidate.sv').write_text('// Distinct native TAG59 + position-tagged admission prototype; legacy profile unchanged.\n'+s)
