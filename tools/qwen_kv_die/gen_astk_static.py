#!/usr/bin/env python3
"""KVE-2-ASTK 2026-10-17: derive the credit-free, lane-free ASTK leaves from the selected static (calendar) masters.

Sources: rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv (qkd_astk_ep_cal, qkd_astk_ctl_cal) and
rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv (qkd_astk_ex).  Output: rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv
Usage: gen_astk_static.py CAL_GEN.sv LEAVES.sv OUT.sv
"""
import hashlib, re, sys
from pathlib import Path

def once(s, a, b):
    n = s.count(a)
    if n != 1:
        raise SystemExit(f'source binding mismatch ({n}x): {a[:80]!r}')
    return s.replace(a, b)

def mod(text, name):
    m = re.search(r'^module ' + name + r' #?\(.*?^endmodule\n', text, re.M | re.S)
    if not m:
        raise SystemExit('module not found: ' + name)
    return m.group()

cal_p, lv_p, out_p = map(Path, sys.argv[1:4])
cal, lv = cal_p.read_text(), lv_p.read_text()

# ---- EP: static calendar slice, no tree lanes, no node credit ----------------------------------------------------------
ep = mod(cal, 'qkd_astk_ep_cal')
ep = once(ep, '''module qkd_astk_ep_cal #(
    parameter integer STATIC_SCHEDULE=0,
    parameter integer EXP_START_AGE=0,
    parameter integer HEADS=`KVD_HEADS
) (''', 'module qkd_astk_ep_s (')
ep = once(ep, '    input  wire [424:0]  so,\n    output wire [633:0]  si,\n',
          '    input  wire [411:0]  so,        // engine so[411:0] (er / sc / lmax); the engine fault so[424] is sf\n'
          '    input  wire          sf,\n'
          '    output wire [632:0]  si,        // engine si[632:0]: no node credit (si[633] of the credit design is gone)\n')
ep = once(ep, '    input  wire          cr,\n', '')
ep = once(ep, '    input  wire [15:0]   cal_exp,   // this EP\'s EXP start age (compiler calendar)\n',
          '    input  wire [15:0]   cal_exp,   // the command\'s EXP base age (compiler calendar, held through the start edge)\n'
          '    input  wire [7:0]    eo,        // strap: this slice\'s EXP offset (9 e + RL (e + e / 2) in the strip)\n')
ep = once(ep, '    always @(posedge ck) cal_exp_q <= cal_exp;\n',
          '    (* keep *) reg [7:0] eo_q;\n    always @(posedge ck) begin cal_exp_q <= cal_exp; eo_q <= eo; end\n')
ep = once(ep, '    always @(posedge ck) if (start) exp_age <= cal_exp_q;\n',
          '    always @(posedge ck) if (start) exp_age <= cal_exp_q + {8\'d0, eo_q};\n')
ep = re.sub(r'    input  wire \[535:0\]  ui,.*?output wire         fo\n', '', ep, count=1, flags=re.S)
ep = once(ep, '    input  wire [135:0]  xe,\n);', '    input  wire [135:0]  xe\n);')
ep = once(ep, '''    (* keep_hierarchy *) qkd_astk_lanes u_l (.ck(ck), .rn(rn_q), .ui(ui), .uo(uo), .di(di), .do_(do_), .pi(pi), .po(po),
        .ci(ci), .co(co), .kui(kui), .kuo(kuo), .kdi(kdi), .kdo(kdo), .tui(tui), .tuo(tuo), .tdi(tdi), .tdo(tdo), .fi(fi), .fo(fo));
''', '''    localparam integer STATIC_SCHEDULE = 1, HEADS = 1;
    wire [424:0] so_x = {sf, 12'd0, so};               // so[423:412] (node beats, k / v done) are not read
''')
ep = once(ep, '    (* keep *) reg         cr_q;\n', '')
ep = once(ep, 'eqc <= 8\'d0; cr_q <= 1\'b0; end', 'eqc <= 8\'d0; end')
ep = once(ep, 'eqc <= {xe[103:102], xe[69:68], xe[35:34], xe[1:0]}; cr_q <= cr; end',
          'eqc <= {xe[103:102], xe[69:68], xe[35:34], xe[1:0]}; end')
ep = once(ep, 'so_q[424] <= so[424]; qq[0]', 'so_q[424] <= so_x[424]; qq[0]')
ep = once(ep, 'so_q[12:1] <= so[12:1]; so_q[423:14] <= so[423:14];', 'so_q[12:1] <= so[12:1]; so_q[411:14] <= so[411:14];')
ep = once(ep, 'so_q[0] <= so[0]; so_q[13] <= so[13];', 'so_q[0] <= so[0]; so_q[13] <= so[13];')
ep = once(ep, '(* keep *) reg [424:0] so_q;', '(* keep *) reg [424:0] so_q;            // [423:412] unused (no flops)')
ep = once(ep, '    initial if (STATIC_SCHEDULE && (HEADS != 1))\n        $fatal(1,"invalid static ASTK EXP profile");\n', '')
ep = once(ep, '(* keep *) reg [569:0] sio;', '(* keep *) reg [568:0] sio;')
ep = once(ep, 'sio[569:537] <= 33\'d0; end', 'sio[568:537] <= 32\'d0; end')
ep = once(ep, 'sio[568:537] <= xdq; sio[569] <= cr_q; end', 'sio[568:537] <= xdq; end')
ep = once(ep, 'assign si = {sio[569], e_rdq, sio[568:0]};', 'assign si = {e_rdq, sio[568:0]};')
ep = once(ep, "(`KVD_AKMUT == 2) ? 6'd1 : 6'd0", "(`KVD_STMUT == 1) ? 6'd1 : 6'd0")
assert 'cr' not in re.findall(r'\bcr\b', ep), 'cr left'
for w in ('ui', 'kui', 'fo', 'u_l'):
    assert not re.search(r'\b' + w + r'\b', ep), w + ' left'

# ---- EP ST3 (S-KVASTK 10-18): physical retiming, 0 cycles on every edge the lockstep bench compares -------------------
# Route qkd_astk_ep_s-st2-71ef7d71e (TT -76.5, 751 D pins) classified on the routed netlist:
#   xq -> xo (228)        the running-max compare (ABC ripple, 13 cells, 476 ps) + the W-band -> E-face xo wire (192 ps)
#   qq -> u_row / u_ca (411), zq -> u_ca (24)  the join stage held the T compare (E-low qq -> W-band seq tags -> b_pos,
#                         fanout 192), bf16 rounding, the Q slot mux and the adder's A1 decode / 31-b compare behind
#                         S-face zq and E-face eq wires
#   qq -> xd / u_sa / u_sb (15)  T - 1 - S x 128 (14-b subtract) recomputed from the E-face T every edge
# Fixes: (1) the compare on two Kogge-Stone carry chains; (2) the join gets an operand register stage (row / tags / e
# rounding / adder operands) and gives the edge back at the output: u_row is one stage shorter and the adders' output
# registers (y / valid_out) are the zo pin registers, so zo keeps its edge; (3) T - 1 - S x 128 and the group count are
# registered (T and S are held from the start edge through the command; every consumer is quiet / act-gated for
# DT + 16 edges after a start).  The adders' error now leaves the output register one edge later, so it joins the
# return-chain fault xo[0] directly (se_f, masked on the edge after a start as the start used to wipe it): xo[0] keeps its edge.
ep = once(ep, '''            xo[11 + 32*(4*g_ + h_) +: 32] <= (la[g_] && (!xq[9 + g_] || fgt(lm[32*(4*g_ + h_) +: 32], xq[11 + 32*(4*g_ + h_) +: 32])))
                                              ? lm[32*(4*g_ + h_) +: 32] : xq[11 + 32*(4*g_ + h_) +: 32];
    end
''', '''            xo[11 + 32*(4*g_ + h_) +: 32] <= (la[g_] && (!xq[9 + g_] || lm_gt[4*g_ + h_])) ? lm[32*(4*g_ + h_) +: 32]
                                                                                          : xq[11 + 32*(4*g_ + h_) +: 32];
    end
''')
ep = once(ep, '''    wire [1:0]   la = so_q[411:410];
''', '''    wire [1:0]   la = so_q[411:410];
    // ST3: fgt on two Kogge-Stone carry chains (log depth; the behavioural > / < mapped as a 13-cell ripple)
    wire [7:0]   lm_gt;
    genvar gw;
    generate for (gw = 0; gw < 8; gw = gw + 1) begin : g_lmax
        wire [31:0] la_ = lm[32*gw +: 32], lb_ = xq[11 + 32*gw +: 32];
        wire        ab_ge, ba_ge;
        wire [30:0] ab_s, ba_s;
        ot_hdc_ksadd_k #(.W(31)) u_ab (.a(la_[30:0]), .b(~lb_[30:0]), .cin(1'b1), .s(ab_s), .cout(ab_ge));
        ot_hdc_ksadd_k #(.W(31)) u_ba (.a(lb_[30:0]), .b(~la_[30:0]), .cin(1'b1), .s(ba_s), .cout(ba_ge));
        assign lm_gt[gw] = (la_[31] != lb_[31]) ? !la_[31] : (!la_[31] ? ((`KVD_STMUT == 5) ? !ab_ge : !ba_ge) : !ab_ge);   // = fgt(la_, lb_)
    end endgenerate
''')
ep = once(ep, '    qkd_astk_seq u_sa (', '    qkd_astk_seq_s u_sa (')
ep = once(ep, '    qkd_astk_seq u_sb (', '    qkd_astk_seq_s u_sb (')
ep = once(ep, "    wire [13:0]  rkb = T - 14'd1 - {5'd0, S, 7'd0} - {6'd0, rq[9:6], 3'd0};\n",
          "    reg  [13:0]  tb_q;                                 // ST3: T - 1 - S x 128 (command-static), registered\n"
          "    always @(posedge ck) tb_q <= T - 14'd1 - {5'd0, S, 7'd0};\n"
          "    wire [13:0]  rkb = tb_q - {6'd0, rq[9:6], 3'd0};\n")
ep = once(ep, '''    wire [63:0]  e16 = b_pos ? {bf16(e[127:96]), bf16(e[95:64]), bf16(e[63:32]), bf16(e[31:0])} : 64'd0;
    wire [511:0] row_in = first ? 512'd0 : zq[650:139];
''', '''    // ST3: the join operand stage (the bf16 rounding, the slot's b_pos, the incoming row, the tags, the adder operands)
    reg  [63:0]  eb_q;
    reg          bp_q, jv_q;
    reg  [511:0] row_in_q;
    reg  [8:0]   tag_q;
    always @(posedge ck) begin
        eb_q <= {bf16(e[127:96]), bf16(e[95:64]), bf16(e[63:32]), bf16(e[31:0])};
        bp_q <= b_pos; row_in_q <= first ? 512'd0 : zq[650:139]; tag_q <= {b_gam, b_k, b_g};
    end
    always @(posedge ck or negedge rn_q) if (!rn_q) jv_q <= 1'b0; else jv_q <= b_v;
    wire [63:0]  e16 = bp_q ? eb_q : 64'd0;
    wire [511:0] row_in = row_in_q;
''')
ep = once(ep, "    ot_hdc_delay #(.W(521), .D(ADD_LAT)) u_row (.clk(ck), .rst_n(rn_q), .d({row_m, b_gam, b_k, b_g}), .q(jd));\n",
          "    ot_hdc_delay #(.W(521), .D(ADD_LAT - 1 - ((`KVD_STMUT == 4) ? 1 : 0))) u_row (.clk(ck), .rst_n(rn_q), .d({row_m, tag_q}), .q(jd));\n")
ep = once(ep, '''        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_chain (.clk(ck), .rst_n(rn_q), .valid_in(b_v),
            .a(first ? 32'd0 : zq[11 + 32*h +: 32]), .b(b_pos ? e[32*h +: 32] : 32'd0), .y(sum[32*h +: 32]), .err(err),
            .valid_out(sv_[h]));
''', '''        reg [31:0] ja_q, jb_q;
        always @(posedge ck) begin ja_q <= first ? 32'd0 : zq[11 + 32*h +: 32]; jb_q <= b_pos ? e[32*h +: 32] : 32'd0; end
        ot_hdc_fp32_add_lat_nr #(.LAT(ADD_LAT)) u_chain (.clk(ck), .rst_n(rn_q), .valid_in(jv_q), .a(ja_q), .b(jb_q),
            .y(sum[32*h +: 32]), .err(err), .valid_out(sv_[h]));
''')
ep = once(ep, '    output reg  [650:0]  zo,\n', '    output wire [650:0]  zo,\n')
ep = once(ep, '    reg          tok1;\n', '    reg          tok1, zo_tok, st_d;\n'
          '    wire         se_f = (|se) && !st_d;              // ST3: the adder error at its original edge\n')
ep = once(ep, 'if (j_bad || (|se) || (trig && a_busy)', 'if (j_bad || se_f || (trig && a_busy)')
ep = once(ep, 'xo[0] <= xq[0] | so_q[424] | e_f | f;', 'xo[0] <= xq[0] | so_q[424] | e_f | f | se_f;')
ep = once(ep, "zo[1:0] <= 2'b00; stl <= 8'd0; end", "zo_tok <= 1'b0; stl <= 8'd0; end")
ep = once(ep, 'tok1 <= trig; zo[1] <= tok1; zo[0] <= sv_[0];', 'tok1 <= trig; zo_tok <= tok1;')
ep = once(ep, "tok1 <= 1'b0; zo[1] <= 1'b0; end", "tok1 <= 1'b0; zo_tok <= 1'b0; end")
ep = once(ep, "zo_tok <= 1'b0; stl <= 8'd0; end", "zo_tok <= 1'b0; st_d <= 1'b0; stl <= 8'd0; end")
ep = once(ep, 'tok1 <= trig; zo_tok <= tok1;', 'tok1 <= trig; zo_tok <= tok1; st_d <= start;')
ep = once(ep, '    always @(posedge ck) zo[650:2] <= {jd[520:9], sum, jd[8:5], jd[4:1], jd[0]};\n',
          '    // ST3: zo = the row / tags behind their pin register and the adders\' output registers (y, valid_out) at the pin\n'
          '    reg  [520:0] jd_q;\n'
          '    always @(posedge ck) jd_q <= jd;\n'
          '    assign zo = {jd_q[520:9], sum, jd_q[8:0], zo_tok, sv_[0]};\n')
assert not re.search(r'\bfgt\(lm', ep) and 'zo[' not in ep.split('`ifdef KVD_AKDBG')[0].replace('zo[1:0]', '')

# ---- SEQ ST3: qkd_astk_seq with the command-static T terms registered (gmax, T - 1 - S x 128) ---------------------------
sq = mod(lv, 'qkd_astk_seq')
sq = once(sq, 'module qkd_astk_seq (', 'module qkd_astk_seq_s (')
sq = once(sq, "    wire [4:0]  gmax = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));\n",
          "    // ST3 (S-KVASTK 10-18): T / S are held from the start edge; a pass starts DT + 16 edges or more after it\n"
          "    reg  [4:0]  gmax;\n"
          "    reg  [13:0] tb;\n"
          "    always @(posedge ck) begin gmax <= !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));\n"
          "                               tb <= T - 14'd1 - base_s; end\n")
sq = once(sq, "    wire [13:0] kb = T - 14'd1 - base_s - {6'd0, gm[3:0], 3'd0};\n",
          "    wire [13:0] kb = tb - {6'd0, gm[3:0], 3'd0};\n")

# ---- EX: one head's exp pipe, no tree lanes ------------------------------------------------------------------------
ex = mod(lv, 'qkd_astk_ex')
ex = once(ex, 'module qkd_astk_ex (', 'module qkd_astk_ex_s (')
ex = re.sub(r'    output reg  \[33:0\]   xe,\n.*?output wire         fo\n', '    output reg  [33:0]   xe\n', ex, count=1, flags=re.S)
ex = re.sub(r'    \(\* keep_hierarchy \*\) qkd_astk_lanes u_l .*?\.fo\(fo\)\);\n', '', ex, count=1, flags=re.S)
ex = once(ex, "(`KVD_AKMUT == 5) ? 32'd1 : 32'd0", "(`KVD_STMUT == 2) ? 32'd1 : 32'd0")
for w in ('ui', 'kui', 'fo', 'u_l'):
    assert not re.search(r'\b' + w + r'\b', ex), w + ' left'

# ---- CTL: static calendar port without the legacy P.V lanes ---------------------------------------------------------
ct = mod(cal, 'qkd_astk_ctl_cal')
ct = once(ct, '''module qkd_astk_ctl_cal #(
    parameter integer HEADS = `KVD_HEADS,  // native TP8 = 1
    parameter integer STATIC_SCHEDULE=0,
    parameter integer LMAX_START_AGE=0,
    parameter integer Z_START_AGE=0,
    parameter integer Z_STRIDE=4
) (''', '''module qkd_astk_ctl_s #(
    parameter integer Z_STRIDE=4
) (''')
ct = once(ct, '    output reg  [564:0]  ap,\n', '    output reg  [42:0]   ap,         // the hub sideband {so_data 32, so_any, so_k 4, so_hh 2, so_g, so_type 2, so_valid}\n')
ct = once(ct, '    output reg  [5:0]    co,\n    input  wire [262:0]  px,\n    input  wire [262:0]  py,\n', '')
ct = once(ct, '    input  wire          fx,\n    input  wire          fy,\n', '')
ct = once(ct, '    (* keep *) reg rn_q;', '''    localparam integer HEADS = 1, STATIC_SCHEDULE = 1;   // the LMAX / Z start ages come from cal
    reg  [5:0]   co;                                   // the legacy tree cells' {gmax, start}: no load
    wire [262:0] px = 263'd0, py = 263'd0;             // P.V is the pvw's (no tree lanes reach the port)
    wire         fx = 1'b0, fy = 1'b0;
    (* keep *) reg rn_q;''')
ct = once(ct, "ap[0] <= 1'b0; ap[45:43] <= 3'b000; lt[0]", "ap[0] <= 1'b0; lt[0]")
ct = once(ct, "ap[0] <= 1'b0; ap[45] <= pv_v; ap[44:43] <= pvd;", "ap[0] <= 1'b0;")
ct = re.sub(r"        ap\[564:46\] <= \{pvw, 1'b0, pxq\[5:1\], pxq\[6\]\};\n", '', ct, count=1)
ct = once(ct, "(`KVD_AKMUT == 4) ? pyq[262:7] : pxq[262:7]", "pxq[262:7]")
ct = once(ct, "(`KVD_AKMUT == 4) ? pxq[262:7] : pyq[262:7]", "pyq[262:7]")
ct = once(ct, "if (z_emit) ap[42:1] <= {z_s,", "if (z_emit) ap[42:1] <= {z_s ^ ((`KVD_STMUT == 3) ? 32'd1 : 32'd0),")
assert 'ap[45' not in ct and 'ap[564' not in ct

# KV core boundary contract: external copies of the controller command launch
# on the original qo edge, separately from qo and the core's local consumers.
ct = once(ct, '    parameter integer Z_STRIDE=4\n',
          '    parameter integer Z_STRIDE=4, parameter integer PORT_REGS=0\n')
ct = once(ct, '    output reg  [571:0]  qo,\n',
          '    output reg  [571:0]  qo,\n    output wire [59:0] tc_faces,\n    output wire [571:0] qo_face,\n')
ct = ct.rsplit('endmodule', 1)[0] + r"""
    generate if (PORT_REGS != 0) begin : g_tc_faces
        genvar face;
        for (face=0; face<4; face=face+1) begin : g_face
            (* keep_hierarchy *) qkd_astk_tc_face u_face
                (.ck(ck), .rn(rn_q), .start(start), .t(T), .q(tc_faces[15*face +: 15]));
        end
        (* keep_hierarchy *) qkd_astk_qo_face u_qo_face
            (.ck(ck), .rn(rn_q), .d({am_q[35:1], am_q[0], kdone, aq_q[539:22], aq_q[21], T, start}), .q(qo_face));
    end else begin : g_tc_disabled
        assign tc_faces=60'd0;
        assign qo_face=572'd0;
    end endgenerate
endmodule

// Each instance stays distinct through synthesis, like the existing plan relay
// cells. Same valid/data edge as ctl.qo[14:0]; no output feedback or alias loads.
(* keep_hierarchy *) module qkd_astk_qo_face(
    input wire ck, rn, input wire [571:0] d, output reg [571:0] q);
`ifdef KVG3_ASTK_QOMUT
    wire [571:0] pd = d ^ (572'd1 << 535);
`else
    wire [571:0] pd = d;
`endif
    always @(posedge ck or negedge rn)
        if (!rn) begin q[0]<=0; q[15]<=0; q[536:534]<=0; end
        else begin q[0]<=pd[0]; q[15]<=pd[15]; q[536:534]<=pd[536:534]; end
    always @(posedge ck) begin q[14:1]<=pd[14:1]; q[533:16]<=pd[533:16]; q[571:537]<=pd[571:537]; end
endmodule

(* keep_hierarchy *) module qkd_astk_tc_face(
    input wire ck, rn, start, input wire [13:0] t, output reg [14:0] q);
    always @(posedge ck or negedge rn)
        if (!rn) q[0] <= 1'b0;
        else q[0] <= start;
`ifdef KVG3_ASTK_TCMUT
    always @(posedge ck) q[14:1] <= t ^ 14'h2000;
`else
    always @(posedge ck) q[14:1] <= t;
`endif
endmodule
"""

hdr = f'''`timescale 1ns/1ps
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
// ---------------------------------------------------------------------------------------------------------------------
// KVE-2-ASTK 2026-10-17: credit-free, lane-free successors of the ASTK strip leaves (owner static-cycle rule; HANDOFF 0db).
// GENERATED by tools/qwen_kv_die/gen_astk_static.py -- do not edit; regenerate.
//   {cal_p.name} sha256 {hashlib.sha256(cal.encode()).hexdigest()}
//   {lv_p.name} sha256 {hashlib.sha256(lv.encode()).hexdigest()}
// The selected static attention (ot_qwen_tp8_attention_native_service_w16) computes P.V in the pvw pairs from the ASTK e
// rows; its ASTK (qkd_astk_native_stack_*cal) has no P.V tree cells, ties every lane / credit input of qkd_astk_ep_cal and
// qkd_astk_ex to 0 and leaves the heads' node beats (nb_d) unconnected.  So the tree cells (qkd_astk_pv / _pv_tp8), the
// lanes that crossed ep / ex (ui / di / pi / ci / kui / kdi / tui / tdi / fi, 1,358 b a face), the node credits
// (cra / crb -> ep cr -> engine nb_cr) and the local credits (lci / lco) carry no work on the static timeline.
// These successors are the calendar masters with those ports removed; logic and edges are otherwise identical:
//   qkd_astk_ep_s   = qkd_astk_ep_cal  (STATIC 1, HEADS 1)  - lanes, cr, si[633] (nb_cr); so[423:412] not taken
//   qkd_astk_ex_s   = qkd_astk_ex                          - lanes
//   qkd_astk_ctl_s  = qkd_astk_ctl_cal (STATIC 1, HEADS 1) - px / py / fx / fy / co; ap = the 43-b sideband only
// Every remaining data input is captured in a pin register (unchanged from the masters).  Bench (lockstep against the
// selected composition qkd_astk_native_stack_cal): rtl/test/qwen_kv_die/tb_qkd_astk_strip_st.sv.
// Mutants (`KVD_STMUT): 1 ep_s e rows written one address off; 2 ex_s e one ulp off; 3 ctl_s Z word one ulp off.
// ST3 (S-KVASTK 10-18): ep_s physically retimed at 0 cycles (operand stage at the join, zo = the adders' y, Kogge-Stone
// running-max compare, registered command-static T terms; qkd_astk_seq_s) -- see gen_astk_static.py.
// ST3 mutants: 4 ep_s row / tag delay one edge short (the join retiming), 5 ep_s running-max compare on the wrong chain.
// ---------------------------------------------------------------------------------------------------------------------
'''
out_p.write_text(hdr + '\n' + ep + '\n' + sq + '\n' + ex + '\n' + ct)
print('wrote', out_p)
