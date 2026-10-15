#!/usr/bin/env python3
"""Reproduce static ME decoder/head/tree successors from archived source.

Generated successor names are separate from the physically closed source.
This generator does not publish or qualify a physical view.
"""
from pathlib import Path
import re,hashlib,json
root=Path(__file__).resolve().parents[2];d=root/'rtl/qwen_sys/static_schedule_20261014';d.mkdir(exist_ok=True)
src=root/'rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm_i.sv';s=src.read_text();a=s.index('module ot_qwen_rom_core_ctrl_x_i #(');b=s.index('endmodule',a)+len('endmodule');s=s[a:b]
s=s.replace('module ot_qwen_rom_core_ctrl_x_i #(','module ot_qwen_rom_core_ctrl_static #(',1)
s=s.replace('    input  wire              start,','''    input  wire              start,
    // Calendar pulses replace INTERNAL issue/fin. Status never gates them.
    input wire fixed_issue, input wire fixed_end,
    input wire [1:0] fixed_unit, input wire fixed_fault,
    output wire candidate_v, output wire [PAW-1:0] candidate_pc,
    output wire [1:0] candidate_unit,
    output wire candidate_available, output wire candidate_end_ok,''',1)
s=s.replace('wire skip = (st == S_RUN) && nx_v && oth && (!odep || opast);','wire skip = (st == S_RUN) && nx_v && oth;')
a=s.index('    wire issue = (ICUT == 0)');b=s.index('    reg fin_seen;',a)
s=s[:a]+'''    wire issue = fixed_issue;
    assign me_go = issue && (fixed_unit == 2'd1);
    assign su_go = issue && (fixed_unit == 2'd2);
    wire fin = fixed_end;
    assign candidate_v=(st==S_RUN)&&nx_v&&(own||d_unit==0);
    assign candidate_pc=pc;
    assign candidate_unit=d_unit;
    assign candidate_available=issue_live;
    assign candidate_end_ok=(st==S_RUN)&&nx_v&&(d_unit==0)&&x_drained&&((OWN==1)||x_ofin);
'''+s[b:]
# Old simulation fatal assumed status gated issue; fixed consumer faults without timeline changes.
s=s.replace('if (rst_n && issue && !issue_live) begin','if (1\'b0) begin')
a=s.index('    generate if (MEREG != 0 && MEREG < 3)');b=s.index('    assign me_clk_en = me_clk_en_w;',a)
s=s[:a]+'''    // Normal production clocks every assigned edge; no supply/status clock gate.
    assign me_en=1'b1;
    assign me_clk_en_w=1'b1;
'''+s[b:]
s=s.replace('if (ME_STALL != 0 || ME_IDLE_GATE != 0) begin : g_me_cg','if (1\'b0) begin : g_me_cg')
s=s.replace('else if (me_fault || su_fault || (|embed_faults) || dyn_tiles_bad_instruction)', 'else if (fixed_fault || me_fault || su_fault || (|embed_faults) || dyn_tiles_bad_instruction)')
p=d/'ot_qwen_rom_core_ctrl_static.sv';p.write_text('`timescale 1ns/1ps\n// Static successor from actual production decoder; numeric/DYN/fold state retained.\n// Source SHA256 '+hashlib.sha256(src.read_bytes()).hexdigest()+'\n'+s+'\n')
# Successor head/tree circuits have explicit distinct names. Archived source untouched.
src2=root/'rtl/physical/ot_qfd_tt_ctlm_split.sv';s=src2.read_text();s=s[:s.index('module ot_qfd_tt_ctlm_split #(')]
s=s.replace('qfd_tt_ctlm_head','qfd_tt_ctlm_head_static').replace('qfd_tt_ctlm_tree','qfd_tt_ctlm_tree_static').replace('ot_qwen_rom_core_ctrl_x_i','ot_qwen_rom_core_ctrl_static')
s=s.replace('    input wire  clk,','    input wire clk,\n    input wire ck_sched,',1)
s=s.replace('        .start(q_h_start),','''        .start(q_h_start),
        .fixed_issue(fixed_issue),.fixed_end(fixed_end),.fixed_unit(fixed_unit),.fixed_fault(schedule_fault),
        .candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),
        .candidate_available(candidate_available),.candidate_end_ok(candidate_end_ok),''',1)
a=s.index('    wire s_me_ready,');s=s[:a]+'''    wire fixed_issue,fixed_end,schedule_fault,candidate_v,candidate_available,candidate_end_ok;
    wire [11:0] candidate_pc,fixed_pc;
    wire [1:0] candidate_unit,fixed_unit;
    reg [5:0] schedule_stage;
    always @(posedge ck_sched or negedge rst_n)
      if(!rst_n) schedule_stage<=0;
      else if(q_pw_v && q_pw_addr==1017) schedule_stage<=q_pw_data[17:12];
    // ck_sched and clk are independently entered, compiler phase-matched roots.
    // Candidate is sampled at the real decoder issue phase; there is no wait.
    ot_qwen_fixed_issue_pw #(.OWN(1)) u_fixed_issue (
      .clk(ck_sched),.rst_n(rsv[1]),.pw_v(q_pw_v),.pw_addr(q_pw_addr),.pw_data(q_pw_data),
      .start(q_h_start && q_prog_base==0),.stage(schedule_stage),
      .candidate_v(candidate_v),.candidate_pc(q_prog_base+candidate_pc),.candidate_unit(candidate_unit),
      .available(candidate_available),.end_ok(candidate_end_ok),
      .issue_v(fixed_issue),.end_v(fixed_end),.issue_pc(fixed_pc),.issue_unit(fixed_unit),
      .active(),.done(),.cycle(),.fault(schedule_fault));
'''+s[a:]
# Remove entire tree private shadow-control circuit and dynamic ICG.
a=s.index('    wire local_en, ec;');b=s.index('    wire up_fault_c',a)
s=s[:a]+'''    // Static tree owns no duplicate/shadow instruction controller. Every assigned
    // production edge clocks the real engine; schedule violations fault upstream.
    wire ec=clk;
'''+s[b:]
# Header replaces claims of unchanged MEREG gates.
s='`timescale 1ns/1ps\n// NEW static physical masters; archived closed head/tree remain unchanged.\n// Fixed normal engine cadence; actual decoder/fold state, no shadow controller.\n'+s[s.index('module qfd_tt_ctlm_head_static'):]
(d/'ot_qfd_tt_ctlm_split_static.sv').write_text(s)
print('wrote static decoder/head/tree successors')
