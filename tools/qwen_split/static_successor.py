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
    output wire accepted_start,
    output wire candidate_v, output wire [PAW-1:0] candidate_pc,
    output wire [1:0] candidate_unit,
    output wire candidate_available, output wire candidate_end_ok,''',1)
s=s.replace('wire skip = (st == S_RUN) && nx_v && oth && (!odep || opast);','wire skip = (st == S_RUN) && nx_v && oth;')
a=s.index('    wire issue = (ICUT == 0)');b=s.index('    reg fin_seen;',a)
s=s[:a]+'''    wire issue = fixed_issue;
    assign me_go = issue && (fixed_unit == 2'd1);
    assign su_go = issue && (fixed_unit == 2'd2);
    wire fin = fixed_end;
    assign accepted_start=start&&(st==S_IDLE);
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
s=s.replace('    parameter integer PSRAM = 1,', '    parameter integer DENSE_IMAGE=1,\n    parameter integer PSRAM = 1,',1)
s=s.replace('    input wire  clk,','    input wire clk,\n    input wire ck_sched,\n    input wire cp_active,\n    output reg [55:0] cp,\n    output reg layer_context_v,\n    output reg [17:0] native_tok,native_pos,\n    output wire me_image_ready,\n    output reg [75:0] program_obs,',1)
s=s.replace('        .start(q_h_start),','''        .start(q_h_start),
        .fixed_issue(fixed_issue),.fixed_end(fixed_end),.fixed_unit(fixed_unit),.fixed_fault(schedule_fault|program_load_fault),
        .accepted_start(accepted_start),.candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),
        .candidate_available(candidate_available),.candidate_end_ok(candidate_end_ok),''',1)
a=s.index('    wire s_me_ready,');s=s[:a]+'''    wire fixed_issue,fixed_end,schedule_fault,candidate_v,candidate_available,candidate_end_ok,cp_v,accepted_start,schedule_active;\n    wire [55:0] cp_cmd;
    wire [11:0] candidate_pc,fixed_pc;
    wire [1:0] candidate_unit,fixed_unit;
    reg cp_active_q;
    always @(posedge ck_sched or negedge rst_n)
      if(!rst_n)cp_active_q<=0;
      else cp_active_q<=cp_active;
    reg program_load_fault;
    always @(posedge clk or negedge rst_n)
      if(!rst_n)program_load_fault<=0;
      else if(q_pw_v && q_pw_addr<976 && schedule_active)program_load_fault<=1;
    always @(posedge clk or negedge rrv[6])
      if(!rrv[6])begin layer_context_v<=0;native_tok<=0;native_pos<=0;end
      else begin
        layer_context_v<=accepted_start && q_prog_base==0;
        if(accepted_start)begin native_tok<=q_token;native_pos<=q_pos;end
      end
    reg [5:0] schedule_stage;
    always @(posedge ck_sched or negedge rst_n)
      if(!rst_n) schedule_stage<=0;
      else if(q_pw_v && q_pw_addr==1017) schedule_stage<=q_pw_data[17:12];
    // ck_sched and clk are independently entered, compiler phase-matched roots.
    // Candidate is sampled at the real decoder issue phase; there is no wait.
    ot_qwen_fixed_issue_pw #(.DENSE_IMAGE(DENSE_IMAGE),.OWN(1)) u_fixed_issue (
      .clk(ck_sched),.rst_n(rsv[1]),.pw_v(q_pw_v),.pw_addr(q_pw_addr),.pw_data(q_pw_data),
      .start(q_h_start && q_prog_base==0),.stage(schedule_stage),
      .candidate_v(candidate_v),.candidate_pc(q_prog_base+candidate_pc),.candidate_unit(candidate_unit),
      .available(candidate_available),.end_ok(candidate_end_ok),.cp_available(!cp_active_q),
      .issue_v(fixed_issue),.end_v(fixed_end),.cp_cmd(cp_cmd),.cp_v(cp_v),.issue_pc(fixed_pc),.issue_unit(fixed_unit),
      .active(schedule_active),.done(),.cycle(),.image_ready(me_image_ready),.fault(schedule_fault));
'''+s[a:]
# Remove entire tree private shadow-control circuit and dynamic ICG.
a=s.index('    wire local_en, ec;');b=s.index('    wire up_fault_c',a)
s=s[:a]+'''    // Static tree owns no duplicate/shadow instruction controller. Every assigned
    // production edge clocks the real engine; schedule violations fault upstream.
    wire ec=clk;
'''+s[b:]
# Header replaces claims of unchanged MEREG gates.
s='`timescale 1ns/1ps\n// NEW static physical masters; archived closed head/tree remain unchanged.\n// Fixed normal engine cadence; actual decoder/fold state, no shadow controller.\n'+s[s.index('module qfd_tt_ctlm_head_static'):]
# Observe actual accepted identity at the exact same registered stage as cmdGO.
s=s.replace('    output wire [379:0] cmd,','    output wire [379:0] cmd,\n    output reg [15:0] me_observe,',1)
a=s.index('    assign cmd = ')
s=s[:a]+"    always @(posedge clk or negedge rrv[6])\n      if(!rrv[6])begin me_observe<=0;cp<=0;end\n      else begin me_observe<={fixed_issue||cp_v,candidate_v,fixed_unit,q_prog_base+candidate_pc};cp<=cp_cmd;end\n"+s[a:]
# Actual macroconsumed-write observation stays local to head, no2062b pin bus.
s=s.replace('        for (m = 0; m < 2; m = m + 1) begin : g_m', '        wire [1:0] program_raw_ce;wire [11:0] program_raw_row;wire [1023:0]program_raw_data,program_raw_mask;\n        for (m = 0; m < 2; m = m + 1) begin : g_m',1)
s=s.replace('            ot_sram_1r1w_64x512_m1_r2c2 u_pm', '            assign program_raw_ce[m]=w_ce;assign program_raw_row[6*m+:6]=pw_row2;\n            assign program_raw_data[512*m+:512]={8{pw_d2}};assign program_raw_mask[512*m+:512]=w_mask;\n            ot_sram_1r1w_64x512_m1_r2c2 u_pm',1)
s=s.replace('.w_ce_in(w_ce), .w_addr_in(pw_row2), .wd_in({8{pw_d2}}), .w_mask_in(w_mask)', '.w_ce_in(program_raw_ce[m]), .w_addr_in(program_raw_row[6*m+:6]), .wd_in(program_raw_data[512*m+:512]), .w_mask_in(program_raw_mask[512*m+:512])',1)
a=s.index('        if (PMUT != 0) begin : g_pmut')
s=s[:a]+"        wire observed_v,observed_full;wire [9:0]observed_addr;wire [63:0]observed_data;\n        qkd_program_pw_observer u_program_observer(.macro_ce(program_raw_ce),.macro_row(program_raw_row),.macro_data(program_raw_data),.macro_mask(program_raw_mask),.consumed_v(observed_v),.consumed_addr(observed_addr),.consumed_data(observed_data),.full_word(observed_full));\n        always @(posedge clk or negedge rst_n)\n          if(!rst_n)program_obs<=0;else program_obs<={observed_v,observed_full,observed_addr,observed_data};\n"+s[a:]
s=s.replace('        reg [1023:0] prog_mem [0:63];', '        reg [9:0]observed_ff_addr;\n        always @(posedge clk)observed_ff_addr<=q_pw_addr;\n        always @(posedge clk or negedge rst_n)\n          if(!rst_n)program_obs<=0;else program_obs<={|pw_row2,((pw_row2&(pw_row2-1))==0)&&((pw_word2&(pw_word2-1))==0),observed_ff_addr,pw_d2};\n        reg [1023:0] prog_mem [0:63];',1)
# Shadow-only interface pins have no remaining receiver in the static tree.
a=s.index('module qfd_tt_ctlm_tree_static');h,b=s[a:].split('\n);',1)
for n in ['me_mem_ok','h_start','token','pos','prog_base','pw_v','pw_addr','pw_data','x_oacc','x_oidle','x_oprog','x_orows','kv_ok','kv_write_drained']:
 h=re.sub(r'^\s*input wire[^\n]*\b'+n+r',\n','',h,flags=re.M)
s=s[:a]+h+'\n);'+b
# Obsolete VM demand-read handshake has no receiver in real distributed XS.
# Preserve actual engine ready as a diagnostic, remove only the phantom VM AND.
a=s.index('module qfd_tt_ctlm_tree_static');h,b=s[a:].split('\n);',1)
for n in ['x_rdy','x_dv','x_dc','x_dcs','x_dsp']:
 h=re.sub(r'^\s*(?:input|output) wire[^\n]*\b'+n+r',\n','',h,flags=re.M)
b=b.replace('wire up_fault_c, x_rdy_c, fab_fault_c;', 'wire up_fault_c, fab_fault_c;')
b=b.replace('DPW = 35 + NPE', 'DPW = 34 + NPE').replace('land_cnt, x_rdy, tr_fault','land_cnt, tr_fault').replace('land_cnt_c, x_rdy_c, tr_fault_c','land_cnt_c, tr_fault_c')
b=b.replace('ot_qfd_tt_ctl #(', 'ot_qfd_tt_ctl_static #(')
b=b.replace('.x_rdy(x_rdy_c), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp),', '.x_dv(), .x_dc(), .x_dcs(), .x_dsp(),')
s=s[:a]+h+'\n);'+b
(d/'ot_qfd_tt_ctlm_split_static.sv').write_text(s)
print('wrote static decoder/head/tree successors')

# Real tree control successor: remove obsolete VM readiness station, retain
# numeric/tree/scale/tag paths exactly. No substitute ready constant is added.
src=root/'rtl/qwen_sys/redesign_qwen/ot_qfd_tt_split.sv';v=src.read_text()
a=v.index('module ot_qfd_tt_ctl #(');b=v.index('endmodule',a)+len('endmodule');v=v[a:b]
v=v.replace('module ot_qfd_tt_ctl #(', 'module ot_qfd_tt_ctl_static #(',1)
v=re.sub(r'^\s*input\s+wire\s+x_rdy,\n','',v,flags=re.M)
v=v.replace('go_q, fab_q, xr_q','go_q, fab_q').replace('.W(3 + W + NPE)', '.W(2 + W + NPE)')
v=v.replace('go, fab_fault, x_rdy, tr_fault', 'go, fab_fault, tr_fault').replace('go_q, fab_q, xr_q, trf_q', 'go_q, fab_q, trf_q')
v=v.replace('c_ready && xr_q','c_ready')
(d/'ot_qfd_tt_ctl_static.sv').write_text('`timescale 1ns/1ps\n// Static no-VM-demand successor; source SHA256 '+hashlib.sha256(src.read_bytes()).hexdigest()+'\n'+v+'\n')
