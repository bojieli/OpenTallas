#!/usr/bin/env python3
"""kv-die 2026-10-09 (owner rule: every element good physical design): generate rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv,
re-cut D with the ROW ENGINE split into HARD SUB-TILES.

Every route of the monolithic row engine failed (_p a / b PREROUTE -6.0 / -4.4 ns at S3 -> product, E -3.6 ns at
sc_addr -> lmax, D stuck in floorplan repair at -49 ns on the central reset leaf feeding the local-tree bank): 512
lanes, 1 M instances and central broadcasts in one 531 x 1,998 um element.  H keeps the arithmetic, the order and the
cycle-level schedule of D and cuts the engine along its natural seams:

  ot_qwen_nearhbm_head_h   one per q head (4 a engine): the head's 128 lanes (product unit + lane adder + loop), its
                           K score tree and scale, its 128 lanes of the local P.V tree (levels 1-3: a lane bank adder,
                           three level registers and the node register a lane), its q rows (heads h and 4 + h, written
                           from the q beat broadcast).  Inputs: the S1b-staged control / row / e / decision words, all
                           captured at the tile pins (the parent's S2 register); outputs: the head's score (the
                           parent's scd1 register), faults, and a 1,024-b node slice register.
  ot_qwen_nearhbm_ectl_h   the engine control: registered boundary, request generator, row / e FIFOs, the K / V
                           issue, pend / arm, the local-tree DECISIONS (now a staged 12-b decision word instead of
                           a combinational 16 k-bit datapath), the score tags / running max, the node beat stream.
                           S1 and the two S1b copies (one per tile pair) are its output registers.
  ot_qwen_nearhbm_row_engine_h  the engine = 1 ectl + 4 head tiles (same ports as row_engine_d).

Timing alignment (exact): a decision made centrally at t reaches the lanes at t + 8 (S1, S1b, S2 at the tile pin, S3 a
group, the PLAT delay line -- the lane control path of the parent), where the slot's loop value is the one the parent
read at t (a pending or just-taken slot keeps its value in the loop for >= 16 cycles).  The bank result the decision
at t expects at t + ADD_LAT arrives at the lane at t + 8 + ADD_LAT, where the arrival decision (also delayed 8) uses it.
The node beat: beat b of a node is the lanes d = LFB k + b of every head (each head tile drives its own 1,024-b slice of
every beat from a register); the aggregator staging places it back (lane h HD + LFB k + b).

    python3 tools/qwen_kv_die/stack_h_gen.py [--check]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stack_d_gen as D               # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DST = ROOT / 'rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv'
rep = D.rep

HEAD = r'''
// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_nearhbm_head_h: one q head of a row engine (HARD SUB-TILE, kv-die 2026-10-09; see the file header)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_head_h #(
    parameter integer HD = 128,
    parameter integer H = 0,             // this head (0..3); its q rows are heads H and 4 + H
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer LFB = 4,
    parameter integer LTW = 12
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [3:0]           c_in,         // S1b control {k issue, v issue of a real row, first round, g}
    input  wire [HD*8-1:0]      row_in,
    input  wire [15:0]          e_in,         // this head's e
    input  wire [LTW-1:0]       lt_in,        // local-tree / node decision word (S1b)
    input  wire                 q_valid_in,   // the q beat broadcast (S1b)
    input  wire [5:0]           q_beat_in,
    input  wire [511:0]         q_data_in,
    output reg  [31:0]          sc_d,         // the head's scaled score (the parent's scd1)
    output reg                  sc_f,         // scale fault (the parent's tf1)
    output reg                  g_f,          // lane / bank faults, ORed
    output reg  [HD*32/LFB-1:0] nb_d          // this head's slice of a node beat
);
    localparam integer LV = $clog2(HD);
    localparam integer GPH = HD / 16;
    localparam integer PLAT = 4;
    // ---- reset leaves: tile root, groups -------------------------------------------------------------------------------
    wire rt;
    wire [GPH-1:0] rgrp;
    (* keep_hierarchy *) ot_nhb_rleaf_h u_rt (.clk(clk), .arst_n(rst_n), .d(1'b1), .q(rt));
    genvar gg, d, l;
    generate for (gg = 0; gg < GPH; gg = gg + 1) begin : g_rgrp
        (* keep_hierarchy *) ot_nhb_rleaf_h u_l (.clk(clk), .arst_n(rst_n), .d(rt), .q(rgrp[gg]));
    end endgenerate
    // ---- S2: the tile pins ---------------------------------------------------------------------------------------------
    reg  [3:0]       c2;
    reg  [HD*8-1:0]  row2;
    reg  [15:0]      e2;
    reg  [LTW-1:0]   lt2;
    reg              qv2;
    reg  [5:0]       qb2;
    reg  [511:0]     qd2;
    always @(posedge clk or negedge rt)
        if (!rt) begin c2[3:1] <= 3'd0; lt2 <= {LTW{1'b0}}; qv2 <= 1'b0; end
        else begin c2[3:1] <= c_in[3:1]; lt2 <= lt_in; qv2 <= q_valid_in; end
    always @(posedge clk) begin c2[0] <= c_in[0]; row2 <= row_in; e2 <= e_in; qb2 <= q_beat_in; qd2 <= q_data_in; end
    // q rows of heads H (g = 0) and 4 + H (g = 1): beats 4 H .. 4 H + 3 and 4 (4 + H) .. + 3 of the h-major broadcast
    reg  [HD*16-1:0] q0, q1;
    localparam integer NQB = 8 * HD * 16 / 512;
    genvar bi;
    generate for (bi = 0; bi < NQB; bi = bi + 1) begin : g_qw
        // the part of beat bi inside head H's / head 4 + H's row (q is h-major: head x at bits x HD 16 ..)
        localparam integer BO = 512 * bi;
        localparam integer L0 = H * HD * 16, L1 = (4 + H) * HD * 16;
        localparam integer A0 = (BO > L0) ? BO : L0, Z0 = (BO + 512 < L0 + HD * 16) ? BO + 512 : L0 + HD * 16;
        localparam integer A1 = (BO > L1) ? BO : L1, Z1 = (BO + 512 < L1 + HD * 16) ? BO + 512 : L1 + HD * 16;
        if (Z0 > A0) begin : g_w0
            always @(posedge clk) if (qv2 && qb2 == 6'(bi)) q0[A0 - L0 +: Z0 - A0] <= qd2[A0 - BO +: Z0 - A0];
        end
        if (Z1 > A1) begin : g_w1
            always @(posedge clk) if (qv2 && qb2 == 6'(bi)) q1[A1 - L1 +: Z1 - A1] <= qd2[A1 - BO +: Z1 - A1];
        end
    end endgenerate
    // ---- S3 per 16-lane group + the adder-control / decision delay lines ------------------------------------------------
    wire [HD*32-1:0] p_y, l_y, fb;
    wire [HD-1:0]    p_vo, p_f, l_vo, l_f, b_f;
    wire [4*GPH-1:0]    c3;
    reg  [128*GPH-1:0]  row3;
    wire [16*GPH-1:0]   e3;
    wire [3*GPH-1:0]    kvz_d;
    wire [LV*GPH-1:0]   kl_g;
    wire [LTW*GPH-1:0]  lt3, lt_d;
    reg  [GPH-1:0]      gfault;
    generate
        for (gg = 0; gg < GPH; gg = gg + 1) begin : g_s3
            (* keep_hierarchy *) ot_nhb_repr_h #(.W(3)) u_c (.clk(clk), .rst_n(rgrp[gg]), .d(c2[3:1]), .q(c3[4*gg+1 +: 3]));
            (* keep_hierarchy *) ot_nhb_rep_h #(.W(1)) u_g (.clk(clk), .d(c2[0]), .q(c3[4*gg]));
            (* keep_hierarchy *) ot_nhb_rep_h #(.W(16)) u_e (.clk(clk), .d(e2), .q(e3[16*gg +: 16]));
            (* keep_hierarchy *) ot_nhb_repr_h #(.W(LTW)) u_t (.clk(clk), .rst_n(rgrp[gg]), .d(lt2), .q(lt3[LTW*gg +: LTW]));
            always @(posedge clk) row3[128*gg +: 128] <= row2[128*gg +: 128];
            ot_hdc_delay #(.W(3), .D(PLAT), .RESET(1)) u_ctl (.clk(clk), .rst_n(rgrp[gg]), .d(c3[4*gg+1 +: 3]),
                                                             .q(kvz_d[3*gg +: 3]));
            ot_hdc_delay #(.W(LTW), .D(PLAT), .RESET(1)) u_ltd (.clk(clk), .rst_n(rgrp[gg]), .d(lt3[LTW*gg +: LTW]),
                                                               .q(lt_d[LTW*gg +: LTW]));
            assign kl_g[LV*gg] = kvz_d[3*gg + 2];
            for (l = 2; l <= LV; l = l + 1) begin : g_kl
                ot_hdc_delay #(.W(1), .D(ADD_LAT), .RESET(1)) u_kl (.clk(clk), .rst_n(rgrp[gg]), .d(kl_g[LV*gg + l - 2]),
                                                                   .q(kl_g[LV*gg + l - 1]));
            end
            always @(posedge clk or negedge rgrp[gg])
                if (!rgrp[gg]) gfault[gg] <= 1'b0;
                else gfault[gg] <= (|(p_f[16*gg +: 16] & p_vo[16*gg +: 16])) || (|l_f[16*gg +: 16]) || (|b_f[16*gg +: 16]);
        end
    endgenerate
    function automatic integer tbase(input integer lev);
        integer k;
        begin
            tbase = 0;
            for (k = 2; k < lev; k = k + 1) tbase = tbase + (HD >> k);
        end
    endfunction
    function automatic integer tlev(input integer m);
        integer k;
        begin
            tlev = 0;
            for (k = LV; k >= 2; k = k - 1) if (m >= tbase(k) && m < tbase(k) + (HD >> k)) tlev = k;
        end
    endfunction
    function automatic integer tnode(input integer lev, input integer idx);
        tnode = (lev == 1) ? 2 * idx : 2 * (tbase(lev) + idx) + 1;
    endfunction
    // ---- the lanes -------------------------------------------------------------------------------------------------------
    wire [HD*32-1:0] obw;
    generate
        for (d = 0; d < HD; d = d + 1) begin : g_d
            localparam integer G = d / 16;
            localparam integer TL = (d % 2 == 0) ? 1 : tlev((d - 1) / 2);
            localparam integer TI = (d % 2 == 0) ? d / 2 : (d - 1) / 2 - tbase(TL > 1 ? TL : 2);
            wire        g3k = c3[4*G + 3], g3v = c3[4*G + 2], g3g = c3[4*G];
            wire [15:0] qv = g3g ? q1[d * 16 +: 16] : q0[d * 16 +: 16];
            wire [15:0] ev = e3[16*G +: 16];
            wire        kd = kvz_d[3*G + 2], vd = kvz_d[3*G + 1], czd = kvz_d[3*G];
            (* keep_hierarchy *) ot_qwen_nearhbm_prod u_p (.clk(clk), .rst_n(rgrp[G]), .valid_in(g3k || g3v),
                .a(g3k ? qv : ev), .k(row3[128*G + 8*(d % 16) +: 8]), .y(p_y[32*d +: 32]), .fault(p_f[d]),
                .valid_out(p_vo[d]));
            wire [31:0] va = czd ? 32'd0 : fb[32*d +: 32];
            wire [31:0] vb = vd ? p_y[32*d +: 32] : 32'd0;
            wire [31:0] la, lb;
            wire        kt;
            if (TL == 1) begin : g_l1
                assign kt = kd;
                assign la = kt ? p_y[32*d +: 32] : va;
                assign lb = kt ? p_y[32*(d+1) +: 32] : vb;
            end else if (TL >= 2) begin : g_ln
                localparam integer LA = tnode(TL - 1, 2 * TI);
                localparam integer LB = tnode(TL - 1, 2 * TI + 1);
                assign kt = kl_g[LV*G + TL - 1];
                assign la = kt ? l_y[32*LA +: 32] : va;
                assign lb = kt ? l_y[32*LB +: 32] : vb;
            end else begin : g_free
                assign kt = 1'b0;
                assign la = va;
                assign lb = vb;
            end
            wire [1:0] err;
            (* keep_hierarchy *) ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_a (.clk(clk), .rst_n(rgrp[G]), .valid_in(kt || vd),
                .a(la), .b(lb), .y(l_y[32*d +: 32]), .err(err), .valid_out(l_vo[d]));
            assign l_f[d] = l_vo[d] && (err != 2'd0);
            ot_hdc_delay #(.W(32), .D(8 - ADD_LAT)) u_pad (.clk(clk), .rst_n(rgrp[G]), .d(l_y[32*d +: 32]),
                                                           .q(fb[32*d +: 32]));
            // the local P.V tree (levels 1-3) of this lane, executing the decision word delayed 8 (see the header)
            wire [LTW-1:0] dw = lt_d[LTW*G +: LTW];
            wire        lis = dw[0], lsel = dw[1], lst0 = dw[4], lsty = dw[5], lob = dw[8];
            wire [1:0]  lal = dw[3:2], lsl = dw[7:6];
            reg  [31:0] lp0, lp1, lp2, obr;
            wire [31:0] ly;
            wire [31:0] lpa = (lal == 2'd0) ? lp0 : ((lal == 2'd1) ? lp1 : lp2);
            wire [1:0]  berr;
            wire        bvo;
            (* keep_hierarchy *) ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_b (.clk(clk), .rst_n(rgrp[G]), .valid_in(lis),
                .a(lpa), .b(lsel ? ly : fb[32*d +: 32]), .y(ly), .err(berr), .valid_out(bvo));
            assign b_f[d] = bvo && (berr != 2'd0);
            always @(posedge clk) begin
                if (lst0) lp0 <= fb[32*d +: 32];
                if (lsty && lsl == 2'd0) lp0 <= ly;
                if (lsty && lsl == 2'd1) lp1 <= ly;
                if (lsty && lsl == 2'd2) lp2 <= ly;
                if (lob) obr <= ly;
            end
            assign obw[32*d +: 32] = obr;
        end
    endgenerate
    // node slice: beat b = the lanes d = LFB k + b, from the decision word {osend, beat} of group 0's delay line
    wire [LTW-1:0] dw0 = lt_d[0 +: LTW];
    integer k_;
    always @(posedge clk) if (dw0[9]) for (k_ = 0; k_ < HD / LFB; k_ = k_ + 1)
        nb_d[32*k_ +: 32] <= obw[32*(LFB*k_ + dw0[11:10]) +: 32];
    // ---- K pass: this head's root x SCALE -------------------------------------------------------------------------------
    localparam integer LR = tnode(LV, 0);
    localparam integer GR = LR / 16;
    wire kroot_h, sv;
    wire [31:0] scd0;
    wire [1:0] merr;
    ot_hdc_delay #(.W(1), .D(ADD_LAT), .RESET(1)) u_kvm (.clk(clk), .rst_n(rt), .d(kl_g[LV*GR + LV - 1]), .q(kroot_h));
    (* keep_hierarchy *) ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_scale (
        .clk(clk), .rst_n(rt), .valid_in(kroot_h), .a(l_y[32*LR +: 32]), .b(SCALE), .y(scd0), .err(merr), .valid_out(sv));
    always @(posedge clk) sc_d <= scd0;
    always @(posedge clk or negedge rt)
        if (!rt) begin sc_f <= 1'b0; g_f <= 1'b0; end
        else begin sc_f <= sv && (merr != 2'd0); g_f <= |gfault; end
endmodule
'''


def generate():
    s = D.generate()
    mods = re.findall(r'(?m)^module\s+(\w+)_d\b', s)
    s = re.sub(r'\b(' + '|'.join(map(re.escape, mods)) + r')_d\b', r'\1_h', s)
    s = rep(s, """// GENERATED by tools/qwen_kv_die/stack_d_gen.py from rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv (do not edit by
// hand).  RE-CUT D of the near-HBM stack""", """// GENERATED by tools/qwen_kv_die/stack_h_gen.py (re-cut D with the row engine as hard sub-tiles: 4 head tiles + an
// engine control tile; do not edit by hand).  RE-CUT H of the near-HBM stack""")
    # ================= the engine: ectl from row_engine (central logic kept verbatim) =================
    i = s.index('module ot_qwen_nearhbm_row_engine_h #(')
    j = s.index('endmodule', i) + len('endmodule')
    eng = s[i:j]
    ectl = eng.replace('module ot_qwen_nearhbm_row_engine_h #(', 'module ot_qwen_nearhbm_ectl_h #(', 1)
    # ports: the node data leaves from the head tiles; the tile interface is added
    ectl = rep(ectl, """    output reg  [4*HD*32/LFB-1:0] nb_data,
""", "")
    ectl = rep(ectl, """    output reg                  ev_k_first,
    output reg                  ev_v_first
);""", """    output reg                  ev_k_first,
    output reg                  ev_v_first,
    // ---- the head tiles (hard sub-tiles): S1b outputs per tile pair, returns per head ----
    output wire [2*4-1:0]       t_c,
    output wire [2*HD*8-1:0]    t_row,
    output wire [2*64-1:0]      t_e,
    output wire [2*12-1:0]      t_lt,
    output wire [1:0]           t_qv,
    output wire [2*6-1:0]       t_qb,
    output wire [2*512-1:0]     t_qd,
    input  wire [4*32-1:0]      t_sc,
    input  wire [3:0]           t_sf,
    input  wire [3:0]           t_gf
);""")
    # q: no engine q registers (the tiles hold them); the count stays
    ectl = rep(ectl, """    reg  [8*HD*16-1:0] q_bf16;
""", "")
    ectl = rep(ectl, """    always @(posedge clk) begin qb_r <= q_beat_in; qd_r <= q_data_in; if (qv_r) q_bf16[512*qb_r +: 512] <= qd_r; end""",
               """    always @(posedge clk) begin qb_r <= q_beat_in; qd_r <= q_data_in; end""")
    # lanes / local tree / K root: replaced by the decision word, the S1 / S1b registers and the tile returns
    a = ectl.index('    // ---- the lanes ---')
    b = ectl.index('    // running max per [g][h] of this engine')
    ectl = ectl[:a] + CTL_MID + ectl[b:]
    ectl = rep(ectl, """    always @(posedge clk or negedge rc) if (!rc) gfault_any <= 1'b0; else gfault_any <= |gfault;""",
               """    always @(posedge clk or negedge rc) if (!rc) gfault_any <= 1'b0; else gfault_any <= |t_gf;""")
    ectl = rep(ectl, """    wire        take;                                   // re-cut D: the local tree takes the leaf (below)
""", """    wire        take;                                   // re-cut H: the local tree's decision (below)
""")
    ectl = rep(ectl, """                if ((|tf) || (|tree_fault) || mac_fault || lt_fault) fault <= 1'b1;""",
               """                if ((|tf) || mac_fault || lt_fault) fault <= 1'b1;""")
    ectl = rep(ectl, """    localparam integer LANE_D = 4;                         // issue -> lane inputs (S1, S1b, S2, S3)""",
               """    localparam integer LANE_D = 4;                         // issue -> lane inputs (S1, S1b, S2 at the tile pin, S3)
    localparam integer PLAT = 4;""")
    wrapper = ENGINE
    s = s[:i] + HEAD.lstrip('\n') + '\n' + ectl + '\n' + wrapper + s[j:]
    # ================= the aggregator: node beat lanes (beat b = lanes d = LFB k + b of every head) =================
    s = rep(s, """            stg[swp][(LN*32/LFB)*bb +: LN*32/LFB] <= bd;""", """            for (hh_ = 0; hh_ < 4; hh_ = hh_ + 1)
                for (kk_ = 0; kk_ < HD / LFB; kk_ = kk_ + 1)
                    stg[swp][32*(HD*hh_ + LFB*kk_ + bb) +: 32] <= bd[32*((HD / LFB)*hh_ + kk_) +: 32];""")
    s = rep(s, """        localparam integer SA = (ND > 1) ? $clog2(ND) : 1;
        reg  [LN*32-1:0] stg [0:ND-1];""", """        localparam integer SA = (ND > 1) ? $clog2(ND) : 1;
        integer          hh_, kk_;
        reg  [LN*32-1:0] stg [0:ND-1];""")
    return s


CTL_MID = r'''    // ---- re-cut H: S1 (control, row, e, decision word) and its two S1b copies, one per head-tile pair ---------------
    localparam integer LTW = 12;
    reg  [3:0]       c1;
    reg  [HD*8-1:0]  row1;
    reg  [63:0]      e1;
    reg  [LTW-1:0]   lt1;
    wire [LTW-1:0]   ltw;
    always @(posedge clk or negedge rc)
        if (!rc) begin c1[3:1] <= 3'd0; lt1 <= {LTW{1'b0}}; end
        else begin c1[3:1] <= {k_issue, v_issue && c_vrow, v_issue && (c_k == 4'd0)}; lt1 <= ltw; end
    always @(posedge clk) begin c1[0] <= c_g; row1 <= row; e1 <= e_word; end
    genvar gg, h;
    generate for (gg = 0; gg < 2; gg = gg + 1) begin : g_s1b
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(3)) u_c (.clk(clk), .rst_n(rhalf[gg]), .d(c1[3:1]), .q(t_c[4*gg+1 +: 3]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(1)) u_g (.clk(clk), .d(c1[0]), .q(t_c[4*gg]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(HD*8)) u_r (.clk(clk), .d(row1), .q(t_row[HD*8*gg +: HD*8]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(64)) u_e (.clk(clk), .d(e1), .q(t_e[64*gg +: 64]));
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(LTW)) u_t (.clk(clk), .rst_n(rhalf[gg]), .d(lt1), .q(t_lt[LTW*gg +: LTW]));
        (* keep_hierarchy *) ot_nhb_repr_h #(.W(1)) u_qv (.clk(clk), .rst_n(rhalf[gg]), .d(qv_r), .q(t_qv[gg]));
        (* keep_hierarchy *) ot_nhb_rep_h #(.W(6 + 512)) u_qd (.clk(clk), .d({qb_r, qd_r}), .q({t_qb[6*gg +: 6], t_qd[512*gg +: 512]}));
    end endgenerate
    // ---- re-cut H: the P.V tree's levels 1-3 -- the DECISIONS here, the data in the head tiles' lanes ---------------------
    // The decision logic is re-cut D's, term for term (leaves in slot order, a pending left node per level, a completing
    // pair always issues, a colliding leaf waits in its loop); the lanes execute it 8 edges later (the header).
    localparam integer NLL = 3;
    reg  [2:0]       lt_rho;
    reg  [NLL-1:0]   LPv;
    reg  [3:0]       lt_infl;
    reg              lt_g;
    reg  [3:0]       lt_gam;
    reg              lt_fault;
    wire [2:0]       lt_tag;
    wire             lt_arr_v = lt_tag[2];
    wire [1:0]       lt_arr_l = lt_tag[1:0] + 2'd1;
    wire             lt_arr_issue = lt_arr_v && (lt_arr_l < NLL) && LPv[lt_arr_l];
    reg              ob_busy;
    reg              ob_g;
    reg  [3:0]       ob_gam;
    reg  [3:0]       ob_b;
    reg  [3:0]       ob_wait;
    reg  [$clog2(ND+1)-1:0] ocred;
    reg              ocr_q;
    wire             lt_room = (lt_rho != 3'd0) || (!ob_busy && (LPv == 0) && (lt_infl == 0) && !lt_arr_v);
    assign take = offer && (os == lt_rho) && lt_room && (!LPv[0] || !lt_arr_issue);
    wire             lt_leaf_issue = take && LPv[0];
    wire             lt_issue = lt_arr_issue || lt_leaf_issue;
    wire [1:0]       lt_l = lt_arr_issue ? lt_arr_l : 2'd0;
    ot_hdc_delay #(.W(3), .D(ADD_LAT), .RESET(1)) u_lttag (.clk(clk), .rst_n(rc), .d({lt_issue, lt_l}), .q(lt_tag));
    wire             ob_send = ob_busy && (ob_wait == 4'd0) && ((ob_b != 4'd0) || (ocred != 0));
    // decision word {ob beat[1:0], osend, lob, lsl[1:0], lsty, lst0, lal[1:0], lsel, lis}
    wire             d_lst0 = take && !LPv[0];
    wire             d_lob  = lt_arr_v && (lt_arr_l == NLL);
    wire             d_lsty = lt_arr_v && (lt_arr_l < NLL) && !LPv[lt_arr_l];
    assign ltw = {ob_b[1:0], ob_send, d_lob, (d_lsty ? lt_arr_l : 2'd0), d_lsty, d_lst0, lt_l, lt_arr_issue, lt_issue};
    // the node beat: the tiles register their slice 8 edges after the decision (valid at t + 9); the tags follow (1 + 7 + 1)
    reg              nbv_n;
    reg  [3:0]       nbb_n;
    reg              nbg_n;
    reg  [3:0]       nbgam_n;
    wire [9:0]       nbt;
    always @(posedge clk or negedge rc)
        if (!rc) nbv_n <= 1'b0;
        else nbv_n <= ob_send;
    always @(posedge clk) begin nbb_n <= ob_b; nbg_n <= ob_g; nbgam_n <= ob_gam; end
    ot_hdc_delay #(.W(10), .D(7), .RESET(1)) u_nbt (.clk(clk), .rst_n(rc), .d({nbv_n, nbb_n, nbg_n, nbgam_n}), .q(nbt));
    always @(posedge clk or negedge rc) begin
        if (!rc) begin
            lt_rho <= 3'd0; LPv <= 0; lt_infl <= 0; lt_fault <= 1'b0; ob_busy <= 1'b0; ob_b <= 4'd0; ob_wait <= 4'd0;
            ocred <= ND; ocr_q <= 1'b0; nb_valid <= 1'b0;
        end else begin
            ocr_q <= nb_cr;
            nb_valid <= nbt[9];
            nb_beat <= nbt[8:5]; nb_g <= nbt[4]; nb_gam <= nbt[3:0];
            lt_infl <= lt_infl + (lt_issue ? 4'd1 : 4'd0) - (lt_arr_v ? 4'd1 : 4'd0);
            if (start) lt_rho <= 3'd0;
            if (lt_arr_v) begin
                if (lt_arr_l == NLL) begin
                    ob_busy <= 1'b1; ob_b <= 4'd0; ob_g <= lt_g; ob_gam <= lt_gam; ob_wait <= 4'd9;
                    if (ob_busy) lt_fault <= 1'b1;
                end else if (LPv[lt_arr_l]) LPv[lt_arr_l] <= 1'b0;
                else LPv[lt_arr_l] <= 1'b1;
            end else if (ob_wait != 4'd0) ob_wait <= ob_wait - 4'd1;
            if (take) begin
                if (LPv[0]) LPv[0] <= 1'b0;
                else LPv[0] <= 1'b1;
                lt_rho <= lt_rho + 3'd1;
                if (lt_rho == 3'd0) begin lt_g <= pend_g[os]; lt_gam <= pend_gam[os]; end
                else if ((pend_g[os] != lt_g) || (pend_gam[os] != lt_gam)) lt_fault <= 1'b1;
            end
            if (ob_send) begin
                if (ob_b == 4'(LFB - 1)) begin ob_busy <= 1'b0; ob_b <= 4'd0; end
                else ob_b <= ob_b + 4'd1;
            end
            ocred <= ocred - ((ob_send && ob_b == 4'd0) ? 1'b1 : 1'b0) + (ocr_q ? 1'b1 : 1'b0);
        end
    end
    // ---- K pass: the scores come back from the head tiles (their scd1); tags as before ---------------------------------------
    localparam integer SCD = KDEPTH + LANE_D + 2;
    wire [11:0] tag_sc;
    wire        sc_v_n;
    ot_hdc_delay #(.W(12), .D(SCD - 1)) u_tag (.clk(clk), .rst_n(rc), .d({c_g, c_idx[10:0]}), .q(tag_sc));
    ot_hdc_delay #(.W(1), .D(SCD - 1), .RESET(1)) u_scv (.clk(clk), .rst_n(rc), .d(k_issue), .q(sc_v_n));
    reg tf2;
    wire [3:0] tf = 4'd0;
    always @(posedge clk or negedge rc)
        if (!rc) begin sc_valid <= 1'b0; tf2 <= 1'b0; end
        else begin sc_valid <= sc_v_n; tf2 <= |t_sf; end
    always @(posedge clk) begin sc_data <= t_sc; sc_addr <= tag_sc; end

'''

ENGINE = r'''
// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_nearhbm_row_engine_h: the row engine as hard sub-tiles -- 1 control tile + 4 head tiles (ports as re-cut D)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_row_engine_h #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer E = 0,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer LFB = 4,
    parameter integer ND = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start_in,
    input  wire [13:0]          T_in,
    input  wire [2:0]           cyc8_in,
    input  wire                 q_valid_in,
    input  wire [5:0]           q_beat_in,
    input  wire [511:0]         q_data_in,
    input  wire [31:0]          exp_done,
    output wire                 req_valid,
    output wire                 req_v,
    output wire                 req_g,
    output wire [12:0]          req_t,
    input  wire                 rsp_valid_in,
    input  wire [HD*8-1:0]      rsp_data_in,
    output wire                 er_valid,
    output wire [11:0]          er_addr,
    input  wire [63:0]          er_data,
    output wire                 sc_valid,
    output wire [11:0]          sc_addr,
    output wire [127:0]         sc_data,
    output wire [2*4*32-1:0]    lmax,
    output wire [1:0]           lmax_any,
    output wire                 nb_valid,
    output wire [3:0]           nb_beat,
    output wire                 nb_g,
    output wire [3:0]           nb_gam,
    output wire [4*HD*32/LFB-1:0] nb_data,
    input  wire                 nb_cr,
    output wire                 k_done,
    output wire                 v_done,
    output wire                 fault,
    output wire                 ev_k_first,
    output wire                 ev_v_first
);
    wire [2*4-1:0]    t_c;
    wire [2*HD*8-1:0] t_row;
    wire [2*64-1:0]   t_e;
    wire [2*12-1:0]   t_lt;
    wire [1:0]        t_qv;
    wire [2*6-1:0]    t_qb;
    wire [2*512-1:0]  t_qd;
    wire [4*32-1:0]   t_sc;
    wire [3:0]        t_sf, t_gf;
    ot_qwen_nearhbm_ectl_h #(.HD(HD), .S(S), .R(R), .E(E), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .DQ(DQ), .SCALE(SCALE),
                             .LFB(LFB), .ND(ND)) u_ctl (
        .clk(clk), .rst_n(rst_n), .start_in(start_in), .T_in(T_in), .cyc8_in(cyc8_in), .q_valid_in(q_valid_in),
        .q_beat_in(q_beat_in), .q_data_in(q_data_in), .exp_done(exp_done), .req_valid(req_valid), .req_v(req_v),
        .req_g(req_g), .req_t(req_t), .rsp_valid_in(rsp_valid_in), .rsp_data_in(rsp_data_in), .er_valid(er_valid),
        .er_addr(er_addr), .er_data(er_data), .sc_valid(sc_valid), .sc_addr(sc_addr), .sc_data(sc_data), .lmax(lmax),
        .lmax_any(lmax_any), .nb_valid(nb_valid), .nb_beat(nb_beat), .nb_g(nb_g), .nb_gam(nb_gam), .nb_cr(nb_cr),
        .k_done(k_done), .v_done(v_done), .fault(fault), .ev_k_first(ev_k_first), .ev_v_first(ev_v_first),
        .t_c(t_c), .t_row(t_row), .t_e(t_e), .t_lt(t_lt), .t_qv(t_qv), .t_qb(t_qb), .t_qd(t_qd), .t_sc(t_sc),
        .t_sf(t_sf), .t_gf(t_gf));
    genvar h;
    generate for (h = 0; h < 4; h = h + 1) begin : g_head
        localparam integer P = h / 2;          // the S1b copy of this head's tile pair
        ot_qwen_nearhbm_head_h #(.HD(HD), .H(h), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .SCALE(SCALE), .LFB(LFB)) u_head (
            .clk(clk), .rst_n(rst_n), .c_in(t_c[4*P +: 4]), .row_in(t_row[HD*8*P +: HD*8]),
            .e_in(t_e[64*P + 16*h +: 16]), .lt_in(t_lt[12*P +: 12]), .q_valid_in(t_qv[P]), .q_beat_in(t_qb[6*P +: 6]),
            .q_data_in(t_qd[512*P +: 512]), .sc_d(t_sc[32*h +: 32]), .sc_f(t_sf[h]), .g_f(t_gf[h]),
            .nb_d(nb_data[(HD*32/LFB)*h +: HD*32/LFB]));
    end endgenerate
endmodule
'''


def main():
    txt = generate()
    if '--check' in sys.argv:
        sys.exit(0 if DST.exists() and DST.read_text() == txt else 1)
    DST.write_text(txt)
    print(DST)


if __name__ == '__main__':
    main()
