#!/usr/bin/env python3
"""KV-PC 2026-10-19 SAFE redesign: generate the opt-in clone chain of the PC path that uses the SRAM-backed storage of
rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_1019.sv (front, return ring, tag queue, embedding CDC FIFOs) and the
replicated scheduler reset / strap-release roots.  Every clone is the ORIGINAL module text (read from its committed
file) with its name suffixed and an explicit list of exact substitutions; each substitution must match exactly once, so
a drift of an original breaks the generator instead of silently diverging.  The originals stay unchanged.

    python3 tools/qwen_kv_die/kv_pc_sram_gen.py [--check]      (--check: exit 1 if the committed output differs)

Chain (tile u_pc):  qkd_kvpc_s_fan_nc_b -> qkd_kvpc_s_emb_nc_b -> qkd_kvpc_s_path_nc -> {qkd_kvpc_s_ctrl ->
{qkd_kvpc_s_sched, qkd_kvpc_s_cdc_child -> ot_qkd_static_emb_cdc_kvpc_s}, qkd_kvpc_s_front, qkd_kvpc_s_return}.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = 'rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_clones_1019.sv'
FAN = 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv'
PATH = 'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv'
CTRL = 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv'
CORE = 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv'
NHGO = 128      # u_ctl strap-release (hgo) copies: 1994 async-reset loads -> <= 32 each
NHR = 16       # sched hclk reset capture (hr_q) copies: 414 loads -> <= 32 each

TQ_DECL = '''    reg  [33:0] tq [0:TQD-1];'''
TQ_DECL_NEW = '''    // KV-PC SAFE: tq (64 x 34) is two native 32 x 64 banks (qkd_kvpc_s_tq): h0 = tq[tr], h1 = tq[tr + 1] (== tq[tr1])
    wire [33:0] tq_h0, tq_h1;'''
TQ_WRITE = '''        if (rd_kv) tq[tw[TQA-1:0]] <= {epoch_q,brow[col_bank], rj};
'''
TQ_INST = '''    // tr(t), presented at t-1: tr is cleared asynchronously by h_rn, which only changes on hclk edges (hr_q capture of
    // hrst); next(tr) = 0 if the scheduler is in reset at this edge or enters it at this edge, else tr + kv_v.
`ifdef OT_KVPC_MUT_TQ_NEXT
    wire [TQA-1:0] tq_a0_next = tr[TQA-1:0];                     // bench mutant: read issued at tr (no advance)
`else
    wire [TQA-1:0] tq_a0_next = (h_rn && hrst) ? (kv_v ? tr[TQA-1:0] + 1'b1 : tr[TQA-1:0]) : {TQA{1'b0}};
`endif
    qkd_kvpc_s_tq #(.TQD(TQD)) u_tq (.clk(hclk), .we(rd_kv), .wa(tw[TQA-1:0]), .wd({epoch_q,brow[col_bank], rj}),
        .a0_next(tq_a0_next), .h0(tq_h0), .h1(tq_h1));
'''

SCHED = [
    # hclk reset capture: NHR kept identical copies (split by physical/common_flow/ot_rst_copies, OT_RST_COPIES_MAX)
    ('''    (* keep *) reg hr_q;
    always @(posedge hclk) hr_q <= hrst;
    wire h_rn = hr_q;''',
     f'''    // KV-PC SAFE: {NHR} kept identical capture copies (family ot_rst_split; ot_rst_copies.tcl spreads the loads)
    (* keep, ot_rst_split *) reg [{NHR - 1}:0] hr_qv;
    always @(posedge hclk) hr_qv <= {{{NHR}{{hrst}}}};
    wire h_rn = hr_qv[0];'''),
    ('''    reg       hgo;''',
     f'''    // KV-PC SAFE: the strap release hgo (u_ctl reset, 1994 loads) as {NHGO} kept identical copies (ot_rst_split)
    (* keep, ot_rst_split *) reg [{NHGO - 1}:0] hgo_qv;
    wire      hgo = hgo_qv[0];'''),
    ('''        if (!h_rn) begin dcnt <= 7'd0; hgo <= 1'b0; end
        else if (dcnt == dsel) hgo <= 1'b1;''',
     f'''        if (!h_rn) begin dcnt <= 7'd0; hgo_qv <= {{{NHGO}{{1'b0}}}}; end
        else if (dcnt == dsel) hgo_qv <= {{{NHGO}{{1'b1}}}};'''),
    (TQ_DECL, TQ_DECL_NEW),
    # KV-PC3 sr6 (gate pc_h_sr3 164813: SS setup -437.5 ps at ot_prs_00560_ff/D): the S-face fault-chain input fi fed the
    # sticky OR of fo, an N-face output register that pin_reg_split clones at the pin -> one cycle from the S face
    # through 5 gates and ~300 um to the N face (an in -> out-register cone).  fi now lands in a face register first
    # (flop-direct pin, no reset: the upstream fo is reset), +1 hclk edge on the fault-only chain per PC tile.
    ("""    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo <= 1'b0;
        else fo <= fo | fi | ctl_fault""",
     """    // KV-PC3 sr6: fault-chain input landing register (pin register at the S face; +1 edge, fault-only, priced)
    reg fi_q;
`ifdef OT_KVPC_LAND_MUT
    always @(*) fi_q = fi;                                         // bench mutant: landing bypassed (old in -> fo cone)
`else
    always @(posedge hclk) fi_q <= fi;
`endif
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) fo <= 1'b0;
        else fo <= fo | fi_q | ctl_fault"""),
    ('''    wire [33:0] t_head  = tq[tr[TQA-1:0]];''', '''    wire [33:0] t_head  = tq_h0;'''),
    (TQ_WRITE, ''),
    ('''    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin tw <= '0; tr <= '0; f_tag <= 1'b0; end''',
     TQ_INST + '''    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin tw <= '0; tr <= '0; f_tag <= 1'b0; end'''),
    ('''    wire [33:0]  h_c0    = tq[tr[TQA-1:0]];
    wire [33:0]  h_c1    = tq[tr1];''', '''    wire [33:0]  h_c0    = tq_h0;
    wire [33:0]  h_c1    = tq_h1;'''),
]

CHILD = 'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_children.sv'
ECC = 'rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv'
CAL = 'rtl/qwen_sys/static_kv_20261014/qkd_controller_hbm_calendar.sv'
UCTL = 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv'
TIM = 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv'
CHAIN = 'rtl/qwen_sys/static_embedding_20261014/qkd_kv_pc_chain_station_b.sv'
ESM = 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv'
RHOP = 'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_hop.sv'
RHEAD = 'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_head.sv'

# KV-PC SAFE item 3 (terminal census 1248d0585 + kv-pc-contract drivers.json: 188 FF roots > 32 loads).  Copies per
# root ~ loads / 24 (<= 32 a copy after the split, margin for mapping).  (reg, width, copies[, (port old, port new)])
CHAIN_WES = [
    ("    output reg  [287:0]  wes,", "    output wire [287:0]  wes,"),
    ("    (* keep *) reg rs_q;\n",
     "    (* keep *) reg rs_q;\n"
     "    // KV-PC SAFE: wes[0] (the es valid, 575 loads in the controller CDC intake) as 24 kept copies; wes[287:1] plain\n"
     "    reg [287:1] wes_d;\n"
     "    (* keep, ot_rst_split *) reg [23:0] wes0__qv;\n"
     "    assign wes = {wes_d, wes0__qv[0]};\n"),
    ("        if (h0 | h1) wes[287:1] <=", "        if (h0 | h1) wes_d[287:1] <="),
    ("        if (!rs_q) begin wes[0] <= 1'b0; hit_a <= 1'b0; x_a <= 1'b0; end\n"
     "        else begin wes[0] <= h0 | h1; hit_a <= h0 | h1; x_a <= x0 | x1; end",
     "        if (!rs_q) begin wes0__qv <= 24'd0; hit_a <= 1'b0; x_a <= 1'b0; end\n"
     "        else begin wes0__qv <= {24{h0 | h1}}; hit_a <= h0 | h1; x_a <= x0 | x1; end"),
    ("            always @(*) begin hit = hit_a; ctx_id = ctx_a;",
     "            reg hit__nolag;   // KV-PC SAFE clone: hit is a kept copy family (the lag-free MUT 5 is not built)\n"
     "            always @(*) begin hit__nolag = hit_a; ctx_id = ctx_a;"),
]
ESM_HQ = [
    ("    reg [287:0] hq;\n"
     "    always @(posedge ck) hq[287:1] <= hes[287:1];\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) hq[0] <= 1'b0; else hq[0] <= hes[0];",
     "    // KV-PC SAFE: hq[0] (the slice word valid, 310 loads) as 13 kept copies; hq[287:1] plain\n"
     "    reg [287:1] hq_d;\n"
     "    (* keep, ot_rst_split *) reg [12:0] hq0__qv;\n"
     "    wire [287:0] hq = {hq_d, hq0__qv[0]};\n"
     "    always @(posedge ck) hq_d[287:1] <= hes[287:1];\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) hq0__qv <= 13'd0; else hq0__qv <= {13{hes[0]}};"),
]
OBS_PO = [
    ("    (* keep *) reg [327:0] po_q;",
     "    // KV-PC SAFE: po_q[34:30] (col_bank: the observer's bank-indexed open-row reads, 641..43 loads) as 27 kept copies\n"
     "    (* keep *) reg [327:0] po_q_d;\n"
     "    (* keep, ot_rst_split = 5 *) reg [134:0] pob__qv;\n"
     "    wire [327:0] po_q = {po_q_d[327:35], pob__qv[4:0], po_q_d[29:0]};"),
    ("if(!h_rn)begin po_q<=0;sc_q<=0;esc_q<=0;end else begin po_q<=po;sc_q<=static_column;",
     "if(!h_rn)begin po_q_d<=0;pob__qv<=135'd0;sc_q<=0;esc_q<=0;end else begin po_q_d<=po;pob__qv<={27{po[34:30]}};sc_q<=static_column;"),
]
PORT_Y1 = [
    ("            for (i = 0; i < 4; i = i + 1) y1[i*8 +: 8] <= syn64(r_d[i*72 +: 72]);",
     "            y1 <= {syn64(r_d[3*72 +: 72]), syn64(r_d[2*72 +: 72]), syn64(r_d[1*72 +: 72]), syn64(r_d[0*72 +: 72])};"),
]

# KV-PC5-A 10-20: scheduler native32 restructure of ot_qkd_static_kv_timing (inserted into kv_pc_sram_gen.py)
NSG, NSW, NRD, NWR, NDA, NEV = 18, 8, 19, 14, 17, 22
NHG = 7          # head groups: sb/sc/swe, srw lo, srw hi, sb_oh 4 x 8
CTX_SL = 14
NCS = (347 + CTX_SL - 1) // CTX_SL     # 25 context slices

def ev(k, f):
    """registered row-command event copy k, field f: act 0, pre 1, pall 2, rfa 3, rfp 4, actS 5"""
    return f'ev_qv[{k * 6 + {"act": 0, "pre": 1, "pall": 2, "rfa": 3, "rfp": 4, "acts": 5}[f]}]'

LEAF = '''// KV-PC5 10-20 (native32, owner pre-gate census rule): a kept two-input AND leaf.  A deep single-cycle decision
// (s_go / rd_ok / wr_ok / desc_acc / s_sw of the PC scheduler) is built as N such leaves on the same two operands, so each
// copy drives one group of loads (<= 32 mapped pins): the last decision gate is replicated as logic, not buffered.
// Fixed width, no parameters (a parameterised keep_hierarchy module is renamed by Yosys and loses the attribute).
(* keep_hierarchy = "yes" *) module ot_kvpc5_and2 (input wire a, input wire b, output wire y);
    assign y = a & b;
endmodule
'''

def leaves(vec, n, a, b):
    return (f'    for (genvar q = 0; q < {n}; q = q + 1) begin : g_{vec}\n'
            f'      ot_kvpc5_and2 u_l (.a({a}), .b({b}), .y({vec}[q]));\n'
            f'    end\n')

def ev_bits(k):
    return '{' + ', '.join(['S && slot_next && r_v && r_s && r_op == ACT', 'slot_next && r_v && r_op == REFPB',
                            'slot_next && r_v && r_op == REFAB', 'slot_next && r_v && r_op == PREALL',
                            'slot_next && r_v && r_op == PRE', 'slot_next && r_v && r_op == ACT']) + '}'

EV_BLOCK = f'''    // KV-PC5: registered row-command event copies (exact: c_v <= slot_next && r_v, c_op <= r_op, c_s <= S && .. r_s),
    // {NEV} kept groups x {{actS, rfp, rfa, pall, pre, act}}; X(t) == (c_v && c_op == X)(t).  Group k serves one load group:
    // 0-7 bank groups (4 banks), 8 bank-group timers, 9/10 open lo/hi, 11/12 stale lo/hi, 13 rrds/refreshed, 14/15
    // open_nx lo/hi, 16/17 ready_stale_next lo/hi, 18 ready_blk_next, 19 wopen, 20 REFpb blk, 21 REFpb counters.
    (* keep *) reg [{NEV * 6 - 1}:0] ev_qv;
    // the six field values as two kept leaf copies (each feeds half of the groups)
    wire [11:0] ev_d;
    wire ev_sv = slot_next && r_v;
    for (genvar q = 0; q < 2; q = q + 1) begin : g_evd
      ot_kvpc5_and2 u_a (.a(ev_sv), .b(r_op == ACT), .y(ev_d[q*6 + 0]));
      ot_kvpc5_and2 u_p (.a(ev_sv), .b(r_op == PRE), .y(ev_d[q*6 + 1]));
      ot_kvpc5_and2 u_l (.a(ev_sv), .b(r_op == PREALL), .y(ev_d[q*6 + 2]));
      ot_kvpc5_and2 u_f (.a(ev_sv), .b(r_op == REFAB), .y(ev_d[q*6 + 3]));
      ot_kvpc5_and2 u_r (.a(ev_sv), .b(r_op == REFPB), .y(ev_d[q*6 + 4]));
      ot_kvpc5_and2 u_s (.a(ev_sv), .b(S && r_s && r_op == ACT), .y(ev_d[q*6 + 5]));
    end
    always @(posedge clk or negedge rst_n)
      if (!rst_n) ev_qv <= {{{NEV * 6}{{1'b0}}}};
      else ev_qv <= {{{{{NEV - NEV // 2}{{ev_d[11:6]}}}}, {{{NEV // 2}{{ev_d[5:0]}}}}}};
    // KV-PC5: ref_c == LEAD as registered copies (ref_c <= ref_n at every non-reset edge): 0 blk/rb, 1 ready_blk_next
    (* keep *) reg [2:0] lead_qv;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) lead_qv <= {{3{{RW'(RPH + PERIOD) == RW'(LEAD)}}}}; else lead_qv <= {{3{{ref_n == RW'(LEAD)}}}};
    wire [16:0] desc_acc_c;
    wire [31:0] open_nx;
    assign open_nx[15:0] = (row_gnt && {ev(14, "act")}) ? (open[15:0] | c_oh[15:0]) : (row_gnt && {ev(14, "pre")}) ? (open[15:0] & ~c_oh[15:0]) :
                           (row_gnt && {ev(14, "pall")}) ? 16'b0 : open[15:0];
    assign open_nx[31:16] = (row_gnt && {ev(15, "act")}) ? (open[31:16] | c_oh[31:16]) : (row_gnt && {ev(15, "pre")}) ? (open[31:16] & ~c_oh[31:16]) :
                            (row_gnt && {ev(15, "pall")}) ? 16'b0 : open[31:16];'''

def half(lo, k, da):
    hi = lo + 15
    s = f'[{hi}:{lo}]'
    return (f'desc_acc_c[{da}] ? open_nx{s} : (row_gnt && {ev(k, "pall")}) ? 16\'b0 : (row_gnt && {ev(k, "pre")}) ? '
            f'stale{s} & ~c_oh{s} : (row_gnt && {ev(k, "acts")}) ? stale{s} | c_oh{s} : stale{s}')

def bank_ix(f):
    return f'ev_qv[(b >> 2) * 6 + {f}]'

SQ_DECL = f'''    reg [SQW:0] sq_n; reg [SQW-1:0] sq_rp;
    // KV-PC5 (native32): the static queue keeps its entries in flat per-entry registers written UNGATED into the free
    // slot (rp + n, none when full: a write to a non-live slot is never read), and every wide read / load uses a
    // registered one-hot select computed from the next-state queue pointers (lookahead, no added edge), as kept copies
    // per <= {CTX_SL}-bit slice.  col_context = entry sq_rp ALWAYS: non-empty it is the head (no write touches a live
    // entry); empty, slot sq_rp is the free slot, written with s_context at every edge, so it holds s_context of the
    // previous edge = the old shead_context (which loaded s_context on every empty edge).  The context writes stop in
    // reset and the select freezes there (the old head held through reset; observed in the strap-release window).
    reg [4*347-1:0] sq_ctx_f;
    reg [19:0] sq_bk_f, sq_cl_f; reg [75:0] sq_rw_f; reg [3:0] sq_we_f; reg [127:0] sq_oh_f;
    (* keep *) reg [{NCS * 4 - 1}:0] sq_csel_qv;   // per context slice: head one-hot
    (* keep *) reg [{NCS * 4 - 1}:0] sq_cws_qv;    // per context slice: write slot one-hot
    (* keep *) reg [19:0] sq_sws_qv;              // write slot one-hot: bank/col/we, row lo, row hi, oh lo, oh hi
    (* keep *) reg [{NHG * 6 - 1}:0] sq_hf_qv;   // head groups {{n >= 2, n == 0, onehot(rp + 1)}}: sb/sc/swe, srw lo/hi, sb_oh 4 x 8
    (* keep *) reg [7:0] swe_bk;                 // KV-PC5: swe for the 8 bank groups (identical to swe)'''

SQ_LOOK = f'''    // ---- KV-PC5 static queue lookahead (next-state pointers -> registered one-hot copies) ----------------------------
    wire sq_push = s_v && s_r;
    wire [SQW:0] sq_n_nx = sq_n + (sq_push ? 1'b1 : 1'b0) - (s_go_c[17] ? 1'b1 : 1'b0);
    wire [SQW-1:0] sq_rp_nx = s_go_c[17] ? SQW'(sq_rp + 1'b1) : sq_rp;
    wire [3:0] sq_rpoh_nx = 4'b1 << sq_rp_nx;
    wire [3:0] sq_r1oh_nx = 4'b1 << SQW'(sq_rp_nx + 1'b1);
    wire [3:0] sq_wsoh_nx = (sq_n_nx != (SQW+1)'(SQD)) ? (4'b1 << SQW'(sq_rp_nx + sq_n_nx[SQW-1:0])) : 4'b0;
    wire sq_eq0_nx = sq_n_nx == 0; wire sq_ge2_nx = sq_n_nx >= 2;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin sq_sws_qv <= {{5{{4'b0001}}}}; sq_hf_qv <= {{{NHG}{{6'b010010}}}}; end
      else begin sq_sws_qv <= {{5{{sq_wsoh_nx}}}}; sq_hf_qv <= {{{NHG}{{sq_ge2_nx, sq_eq0_nx, sq_r1oh_nx}}}}; end
    // the context select / write slot / bypass FREEZE while the scheduler is in reset (the old shead_context held its
    // pre-reset value through reset; at the first edge after release they load f(n = 0, rp = 0) like the old chg).
    // Not reset: their only consumers are the context entries and col_context (no initial value is observed before
    // the first post-reset edge loads them: KVPC sched bench strap-release window).
    always @(posedge clk) begin
      if (rst_n) sq_csel_qv <= {{{NCS}{{sq_rpoh_nx}}}};
      sq_cws_qv <= {{{NCS}{{sq_wsoh_nx}}}};
    end
    wire [31:0] sq_s_oh = 32'b1 << s_bank;
    always @(posedge clk) begin
      for (integer e = 0; e < 4; e = e + 1) begin
        for (integer x = 0; x < 347; x = x + 1) if (sq_cws_qv[(x / {CTX_SL}) * 4 + e] && rst_n) sq_ctx_f[e * 347 + x] <= s_context[x];
        if (sq_sws_qv[e]) begin sq_bk_f[e*5 +: 5] <= s_bank; sq_cl_f[e*5 +: 5] <= s_col; sq_we_f[e] <= s_we; end
        if (sq_sws_qv[4 + e]) sq_rw_f[e*19 +: 10] <= s_row[9:0];
        if (sq_sws_qv[8 + e]) sq_rw_f[e*19 + 10 +: 9] <= s_row[18:10];
        if (sq_sws_qv[12 + e]) sq_oh_f[e*32 +: 16] <= sq_s_oh[15:0];
        if (sq_sws_qv[16 + e]) sq_oh_f[e*32 + 16 +: 16] <= sq_s_oh[31:16];
      end
    end
    for (genvar x = 0; x < 347; x = x + 1) begin : g_sqcr
      localparam integer Q = x / {CTX_SL};
      assign col_context[x] = |(sq_csel_qv[Q*4 +: 4] & {{sq_ctx_f[3*347 + x], sq_ctx_f[2*347 + x], sq_ctx_f[347 + x], sq_ctx_f[x]}});
    end
    // the entry after the head (rp + 1) for each head group, by its own registered one-hot
    function automatic [31:0] sq_rd1(input [3:0] oh, input [127:0] f, input integer w, input integer off);
      reg [31:0] r; begin r = 0;
        for (integer e = 0; e < 4; e = e + 1) if (oh[e]) r = r | ((f >> (e * w + off)) & ((32'd1 << 16) - 1));
        sq_rd1 = r; end
    endfunction
    wire [4:0] sq_a1_bk = sq_rd1(sq_hf_qv[3:0], {{108'b0, sq_bk_f}}, 5, 0);
    wire [4:0] sq_a1_cl = sq_rd1(sq_hf_qv[3:0], {{108'b0, sq_cl_f}}, 5, 0);
    wire       sq_a1_we = |(sq_hf_qv[3:0] & sq_we_f);
    wire [9:0] sq_a1_rl = sq_rd1(sq_hf_qv[9:6], {{52'b0, sq_rw_f}}, 19, 0);
    wire [8:0] sq_a1_rh = sq_rd1(sq_hf_qv[15:12], {{52'b0, sq_rw_f}}, 19, 10);
    wire [7:0] sq_a1_o0 = sq_rd1(sq_hf_qv[21:18], sq_oh_f, 32, 0);
    wire [7:0] sq_a1_o1 = sq_rd1(sq_hf_qv[27:24], sq_oh_f, 32, 8);
    wire [7:0] sq_a1_o2 = sq_rd1(sq_hf_qv[33:30], sq_oh_f, 32, 16);
    wire [7:0] sq_a1_o3 = sq_rd1(sq_hf_qv[39:36], sq_oh_f, 32, 24);
    wire [31:0] sq_a1_o = {{sq_a1_o3, sq_a1_o2, sq_a1_o1, sq_a1_o0}};
    wire [18:0] srw_tw = 19'(srw + 19'(TWIN_ROFF));
    wire swe_nx = s_go_c[10] ? (sq_hf_qv[5] ? sq_a1_we : s_we) : (sq_hf_qv[4] ? s_we : swe);'''

SQ_BLOCK_OLD = '''        if (S) begin : sq
          reg [SQW-1:0] rpn; reg chg;
          if (s_v && s_r) begin
            sq_bank[SQW'(sq_rp + sq_n)] <= s_bank; sq_col[SQW'(sq_rp + sq_n)] <= s_col;
            sq_row[SQW'(sq_rp + sq_n)] <= s_row; sq_we[SQW'(sq_rp + sq_n)] <= s_we;
            sq_context[SQW'(sq_rp + sq_n)]<=s_context;
          end
          sq_n <= sq_n + ((s_v && s_r) ? 1'b1 : 1'b0) - (s_go ? 1'b1 : 1'b0);
          if (s_go) sq_rp <= SQW'(sq_rp + 1'b1);
          rpn = s_go ? SQW'(sq_rp + 1'b1) : sq_rp;
          chg = s_go || sq_n == 0;
          if (chg) begin
            if (sq_n - (s_go ? 1'b1 : 1'b0) != 0) begin
              shead_context<=sq_context[rpn];
              sb <= sq_bank[rpn]; sc <= sq_col[rpn]; srw <= sq_row[rpn]; swe <= sq_we[rpn]; sb_oh <= 32'b1 << sq_bank[rpn];
            end else begin
              shead_context<=s_context;
              sb <= s_bank; sc <= s_col; srw <= s_row; swe <= s_we; sb_oh <= 32'b1 << s_bank;
            end
            sfl <= 1'b0; scm <= 1'b0;
          end else if (s_sw) begin
            sb <= sb ^ 5'd2; srw <= 19'(srw + 19'(TWIN_ROFF)); sb_oh <= ab_oh; sfl <= 1'b1;
          end else if (s_hit || (row_fire && c_op == ACT && c_s)) scm <= 1'b1;
          if (!sq_ne || chg || s_sw) swait <= 0; else if (swait != 8'hff) swait <= swait + 1'b1;'''

def hg(k):   # head group k: (s_go copy, s_sw copy, ge2, eq0)
    return f's_go_c[{10 + k}]', f's_sw_c[{1 + k}]', f'sq_hf_qv[{k * 6 + 5}]', f'sq_hf_qv[{k * 6 + 4}]'

def head_stmt(k, lhs, a1, sv, tw):
    g, w, ge2, eq0 = hg(k)
    t = f'({w} ? {tw} : {lhs})' if tw else lhs
    return f'          {lhs} <= {g} ? ({ge2} ? {a1} : {sv}) : ({eq0} ? {sv} : {t});\n'

SQ_BLOCK_NEW = ('''        if (S) begin : sq
          // KV-PC5: entry writes, the context and the next-head reads are outside (lookahead one-hot copies); the head
          // registers load per group from their own s_go / s_sw copies and flags (exactly the old chg / s_sw priority:
          // s_go && n >= 2 -> entry rp + 1; s_go && n == 1 or n == 0 -> the pushed fields; else s_sw -> twin; else hold)
          sq_n <= sq_n_nx;
          sq_rp <= sq_rp_nx;
'''
    + head_stmt(0, 'sb', 'sq_a1_bk', 's_bank', 'sb ^ 5\'d2') + head_stmt(0, 'sc', 'sq_a1_cl', 's_col', None)
    + '          swe <= swe_nx;\n'
    + head_stmt(1, 'srw[9:0]', 'sq_a1_rl', 's_row[9:0]', 'srw_tw[9:0]')
    + head_stmt(2, 'srw[18:10]', 'sq_a1_rh', 's_row[18:10]', 'srw_tw[18:10]')
    + ''.join(head_stmt(3 + h, f'sb_oh[{8 * h + 7}:{8 * h}]', f'sq_a1_o[{8 * h + 7}:{8 * h}]', f'sq_s_oh[{8 * h + 7}:{8 * h}]',
                        f'ab_oh[{8 * h + 7}:{8 * h}]') for h in range(4))
    + '          swe_bk <= {8{swe_nx}};\n'
    + '''          if (s_go_c[17] || sq_n == 0) begin sfl <= 1'b0; scm <= 1'b0; end
          else if (s_sw_c[0]) sfl <= 1'b1;
          else if (s_hit || (row_fire && c_op == ACT && c_s)) scm <= 1'b1;
          if (!sq_ne || s_go_c[17] || sq_n == 0 || s_sw_c[0]) swait <= 0; else if (swait != 8'hff) swait <= swait + 1'b1;''')

WQ_DECL_OLD = '''    reg [31:0] wq_oh [0:WQ-1]; reg [WQW-1:0] wq_rp1;'''
WQ_DECL_NEW = '''    reg [31:0] wq_oh [0:WQ-1]; reg [WQW-1:0] wq_rp1;
    // KV-PC5 (native32): registered one-hot copies of wq_rp (0 queued banks wq_bq, 1 head hb/hc/hr, 2/3 head hb_oh
    // lo/hi), of the head's {n != 1, n != 0} (per head group) and of the free write slot (bank/col, oh lo, oh hi),
    // computed from the next-state pointers (lookahead): the queue writes go ungated into the free slot.
    (* keep *) reg [15:0] wq_rpoh_qv; (* keep *) reg [5:0] wq_ne_qv; (* keep *) reg [11:0] wq_ws_qv;
    function automatic [3:0] wq_rot(input [3:0] oh, input integer i);   // one-hot of (rp + i) from one-hot rp
      wq_rot = (({oh, oh} << i) >> 4);
    endfunction'''

WQE_OLD = '''      assign wq_bq[i*5 +: 5] = wq_bank[WQW'(wq_rp + i)];'''
WQE_NEW = '''      wire [3:0] q_oh = wq_rot(wq_rpoh_qv[3:0], i);
      assign wq_bq[i*5 +: 5] = ({5{q_oh[0]}} & wq_bank[0]) | ({5{q_oh[1]}} & wq_bank[1]) |
                               ({5{q_oh[2]}} & wq_bank[2]) | ({5{q_oh[3]}} & wq_bank[3]);'''

WQ_BLOCK_OLD = '''          if (wr_v && wr_r) begin
            wq_bank[WQW'(wq_rp + wq_n)] <= wr_bank; wq_col[WQW'(wq_rp + wq_n)] <= wr_col;
            wq_oh[WQW'(wq_rp + wq_n)] <= 32'b1 << wr_bank;
            if (AQ) wq_rd[WQW'(wq_rp + wq_n)] <= wr_rd;
          end
          wq_n <= wq_n + (wr_v && wr_r ? 1'b1 : 1'b0) - (wr_ok ? 1'b1 : 1'b0);'''
WQ_BLOCK_NEW = '''          wq_n <= wq_n_nx;'''

WQ_RP_OLD = '''          if (wr_ok) begin wq_rp <= wq_rp1; wq_rp1 <= WQW'(wq_rp1 + 1'b1); end
          // next head: the entry after the popped one if it exists, else the entry pushed now
          begin : headn
            // identical to: rpn = wr_ok ? wq_rp + 1 : wq_rp; head = (wq_n - wr_ok != 0) ? q[rpn] : the pushed entry
            reg [4:0] b0, c0, b1, c1; reg r0, r1, ne0, ne1; reg [31:0] o0, o1;
            b0 = wq_bank[wq_rp];  c0 = wq_col[wq_rp];  r0 = AQ && wq_rd[wq_rp];  o0 = wq_oh[wq_rp];
            b1 = wq_bank[wq_rp1]; c1 = wq_col[wq_rp1]; r1 = AQ && wq_rd[wq_rp1]; o1 = wq_oh[wq_rp1];
            ne0 = wq_n != 0; ne1 = wq_n != 1;
            if (wr_ok) begin
              if (ne1) begin hb <= b1; hc <= c1; hb_oh <= o1; hr <= r1; end
              else begin hb <= wr_bank; hc <= wr_col; hb_oh <= 32'b1 << wr_bank; hr <= AQ && wr_rd; end
            end else begin
              if (ne0) begin hb <= b0; hc <= c0; hb_oh <= o0; hr <= r0; end
              else begin hb <= wr_bank; hc <= wr_col; hb_oh <= 32'b1 << wr_bank; hr <= AQ && wr_rd; end
            end
          end'''
WQ_RP_NEW = '''          wq_rp <= wq_rp_nx; wq_rp1 <= wr_ok_c[2] ? WQW'(wq_rp1 + 1'b1) : wq_rp1;
          // next head (KV-PC5: per field group from its own wr_ok copy, one-hot rp copy and {n != 1, n != 0} flags;
          // identical to: rpn = wr_ok ? wq_rp + 1 : wq_rp; head = (wq_n - wr_ok != 0) ? q[rpn] : the pushed entry)
          hb <= wr_ok_c[3] ? (wq_ne_qv[1] ? wq_hb1 : wr_bank) : (wq_ne_qv[0] ? wq_hb0 : wr_bank);
          hc <= wr_ok_c[3] ? (wq_ne_qv[1] ? wq_hc1 : wr_col) : (wq_ne_qv[0] ? wq_hc0 : wr_col);
          hr <= wr_ok_c[3] ? (wq_ne_qv[1] ? wq_hr1 : AQ && wr_rd) : (wq_ne_qv[0] ? wq_hr0 : AQ && wr_rd);
          hb_oh[15:0] <= wr_ok_c[4] ? (wq_ne_qv[3] ? wq_ho1[15:0] : wq_dec[15:0]) : (wq_ne_qv[2] ? wq_ho0[15:0] : wq_dec[15:0]);
          hb_oh[31:16] <= wr_ok_c[5] ? (wq_ne_qv[5] ? wq_ho1[31:16] : wq_dec[31:16]) : (wq_ne_qv[4] ? wq_ho0[31:16] : wq_dec[31:16]);'''

WQ_LOOK = '''    // ---- KV-PC5 write queue lookahead ---------------------------------------------------------------------------
    wire [WQW:0] wq_n_nx = wq_n + (wr_v && wr_r ? 1'b1 : 1'b0) - (wr_ok ? 1'b1 : 1'b0);
    wire [WQW-1:0] wq_rp_nx = wr_ok_c[2] ? wq_rp1 : wq_rp;
    wire [3:0] wq_rpoh_nx = 4'b1 << wq_rp_nx;
    wire [3:0] wq_wsoh_nx = (wq_n_nx != (WQW+1)'(WQ)) ? (4'b1 << WQW'(wq_rp_nx + wq_n_nx[WQW-1:0])) : 4'b0;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin wq_rpoh_qv <= {4{4'b0001}}; wq_ne_qv <= {3{2'b10}}; wq_ws_qv <= {3{4'b0001}}; end
      else begin
        wq_rpoh_qv <= {4{wq_rpoh_nx}}; wq_ne_qv <= {3{wq_n_nx != 1, wq_n_nx != 0}}; wq_ws_qv <= {3{wq_wsoh_nx}};
      end
    wire [31:0] wq_dec = 32'b1 << wr_bank;
    always @(posedge clk) if (W) for (integer e = 0; e < WQ; e = e + 1) begin
      if (wq_ws_qv[e]) begin wq_bank[e] <= wr_bank; wq_col[e] <= wr_col; if (AQ) wq_rd[e] <= wr_rd; end
      if (wq_ws_qv[4 + e]) wq_oh[e][15:0] <= wq_dec[15:0];
      if (wq_ws_qv[8 + e]) wq_oh[e][31:16] <= wq_dec[31:16];
    end
    function automatic [36:0] wq_sel(input [3:0] oh, input [4:0] b0, b1, b2, b3, input [4:0] c0, c1, c2, c3,
                                     input r0, r1, r2, r3);
      wq_sel = {({5{oh[0]}} & b0) | ({5{oh[1]}} & b1) | ({5{oh[2]}} & b2) | ({5{oh[3]}} & b3),
                ({5{oh[0]}} & c0) | ({5{oh[1]}} & c1) | ({5{oh[2]}} & c2) | ({5{oh[3]}} & c3),
                (oh[0] & r0) | (oh[1] & r1) | (oh[2] & r2) | (oh[3] & r3), 26'b0};
    endfunction
    wire [3:0] wq_h0 = wq_rpoh_qv[7:4], wq_h1 = wq_rot(wq_rpoh_qv[7:4], 1);
    wire [36:0] wq_s0 = wq_sel(wq_h0, wq_bank[0], wq_bank[1], wq_bank[2], wq_bank[3], wq_col[0], wq_col[1], wq_col[2], wq_col[3],
                               wq_rd[0], wq_rd[1], wq_rd[2], wq_rd[3]);
    wire [36:0] wq_s1 = wq_sel(wq_h1, wq_bank[0], wq_bank[1], wq_bank[2], wq_bank[3], wq_col[0], wq_col[1], wq_col[2], wq_col[3],
                               wq_rd[0], wq_rd[1], wq_rd[2], wq_rd[3]);
    wire [4:0] wq_hb0 = wq_s0[36:32], wq_hb1 = wq_s1[36:32], wq_hc0 = wq_s0[31:27], wq_hc1 = wq_s1[31:27];
    wire wq_hr0 = AQ && wq_s0[26], wq_hr1 = AQ && wq_s1[26];
    wire [3:0] wq_l0 = wq_rpoh_qv[11:8], wq_l1 = wq_rot(wq_rpoh_qv[11:8], 1);
    wire [3:0] wq_u0 = wq_rpoh_qv[15:12], wq_u1 = wq_rot(wq_rpoh_qv[15:12], 1);
    wire [31:0] wq_ho0 = {({16{wq_u0[0]}} & wq_oh[0][31:16]) | ({16{wq_u0[1]}} & wq_oh[1][31:16]) | ({16{wq_u0[2]}} & wq_oh[2][31:16]) | ({16{wq_u0[3]}} & wq_oh[3][31:16]),
                          ({16{wq_l0[0]}} & wq_oh[0][15:0]) | ({16{wq_l0[1]}} & wq_oh[1][15:0]) | ({16{wq_l0[2]}} & wq_oh[2][15:0]) | ({16{wq_l0[3]}} & wq_oh[3][15:0])};
    wire [31:0] wq_ho1 = {({16{wq_u1[0]}} & wq_oh[0][31:16]) | ({16{wq_u1[1]}} & wq_oh[1][31:16]) | ({16{wq_u1[2]}} & wq_oh[2][31:16]) | ({16{wq_u1[3]}} & wq_oh[3][31:16]),
                          ({16{wq_l1[0]}} & wq_oh[0][15:0]) | ({16{wq_l1[1]}} & wq_oh[1][15:0]) | ({16{wq_l1[2]}} & wq_oh[2][15:0]) | ({16{wq_l1[3]}} & wq_oh[3][15:0])};'''

CASE_OLD = '''        if (row_fire) case (c_op)
          ACT: begin open <= open | c_oh; rrds_c <= 2'(T_RRDS - 1); if (S && c_s) stale <= stale | c_oh; end
          PRE: begin open <= open & ~c_oh; stale <= stale & ~c_oh; end
          PREALL: begin open <= 0; stale <= 0; end
          REFPB: begin
            noact_c <= 4'(T_RREFD - 1); ref_pend <= 0; blk <= 0;
            if (PI && ep && !ref_pend) begin ep <= 0; pin <= pin + 1'b1; end
            refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));
          end
          default: ;
        endcase'''

def oc(k, h):
    lo, hi = (0, 15) if h == 0 else (16, 31)
    s = f'[{hi}:{lo}]'
    return (f'        if (row_gnt && {ev(k, "act")}) open{s} <= open{s} | c_oh{s};\n'
            f'        else if (row_gnt && {ev(k, "pre")}) open{s} <= open{s} & ~c_oh{s};\n'
            f'        else if (row_gnt && {ev(k, "pall")}) open{s} <= 16\'b0;\n')

def sc_(k, h):
    lo, hi = (0, 15) if h == 0 else (16, 31)
    s = f'[{hi}:{lo}]'
    return (f'        if (row_gnt && {ev(k, "acts")}) stale{s} <= stale{s} | c_oh{s};\n'
            f'        else if (row_gnt && {ev(k, "pre")}) stale{s} <= stale{s} & ~c_oh{s};\n'
            f'        else if (row_gnt && {ev(k, "pall")}) stale{s} <= 16\'b0;\n')

CASE_NEW = ('        // KV-PC5: the row-command case per load group from its own registered event copy (exclusive fields)\n'
            + oc(9, 0) + oc(10, 1) + sc_(11, 0) + sc_(12, 1)
            + f'''        if (row_gnt && {ev(13, "act")}) rrds_c <= 2'(T_RRDS - 1);
        if (row_gnt && {ev(20, "rfp")}) blk <= 0;
        if (row_gnt && {ev(21, "rfp")}) begin
          noact_c <= 4'(T_RREFD - 1); ref_pend <= 0;
          if (PI && ep && !ref_pend) begin ep <= 0; pin <= pin + 1'b1; end
        end
        if (row_gnt && {ev(13, "rfp")}) refreshed <= (&(refreshed | (32'b1 << rb))) ? 32'b0 : (refreshed | (32'b1 << rb));''')

DESC_OLD = '''        if (desc_v && !streaming && !fault_r) begin
          j <= first_sector; n <= desc_n; row <= desc_row;
          context_active<=context_accept;context_v<=desc_vpass;context_kb<=desc_k_order_b;context_k0<=desc_k_count0;ordinal<=0;context_count<=desc_n[8:0];
          v_consumer_order <= !context_accept && desc_first==10'd512 && desc_n==11'd768; done <= 0; running <= 0;
          streaming <= (desc_n != 0); nm1 <= desc_n - 11'd1; last <= context_accept ? (desc_vpass?3'd5:3'd1) : 3'((desc_n - 11'd1) >> 7);
          stale <= open_nx;                     // rows still open from the old descriptor close first
        end'''
DESC_NEW = '''        // KV-PC5: the descriptor accept per load group from its own desc_acc copy (same statements, same order)
        if (desc_acc_c[6]) j <= first_sector;
        if (desc_acc_c[7]) n <= desc_n;
        if (desc_acc_c[8]) row <= desc_row;
        if (desc_acc_c[9]) begin context_active<=context_accept;context_v<=desc_vpass;context_kb<=desc_k_order_b;context_k0<=desc_k_count0; end
        if (desc_acc_c[10]) ordinal<=0;
        if (desc_acc_c[11]) context_count<=desc_n[8:0];
        if (desc_acc_c[12]) begin
          v_consumer_order <= !context_accept && desc_first==10'd512 && desc_n==11'd768; running <= 0;
          streaming <= (desc_n != 0); nm1 <= desc_n - 11'd1; last <= context_accept ? (desc_vpass?3'd5:3'd1) : 3'((desc_n - 11'd1) >> 7);
        end
        if (desc_acc_c[13]) done[15:0] <= 16'b0;
        if (desc_acc_c[14]) done[31:16] <= 16'b0;
        if (desc_acc_c[15]) stale[15:0] <= open_nx[15:0];     // rows still open from the old descriptor close first
        if (desc_acc_c[16]) stale[31:16] <= open_nx[31:16];'''

RD_OLD = '''        if (rd_ok) begin
          j <= j_p1;
          if (context_active ? ordinal+9'd1==context_count : j==nm1) streaming<=0;
          if(context_active)ordinal<=ordinal+9'd1;
          if (!context_active && j[6:2] == 5'd31) done <= done | rd_oh;
          if(context_active && ordinal+9'd1==context_count)done<=done|32'hffffffff;
        end'''
RD_NEW = '''        if (rd_ok) begin
          j <= j_p1;
          if (context_active ? ordinal+9'd1==context_count : j==nm1) streaming<=0;
        end
        // KV-PC5: ordinal / done per load group from their own rd_ok copies (same order)
        if (rd_ok_c[1] && context_active) ordinal<=ordinal+9'd1;
        if (rd_ok_c[4] && !context_active && j[6:2] == 5'd31) done[15:0] <= done[15:0] | rd_oh[15:0];
        if (rd_ok_c[4] && context_active && ordinal+9'd1==context_count) done[15:0] <= 16'hffff;
        if (rd_ok_c[5] && !context_active && j[6:2] == 5'd31) done[31:16] <= done[31:16] | rd_oh[31:16];
        if (rd_ok_c[5] && context_active && ordinal+9'd1==context_count) done[31:16] <= 16'hffff;'''

RDOH_OLD = '''        if (desc_acc) begin rd_oh <= 32'b1 << {first_sector[9:7],first_sector[1:0]}; rd_bgoh <= 4'b1 << first_sector[1:0]; end
        else if (rd_ok) begin rd_oh <= 32'b1 << {j_p1[9:7], j_p1[1:0]}; rd_bgoh <= 4'b1 << j_p1[1:0]; end'''
RDOH_NEW = '''        // KV-PC5: rd_oh lo / hi and rd_bgoh each from their own desc_acc / rd_ok copies
        if (desc_acc_c[3]) rd_oh[15:0] <= rd_oh_d[15:0]; else if (rd_ok_c[6]) rd_oh[15:0] <= rd_oh_j[15:0];
        if (desc_acc_c[4]) rd_oh[31:16] <= rd_oh_d[31:16]; else if (rd_ok_c[7]) rd_oh[31:16] <= rd_oh_j[31:16];
        if (desc_acc_c[5]) rd_bgoh <= 4'b1 << first_sector[1:0]; else if (rd_ok_c[8]) rd_bgoh <= 4'b1 << j_p1[1:0];'''

TIM_PC5 = [
    # KV-PC5: c_oh = onehot(c_bank) registered from r_bank (every consumer qualifies c_oh by c_op in {ACT, PRE, REFPB},
    # where the old r_oh was exactly onehot(r_bank): blk = 1 << rb, sb_oh / wab_oh one-hot of sb / wab, act_oh / pre_oh
    # the lowest-first one-hots of act_sel / pre_sel); removes the 32-bit priority mux of r_oh (74 / 81-load selects)
    ('''c_bank <= r_bank; c_oh <= r_oh; c_w <= W && r_w;''', '''c_bank <= r_bank; c_oh <= 32'b1 << r_bank; c_w <= W && r_w;'''),
    ('''    always @* s_pblk = ((S && slot_next && r_v && r_sp) ? r_oh : 32'b0)''',
     '''    always @* s_pblk = ((S && slot_next && r_v && r_sp) ? sb_oh : 32'b0)'''),
    ('''    wire s_hit = sq_ne && so_v && so_b == sb && so_row == srw && |(sb_oh & open);
    wire [31:0] shold = s_hit ? sb_oh : 32'b0;''',
     '''    // KV-PC5: s_hit as two kept leaf copies (1 = the 32-bit shold mask)
    wire [1:0] s_hit_c;
''' + leaves('s_hit_c', 2, 'sq_ne && so_v && so_b == sb && so_row == srw', '|(sb_oh & open)') + '''    wire s_hit = s_hit_c[0];
    wire [31:0] shold = s_hit_c[1] ? sb_oh : 32'b0;'''),
    ('''        sq_n <= 0; sq_rp <= 0; sb <= 0; sc <= 0; srw <= 0; swe <= 0;''',
     '''        sq_n <= 0; sq_rp <= 0; sb <= 0; sc <= 0; srw <= 0; swe <= 0; swe_bk <= 8'b0;'''),
    ('''    wire wr_ok, wr_ok0, rd_ok0;''',
     f'''    wire wr_ok, wr_ok0, rd_ok0;
    wire [{NWR - 1}:0] wr_ok_c;   // KV-PC5: kept leaf copies of wr_ok (0 = wr_ok)'''),
    ('''    reg [SQW:0] sq_n; reg [SQW-1:0] sq_rp;
    reg [346:0] sq_context[0:SQD-1];reg [346:0] shead_context;
    assign col_context=shead_context;''', SQ_DECL),
    ('''    reg [4:0] sq_bank [0:SQD-1]; reg [4:0] sq_col [0:SQD-1]; reg [18:0] sq_row [0:SQD-1]; reg sq_we [0:SQD-1];\n''', ''),
    ('''    wire s_go;                                        // the static head's column command issues this cycle''',
     f'''    wire s_go;                                        // the static head's column command issues this cycle
    wire [{NSG - 1}:0] s_go_c;   // KV-PC5: kept leaf copies of s_go (0 = s_go)
    wire [{NSW - 1}:0] s_sw_c;   // KV-PC5: kept leaf copies of s_sw (0 = s_sw)'''),
    ('''    wire [31:0] open_nx = !row_fire ? open : (c_op == ACT) ? (open | c_oh) : (c_op == PRE) ? (open & ~c_oh) :
                          (c_op == PREALL) ? 32'b0 : open;
    wire rd_ok;''', EV_BLOCK + f'''
    wire rd_ok;
    wire [{NRD - 1}:0] rd_ok_c;   // KV-PC5: kept leaf copies of rd_ok (0 = rd_ok)'''),
    ('''    wire [31:0] ready_stale_next = desc_acc ? open_nx :
      (row_fire && c_op == PREALL) ? 32'b0 :
      (row_fire && c_op == PRE) ? stale & ~c_oh :
      (row_fire && c_op == ACT && S && c_s) ? stale | c_oh : stale;
    wire [31:0] ready_blk_next = (row_fire && c_op == REFPB) ? 32'b0 :''',
     f'''    wire [31:0] ready_stale_next = {{{half(16, 17, 2)}, {half(0, 16, 1)}}};
    wire [31:0] ready_blk_next = (row_gnt && {ev(18, "rfp")}) ? 32'b0 :'''),
    ('''      (REF_MODE && ref_c == RW'(LEAD)) ? (32'b1 << bsel) : blk;''', '''      !REF_MODE ? blk : (({{16{lead_qv[2]}}, {16{lead_qv[1]}}} & (32'b1 << bsel)) |
                          ({{16{!lead_qv[2]}}, {16{!lead_qv[1]}}} & blk));'''),
    ('''          if (REF_MODE && ref_c == RW'(LEAD)) begin ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; end''',
     '''          if (REF_MODE && lead_qv[0]) begin ref_pend <= 1; rb <= bsel; blk <= 32'b1 << bsel; end'''),
    ('''      wire wr_e = (W && wr_ok && hb_oh[b] && !(AQ && hr)) || (s_go && swe && sb_oh[b]);
      wire act_e = row_fire && c_op == ACT && c_oh[b];
      wire pre_e = row_fire && ((c_op == PRE && c_oh[b]) || c_op == PREALL);
      wire rfa_e = row_fire && c_op == REFAB;
      wire rfp_e = row_fire && c_op == REFPB && c_oh[b];
      wire rd_e  = (rd_ok && rd_oh[b]) || (AQ && wr_ok && hr && hb_oh[b]) || (s_go && !swe && sb_oh[b]);''',
     f'''      // KV-PC5: this bank group's own decision / event copies
      wire wr_e = (W && wr_ok_c[6 + (b >> 2)] && hb_oh[b] && !(AQ && hr)) || (s_go_c[2 + (b >> 2)] && swe_bk[b >> 2] && sb_oh[b]);
      wire act_e = row_gnt && {bank_ix(0)} && c_oh[b];
      wire pre_e = row_gnt && (({bank_ix(1)} && c_oh[b]) || {bank_ix(2)});
      wire rfa_e = row_gnt && {bank_ix(3)};
      wire rfp_e = row_gnt && {bank_ix(4)} && c_oh[b];
      wire rd_e  = (rd_ok_c[11 + (b >> 2)] && rd_oh[b]) || (AQ && wr_ok_c[6 + (b >> 2)] && hr && hb_oh[b]) || (s_go_c[2 + (b >> 2)] && !swe_bk[b >> 2] && sb_oh[b]);'''),
    ('''      wire act_g = row_fire && c_op == ACT && c_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire ccdl_e = (rd_ok && rd_bgoh[g]) || (W && wr_ok && hb[1:0] == 2'(g)) || (s_go && sb[1:0] == 2'(g));
      wire faw_take = row_fire && c_op == ACT && faw == 0''',
     f'''      wire act_g = row_gnt && {ev(8, "act")} && c_bank[1:0] == 2'(g);
      // FAW slot g takes this ACT if it is the lowest free slot
      wire ccdl_e = (rd_ok_c[3] && rd_bgoh[g]) || (W && wr_ok_c[1] && hb[1:0] == 2'(g)) || (s_go_c[0] && sb[1:0] == 2'(g));
      wire faw_take = row_gnt && {ev(8, "act")} && faw == 0'''),
    ('''    assign s_go = legal_static && (PROFILE == 1 || reserved_static_col);
    wire legal_rd = rd_ok0 && !s_go && !(|(rd_oh & s_pblk));
    assign rd_ok = legal_rd && (PROFILE == 1 || reserved_rd);''',
     leaves('s_go_c', NSG, 'legal_static', 'PROFILE == 1 || reserved_static_col') +
     '''    assign s_go = s_go_c[0];
    wire legal_rd = rd_ok0 && !s_go_c[0] && !(|(rd_oh & s_pblk));
''' + leaves('rd_ok_c', NRD, 'legal_rd', 'PROFILE == 1 || reserved_rd') + '''    assign rd_ok = rd_ok_c[0];'''),
    ('''    wire legal_write = wr_ok0 && !s_go && !(|(hb_oh & s_pblk));
    assign wr_ok = legal_write && (PROFILE == 1 || reserved_write_col);''',
     '''    wire legal_write = wr_ok0 && !s_go_c[0] && !(|(hb_oh & s_pblk));
''' + leaves('wr_ok_c', NWR, 'legal_write', 'PROFILE == 1 || reserved_write_col') + '''    assign wr_ok = wr_ok_c[0];'''),
    ('''    wire desc_acc = desc_v && !streaming && !fault_r;
    wire k_step = rd_ok && (j[6:0] == 7'h7f);
    wire v_set_flip=v_consumer_order && rd_ok && j[2:0]==3'd7;
    wire [2:0] k_n = desc_acc ? first_sector[9:7] : context_active&&rd_ok ? j_p1[9:7]''',
     leaves('desc_acc_c', NDA, 'desc_v', '!streaming && !fault_r') + '''    wire desc_acc = desc_acc_c[0];
    wire [31:0] rd_oh_d = 32'b1 << {first_sector[9:7],first_sector[1:0]};
    wire [31:0] rd_oh_j = 32'b1 << {j_p1[9:7], j_p1[1:0]};
    wire k_step = rd_ok_c[2] && (j[6:0] == 7'h7f);
    wire v_set_flip=v_consumer_order && rd_ok_c[2] && j[2:0]==3'd7;
    wire [2:0] k_n = desc_acc ? first_sector[9:7] : context_active&&rd_ok_c[2] ? j_p1[9:7]'''),
    ('''context_active&&rd_ok ? (8'b1 << j_p1[9:7])''', '''context_active&&rd_ok_c[2] ? (8'b1 << j_p1[9:7])'''),
    ('''    wire s_sw = S && (TWIN != 0) && sq_ne && !swe && !sfl && !scm && !s_hit && s_unav && s_av_a;
    wire s_act_ok = sq_ne && !s_sw &&''',
     leaves('s_sw_c', NSW, 'S && (TWIN != 0) && sq_ne && !swe && !sfl && !scm && !s_hit', 's_unav && s_av_a') +
     '''    wire s_sw = s_sw_c[0];
    wire s_act_ok = sq_ne && !s_sw &&'''),
    ('''    assign col_v = rd_ok || (W && wr_ok) || s_go; assign col_we = (W && wr_ok && !(AQ && hr)) || (s_go && swe);
    assign col_aq = AQ && wr_ok && hr; assign col_sr = s_go;
    assign col_bank = s_go ? sb : (W && wr_ok) ? hb : rd_bank; assign col_col = s_go ? sc : (W && wr_ok) ? hc : j[6:2];
    assign s_r = S && sq_n != (SQW+1)'(SQD); assign s_pop = s_go;''',
     '''    assign col_v = rd_ok_c[3] || (W && wr_ok_c[1]) || s_go_c[0]; assign col_we = (W && wr_ok_c[1] && !(AQ && hr)) || (s_go_c[0] && swe);
    assign col_aq = AQ && wr_ok_c[1] && hr; assign col_sr = s_go_c[0];
    assign col_bank = s_go_c[1] ? sb : (W && wr_ok_c[1]) ? hb : rd_bank; assign col_col = s_go_c[1] ? sc : (W && wr_ok_c[1]) ? hc : j[6:2];
    assign s_r = S && sq_n != (SQW+1)'(SQD); assign s_pop = s_go_c[0];
''' + SQ_LOOK + '\n' + WQ_LOOK),
    ('''          if (rd_ok || (AQ && wr_ok && hr) || (s_go && !swe)) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
          if ((wr_ok && !(AQ && hr)) || (s_go && swe)) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;''',
     '''          if (rd_ok_c[3] || (AQ && wr_ok_c[2] && hr) || (s_go_c[1] && !swe)) rtw_c <= 4'(T_RTW - 1); else if (rtw_c != 0) rtw_c <= rtw_c - 1'b1;
          if ((wr_ok_c[2] && !(AQ && hr)) || (s_go_c[1] && swe)) wtr_c <= 4'(T_WTR - 1); else if (wtr_c != 0) wtr_c <= wtr_c - 1'b1;'''),
    (WQ_DECL_OLD, WQ_DECL_NEW), (WQE_OLD, WQE_NEW), (WQ_BLOCK_OLD, WQ_BLOCK_NEW), (WQ_RP_OLD, WQ_RP_NEW),
    ('''          wopen <= ((wopen | ((row_fire && c_op == ACT && c_w) ? c_oh : 32'b0))
                    & ~((row_fire && c_op == PRE) ? c_oh : 32'b0)
                    & ~(rd_ok ? rd_oh : 32'b0))
                   & {32{!(row_fire && c_op == PREALL)}};''',
     f'''          wopen <= ((wopen | ((row_gnt && {ev(19, "act")} && c_w) ? c_oh : 32'b0))
                    & ~((row_gnt && {ev(19, "pre")}) ? c_oh : 32'b0)
                    & ~({{{{16{{rd_ok_c[10]}}}}, {{16{{rd_ok_c[9]}}}}}} & rd_oh))
                   & {{32{{!(row_gnt && {ev(19, "pall")})}}}};'''),
    (RDOH_OLD, RDOH_NEW),
    (SQ_BLOCK_OLD, SQ_BLOCK_NEW), (CASE_OLD, CASE_NEW), (DESC_OLD, DESC_NEW), (RD_OLD, RD_NEW),
]

# KV-PC5-A: u_ctl (ot_qkd_static_ctrl_pc_emb) command FIFO native32 restructure
def _hg(k, lhs, a1, cq):
    return (f'  {lhs} <= ctl_pop_c[{1 + k}] ? (ctl_hf_qv[{k * 10 + 9}] ? {a1} : (ctl_push_c[{1 + k}] ? {cq} : {lhs})) :\n'
            f'          ((ctl_hf_qv[{k * 10 + 8}] && ctl_push_c[{1 + k}]) ? {cq} : {lhs});\n')

def _rd(k, lo, w, src):
    return ('|{' + ', '.join(f'{{{w}{{ctl_hf_qv[{k * 10 + e}]}}}} & {src}[{e}][{lo + w - 1}:{lo}]' for e in range(8)) + '}') if False else \
        ' | '.join(f'({{{w}{{ctl_hf_qv[{k * 10 + e}]}}}} & {src}[{e}][{lo + w - 1}:{lo}])' for e in range(8))

UCTL_PC5 = [
    (''' wire pop=live && (malformed || (descriptor_head ? desc_ready : head[31:30]==2 ? wr_ready : 1'b1));
 wire push=(ENABLE!=0) && cmd_v_q && count<8;''',
     ''' // KV-PC5 (native32): pop / push as kept AND-leaf copies (0 = the plain signal; 1..3 = head field groups)
 wire [3:0] ctl_pop_c, ctl_push_c;
 for (genvar q = 0; q < 4; q = q + 1) begin : g_ctl_pp
   ot_kvpc5_and2 u_pop (.a(live), .b(malformed || (descriptor_head ? desc_ready : head[31:30]==2 ? wr_ready : 1'b1)), .y(ctl_pop_c[q]));
   ot_kvpc5_and2 u_push (.a((ENABLE!=0) && cmd_v_q), .b(count<8), .y(ctl_push_c[q]));
 end
 wire pop=ctl_pop_c[0];
 wire push=ctl_push_c[0];
 // lookahead (next-state pointers -> registered one-hot copies): free write slot per field group (ungated write: slot
 // wp is never live while count < 8), and per head group {count > 1, count == 0, onehot(rp + 1)}
 wire [3:0] ctl_count_nx = count + (push ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0);
 wire [2:0] ctl_wp_nx = push ? wp + 3'd1 : wp;
 wire [2:0] ctl_rp_nx = pop ? rp + 3'd1 : rp;
 wire [7:0] ctl_ws_nx = (ctl_count_nx != 4'd8) ? (8'b1 << ctl_wp_nx) : 8'b0;
 wire [9:0] ctl_hf_nx = {ctl_count_nx > 4'd1, ctl_count_nx == 4'd0, 8'b1 << 3'(ctl_rp_nx + 3'd1)};
 (* keep *) reg [23:0] ctl_ws_qv; (* keep *) reg [29:0] ctl_hf_qv;
 always @(posedge clk or negedge rst_n)
  if (!rst_n) begin ctl_ws_qv <= {3{8'b1}}; ctl_hf_qv <= {3{2'b01, 8'b10}}; end
  else begin ctl_ws_qv <= {3{ctl_ws_nx}}; ctl_hf_qv <= {3{ctl_hf_nx}}; end'''),
    ('''  if(push)begin fifo[wp]<=cmd_q;first_fifo[wp]<=first_q;end
  if(count==0 && push)begin head<=cmd_q;head_first<=first_q;end
  else if(pop) begin
   if(count>1)begin head<=fifo[rp_next];head_first<=first_fifo[rp_next];end
   else if(push)begin head<=cmd_q;head_first<=first_q;end
  end''',
     '''  // KV-PC5: ungated slot writes and per-group head loads (exactly: count == 0 && push -> cmd_q; pop && count > 1 ->
  // fifo[rp + 1]; pop && count == 1 && push -> cmd_q; else hold)
  for (integer e = 0; e < 8; e = e + 1) begin
   if (ctl_ws_qv[e]) fifo[e][13:0] <= cmd_q[13:0];
   if (ctl_ws_qv[8 + e]) fifo[e][27:14] <= cmd_q[27:14];
   if (ctl_ws_qv[16 + e]) begin fifo[e][31:28] <= cmd_q[31:28]; first_fifo[e] <= first_q; end
  end
''' + _hg(0, 'head[13:0]', 'ctl_a1_0', 'cmd_q[13:0]') + _hg(1, 'head[27:14]', 'ctl_a1_1', 'cmd_q[27:14]')
     + _hg(2, 'head[31:28]', 'ctl_a1_2[13:10]', 'cmd_q[31:28]') + _hg(2, 'head_first', 'ctl_a1_2[9:0]', 'first_q')),
    (' output reg row_v,output reg [2:0] row_op,output reg [4:0] row_bank,',
     ' output reg row_v,output reg [2:0] row_op,output reg [4:0] row_bank,\n'
     ' output reg [31:0] row_act_oh,   // KV-PC5: == {32{row_v && row_op == ACT}} & onehot(row_bank), registered'),
    ('   row_v<=0;col_v<=0;col_we<=0;busy<=0;fault_q<=0;fault<=0;',
     '   row_v<=0;col_v<=0;col_we<=0;busy<=0;fault_q<=0;fault<=0;row_act_oh<=32\'b0;'),
    ('   row_v<=rv;col_v<=cv;col_we<=cwe;busy<=core_busy;',
     "   row_v<=rv;col_v<=cv;col_we<=cwe;busy<=core_busy;row_act_oh<=(rv && rop==3'd1) ? (32'b1 << rb) : 32'b0;"),
    (''' always @(posedge clk) begin
  cmd_q<=cmd;first_q<=cmd_first;''',
     ''' wire [13:0] ctl_a1_0 = ''' + _rd(0, 0, 14, 'fifo') + ''';
 wire [13:0] ctl_a1_1 = ''' + _rd(1, 14, 14, 'fifo') + ''';
 wire [3:0] ctl_a1_2h = ''' + _rd(2, 28, 4, 'fifo') + ''';
 wire [9:0] ctl_a1_2l = ''' + _rd(2, 0, 10, 'first_fifo') + ''';
 wire [13:0] ctl_a1_2 = {ctl_a1_2h, ctl_a1_2l};
 always @(posedge clk) begin
  cmd_q<=cmd;first_q<=cmd_first;'''),
    ('''   if(pop) rp<=rp+1'b1;''', '''   rp<=ctl_rp_nx;'''),
]


CLONES = [
    # (file, original module, clone name, [(old, new), ...], [kept copy families])
    (FAN, 'qkd_static_kv_pc_path_fan_nc_b', 'qkd_kvpc_s_fan_nc_b',
     [('qkd_static_kv_pc_path_emb_nc_b #(.MU(MU)) u_pce (', 'qkd_kvpc_s_emb_nc_b #(.MU(MU)) u_pce ('),
      ('    qkd_kv_pc_chain_station_b u_chain (', '    qkd_kvpc_s_chain u_chain (')]),
    (FAN, 'qkd_static_kv_pc_path_emb_nc_b', 'qkd_kvpc_s_emb_nc_b',
     [('qkd_static_kv_pc_path_nc #(.MU(MU)) u_path (', 'qkd_kvpc_s_path_nc #(.MU(MU)) u_path ('),
      ('    qkd_static_kv_pc_es_merge_b u_esm (', '    qkd_kvpc_s_esm u_esm (')]),
    (PATH, 'qkd_static_kv_pc_path_nc', 'qkd_kvpc_s_path_nc',
     [('qkd_ctrl_pc_host_static_nc #(', 'qkd_kvpc_s_ctrl #('),
      ('qkd_kv_hbm_elastic_front_mc_nc #(', 'qkd_kvpc_s_front #('),
      ('qkd_static_kv_return_slots_mc_nc #(.DEPTH(8)) u_return (', 'qkd_kvpc_s_return #(.DEPTH(8)) u_return ('),
      ('    qkd_controller_hbm_calendar #(', '    qkd_kvpc_s_calendar #(')]),
    (CTRL, 'qkd_ctrl_pc_host_static_nc', 'qkd_kvpc_s_ctrl',
     [('    qkd_ctrl_pc_sched_nc #(', '    qkd_kvpc_s_sched #('),
      ('    qkd_ctrl_pc_cdc_child #(', '    qkd_kvpc_s_cdc_child #('),
      ('    qkd_ctrl_pc_obs_child #(', '    qkd_kvpc_s_obs_child #('),
      ('    qkd_ctrl_pc_port_child_nc #(', '    qkd_kvpc_s_port_child #('),
      ('    qkd_ctrl_pc_ecc_child u_ecc (', '    qkd_kvpc_s_ecc_child u_ecc (')]),
    (CTRL, 'qkd_ctrl_pc_sched_nc', 'qkd_kvpc_s_sched',
     SCHED + [('    ot_qkd_static_ctrl_pc_emb #(', '    ot_qkd_static_ctrl_pc_emb_kvpc_s #('),
              # KV-PC5: brow written by the registered ACT one-hot of u_ctl (was row_v && row_op == ACT decoded with
              # row_bank: 49-load enable nodes)
              ('    wire [18:0] row_row;\n', '    wire [18:0] row_row;\n    wire [31:0] row_act_oh;\n'),
              ('        .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row),',
               '        .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row), .row_act_oh(row_act_oh),'),
              ('        if (row_v && row_op == 3\'d1) brow[row_bank] <= row_row[7:0];',
               '        for (integer b = 0; b < 32; b = b + 1) if (row_act_oh[b]) brow[b] <= row_row[7:0];')],
     [('static_owner_q', 1, 3)]),
    (CORE, 'qkd_ctrl_pc_cdc_child', 'qkd_kvpc_s_cdc_child',
     [('ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (', 'ot_qkd_static_emb_cdc_kvpc_s #(.ENABLE(1)) u_ecdc (')],
     [('hr_q', 1, 2), ('rs_q', 1, 3)]),
    (CORE, 'qkd_ctrl_pc_obs_child', 'qkd_kvpc_s_obs_child', OBS_PO, [('hr_q', 1, 16)]),
    (CTRL, 'qkd_ctrl_pc_port_child_nc', 'qkd_kvpc_s_port_child',
     [('    ot_qfd_emb_pcport_nkw #(', '    ot_qfd_emb_pcport_nkw_kvpc_s #(')],
     [('rv_q', 1, 56), ('col_sr_q', 1, 2)]),
    (CTRL, 'ot_qfd_emb_pcport_nkw', 'ot_qfd_emb_pcport_nkw_kvpc_s',
     PORT_Y1 + [("    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;",
                 "    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;\n"
                 "    initial if (WA != 2 || RA != 6) $error(\"ot_qfd_emb_pcport_nkw_kvpc_s: kept copy widths assume WQD 4, RQD 64\");")],
     [('wr', 3, 49), ('wc1_st', 1, 24), ('v1', 1, 22), ('wc1_kv', 1, 13), ('kr', 7, 3), ('y1', 32, 4),
      ('kv_v', 1, 2, ('    output reg          kv_v,', '    output wire         kv_v,'))]),
    (CHILD, 'qkd_ctrl_pc_ecc_child', 'qkd_kvpc_s_ecc_child',
     [('    ot_qfd_kv_landing_ecc #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (',
       '    ot_qfd_kv_landing_ecc_kvpc_s #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (')]),
    (ECC, 'ot_qfd_kv_landing_ecc', 'ot_qfd_kv_landing_ecc_kvpc_s', [], [('p1_v', 1, 23)]),
    (CAL, 'qkd_controller_hbm_calendar', 'qkd_kvpc_s_calendar', [], [('rn', 1, 28), ('go_q', 1, 41)]),
    (UCTL, 'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_ctrl_pc_emb_kvpc_s',
     [(' ot_qkd_static_kv_timing #(', ' ot_qkd_static_kv_timing_kvpc_s #(')] + UCTL_PC5,
     [('rp', 3, 2),
      ('col_bank', 5, 11, ('output reg [4:0] col_bank,col_col,', 'output wire [4:0] col_bank,output reg [4:0] col_col,')),
      ('col_col', 5, 3, ('output reg [4:0] col_col,', 'output wire [4:0] col_col,')),
      ('row_row', 19, 2, ('output reg [18:0] row_row,', 'output wire [18:0] row_row,'))]),
    (TIM, 'ot_qkd_static_kv_timing', 'ot_qkd_static_kv_timing_kvpc_s',
     [("    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;",
       "    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;\n"
       "    initial if (SQW != 2 || WQW != 2) $error(\"ot_qkd_static_kv_timing_kvpc_s: kept copy widths assume SQD 4, WQ 4\");")] + TIM_PC5,
     [('sq_rp', 2, 2), ('wq_rp', 2, 2), ('wq_rp1', 2, 2), ('context_active', 1, 5), ('streaming', 1, 10),
      ('wq_n', 3, 3), ('c_s', 1, 2), ('wq_v', 4, 2)]),
    (CHAIN, 'qkd_kv_pc_chain_station_b', 'qkd_kvpc_s_chain', CHAIN_WES,
     [('rs_q', 1, 10), ('bt', 1, 12), ('ss', 1, 4), ('hit', 1, 11),
      ('emb_issue_v', 1, 4, ('    output reg           emb_issue_v,', '    output wire          emb_issue_v,'))]),
    (ESM, 'qkd_static_kv_pc_es_merge_b', 'qkd_kvpc_s_esm', ESM_HQ, [('own', 1, 11)]),
    (RHOP, 'qkd_embedding_static_return_hop', 'qkd_kvpc_s_rhop', [], [('ts_q', 1, 25)]),
    (RHEAD, 'qkd_embedding_static_return_head', 'qkd_kvpc_s_rhead', [], [('ts_q', 1, 25)]),
]


def module_text(path, name):
    t = (ROOT / path).read_text()
    m = re.search(rf'^module {re.escape(name)}\b', t, re.M)
    if not m:
        raise SystemExit(f'kv_pc_sram_gen: {name} not in {path}')
    e = re.compile(r'^endmodule\b.*$', re.M).search(t, m.end())
    return t[m.start():e.end()] + '\n'


def _expr_end(t, i):
    """index of the ';' ending the expression starting at i (paren / brace / bracket depth 0)"""
    d = 0
    while True:
        c = t[i]
        if c in '([{':
            d += 1
        elif c in ')]}':
            d -= 1
        elif c == ';' and d == 0:
            return i
        i += 1


def fam(t, new, name, W, N, port=None):
    """KV-PC SAFE item 3: register NAME (W bits) -> N kept identical copies, copy-major in NAME__qv, family attribute
    ot_rst_split (= W when W > 1: one family per bit position; physical/common_flow/ot_rst_copies spreads the loads,
    reset_relay_split / OT_RST_COPIES_WIDE).  Every full assignment 'NAME <= E;' becomes 'NAME__qv <= {N{NAME__f(E)}};'
    (NAME__f sizes E to W bits exactly as the assignment did); every read sees copy 0 through 'NAME' (a wire / the
    port).  port: (old header text, new header text) for an 'output reg' port.  Returns (text, assignments rewritten)."""
    rng = f'[{W - 1}:0] ' if W > 1 else ''
    attr = f'(* keep, ot_rst_split = {W} *)' if W > 1 else '(* keep, ot_rst_split *)'
    famdecl = (f'{attr} reg [{N * W - 1}:0] {name}__qv;   // KV-PC SAFE: {N} kept copies of {name}\n'
               f'    function {rng}{name}__f; input {rng}v; {name}__f = v; endfunction')
    if port:
        old, newh = port
        if t.count(old) != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}.{name}: port declaration found {t.count(old)} times')
        t = t.replace(old, newh)
        hdr_end = t.index(');', t.index(newh)) + 2
        t = t[:hdr_end] + f'\n    {famdecl}\n    assign {name} = {name}__qv[{W - 1}:0];' + t[hdr_end:]
    else:
        decl = re.compile(r'(?:(?<=\n)|(?<=;))([ \t]*(?:\(\*[^*]*\*\)[ \t]*)?reg\b[ \t]*(\[[^\]]*\][ \t]*)?)([^;]*);')
        hits = []
        for m in decl.finditer(t):
            ids = [x.strip() for x in m.group(3).split(',')]
            if name in ids:
                hits.append((m, ids))
        if len(hits) != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}.{name}: {len(hits)} reg declarations')
        m, ids = hits[0]
        rest = [x for x in ids if x != name]
        ind = re.match(r'[ \t]*', m.group(1)).group(0)
        keep = (m.group(1) + ', '.join(rest) + ';') if rest else ''
        rep = (keep + ('\n' if keep else '') + f'{ind}{famdecl}\n{ind}wire {rng}{name} = {name}__qv[{W - 1}:0];')
        t = t[:m.start()] + rep + t[m.end():]
    pat = re.compile(rf'(?<![\w.$\]\[])({re.escape(name)})(\s*)<=(?!=)')
    out, pos, n = [], 0, 0
    for m in pat.finditer(t):
        if m.start() < pos:
            continue
        j = m.start() - 1
        while j >= 0 and t[j] in ' \t\n':
            j -= 1
        w = re.search(r'(\w+)$', t[max(0, j - 12):j + 1])
        if not (t[j] in ';):' or (w and w.group(1) in ('begin', 'else', 'end'))):
            continue
        e = _expr_end(t, m.end())
        expr = t[m.end():e].strip()
        out.append(t[pos:m.start()])
        out.append(f'{name}__qv <= {{{N}{{{name}__f({expr})}}}};')
        pos = e + 1
        n += 1
    out.append(t[pos:])
    if n == 0:
        raise SystemExit(f'kv_pc_sram_gen: {new}.{name}: no assignment rewritten')
    return ''.join(out), n


FAM_LOG = []


def clone(path, name, new, subs, fams=()):
    t = module_text(path, name)
    t = re.sub(rf'^module {re.escape(name)}\b', f'module {new}', t, count=1, flags=re.M)
    for old, rep in subs:
        n = t.count(old)
        if n != 1:
            raise SystemExit(f'kv_pc_sram_gen: {new}: substitution site found {n} times:\n{old}')
        t = t.replace(old, rep)
    fl = []
    for f in fams:
        reg, W, N = f[:3]
        t, n = fam(t, new, reg, W, N, port=f[3] if len(f) > 3 else None)
        fl.append(f'{reg}[{W}]x{N}({n})')
    FAM_LOG.append((new, fl))
    fs = f'; kept copy families {", ".join(fl)}' if fl else ''
    return f'// ---- {new}: clone of {name} ({path}) with {len(subs)} substitution(s){fs} ----\n' + t


# KV-PC2 10-19 edits (edaed078e / dc3010ee5 were applied to the generated file by hand; KV-PC3 moved them here so the
# generator reproduces the committed output again).  Exact-once substitutions on the rendered text, after the copy
# families are expanded (the streaming master + identical-D restructure reads the expanded streaming__qv names).
POST = [
    ("    (* keep, ot_rst_split *) reg [127:0] hgo_qv;",
     "    // (KV-PC2: 64 -> 72: gate 164813 measured 2178 loads = 35 / copy at 64; KV-PC5: 72 -> 128 for the static-queue\n"
     "    // lookahead / freeze registers)\n"
     "    (* keep, ot_rst_split *) reg [127:0] hgo_qv;"),
    ("// KV-PC SAFE: 56 kept copies of rv_q\n",
     "// KV-PC SAFE: 56 kept copies of rv_q (KV-PC2: 27 -> 56, 1576 loads = 59 / copy at 27)\n"),
    ("// KV-PC SAFE: 10 kept copies of streaming\n",
     "// KV-PC SAFE: 10 kept copies of streaming (KV-PC2: 7 -> 10, 264 loads = 38 / copy at 7)\n"),
    ("""    assign busy = streaming; assign ref_fault = fault_r;
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        streaming__qv <= {10{streaming__f(0)}};v_consumer_order<=0;""",
     """    assign busy = streaming; assign ref_fault = fault_r;
    // KV-PC2: streaming as master + identical copies.  The copies' hold term was each copy's own Q (bit 0 became a
    // DFFE, the rest plain DFF: ot_rst_copies REFUSED the family, gate 164813).  Now one master streaming_m holds the
    // state; every copy loads streaming_nx each edge (identical D), and the copies drive the loads.
    (* keep *) reg streaming_m;
    wire streaming_nx = (desc_v && !streaming && !fault_r) ? (desc_n != 0) :
                        (rd_ok && (context_active ? ordinal+9'd1==context_count : j==nm1)) ? 1'b0 : streaming_m;
    always @(posedge clk or negedge rst_n)
      if (!rst_n) begin streaming_m <= 1'b0; streaming__qv <= {10{streaming__f(0)}}; end
      else begin streaming_m <= streaming_nx; streaming__qv <= {10{streaming__f(streaming_nx)}}; end
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        v_consumer_order<=0;"""),
    ("          if (context_active ? ordinal+9'd1==context_count : j==nm1) streaming__qv <= {10{streaming__f(0)}};\n",
     "          // (streaming end: streaming_nx)\n"),
    ("          streaming__qv <= {10{streaming__f((desc_n != 0))}}; nm1 <= desc_n - 11'd1;",
     "          nm1 <= desc_n - 11'd1;"),
    # KV-PC3 sr6 (scratch CTS rerun of gate pc_h_sr3 164813 with the hck boundary re-applied): the two remaining
    # input cones that are not flop-direct fail their own-domain 0.2 T budget -- pc__ki -> kcmd tap (o_v / o_d / tc_d,
    # 3 levels + wire: TT setup -181 ps at u_tap.o_v) and x__est__0_1 -> u_emb boot_ready -> emb_fault (-168 ps).
    # Both land in face registers (no reset; consumers keep their own resets): +1 hclk edge on the kc kick chain per PC
    # tile (handed to the die schedule / KV-GEN9) and +1 ck edge on the embedding boot-ready level.
    ("    ot_qkvd_kcmd_tap #(.ROW0(ROW0)) u_tap (.clk(hclk), .rst_n(h_rn), .i_v(ki[0]), .i_d(ki[32:1]),",
     """    // KV-PC3 sr6: kc kick word landing register (pin register at the N face; +1 hclk edge, priced)
    reg [32:0] ki_q;
`ifdef OT_KVPC_LAND_MUT
    always @(*) ki_q = ki;                                         // bench mutant: landing bypassed
`else
    always @(posedge hclk) ki_q <= ki;
`endif
    ot_qkvd_kcmd_tap #(.ROW0(ROW0)) u_tap (.clk(hclk), .rst_n(h_rn), .i_v(ki_q[0]), .i_d(ki_q[32:1]),"""),
    ("    // phase: own = boot window (the slice owns the controller face)\n",
     """    // KV-PC3 sr6: embedding boot-ready level landing register (pin register; +1 ck edge on a level)
    reg ebr_q;
`ifdef OT_KVPC_LAND_MUT
    always @(*) ebr_q = emb_boot_ready;                            // bench mutant: landing bypassed
`else
    always @(posedge ck) ebr_q <= emb_boot_ready;
`endif
    // phase: own = boot window (the slice owns the controller face)
"""),
    ("own__f(!emb_boot_ready)", "own__f(!ebr_q)"),
    (".boot_ready(emb_boot_ready), .strap_stack(cfg_stack)", ".boot_ready(ebr_q), .strap_stack(cfg_stack)"),
]


def post(t):
    for old, rep in POST:
        n = t.count(old)
        if n != 1:
            raise SystemExit(f'kv_pc_sram_gen: POST substitution site found {n} times:\\n{old}')
        t = t.replace(old, rep)
    return t


def render():
    hdr = ['`timescale 1ns/1ps',
           '// GENERATED by tools/qwen_kv_die/kv_pc_sram_gen.py -- do not edit.  KV-PC 2026-10-19 SAFE redesign: the PC path',
           '// clone chain on the SRAM-backed storage of qkd_kvpc_sram_1019.sv.  Each module below is its original verbatim',
           '// except for the listed substitutions (instance module names; in qkd_kvpc_s_sched the tag queue and the',
           f'// replicated hr_q ({NHR}) / hgo ({NHGO}) roots).',
           '`ifndef OT_KVPC_SRAM_CLONES_1019_SV', '`define OT_KVPC_SRAM_CLONES_1019_SV', '']
    body = [LEAF] + [clone(*c) for c in CLONES]
    return post('\n'.join(hdr) + '\n'.join(body) + '`endif\n')


RL_TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv'
SR_TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl_sr.sv'


def sr_tile():
    """the OT_KV_PC_SRAM tile file = kv_static_die.pc_sram_text applied to the pc / pc_h modules of the committed _rl
    file (the die GEN with OT_KV_PC_RLAND=1 OT_KV_PC_SRAM=1 produces the same modules)"""
    import ast
    src = (ROOT / 'tools/qwen_kv_die/kv_static_die.py').read_text()
    import os
    ns = {'PC_RLAND': True, 're': re, 'os': os}
    for n in ast.parse(src).body:     # the two text functions + the module-level PC_* constants they read
        if (isinstance(n, ast.FunctionDef) and n.name in ('pc_sram_text', 'pc_hfx_text')) or (
                isinstance(n, ast.Assign) and all(isinstance(x, ast.Name) and x.id.startswith('PC_') for x in n.targets)):
            exec(ast.get_source_segment(src, n), ns)
    ns['PC_RLAND'] = True
    t = (ROOT / RL_TILE).read_text()
    for m in ('qkd_kvs_pc', 'qkd_kvs_pc_h'):
        a = re.search(rf'^module {m} \(', t, re.M).start()
        b = t.index('endmodule\n', a) + len('endmodule\n')
        t = t[:a] + ns['pc_sram_text'](t[a:b]) + t[b:]
    return t.replace('// KVJ-G2 2026-10-17:', '// KV-PC 2026-10-19 OT_KV_PC_SRAM=1 (pc / pc_h: kv_static_die.pc_sram_text; kv_pc_sram_gen.py).\n'
                     '// KVJ-G2 2026-10-17:', 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = {OUT: render(), SR_TILE: sr_tile()}
    if a.check:
        bad = [o for o, txt in outs.items() if not (ROOT / o).exists() or (ROOT / o).read_text() != txt]
        print('kv_pc_sram_gen: ' + ('UP TO DATE' if not bad else f'STALE {bad}'))
        return 1 if bad else 0
    for o, txt in outs.items():
        (ROOT / o).write_text(txt)
        print(f'kv_pc_sram_gen: wrote {o} ({len(txt.splitlines())} lines)')
    for new, fl in FAM_LOG:
        if fl:
            print(f'  {new}: {", ".join(fl)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
