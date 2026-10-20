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
NHGO = 72      # u_ctl strap-release (hgo) copies: 1994 async-reset loads -> <= 32 each
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
     "    // KV-PC SAFE: hq[0] (the slice word valid, 310 loads) as 24 kept copies (KV-PC5-C: 13 -> 24); hq[287:1] plain\n"
     "    reg [287:1] hq_d;\n"
     "    (* keep, ot_rst_split *) reg [23:0] hq0__qv;\n"
     "    wire [287:0] hq = {hq_d, hq0__qv[0]};\n"
     "    always @(posedge ck) hq_d[287:1] <= hes[287:1];\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) hq0__qv <= 24'd0; else hq0__qv <= {24{hes[0]}};"),
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

# ---- KV-PC5-C (10-20) native32 PORT rewrite (census f1 qkd_kvs_pc_sr7-20261020-022436: wr_static 751, wq write decode
# 572/546x3, hr_q 302, rv_q copies 58 x25 + pc__pi[0] 57, y1 copies 59..66, col_sr_q 48, wr enables 49).  Same ports and
# same function as ot_qfd_emb_pcport_nkw / qkd_ctrl_pc_port_child_nc (lockstep benches ctrl / path / tile), no added
# edge.  Every wide enable / select is a slice of <= 15 bits driven by its OWN kept register copy (direct references:
# no ot_rst_split re-pointing, which weighs a mapped 2-pin enable as one load):
#   * child lookahead copies (registered one edge early from the child's own inputs, reset 0 = f(reset state)):
#     rvk[22:0] = r_v (kv_d 20 x <=15-bit slices, kr copies + kv_v/v1/k fault), wsk[29:0] = wr_static,
#     wvk[29:0] = w_v (29 x <= 10-bit wq write / st1_wd / s2_wd slices + master), rik[4:0] = rd_issue, csk[4:0] = col_sr;
#   * per-slice pointer copies wwv / kwv / krq / rsel advance on their own enable copy (identical values by induction:
#     same reset, same enable value every edge);
#   * c1 / y1 capture every edge: they are read only under v1, the edge after r_v (exact; em_d unchanged);
#   * the SECDED correction reads four syndrome copies per lane, each for 16 data positions;
#   * hr_q (reset capture, 302+ async loads) is a 24-copy ot_rst_split family (reset pins weigh 1 each: exact).
PORT_CHILD_TXT = r'''module qkd_kvpc_s_port_child #(
    parameter integer RQD = 64,
    parameter integer MUT = 0
) (
    input  wire         hclk,
    input  wire         hrst,
    input  wire         col_v_e, col_we_e, col_sr_e,   // one edge early
    input  wire         w_v,
    input  wire [255:0] w_d,
    input  wire [288:0] pi,
    output wire [287:0] wd,
    output wire         kv_v,
    output wire [287:0] kv_d,
    output wire         em_v,
    output wire [257:0] em_d,
    output wire         fault
);
    (* keep, ot_rst_split *) reg [23:0] hr_q__qv;      // KV-PC5-C: reset capture as 24 kept identical copies
    always @(posedge hclk) hr_q__qv <= {24{hrst}};
    wire h_rn = hr_q__qv[0];
    (* keep *) reg col_v_q, col_we_q, w_v_q;
    (* keep *) reg [4:0] csk;                           // col_sr_q copies: [0] wr_static / wr_kv, [1..4] kq data
    (* keep *) reg [22:0] rvk;                          // rv_q copies (pi[0] -> 23 loads + the sched rv_q)
    (* keep *) reg [29:0] wsk, wvk;                     // wr_static / w_v lookahead copies
    (* keep *) reg [4:0] rik;                           // rd_issue lookahead copies
    (* keep *) reg [287:0] rd_q;
    (* keep *) reg [255:0] w_d_q;
    always @(posedge hclk or negedge h_rn)
        if (!h_rn) begin
            rvk <= 23'd0; col_v_q <= 1'b0; col_we_q <= 1'b0; csk <= 5'd0; w_v_q <= 1'b0;
            wsk <= 30'd0; wvk <= 30'd0; rik <= 5'd0;
        end else begin
            rvk <= {23{pi[0]}}; col_v_q <= col_v_e; col_we_q <= col_we_e; csk <= {5{col_sr_e}}; w_v_q <= w_v;
            wsk <= {30{col_v_e && col_we_e && col_sr_e}}; wvk <= {30{w_v}}; rik <= {5{col_v_e && !col_we_e}};
        end
    always @(posedge hclk) begin rd_q <= pi[288:1]; w_d_q <= w_d; end
    ot_qfd_emb_pcport_nkw_kvpc_s #(.RQD(RQD), .MUT(MUT)) u_port (
        .clk(hclk), .rst_n(h_rn), .col_v(col_v_q), .col_we(col_we_q), .csk(csk),
        .wvk(wvk), .w_d(w_d_q), .wd(wd), .wsk(wsk), .rik(rik),
        .rvk(rvk), .r_d(rd_q), .kv_v(kv_v), .kv_d(kv_d), .em_v(em_v), .em_d(em_d), .fault(fault));
endmodule
'''

PORT_HEAD = r'''module ot_qfd_emb_pcport_nkw_kvpc_s #(
    parameter integer RQD = 32,
    parameter integer WQD = 4,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         col_v,
    input  wire         col_we,
    input  wire [4:0]   csk,              // col_sr copies
    input  wire [29:0]  wvk,              // w_v copies (29 slices + master)
    input  wire [255:0] w_d,
    output wire [287:0] wd,
    input  wire [29:0]  wsk,              // wr_static = col_v && col_we && col_sr, registered one edge early
    input  wire [4:0]   rik,              // rd_issue = col_v && !col_we, registered one edge early
    input  wire [22:0]  rvk,              // r_v copies
    input  wire [287:0] r_d,
    output wire         kv_v,
    output reg  [287:0] kv_d,
    output reg          em_v,
    output reg  [257:0] em_d,             // {ue, ce, data}
    output reg          fault
);
'''

PORT_BODY = r'''
  // KV-PC5-C: cor64 with the corrected-position decode split over four syndrome copies (data positions 16k..16k+15
  // read copy k; ue / ce read copy 0).  d_j = code[p_j-1] ^ (ov && sy == p_j); ce = ov && sy <= 71;
  // ue = sy != 0 && !(ov && sy <= 71): exactly cor64.
  function automatic [65:0] cor64q(input [71:0] code, input [7:0] s0, input [7:0] s1, input [7:0] s2, input [7:0] s3);
    reg [7:0] so; reg [63:0] d; integer p, j;
    begin
      d = '0; j = 0;
      for (p = 1; p <= 71; p = p + 1)
        if ((p & (p - 1)) != 0) begin
          so = (j < 16) ? s0 : (j < 32) ? s1 : (j < 48) ? s2 : s3;
          d[j] = code[p-1] ^ (so[0] && so[7:1] == 7'(p));
          j = j + 1;
        end
      cor64q = {(s0[7:1] != 7'd0) && !(s0[0] && s0[7:1] <= 7'd71), s0[0] && s0[7:1] <= 7'd71, d};
    end
  endfunction

    localparam integer RA = $clog2(RQD);
    localparam integer WA = (WQD > 1) ? $clog2(WQD) : 1;
    localparam integer NS = 29, SW = 10;              // wq / st1_wd / s2_wd slices (28 x 10 + 8; census c2: 12-bit slices 33)
    localparam integer NK = 20, KW = 15;              // kv_d slices (19 x 15 + 3)
    initial if (WA != 2 || RA != 6) $error("ot_qfd_emb_pcport_nkw_kvpc_s: copy layout assumes WQD 4, RQD 64");
    reg [RQD-1:0] kq;
    // pointer copies: kwv (4 kq write decode quarters, copy 0 = master), krq (4 read quarters) / krc, wrv / wwv per slice + master
    (* keep *) reg [4*(RA+1)-1:0] kwv;          // copy e = kwv[e*(RA+1) +: RA+1]
    (* keep *) reg [RA:0] krc;
    (* keep *) reg [4*(RA+1)-1:0] krq;            // kq read quarter copies (quarter e = krq[e*(RA+1) +: RA+1])
    (* keep *) reg [(NS+1)*(WA+1)-1:0] wwv;      // copy g = [g*(WA+1) +: WA+1]
    (* keep *) reg [WA:0] wrm;                    // wr master (w_empty / w_full); slices read rsel
    wire [RA:0] kw = kwv[0 +: RA+1], kr = krc;
    wire [WA:0] ww = wwv[NS*(WA+1) +: WA+1], wr = wrm;
    wire r_v = rvk[22];
    wire w_v = wvk[NS];
    wire rd_issue = rik[4];
    wire wr_static = wsk[NS];
    wire wr_kv = col_v && col_we && !csk[0];      // no KV write data source: a KV WR column is a fault
    wire k_empty = kw == kr;
    wire k_full = (kw[RA-1:0] == kr[RA-1:0]) && (kw[RA] != kr[RA]);
    wire w_empty = ww == wr;
    wire w_full = (ww[WA-1:0] == wr[WA-1:0]) && (ww[WA] != wr[WA]);
    // cls = kq[kr]: four 16:1 muxes (one krq copy each), then 4:1 on krc[5:4]
    wire [3:0] clsq;
    assign clsq[0] = kq[{2'd0, krq[0*(RA+1) +: 4]}]; assign clsq[1] = kq[{2'd1, krq[1*(RA+1) +: 4]}];
    assign clsq[2] = kq[{2'd2, krq[2*(RA+1) +: 4]}]; assign clsq[3] = kq[{2'd3, krq[3*(RA+1) +: 4]}];
    wire cls = clsq[krc[5:4]];
    (* keep, ot_rst_split *) reg [3:0] kv_v__qv; assign kv_v = kv_v__qv[0];   // 44 loads in u_ctrl (census c1)
    (* keep *) reg [NS-1:0] wc1_kvk, wc1_stk;     // KVW 2 timing: wd two edges after every WR column
    (* keep, ot_rst_split *) reg [21:0] v1__qv;  // v1 enables em_d (258 b): 22 kept copies (unchanged)
    wire v1 = v1__qv[0];
    reg [287:0] st1_wd, s2_wd, c1;
    assign wd = s2_wd;
    (* keep *) reg [127:0] y1k;                   // syndrome copies: lane i copy k = y1k[(i*4+k)*8 +: 8]
    integer i;
    genvar g, e;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            krq <= 0; krc <= 0; wrm <= 0; kv_v__qv <= 4'd0; em_v <= 1'b0; v1__qv <= 22'd0; fault <= 1'b0;
        end else begin
            if (rd_issue && k_full) fault <= 1'b1;
            if (rvk[20]) begin krq[0 +: RA+1] <= krq[0 +: RA+1] + 1'b1; krq[RA+1 +: RA+1] <= krq[RA+1 +: RA+1] + 1'b1; end
            if (rvk[21]) begin krq[2*(RA+1) +: RA+1] <= krq[2*(RA+1) +: RA+1] + 1'b1;
                               krq[3*(RA+1) +: RA+1] <= krq[3*(RA+1) +: RA+1] + 1'b1; end
            if (r_v) begin krc <= krc + 1'b1; if (k_empty) fault <= 1'b1; end
            kv_v__qv <= {4{r_v && !cls}};
            v1__qv <= {22{r_v && cls}};
            em_v <= v1;
            if (w_v && w_full) fault <= 1'b1;
            if (wr_static) begin wrm <= wrm + 1'b1; if (w_empty) fault <= 1'b1; end
            if (wc1_kvk[0]) fault <= 1'b1;
        end
    for (e = 0; e < 4; e = e + 1) begin : g_kw
        always @(posedge clk or negedge rst_n)
            if (!rst_n) kwv[e*(RA+1) +: RA+1] <= 0; else if (rik[e]) kwv[e*(RA+1) +: RA+1] <= kwv[e*(RA+1) +: RA+1] + 1'b1;
        for (g = 0; g < 16; g = g + 1) begin : g_kq
            always @(posedge clk) if (rik[e] && kwv[e*(RA+1) +: RA] == RA'(e * 16 + g)) kq[e * 16 + g] <= csk[1 + e];
        end
    end
    for (g = 0; g <= NS; g = g + 1) begin : g_wp
        always @(posedge clk or negedge rst_n)
            if (!rst_n) wwv[g*(WA+1) +: WA+1] <= 0;
            else if (wvk[g]) wwv[g*(WA+1) +: WA+1] <= wwv[g*(WA+1) +: WA+1] + 1'b1;
    end
    wire [287:0] wenc = enc256(w_d);
    for (g = 0; g < NS; g = g + 1) begin : g_ws
        localparam integer LO = g * SW, WD = (288 - LO < SW) ? 288 - LO : SW;
        reg [WD-1:0] wq0, wq1, wq2, wq3;
        // read select one-hot of wr[1:0] (census c1: the binary wr copy bit 0 drove 51 mux pins), rotates with wr
        (* keep *) reg [3:0] rsel;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rsel <= 4'b0001; else if (wsk[g]) rsel <= {rsel[2:0], rsel[3]};
        always @(posedge clk) begin
            if (wvk[g] && wwv[g*(WA+1) +: WA] == 2'd0) wq0 <= wenc[LO +: WD];
            if (wvk[g] && wwv[g*(WA+1) +: WA] == 2'd1) wq1 <= wenc[LO +: WD];
            if (wvk[g] && wwv[g*(WA+1) +: WA] == 2'd2) wq2 <= wenc[LO +: WD];
`ifdef OT_KVPC5_TAP_MUT
            if (wvk[g] && wwv[g*(WA+1) +: WA] == 2'd3) wq3 <= (g == 7) ? ~wenc[LO +: WD] : wenc[LO +: WD];   // bench mutant
`else
            if (wvk[g] && wwv[g*(WA+1) +: WA] == 2'd3) wq3 <= wenc[LO +: WD];
`endif
            if (wsk[g]) st1_wd[LO +: WD] <= ({WD{rsel[0]}} & wq0) | ({WD{rsel[1]}} & wq1) |
                                              ({WD{rsel[2]}} & wq2) | ({WD{rsel[3]}} & wq3);
            if (wc1_kvk[g]) s2_wd[LO +: WD] <= {WD{1'b0}}; else if (wc1_stk[g]) s2_wd[LO +: WD] <= st1_wd[LO +: WD];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wc1_kvk[g] <= 1'b0; wc1_stk[g] <= 1'b0; end
            else begin wc1_kvk[g] <= wr_kv; wc1_stk[g] <= wsk[g]; end
    end
    for (g = 0; g < NK; g = g + 1) begin : g_kv
        localparam integer LO = g * KW, WD = (288 - LO < KW) ? 288 - LO : KW;
        always @(posedge clk) if (rvk[g]) kv_d[LO +: WD] <= r_d[LO +: WD];
    end
    always @(posedge clk) begin : dp
        reg [65:0] dc; reg ue, ce; reg [255:0] d;
        c1 <= r_d;                                                   // read only under v1 (the edge after r_v)
        for (i = 0; i < 4; i = i + 1) y1k[i*32 +: 32] <= {4{syn64(r_d[i*72 +: 72])}};
        ue = 1'b0; ce = 1'b0;
        for (i = 0; i < 4; i = i + 1) begin
            if (MUT == 3) dc = cor64q(c1[i*72 +: 72], 8'd0, 8'd0, 8'd0, 8'd0);
            else dc = cor64q(c1[i*72 +: 72], y1k[(i*4+0)*8 +: 8], y1k[(i*4+1)*8 +: 8], y1k[(i*4+2)*8 +: 8],
                             y1k[(i*4+3)*8 +: 8]);
            d[i*64 +: 64] = dc[63:0]; ue = ue | dc[65]; ce = ce | dc[64];
        end
        if (v1) em_d <= {ue, ce, d};
    end
endmodule
'''


# KV-PC5-C chain station: the generated clone of qkd_kv_pc_chain_station_b (CHAIN_WES + families) with the sliced
# native32 taps, rs_q 14 copies and emb_scale 3 copies (see the comments in the text)
CHAIN_TXT = r'''module qkd_kvpc_s_chain #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [4:0]    pc,
    input  wire [1:0]    cfg_stack,
    input  wire [779:0]  di,
    output wire [779:0]  dout,
    // BOOT: this PC's HOST slice landing face (qkd_host_pc_slice_die land_es / land_er, unchanged slice)
    output reg  [287:0]  land_es,
    input  wire [260:0]  land_er,
    // PC face: writer word + intake context / expected descriptor
    output wire [287:0]  wes,
    output wire [317:0]  es_context,
    output reg           es_expected_valid,
    output reg  [60:0]   es_expected_identity,
    output reg  [28:0]   es_expected_address,
    output reg  [4:0]    es_expected_pc,
    output reg  [1:0]    es_expected_stack,
    // PC face: embedding read issue (qkd_static_kv_pc_es_merge)
    output wire          emb_issue_v,
    output reg  [17:0]   emb_token,
    output reg  [5:0]    emb_word_index,
    output reg           emb_half,
    output wire          emb_scale,
    output reg  [15:0]   emb_epoch,
    output reg           emb_return_slot,
    // the PC's return station
    output reg           capture_slot,
    output reg           transfer_slot,
    output reg           fault
);
    // KV-PC5-C: emb_scale (45 loads) = 3 kept copies with an identical D (master emb_scale_m holds the state)
    (* keep, ot_rst_split *) reg [2:0] emb_scale__qv;
    assign emb_scale = emb_scale__qv[0];
    (* keep *) reg emb_scale_m;
    wire emb_scale_nx;
    (* keep, ot_rst_split *) reg [3:0] emb_issue_v__qv;   // KV-PC SAFE: 4 kept copies of emb_issue_v
    function emb_issue_v__f; input v; emb_issue_v__f = v; endfunction
    assign emb_issue_v = emb_issue_v__qv[0:0];
    localparam integer F_V = 0, F_PC0 = 2, F_PC1 = 7, F_D0 = 12, F_D1 = 268, F_AD = 524, F_SV = 553, F_CTX = 554,
                       F_EV = 615, F_EPC0 = 617, F_EPC1 = 622, F_EST = 627, F_EID = 629, F_EAD = 690,
                       F_SS = 719, F_TOK = 720, F_EP = 738, F_CV = 754, F_CPC = 755, F_CRG = 760, F_CVL = 763, F_BT = 779,
                       W = 780;
    (* keep, ot_rst_split *) reg [13:0] rs_q__qv;   // KV-PC SAFE: 14 kept copies of rs_q (KV-PC5-C: 10 -> 14)
    function rs_q__f; input v; rs_q__f = v; endfunction
    wire rs_q = rs_q__qv[0:0];
    // KV-PC SAFE: wes[0] (the es valid, 575 loads in the controller CDC intake) as 24 kept copies; wes[287:1] plain
    reg [287:1] wes_d;   // KV-PC5-C: = hq[286:0] (sliced tap below)
    (* keep, ot_rst_split *) reg [23:0] wes0__qv;
    assign wes = {wes_d, wes0__qv[0]};
    always @(posedge ck) rs_q__qv <= {14{rs_q__f(rst_n)}};
    // ---- the hop register (pin flop) ----
    reg [W-1:0] c;
    always @(posedge ck) c[W-1:F_V+2] <= di[W-1:F_V+2];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) c[F_V +: 2] <= 2'd0; else c[F_V +: 2] <= di[F_V +: 2];
    // valid-type control bits that are not data-qualified: register with reset
    reg ev0, ev1, cv;
    (* keep, ot_rst_split *) reg [3:0] ss__qv;   // KV-PC SAFE: 4 kept copies of ss
    function ss__f; input v; ss__f = v; endfunction
    wire ss = ss__qv[0:0];
    (* keep, ot_rst_split *) reg [11:0] bt__qv;   // KV-PC SAFE: 12 kept copies of bt
    function bt__f; input v; bt__f = v; endfunction
    wire bt = bt__qv[0:0];
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ev0 <= 1'b0; ev1 <= 1'b0; ss__qv <= {4{ss__f(1'b0)}}; cv <= 1'b0; bt__qv <= {12{bt__f(1'b0)}}; end
        else begin ev0 <= di[F_EV]; ev1 <= di[F_EV + 1]; ss__qv <= {4{ss__f(di[F_SS])}}; cv <= di[F_CV]; bt__qv <= {12{bt__f(di[F_BT])}}; end
    assign dout = {bt, c[F_BT-1:F_CV+1], cv, c[F_CV-1:F_SS+1], ss, c[F_SS-1:F_EV+2], ev1, ev0, c[F_EV-1:0]};
    // ---- identity strap registers (HKV-PCH 2026-10-19) ----
    // pc / cfg_stack are die-top identity straps (kv_static_die cls strap: constants on the die).  Unregistered they
    // reached ~1,100 tap enables (wes / land_es / ctx / eid / r[] / emb_*) straight from the tile pins inside the
    // 0.2 T input budget (qkd_kvs_pc_h_k1 route eb7cbd435: TT -50.35, 1,131 input->register endpoints, all strap).
    // Registered here, every tap compare starts at a local flop.  Constant straps: identical behaviour from the first
    // edge (reset is held far longer); no edge age, calendar slot or die relay stage changes.
    (* keep *) reg [4:0] spc;
    (* keep *) reg [1:0] sst;
    always @(posedge ck) begin spc <= pc; sst <= cfg_stack; end
    // ---- (1) fan-out tap ----
    wire [4:0] pm = (MUT == 1) ? 5'h0f : 5'h1f;
    wire h0 = c[F_V]     && ((c[F_PC0 +: 5] & pm) == (spc & pm));
    wire h1 = c[F_V + 1] && ((c[F_PC1 +: 5] & pm) == (spc & pm));
    wire x0 = ev0 && c[F_EPC0 +: 5] == spc;
    wire x1 = ev1 && c[F_EPC1 +: 5] == spc;
    (* keep, ot_rst_split *) reg [10:0] hit__qv;   // KV-PC SAFE: 11 kept copies of hit
    function hit__f; input v; hit__f = v; endfunction
    wire hit = hit__qv[0:0];                       // context valid (bit 317), lagged
    reg [60:0] ctx_id;
    // lag stage (CTX_LAG = 1): context / expected computed from the hop register one edge later than wes
    reg        hit_a, x_a; reg [60:0] ctx_a, eid_a; reg [28:0] ead_a; reg [4:0] epc_a; reg [1:0] est_a;   // ctx_a / eid_a / ead_a / epc_a / est_a: sliced taps
    // KV-PC5-C native32 taps (census f1: h0|h1 598 / 342, h0 select 256, x0|x1 104, bh 287 x2, bt copy 287): the wide
    // enabled captures are cut into <= 16-bit slices; slice g reads its OWN kept copies of the pin registers it
    // qualifies on (valid bits / bt, flop-direct from di like c, same reset), and each tap group has its own kept copy
    // of the PC-id fields for its match compare (the match gate then drives <= 22 slice gates).  Same edges, same
    // function: every copy is a register of the same di bit (identical from the first edge; the unreset id copies are
    // only read while a reset valid copy is set).
    localparam integer HN = 22, XN = 7, BN = 18, SL = 16;
    (* keep *) reg [HN-1:0] hv0k, hv1k;            // c[F_V] / c[F_V+1] copies (wes / ctx taps)
    (* keep *) reg [XN-1:0] xe0k, xe1k;            // ev0 / ev1 copies (expected taps)
    (* keep *) reg [BN-1:0] btk;                   // bt copies (boot tap)
    // PC-id field copies (5 per wes/boot group, 3 per expected group) x strap copies spck (5): slice g compares
    // field copy g%N with strap copy g/N, so every slice match is its own gate (census c1: one shared match gate
    // was absorbed into every enabled bit, 297 / 303 loads) while each field bit drives <= 11 flops.
    (* keep *) reg [24:0] hpc0k, hpc1k, bpc0k;
    (* keep *) reg [14:0] xpc0k, xpc1k;
    (* keep *) reg [24:0] spck;
    always @(posedge ck) begin
        hpc0k <= {5{di[F_PC0 +: 5]}}; hpc1k <= {5{di[F_PC1 +: 5]}}; bpc0k <= {5{di[F_PC0 +: 5]}};
        xpc0k <= {3{di[F_EPC0 +: 5]}}; xpc1k <= {3{di[F_EPC1 +: 5]}}; spck <= {5{pc}};
    end
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin hv0k <= 0; hv1k <= 0; xe0k <= 0; xe1k <= 0; btk <= 0; end
        else begin
            hv0k <= {HN{di[F_V]}}; hv1k <= {HN{di[F_V + 1]}}; xe0k <= {XN{di[F_EV]}}; xe1k <= {XN{di[F_EV + 1]}};
            btk <= {BN{di[F_BT]}};
        end
    // wes / ctx tap: {ctx_a 61, wes_d[287:1] 287} = 348 b, data A (h0) / B (h1) differ only in the 256 data bits
    reg [347:0] hq;
    wire [347:0] hdA = {c[F_CTX +: 61], c[F_SV], c[F_SV], c[F_AD +: 29], c[F_D0 +: 256]};
    wire [347:0] hdB = {c[F_CTX +: 61], c[F_SV], c[F_SV], c[F_AD +: 29], c[F_D1 +: 256]};
    always @(*) begin wes_d[287:1] = hq[286:0]; ctx_a = hq[347:287]; end
    // expected tap: {est 2, epc 5, ead 29, eid 61} = 97 b
    reg [96:0] xq;
    wire [96:0] xdA = {c[F_EST +: 2], c[F_EPC0 +: 5], c[F_EAD +: 29], c[F_EID +: 61]};
    wire [96:0] xdB = {c[F_EST +: 2], c[F_EPC1 +: 5], c[F_EAD +: 29], c[F_EID +: 61]};
    always @(*) begin est_a = xq[96:95]; epc_a = xq[94:90]; ead_a = xq[89:61]; eid_a = xq[60:0]; end
    genvar gs;
    for (gs = 0; gs < HN; gs = gs + 1) begin : g_ht
        localparam integer LO = gs * SL, WD = (348 - LO < SL) ? 348 - LO : SL;
        wire [4:0] sp = spck[(gs / 5) * 5 +: 5];
        wire g0 = hv0k[gs] && ((hpc0k[(gs % 5) * 5 +: 5] & pm) == (sp & pm));
        wire g1 = hv1k[gs] && ((hpc1k[(gs % 5) * 5 +: 5] & pm) == (sp & pm));
`ifdef OT_KVPC5_TAP_MUT
        always @(posedge ck) if (g0 | g1) hq[LO +: WD] <= (g0 && gs != 5) ? hdA[LO +: WD] : hdB[LO +: WD];   // bench mutant
`else
        always @(posedge ck) if (g0 | g1) hq[LO +: WD] <= g0 ? hdA[LO +: WD] : hdB[LO +: WD];
`endif
    end
    for (gs = 0; gs < XN; gs = gs + 1) begin : g_xt
        localparam integer LO = gs * SL, WD = (97 - LO < SL) ? 97 - LO : SL;
        wire [4:0] sp = spck[(gs / 3) * 5 +: 5];
        wire g0 = xe0k[gs] && (xpc0k[(gs % 3) * 5 +: 5] == sp), g1 = xe1k[gs] && (xpc1k[(gs % 3) * 5 +: 5] == sp);
        always @(posedge ck) if (g0 | g1) xq[LO +: WD] <= g0 ? xdA[LO +: WD] : xdB[LO +: WD];
    end
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin wes0__qv <= 24'd0; hit_a <= 1'b0; x_a <= 1'b0; end
        else begin wes0__qv <= {24{h0 | h1}}; hit_a <= h0 | h1; x_a <= x0 | x1; end
    generate
        if (MUT == 5) begin : g_nolag
            reg hit__nolag;   // KV-PC SAFE clone: hit is a kept copy family (the lag-free MUT 5 is not built)
            always @(*) begin hit__nolag = hit_a; ctx_id = ctx_a; es_expected_valid = x_a; es_expected_identity = eid_a;
                              es_expected_address = ead_a; es_expected_pc = epc_a; es_expected_stack = est_a; end
        end else begin : g_lag
            always @(posedge ck) begin
                ctx_id <= ctx_a; es_expected_identity <= eid_a; es_expected_address <= ead_a;
                es_expected_pc <= epc_a; es_expected_stack <= est_a;
            end
            always @(posedge ck or negedge rs_q)
                if (!rs_q) begin hit__qv <= {11{hit__f(1'b0)}}; es_expected_valid <= 1'b0; end
                else begin hit__qv <= {11{hit__f(hit_a)}}; es_expected_valid <= x_a; end
        end
    endgenerate
    assign es_context = {hit, ctx_id, {256{hit}}};
    // ---- (3) BOOT tap: the embedding boot word for this PC -> the HOST slice landing source (registered, +1), as the
    //      HOST static ABI word {we-data 1, we 1, bank, col, row, data 256, v} (= qkd_host_ingest_station host_es).
    //      land_er (the slice's landing return) lands on pin flops and is CHECKED, never waited on: the slice returns
    //      one credit (er[259]) per landing word it launches; a credit with none outstanding, a landing read return
    //      (no landing reads exist on the static die), the slice's fault bit (er[260]: its landing queue overflow is
    //      flagged there, exactly) or a counter overflow latch fault.  Static: no ready / wait (the gateway paces the
    //      boot stream; note.md).
    wire [4:0] bpm = (MUT == 6) ? 5'h0f : 5'h1f;
    wire bh = bt && ((c[F_PC0 +: 5] & bpm) == (spc & bpm));
    // KV-PC5-C: boot tap in BN <= 16-bit slices, slice g on its own bt copy (bh itself stays for land_es[0] / fault)
    wire [286:0] bdat = {1'b1, 1'b1, c[F_AD +: 29], c[F_D0 +: 256]};
    for (gs = 0; gs < BN; gs = gs + 1) begin : g_bt
        localparam integer LO = gs * SL, WD = (287 - LO < SL) ? 287 - LO : SL;
        wire [4:0] sp = spck[(gs / 5) * 5 +: 5];
        wire bm = (bpc0k[(gs % 5) * 5 +: 5] & bpm) == (sp & bpm);
        always @(posedge ck) if (btk[gs] && bm) land_es[1 + LO +: WD] <= bdat[LO +: WD];
    end
    always @(posedge ck or negedge rs_q) if (!rs_q) land_es[0] <= 1'b0; else land_es[0] <= bh;
    (* keep *) reg ler_v, ler_cr, ler_f;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin ler_v <= 1'b0; ler_cr <= 1'b0; ler_f <= 1'b0; end
        else begin ler_v <= land_er[0]; ler_cr <= land_er[259]; ler_f <= land_er[260]; end
    reg [2:0] bo;                         // boot words outstanding in the slice's landing queue
    reg       bfault;
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin bo <= 3'd0; bfault <= 1'b0; end
        else begin
            bo <= bo + {2'd0, land_es[0]} - {2'd0, ler_cr};
            if ((ler_cr && bo == 3'd0 && !land_es[0]) || (land_es[0] && !ler_cr && bo == 3'd7) || ler_v || ler_f)
                bfault <= 1'b1;
        end
    // ---- (2) embedding slot player ----
    reg [15:0] r [0:7];
    reg [15:0] cnt, last; reg act; reg [17:0] tok; reg [15:0] ep;
    wire home = tok[8:4] == spc && (MUT == 4 || tok[10:9] == sst);
    wire [15:0] trn = (MUT == 3 && spc == 5'd5) ? r[3] + 16'd1 : r[3];
    integer k;
    assign emb_scale_nx = (act && cnt == r[0]) ? 1'b0 : (act && home && cnt == r[4]) ? 1'b1 : emb_scale_m;
    always @(posedge ck) if (ss) begin tok <= c[F_TOK +: 18]; ep <= c[F_EP +: 16]; end
    always @(posedge ck or negedge rs_q)
        if (!rs_q) begin
            for (k = 0; k < 8; k = k + 1) r[k] <= 16'hffff;
            cnt <= 16'd0; last <= 16'd0; act <= 1'b0; fault <= 1'b0;
            emb_issue_v__qv <= {4{emb_issue_v__f(1'b0)}}; emb_return_slot <= 1'b0; capture_slot <= 1'b0; transfer_slot <= 1'b0;
            emb_token <= 18'd0; emb_epoch <= 16'd0; emb_word_index <= 6'd0; emb_half <= 1'b0; emb_scale__qv <= 3'd0; emb_scale_m <= 1'b0;
        end else begin
            if (cv && c[F_CPC +: 5] == spc) begin
                r[c[F_CRG +: 3]] <= c[F_CVL +: 16];
                if (c[F_CVL +: 16] != 16'hffff && c[F_CVL +: 16] > last) last <= c[F_CVL +: 16];
                if (act) fault <= 1'b1;
            end
            if (ss) begin
                if (act) fault <= 1'b1;
                act <= 1'b1; cnt <= 16'd0;
            end else if (act) begin
                cnt <= cnt + 16'd1;
                if (cnt == last) act <= 1'b0;      // the calendar ends on its last configured event
            end
            emb_token <= tok; emb_epoch <= ep;
            emb_issue_v__qv <= {4{emb_issue_v__f(act && (cnt == r[0] || (home && cnt == r[4])))}};
            emb_return_slot <= act && (cnt == r[1] || (home && cnt == r[5]));
            capture_slot    <= act && (cnt == r[2] || (home && cnt == r[6]));
            transfer_slot   <= act && (cnt == trn  || (home && cnt == r[7]));
            if (act && cnt == r[0]) begin emb_word_index <= {sst, spc[4:1]}; emb_half <= spc[0]; end
            else if (act && home && cnt == r[4]) begin emb_word_index <= 6'd0; emb_half <= 1'b0; end
            emb_scale_m <= emb_scale_nx; emb_scale__qv <= {3{emb_scale_nx}};
            if ((h0 && h1) || (x0 && x1) || bfault || (bh && (h0 || h1))) fault <= 1'b1;
        end
endmodule
'''


def port_text():
    """KV-PC5-C: the SECDED functions of the original port module verbatim + the native32 port body"""
    o = module_text(CTRL, 'ot_qfd_emb_pcport_nkw')
    a = o.index('  // ---- SECDED(72,64)')
    b = o.index('    localparam integer RA = $clog2(RQD);')
    return PORT_HEAD + o[a:b] + PORT_BODY


# (file, original module, sha256[:16] of the original text, new name, text function): hand rewrites of the same
# function (lockstep-benched against the original); the hash pins the original so a drift breaks the generator.
REWRITES = {
    'qkd_kvpc_s_port_child': (CTRL, 'qkd_ctrl_pc_port_child_nc', '15c8d96e67c4c788', lambda: PORT_CHILD_TXT),
    'ot_qfd_emb_pcport_nkw_kvpc_s': (CTRL, 'ot_qfd_emb_pcport_nkw', 'd6ea6f33c801240f', port_text),
    'qkd_kvpc_s_chain': (CHAIN, 'qkd_kv_pc_chain_station_b', '4d2ff98743d43d7b', lambda: CHAIN_TXT),
}


# KV-PC5-C: the embedding return-hold slices (strap h_d 259 b enable / beat_data 256 b select, census f1 479 / 495) read
# their own copies of er[0]: 20 kept er_v copies (erk) from the cdc child, carried up ctrl -> path -> emb_nc -> esm.
ERK_CDC = [
    ("    output wire [260:0] er,\n",
     "    output wire [260:0] er,\n    output wire [19:0]  erk,                           // KV-PC5-C: 20 kept copies of er_v (er[0])\n"),
    ("    reg          er_v, er_cr, er_f;\n",
     "    reg          er_v, er_cr, er_f;\n"
     "    (* keep *) reg [19:0] erk_q;                     // KV-PC5-C: er_v copies (same D, same reset)\n"
     "    assign erk = erk_q;\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) erk_q <= 20'd0; else erk_q <= {20{e_v}};\n"),
]
ERK_CTRL = [("    output wire [260:0] er,\n", "    output wire [260:0] er,\n    output wire [19:0]  erk,\n"),
            ("        .es(es), .er(er), .cfg_stack(cfg_stack),", "        .es(es), .er(er), .erk(erk), .cfg_stack(cfg_stack),")]
ERK_PATH = [("    output wire [260:0] er,\n", "    output wire [260:0] er,\n    output wire [19:0]  erk,\n"),
            ("        .er(er),\n", "        .er(er),\n        .erk(erk),\n")]
ERK_EMB = [("    output wire [260:0] er,\n", "    output wire [260:0] er,\n"),
           ("    qkd_static_kv_pc_es_merge_b u_esm (", "    wire [19:0] erk;                                   // KV-PC5-C: er_v copies (u_path -> u_esm)\n    qkd_static_kv_pc_es_merge_b u_esm ("),
           (".es(es_merged), .er(er),", ".es(es_merged), .er(er), .erk(erk),"),
           ("        .er(er),\n", "        .er(er),\n        .erk(erk),\n")]
ESM_ERK = [
    ("    input  wire [260:0]  er,\n", "    input  wire [260:0]  er,\n    input  wire [19:0]   erk,                          // KV-PC5-C: er[0] copies\n"),
    ("    (* keep *) reg rs_q;\n    always @(posedge ck) rs_q <= rst_n;\n",
     "    // KV-PC5-C: rs_q (36 loads) as 3 kept identical copies (ot_rst_split: reset pins weigh 1 each)\n"
     "    (* keep, ot_rst_split *) reg [2:0] rs_q__qv;\n    wire rs_q = rs_q__qv[0];\n    always @(posedge ck) rs_q__qv <= {3{rst_n}};\n"),
    ("    wire [260:0] er_e = (own && MUT != 4) ? 261'd0 : er;",
     "    wire [260:0] er_e = (own && MUT != 4) ? 261'd0 : er;\n"
     "    // KV-PC5-C: er_e[0] per hold slice from its own er_v / own copies\n"
     "    (* keep *) reg [19:0] ownk;\n"
     "    always @(posedge ck or negedge rs_q) if (!rs_q) ownk <= 20'hfffff; else ownk <= {20{!ebr_q}};\n"
     "    wire [19:0] evk = erk & ~(ownk & {20{MUT != 4}});"),
    ("    qkd_embedding_static_pc_strap #(.ROW0(ROW0), .MUT(MUT == 2 ? 2 : 0), .RETIME(RETIME)) u_emb (.ck(ck), .rst_n(rs_q),",
     "    qkd_kvpc_s_emb_strap #(.ROW0(ROW0), .MUT(MUT == 2 ? 2 : 0), .RETIME(RETIME)) u_emb (.ck(ck), .rst_n(rs_q), .evk(evk),"),
]
# strap clone: h_d written in 20 x <= 13-bit slices on er_e[0] copies (writing on er[0] alone is exact: h_d is read
# only while h_v, and an er[0] && return_slot edge clears h_v), beat_data selected per slice on copies of the hold
# select; h_v copies hvk load h_v's next state.
STRAP = 'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge.sv'
STRAP_SUBS = [
    ("  input wire return_slot,\n", "  input wire return_slot,\n  input wire [19:0] evk,                 // KV-PC5-C: er[0] copies (one per hold slice)\n"),
    ("    wire [260:0] eff=(RETIME!=0&&!er[0]&&h_v)?{er[260],h_d,1'b1}:er;\n",
     "    wire [260:0] eff=(RETIME!=0&&!er[0]&&h_v)?{er[260],h_d,1'b1}:er;\n"
     "    (* keep *) reg [19:0] hvk;                  // KV-PC5-C: h_v copies\n"
     "    always @(posedge ck or negedge rst_n)\n"
     "        if(!rst_n) hvk<=20'd0; else hvk<={20{(RETIME!=0)&&!return_slot&&(er[0]||h_v)}};\n"
     "    genvar gh;\n"
     "    for(gh=0;gh<20;gh=gh+1) begin: g_hold\n"
     "        localparam integer LO=1+gh*13, WD=(260-LO<13)?260-LO:13;   // h_d / er bits [LO +: WD] (1..259)\n"
     "        localparam integer BW=(257-LO<WD)?((257-LO>0)?257-LO:0):WD; // beat_data bits LO-1 .. (<= 256)\n"
     "        always @(posedge ck) if(RETIME!=0&&evk[gh]) h_d[LO+:WD]<=er[LO+:WD];\n"
     "        if(BW>0) begin: g_b\n"
     "`ifdef OT_KVPC5_TAP_MUT\n"
     "            always @(posedge ck) beat_data[LO-1+:BW]<=(RETIME!=0&&!evk[gh]&&hvk[gh]&&gh!=3)?h_d[LO+:BW]:er[LO+:BW];   // bench mutant\n"
     "`else\n"
     "            always @(posedge ck) beat_data[LO-1+:BW]<=(RETIME!=0&&!evk[gh]&&hvk[gh])?h_d[LO+:BW]:er[LO+:BW];\n"
     "`endif\n"
     "        end\n"
     "    end\n"),
    ("        beat_data<=eff[256:1];", ""),
    ("        if(RETIME!=0&&er[0]&&!return_slot) h_d<=er[259:1];\n", ""),
]

RET_SUBS = [
    ("        if(cs_q&&cv_q)retained<=record_q;\n", ""),
    ("    reg occupied;\n",
     "    reg occupied;\n"
     "    // KV-PC5-C: retained (298 b, census f1 301 / 297) captured in 20 x <= 15-bit slices on kept cs / cv copies\n"
     "    (* keep *) reg [19:0] csk, cvk;\n"
     "    always @(posedge ck or negedge rst_n)\n"
     "        if(!rst_n) begin csk<=20'd0;cvk<=20'd0; end else begin csk<={20{capture_slot}};cvk<={20{capture_v}}; end\n"
     "    genvar gr;\n"
     "    for(gr=0;gr<20;gr=gr+1) begin: g_ret\n"
     "        localparam integer LO=gr*15, WD=(298-LO<15)?298-LO:15;\n"
     "`ifdef OT_KVPC5_TAP_MUT\n"
     "        always @(posedge ck) if(csk[gr]&&cvk[gr]&&gr!=2) retained[LO+:WD]<=record_q[LO+:WD];   // bench mutant\n"
     "`else\n"
     "        always @(posedge ck) if(csk[gr]&&cvk[gr]) retained[LO+:WD]<=record_q[LO+:WD];\n"
     "`endif\n"
     "    end\n"),
]

CLONES = [
    # (file, original module, clone name, [(old, new), ...], [kept copy families])
    (FAN, 'qkd_static_kv_pc_path_fan_nc_b', 'qkd_kvpc_s_fan_nc_b',
     [('qkd_static_kv_pc_path_emb_nc_b #(.MU(MU)) u_pce (', 'qkd_kvpc_s_emb_nc_b #(.MU(MU)) u_pce ('),
      ('    qkd_kv_pc_chain_station_b u_chain (', '    qkd_kvpc_s_chain u_chain (')]),
    (FAN, 'qkd_static_kv_pc_path_emb_nc_b', 'qkd_kvpc_s_emb_nc_b',
     ERK_EMB + [('qkd_static_kv_pc_path_nc #(.MU(MU)) u_path (', 'qkd_kvpc_s_path_nc #(.MU(MU)) u_path ('),
                ('    qkd_static_kv_pc_es_merge_b u_esm (', '    qkd_kvpc_s_esm u_esm (')]),
    (PATH, 'qkd_static_kv_pc_path_nc', 'qkd_kvpc_s_path_nc',
     ERK_PATH + [('qkd_ctrl_pc_host_static_nc #(', 'qkd_kvpc_s_ctrl #('),
      ('qkd_kv_hbm_elastic_front_mc_nc #(', 'qkd_kvpc_s_front #('),
      ('qkd_static_kv_return_slots_mc_nc #(.DEPTH(8)) u_return (', 'qkd_kvpc_s_return #(.DEPTH(8)) u_return ('),
      ('    qkd_controller_hbm_calendar #(', '    qkd_kvpc_s_calendar #(')]),
    (CTRL, 'qkd_ctrl_pc_host_static_nc', 'qkd_kvpc_s_ctrl',
     ERK_CTRL + [('    qkd_ctrl_pc_sched_nc #(', '    qkd_kvpc_s_sched #('),
      ('    qkd_ctrl_pc_cdc_child #(', '    qkd_kvpc_s_cdc_child #('),
      ('    qkd_ctrl_pc_obs_child #(', '    qkd_kvpc_s_obs_child #('),
      ('    qkd_ctrl_pc_port_child_nc #(', '    qkd_kvpc_s_port_child #('),
      ('    qkd_ctrl_pc_ecc_child u_ecc (', '    qkd_kvpc_s_ecc_child u_ecc (')]),
    (CTRL, 'qkd_ctrl_pc_sched_nc', 'qkd_kvpc_s_sched',
     SCHED + [('    ot_qkd_static_ctrl_pc_emb #(', '    ot_qkd_static_ctrl_pc_emb_kvpc_s #(')],
     [('static_owner_q', 1, 3)]),
    (CORE, 'qkd_ctrl_pc_cdc_child', 'qkd_kvpc_s_cdc_child',
     ERK_CDC + [('ot_qkd_static_emb_cdc #(.ENABLE(1)) u_ecdc (', 'ot_qkd_static_emb_cdc_kvpc_s #(.ENABLE(1)) u_ecdc (')],
     [('hr_q', 1, 2), ('rs_q', 1, 3)]),
    (CORE, 'qkd_ctrl_pc_obs_child', 'qkd_kvpc_s_obs_child', OBS_PO, [('hr_q', 1, 16)]),
    ('REWRITE', 'qkd_kvpc_s_port_child'),
    ('REWRITE', 'ot_qfd_emb_pcport_nkw_kvpc_s'),
    (CHILD, 'qkd_ctrl_pc_ecc_child', 'qkd_kvpc_s_ecc_child',
     [('    ot_qfd_kv_landing_ecc #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (',
       '    ot_qfd_kv_landing_ecc_kvpc_s #(.ENABLE(1), .INTERLEAVED(1)) u_ecc (')]),
    (ECC, 'ot_qfd_kv_landing_ecc', 'ot_qfd_kv_landing_ecc_kvpc_s', [], [('p1_v', 1, 23)]),
    (CAL, 'qkd_controller_hbm_calendar', 'qkd_kvpc_s_calendar', [], [('rn', 1, 28), ('go_q', 1, 41)]),
    (UCTL, 'ot_qkd_static_ctrl_pc_emb', 'ot_qkd_static_ctrl_pc_emb_kvpc_s',
     [(' ot_qkd_static_kv_timing #(', ' ot_qkd_static_kv_timing_kvpc_s #(')],
     [('rp', 3, 15),
      ('col_bank', 5, 11, ('output reg [4:0] col_bank,col_col,', 'output wire [4:0] col_bank,output reg [4:0] col_col,')),
      ('col_col', 5, 3, ('output reg [4:0] col_col,', 'output wire [4:0] col_col,')),
      ('row_row', 19, 2, ('output reg [18:0] row_row,', 'output wire [18:0] row_row,'))]),
    (TIM, 'ot_qkd_static_kv_timing', 'ot_qkd_static_kv_timing_kvpc_s',
     [("    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;",
       "    localparam integer SQW = (SQD > 1) ? $clog2(SQD) : 1;\n"
       "    initial if (SQW != 2 || WQW != 2) $error(\"ot_qkd_static_kv_timing_kvpc_s: kept copy widths assume SQD 4, WQ 4\");")],
     [('sq_rp', 2, 27), ('wq_rp', 2, 9), ('wq_rp1', 2, 8), ('context_active', 1, 5), ('streaming', 1, 10),
      ('wq_n', 3, 3), ('c_s', 1, 2), ('wq_v', 4, 2)]),
    ('REWRITE', 'qkd_kvpc_s_chain'),
    (ESM, 'qkd_static_kv_pc_es_merge_b', 'qkd_kvpc_s_esm', ESM_HQ + ESM_ERK, [('own', 1, 11)]),
    (STRAP, 'qkd_embedding_static_pc_strap', 'qkd_kvpc_s_emb_strap', STRAP_SUBS),
    (RHOP, 'qkd_embedding_static_return_hop', 'qkd_kvpc_s_rhop', RET_SUBS, [('ts_q', 1, 25)]),
    (RHEAD, 'qkd_embedding_static_return_head', 'qkd_kvpc_s_rhead', RET_SUBS, [('ts_q', 1, 25)]),
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


def rewrite(new):
    import hashlib
    path, name, sha, fn = REWRITES[new]
    h = hashlib.sha256(module_text(path, name).encode()).hexdigest()[:16]
    if h != sha:
        raise SystemExit(f'kv_pc_sram_gen: {new}: original {name} changed ({h} != {sha}); re-derive the rewrite')
    FAM_LOG.append((new, []))
    return f'// ---- {new}: KV-PC5-C native32 REWRITE of {name} ({path}, sha {sha}); same function ----\n' + fn()


def clone(path, name, new=None, subs=(), fams=()):
    if path == 'REWRITE':
        return rewrite(name)
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
    ("    (* keep, ot_rst_split *) reg [71:0] hgo_qv;",
     "    // (KV-PC2: 64 -> 72: gate 164813 measured 2178 loads = 35 / copy at 64)\n"
     "    (* keep, ot_rst_split *) reg [71:0] hgo_qv;"),
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
    body = [clone(*c) for c in CLONES]
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
