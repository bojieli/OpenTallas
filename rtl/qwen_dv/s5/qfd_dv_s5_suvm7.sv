`timescale 1ns/1ps
// =====================================================================================================================
// QW-SLICE7-LEAVES/SUVM 10-20: qfd_dv_s5_suvm7 = the SAFE successor master of qfd_dv_s5_suvm (HARD 1), same ports.
// Predecessor qfd_dv_s5_suvm (claude/qw-slice6-suvm-1019 375403eb0) FAILED the pre-gate ASAP7 mapped native census:
// 211 non-clock drivers > 32 loads (107 flops, 2 raw ports), max 1150 (su_go accept enable), VM read-select registers
// 1024 / 512 / 256 loads, raw ports w16_we 651 / vm_waddr[3] 254 (write merge selects).
// Structure (no masking, no layout tweak):
//   * reset: rst_n lands in 2 registered stages as before (rs1 -> rs2), but stage 2 and the control-reset copy rc are
//     KEPT REPLICAS (qfd_dv_s7_kffr), each serving <= 32 async-reset pins.  Same assertion / release edges (0 edges).
//   * issue loop: every wide-fanout control (accept = su_go, active, v_last_r) is a set of kept replica flops that all
//     capture ONE shared next-state net; each replica enables one <= 24-bit chunk.  0 edges.
//   * VM read answers: the capture flops at the macro pins stay (macro clk->q ~550 ps of the 770 ps cycle leaves no
//     room for logic before capture); the stage-2 bank / lane-offset selects are kept replicas decoded one-hot from
//     stage 1, each driving <= 16 / 32 mux pins.  Same 2-edge answer (0 edges).
//   * VM writes (su lanes window 00, w16, w1): LANDED in pin registers (+1 edge on VM write visibility); the merge
//     controls are decoded from the raw pins into kept per-(bank, 32-bit slot) one-hot registers in the same landing
//     edge, so no raw port and no landed register drives more than 32 loads.  Behaviour == qfd_dv_s5_suvm fed with the
//     write bundle {vm_we, vm_waddr, vm_wdata, w16_*, w1_*} one cycle later (bench rtl/test/qwen_dv/s5/suvm7).
//     PRICE: +1 edge VM write -> read visibility (static schedule: a read of a row written <= 1 cycle earlier is a
//     collision; compiler distance 1 -> 2) and su_idle / vm_fault see writes one edge later.  NOTICE QW-GEN3 / TOKSIM.
//   * table writes tw_* (stream tap -> CROM / BTAB / PROG) and all reads are unchanged (0 edges).
// =====================================================================================================================

(* keep_hierarchy = "yes" *) module qfd_dv_s7_kff #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule

(* keep_hierarchy = "yes" *) module qfd_dv_s7_kffr #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire rn, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck or negedge rn) if (!rn) q <= {W{1'b0}}; else q <= d;
endmodule

module qfd_dv_s5_suvm7 #(parameter integer HARD = 1, parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [9:0]     su_cmd,
    output wire [499:0]   gb,
    output wire [2:0]     gv,
    output wire [7:0]     lv1,
    output wire [8*96-1:0] pd1,
    input  wire [7:0]     va_re, vb_re, vc_re, cr_re, vm_we, kv_we, l_retire, l_last, l_fault, l_wrom_re,
    input  wire [8*24-1:0] va_addr, vb_addr, vc_addr, cr_addr, vm_waddr, l_wrom_addr,
    input  wire [8*32-1:0] vm_wdata,
    output wire [8*32-1:0] va_q, vb_q, vc_q,
    output wire [8*64-1:0] cr_q,
    input  wire           rd_v,
    input  wire           red_busy,
    input  wire           red_fault,
    input  wire           w16_we,
    input  wire [23:0]    w16_addr,
    input  wire [511:0]   w16_data,
    input  wire           w1_we,
    input  wire [23:0]    w1_addr,
    input  wire [31:0]    w1_data,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data,
    output wire           su_nr,
    output reg            su_idle,
    output reg            su_fault,
    output reg  [15:0]    su_prog,
    output reg  [15:0]    su_rows,
    output wire           vm_fault
);
    localparam integer SW = 8, LS = 3, NW = 18, AW = 24, WR = 16;
`ifndef SYNTHESIS
    initial if (HARD == 0) $fatal(1, "qfd_dv_s5_suvm7 is the HARD 1 master only (HARD 0 = qfd_dv_s5_suvm)");
`endif
    // ---------------------------------------------------------------------------------------------- reset (0 edges)
    localparam integer NR2 = 6, NRC = 10;
    reg rs1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    wire [NR2-1:0] rst_k;                     // rs2 replicas (= qfd_dv_s5_rst2 output)
    wire [NRC-1:0] rc_k;                      // rc replicas (= su8 RTREE control reset copy)
    genvar gi;
    generate for (gi = 0; gi < NR2; gi = gi + 1) begin : g_rs2
        qfd_dv_s7_kffr #(.W(1), .ID(gi)) u (.ck(ck), .rn(rst_n), .d(rs1), .q(rst_k[gi]));
    end
    for (gi = 0; gi < NRC; gi = gi + 1) begin : g_rc
        qfd_dv_s7_kffr #(.W(1), .ID(gi)) u (.ck(ck), .rn(rst_k[gi % NR2]), .d(1'b1), .q(rc_k[gi]));
    end endgenerate
    wire rg;
    qfd_dv_s7_kffr #(.W(1), .ID(100)) u_rg (.ck(ck), .rn(rst_k[0]), .d(1'b1), .q(rg));

    // ---------------------------------------------------------------------------------------------- su_go (c_su + 2)
    localparam integer NFA = 31;               // accept-only field chunks (12 b)
    localparam integer NCH = 32;               // active-updated register chunks (8 b: cur 12, row 12, rrow 3, v 2, o 2, cls 1)
    localparam integer NXS = 8;                // lane copies of the stride fields (12 b select groups)
    localparam integer NACC = NFA + NCH + 8 + NXS; // + act_next, vl_next, ol_next/gvr, first_mark, su_prog, r_mark, su_rows, su_go
    wire c_su = su_cmd[9];
    wire [2:0] sg0;
    generate for (gi = 0; gi < 3; gi = gi + 1) begin : g_sg0
        qfd_dv_s7_kffr #(.W(1), .ID(200 + gi)) u (.ck(ck), .rn(rst_k[1]), .d(c_su), .q(sg0[gi]));
    end endgenerate
    wire [NACC-1:0] acc_k;
    generate for (gi = 0; gi < NACC; gi = gi + 1) begin : g_acc
        qfd_dv_s7_kffr #(.W(1), .ID(300 + gi)) u (.ck(ck), .rn(rst_k[2 + (gi % 4)]), .d(sg0[gi % 3]), .q(acc_k[gi]));
    end endgenerate
    wire su_go = acc_k[NFA + NCH + 7];        // su_idle, su_nr / fault

    // ---------------------------------------------------------------------------------------------- program word
    wire [456:0] si;
    wire [NW-1:0] i_nout = si[18:1], i_nin = si[36:19];
    wire          i_asrc = si[37], i_bsrc = si[110], i_csrc = si[183];
    wire [AW-1:0] i_abase = si[61:38], i_aso = si[85:62], i_asi = si[109:86];
    wire [AW-1:0] i_bbase = si[134:111], i_bso = si[158:135], i_bsi = si[182:159];
    wire [AW-1:0] i_cbase = si[207:184], i_cso = si[231:208], i_csi = si[255:232];
    wire [1:0]    i_ma = si[257:256], i_mb = si[259:258];
    wire [2:0]    i_ad = si[262:260], i_sfu = si[265:263];
    wire          i_mc = si[266], i_md = si[267];
    wire [1:0]    i_dst = si[269:268];
    wire [AW-1:0] i_dbase = si[293:270], i_dso = si[317:294], i_dsi = si[341:318];
    wire [1:0]    i_red = si[343:342];
    wire          i_redsq = si[344];
    wire [AW-1:0] i_rbase = si[368:345], i_rso = si[392:369];
    wire [31:0]   i_imm1 = si[424:393], i_imm2 = si[456:425];
    wire [NW-1:0] nvec_in = (i_nin + (SW - 1)) >> LS;

    // ---------------------------------------------------------------------------------------------- accept-only fields
    // packed: {nout_r, nin_r, nvec_r, fin_th, aso, asi, bso, bsi, cso, csi, dso, dsi, rso,
    //          asrc, bsrc, csrc, mc, md, redsq, ma, mb, dst, red, ad, imm1, imm2} = 18*3 + 19 + 9*24 + 6 + 8 + 3 + 64 = 370
    localparam integer FAW = 370, FCW = 12;
    wire [FAW-1:0] fa_in = {i_nout, i_nin, nvec_in, ({1'b0, nvec_in} - 19'd8), i_aso, i_asi, i_bso, i_bsi, i_cso, i_csi,
                            i_dso, i_dsi, i_rso, i_asrc, i_bsrc, i_csrc, i_mc, i_md, i_redsq, i_ma, i_mb, i_dst, i_red,
                            i_ad, i_imm1, i_imm2};
    reg  [FAW-1:0] fa;
    integer fi;
    always @(posedge ck)
        for (fi = 0; fi < FAW; fi = fi + 1) if (acc_k[fi / FCW]) fa[fi] <= fa_in[fi];
    wire [NW-1:0] nout_r = fa[369:352], nin_r = fa[351:334], nvec_r = fa[333:316];
    wire [NW:0]   fin_th = fa[315:297];
    wire [AW-1:0] aso = fa[296:273], asi = fa[272:249], bso = fa[248:225], bsi = fa[224:201];
    wire [AW-1:0] cso = fa[200:177], csi = fa[176:153], dso = fa[152:129], dsi = fa[128:105], rso = fa[104:81];
    wire          asrc = fa[80], bsrc = fa[79], csrc = fa[78], mc = fa[77], md = fa[76], redsq = fa[75];
    wire [1:0]    ma = fa[74:73], mb = fa[72:71], dst = fa[70:69], red = fa[68:67];
    wire [2:0]    ad = fa[66:64];
    wire [31:0]   imm1 = fa[63:32], imm2 = fa[31:0];

    // ---------------------------------------------------------------------------------------------- active / v_last
    localparam integer NACT = NCH + 6;          // chunk users + emit (inflight, counters, gvr), idle, ready, next-B source
    localparam integer NVL  = NCH + 4;
    wire [NACT-1:0] act_k;
    wire [NVL-1:0]  vl_k;
    wire            o_last_r;
    reg  [2:0]      cls;
    reg  [7:0]      inflight;
    wire            act0 = act_k[NACT-1], vl0 = vl_k[NVL-1];
    wire            acc0 = acc_k[NFA + NCH];
    // two structurally distinct copies of the next-state net (different source replicas: never merged), <= 19 D pins each
    wire act_nextA = acc0 ? 1'b1 : (act0 && vl0 && o_last_r) ? 1'b0 : act0;
    wire act_nextB = acc_k[NFA + NCH + 3] ? 1'b1 : (act_k[NACT-6] && vl_k[NVL-4] && o_last_r) ? 1'b0 : act_k[NACT-6];
    generate for (gi = 0; gi < NACT; gi = gi + 1) begin : g_act
        qfd_dv_s7_kffr #(.W(1), .ID(400 + gi)) u (.ck(ck), .rn(rc_k[gi % 4]), .d((gi % 2) ? act_nextB : act_nextA), .q(act_k[gi]));
    end endgenerate
    // the active-updated registers (chunked, each chunk with its own accept / active / v_last copies)
    reg  [NW-1:0] o, v;
    reg  [AW-1:0] rowa, rowb, rowc, rowd, cura, curb, curc, curd, rrow;
    wire          acc1 = acc_k[NFA + NCH + 1];
    wire          vl_stepA = (v + 2 == nvec_r), vl_one = (nvec_r == 1), vl_inA = (nvec_in == 1);
    wire          vl_nextA = acc1 ? vl_inA : act_k[NACT-2] ? (!vl_k[NVL-2] ? vl_stepA : vl_one) : vl_k[NVL-2];
    wire          vl_nextB = acc_k[NFA + NCH + 4] ? vl_inA : act_k[NACT-6] ? (!vl_k[NVL-4] ? vl_stepA : vl_one) : vl_k[NVL-4];
    generate for (gi = 0; gi < NVL; gi = gi + 1) begin : g_vl
        qfd_dv_s7_kff #(.W(1), .ID(500 + gi)) u (.ck(ck), .d((gi % 2) ? vl_nextB : vl_nextA), .q(vl_k[gi]));
    end endgenerate
    wire          acc2 = acc_k[NFA + NCH + 2];
    wire          ol_next = acc2 ? (i_nout == 1) : (act_k[NACT-3] && vl_k[NVL-3]) ? (o + 2 == nout_r) : o_last_r;
    qfd_dv_s7_kff #(.W(1), .ID(600)) u_ol (.ck(ck), .d(ol_next), .q(o_last_r));
    // chunk c: selects of chunk c (accept, step-vector, step-row)
    wire [NCH-1:0] s_acc, s_vec, s_row;
    generate for (gi = 0; gi < NCH; gi = gi + 1) begin : g_sel
        assign s_acc[gi] = acc_k[NFA + gi];
        assign s_vec[gi] = act_k[gi] && !vl_k[gi];
        assign s_row[gi] = act_k[gi] && vl_k[gi];
    end endgenerate
    // 8-bit chunk next-state nets: base on accept, vector step / row step while active, else hold
`define S7_CH(R, RN, LO, C, BASE, VSTEP, RSTEP) \
    assign RN[LO +: 8] = s_acc[C] ? BASE : s_vec[C] ? VSTEP : s_row[C] ? RSTEP : R[LO +: 8];
    wire [AW-1:0] cura_v = cura + (asi << LS), curb_v = curb + (bsi << LS), curc_v = curc + (csi << LS), curd_v = curd + (dsi << LS);
    wire [AW-1:0] rowa_n = rowa + aso, rowb_n = rowb + bso, rowc_n = rowc + cso, rowd_n = rowd + dso, rrow_n = rrow + rso;
    wire [AW-1:0] cura_nx, curb_nx, curc_nx, curd_nx, rowa_nx, rowb_nx, rowc_nx, rowd_nx, rrow_nx;
    genvar gc;
    generate for (gc = 0; gc < 3; gc = gc + 1) begin : g_ch
        `S7_CH(cura, cura_nx, 8*gc, 0 + gc, i_abase[8*gc +: 8], cura_v[8*gc +: 8], rowa_n[8*gc +: 8])
        `S7_CH(curb, curb_nx, 8*gc, 3 + gc, i_bbase[8*gc +: 8], curb_v[8*gc +: 8], rowb_n[8*gc +: 8])
        `S7_CH(curc, curc_nx, 8*gc, 6 + gc, i_cbase[8*gc +: 8], curc_v[8*gc +: 8], rowc_n[8*gc +: 8])
        `S7_CH(curd, curd_nx, 8*gc, 9 + gc, i_dbase[8*gc +: 8], curd_v[8*gc +: 8], rowd_n[8*gc +: 8])
        `S7_CH(rowa, rowa_nx, 8*gc, 12 + gc, i_abase[8*gc +: 8], rowa[8*gc +: 8], rowa_n[8*gc +: 8])
        `S7_CH(rowb, rowb_nx, 8*gc, 15 + gc, i_bbase[8*gc +: 8], rowb[8*gc +: 8], rowb_n[8*gc +: 8])
        `S7_CH(rowc, rowc_nx, 8*gc, 18 + gc, i_cbase[8*gc +: 8], rowc[8*gc +: 8], rowc_n[8*gc +: 8])
        `S7_CH(rowd, rowd_nx, 8*gc, 21 + gc, i_dbase[8*gc +: 8], rowd[8*gc +: 8], rowd_n[8*gc +: 8])
        `S7_CH(rrow, rrow_nx, 8*gc, 24 + gc, i_rbase[8*gc +: 8], rrow[8*gc +: 8], rrow_n[8*gc +: 8])
    end endgenerate
`undef S7_CH
    always @(posedge ck) begin
        cura <= cura_nx; curb <= curb_nx; curc <= curc_nx; curd <= curd_nx;
        rowa <= rowa_nx; rowb <= rowb_nx; rowc <= rowc_nx; rowd <= rowd_nx; rrow <= rrow_nx;
    end
    // v (vector index): 0 on accept, +1 per vector step, 0 on row step; o (row index): 0 on accept, +1 per row step
    wire [NW-1:0] v_p1 = v + 1'b1, o_p1 = o + 1'b1;
    always @(posedge ck) begin
        if (s_acc[27]) v[8:0] <= 9'd0; else if (s_vec[27]) v[8:0] <= v_p1[8:0]; else if (s_row[27]) v[8:0] <= 9'd0;
        if (s_acc[28]) v[17:9] <= 9'd0; else if (s_vec[28]) v[17:9] <= v_p1[17:9]; else if (s_row[28]) v[17:9] <= 9'd0;
        if (s_acc[29]) o[8:0] <= 9'd0; else if (s_row[29]) o[8:0] <= o_p1[8:0];
        if (s_acc[30]) o[17:9] <= 9'd0; else if (s_row[30]) o[17:9] <= o_p1[17:9];
    end
    // chunk 31: the sfu class (reset register, accept-loaded)
    always @(posedge ck or negedge rc_k[0]) begin
        if (!rc_k[0]) cls <= 3'd0;
        else if (s_acc[31]) cls <= i_sfu;
    end
    // per-lane-pair copies of the current addresses and per-lane copies of the strides (lane offset adders)
    wire [4*AW-1:0] cur_nx = {cura_nx, curb_nx, curc_nx, curd_nx};
    wire [4*AW-1:0] xs_cur = {asi, bsi, csi, dsi};
    wire [4*AW-1:0] xs_in  = {i_asi, i_bsi, i_csi, i_dsi};
    wire [4*AW-1:0] xs_nx;
    generate for (gc = 0; gc < NXS; gc = gc + 1) begin : g_xs
        assign xs_nx[12*gc +: 12] = acc_k[NFA + NCH + 8 + gc] ? xs_in[12*gc +: 12] : xs_cur[12*gc +: 12];
    end endgenerate
    wire [4*AW-1:0] cur_l [0:3];
    wire [4*AW-1:0] xs_l [0:7];
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_curl
        qfd_dv_s7_kff #(.W(4*AW), .ID(650 + gc)) u (.ck(ck), .d(cur_nx), .q(cur_l[gc]));
    end
    for (gc = 0; gc < 8; gc = gc + 1) begin : g_xsl
        qfd_dv_s7_kff #(.W(4*AW), .ID(660 + gc)) u (.ck(ck), .d(xs_nx), .q(xs_l[gc]));
    end endgenerate
    wire retire = l_retire[0];
    wire emit_i = act_k[NACT-4];                 // inflight
    wire emit_c = act_k[NACT-5];                 // counters + group relay valid
    wire ready = !act_k[NACT-3 - 0] && ((i_sfu == cls) || (inflight == 0));
    always @(posedge ck or negedge rc_k[1])
        if (!rc_k[1]) inflight <= 8'd0;
        else inflight <= inflight + (emit_i ? 8'd1 : 8'd0) - (retire ? 8'd1 : 8'd0);

    // ---------------------------------------------------------------------------------------------- group relay (kept)
    wire [WR*16-1:0] wrom_q;
    (* keep *) reg [499:0] gbr;
    (* keep *) reg [2:0]   gvr;
    always @(posedge ck or negedge rg) if (!rg) gvr <= 3'd0; else gvr <= {emit_c, acc_k[NFA + NCH + 2], vl_k[NVL-1]};
    always @(posedge ck) gbr <= {v, fin_th, rrow, asi, bsi, csi, dsi, asrc, bsrc, csrc, mc, md, redsq,
                                 ma, mb, dst, red, ad, cls, i_sfu, imm1, imm2, wrom_q};
    assign gb = gbr;
    assign gv = gvr;

    // ---------------------------------------------------------------------------------------------- lanes, stage 1
`ifdef OT_S7_SUVM_MUT
    localparam integer LMUT = 1;      // bench mutant (suvm7 only): lane offset applied twice (must FAIL)
`else
    localparam integer LMUT = 0;
`endif
    genvar gl;
    generate for (gl = 0; gl < SW; gl = gl + 1) begin : g_lane
        wire live = ({1'b0, v} << LS) + gl < {1'b0, nin_r};
        wire [AW-1:0] lcura = cur_l[gl/2][72 +: 24], lcurb = cur_l[gl/2][48 +: 24], lcurc = cur_l[gl/2][24 +: 24], lcurd = cur_l[gl/2][0 +: 24];
        wire [AW-1:0] lasi = xs_l[gl][72 +: 24], lbsi = xs_l[gl][48 +: 24], lcsi = xs_l[gl][24 +: 24], ldsi = xs_l[gl][0 +: 24];
        wire [AW-1:0] tcura = lcura + gl * lasi + LMUT * gl * lasi, tcurb = lcurb + gl * lbsi;
        wire [AW-1:0] tcurc = lcurc + gl * lcsi, tcurd = lcurd + gl * ldsi;
        qfd_dv_s7_kffr #(.W(1), .ID(700 + gl)) u_lv (.ck(ck), .rn(rc_k[2 + (gl % 2)]), .d(live), .q(lv1[gl]));
        reg [4*AW-1:0] pdr;
        always @(posedge ck) pdr <= {tcura, tcurb, tcurc, tcurd};
        assign pd1[96*gl +: 96] = pdr;
    end endgenerate

    // ---------------------------------------------------------------------------------------------- progress / idle / fault
    reg [15:0] n_emit, n_retire, first_mark, r_emit, r_retire, r_mark;
    wire [15:0] done_n = n_retire - first_mark, rdone_n = r_retire - r_mark;
    always @(posedge ck or negedge rc_k[4])
        if (!rc_k[4]) begin n_emit <= 0; n_retire <= 0; end
        else begin
            n_emit <= n_emit + (emit_c ? 16'd1 : 16'd0);
            n_retire <= n_retire + (retire ? 16'd1 : 16'd0);
        end
    always @(posedge ck or negedge rc_k[8])
        if (!rc_k[8]) begin first_mark <= 0; su_prog <= 0; end
        else begin
            if (acc_k[NFA + NCH + 3]) first_mark <= n_emit;
            if (acc_k[NFA + NCH + 4]) su_prog <= 0; else su_prog <= done_n[15] ? 16'd0 : done_n;
        end
    always @(posedge ck or negedge rc_k[5])
        if (!rc_k[5]) begin r_emit <= 0; r_retire <= 0; end
        else begin
            r_emit <= r_emit + ((act_k[NACT-1] && vl_k[NVL-3]) ? 16'd1 : 16'd0);
            r_retire <= r_retire + ((retire && l_last[0]) ? 16'd1 : 16'd0);
        end
    always @(posedge ck or negedge rc_k[9])
        if (!rc_k[9]) begin r_mark <= 0; su_rows <= 0; end
        else begin
            if (acc_k[NFA + NCH + 5]) r_mark <= r_emit;
            if (acc_k[NFA + NCH + 6]) su_rows <= 0; else su_rows <= rdone_n[15] ? 16'd0 : rdone_n;
        end
    // landed write enables (the VM write bundle lands one edge late: idle sees the landed bundle)
    wire [7:0] lvm_we;
    wire idle_c = !act_k[NACT-2] && inflight == 0 && !(|lvm_we) && !(|kv_we) && !rd_v && !red_busy;
    always @(posedge ck or negedge rc_k[6])
        if (!rc_k[6]) su_idle <= 1'b1;
        else su_idle <= idle_c && !su_go;
    reg fault_q;
    wire nr_c = su_go && !ready;
    always @(posedge ck or negedge rc_k[7]) begin
        if (!rc_k[7]) begin fault_q <= 1'b0; su_fault <= 1'b0; end
        else begin
            fault_q <= fault_q || nr_c || (|l_fault) || red_fault;
            su_fault <= fault_q;
        end
    end
    qfd_dv_s7_kffr #(.W(1), .ID(800)) u_nq (.ck(ck), .rn(rst_k[0]), .d(nr_c), .q(su_nr));

    // ---------------------------------------------------------------------------------------------- VM
    qfd_dv_s5_vm7 #(.MUT(MUT)) u_vm (.ck(ck), .rst_n(rst_k[0]),
        .a_re(va_re), .b_re(vb_re), .c_re(vc_re), .a_addr(va_addr), .b_addr(vb_addr), .c_addr(vc_addr),
        .a_q(va_q), .b_q(vb_q), .c_q(vc_q),
        .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(cr_q),
        .bs_re(l_wrom_re[0]), .bs_addr(l_wrom_addr[0 +: AW]), .bs_q(wrom_q),
        .p_re(c_su), .p_idx(su_cmd[8:0]), .p_q(si),
        .vm_we(vm_we), .su_waddr(vm_waddr), .su_wdata(vm_wdata), .lvm_we(lvm_we),
        .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(vm_fault));
endmodule

// =====================================================================================================================
// qfd_dv_s5_vm7: qfd_dv_s5_vm with (1) the VM write bundle landed (+1 edge) and its merge controls decoded into kept
// per-(bank, slot) one-hot registers, (2) stage-2 read selects as kept one-hot replicas.  Reads, CROM / BTAB / PROG
// answers, table writes: edge-for-edge qfd_dv_s5_vm.
// =====================================================================================================================
module qfd_dv_s5_vm7 #(parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output wire [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]    cr_re,
    input  wire [8*24-1:0] cr_addr,
    output wire [8*64-1:0] cr_q,
    input  wire          bs_re,
    input  wire [23:0]   bs_addr,
    output wire [255:0]  bs_q,
    input  wire          p_re,
    input  wire [8:0]    p_idx,
    output wire [456:0]  p_q,
    input  wire [7:0]    vm_we,              // ALL lane VM writes (window decode here; idle uses the landed copy)
    input  wire [8*24-1:0] su_waddr,
    input  wire [8*32-1:0] su_wdata,
    output wire [7:0]    lvm_we,
    input  wire          w16_we,
    input  wire [23:0]   w16_addr,
    input  wire [511:0]  w16_data,
    input  wire          w1_we,
    input  wire [23:0]   w1_addr,
    input  wire [31:0]   w1_data,
    input  wire          tw_we,
    input  wire [1:0]    tw_kind,
    input  wire [23:0]   tw_addr,
    input  wire [1023:0] tw_data,
    output reg           fault
);
    integer l, b, s, k;
    genvar gl, gb, gs, gk, op, bk;
    // ================================================================ write landing (+1 edge)
    // raw-pin decode (each raw pin <= ~20 loads), landed in the same edge
    wire su_any_r = (|vm_we) && su_waddr[23:22] == 2'b00;          // qfd_dv_s5_suvm su_vm_we window 00
    wire [7:0] su_we_r = su_any_r ? vm_we : 8'd0;
    wire su_bank_r = su_waddr[3];
    wire w1_bank_r = w1_addr[3];
    // hit[l][s]: lane l writes slot s; later lanes win (qfd_dv_vm loop order)
    reg [7:0] hit_r [0:7];
    reg [7:0] win_r [0:1][0:7];              // [bank][slot] one-hot lane (no w16 this cycle)
    reg [7:0] gw1_r [0:1], gmx_r [0:1];      // w1 select / mask without the w16 term
    wire [1:0] sub_r;                         // su write lands in bank b (and no w16 overrides it)
    assign sub_r[0] = !w16_we && su_any_r && !su_bank_r;
    assign sub_r[1] = !w16_we && su_any_r && su_bank_r;
    wire [1:0] w1b_r;
    assign w1b_r[0] = !w16_we && w1_we && !w1_bank_r && !(su_any_r && !su_bank_r);
    assign w1b_r[1] = !w16_we && w1_we && w1_bank_r && !(su_any_r && su_bank_r);
    // bank-qualified lane enables first (sub_r: 8 loads each), then the slot decode (one-hot offset: 2 banks each)
    reg [7:0] lwe_b [0:1];
    reg [7:0] off_oh [0:7];
    always @(*) begin
        for (l = 0; l < 8; l = l + 1) begin
            lwe_b[0][l] = sub_r[0] && vm_we[l];
            lwe_b[1][l] = sub_r[1] && vm_we[l];
            off_oh[l] = 8'd1 << su_waddr[24*l +: 3];
        end
        for (l = 0; l < 8; l = l + 1)
            for (s = 0; s < 8; s = s + 1) hit_r[l][s] = su_we_r[l] && off_oh[l][s];
        for (b = 0; b < 2; b = b + 1)
            for (s = 0; s < 8; s = s + 1) begin
                for (l = 0; l < 8; l = l + 1) begin
                    win_r[b][s][l] = lwe_b[b][l] && off_oh[l][s];
`ifdef OT_S7_WPRI_MUT
                    for (k = 0; k < l; k = k + 1) if (hit_r[k][s]) win_r[b][s][l] = 1'b0;   // bench mutant: EARLIER lane wins (must FAIL)
`else
                    for (k = l + 1; k < 8; k = k + 1) if (hit_r[k][s]) win_r[b][s][l] = 1'b0;
`endif
                end
                gw1_r[b][s] = w1b_r[b] && w1_addr[2:0] == s[2:0];
                gmx_r[b][s] = (|win_r[b][s]) || gw1_r[b][s];
            end
    end
    // per-bank row selects (landed): w16 > su > w1 (qfd_dv_vm merge order)
    wire [1:0] s16_r = {2{w16_we}};
    wire [1:0] ssu_r = {su_any_r && su_bank_r, su_any_r && !su_bank_r};
    wire [1:0] sw1_r = {w1_we && w1_bank_r, w1_we && !w1_bank_r};
    // write checks on the raw bundle, landed (fault = qfd_dv_s5_vm's on the one-edge-late bundle)
    reg w_coll_r, w_bad_r;
    always @(*) begin
        w_coll_r = 1'b0; w_bad_r = 1'b0;
        if (w1_we && w1_addr[23:14] != 10'd0) w_bad_r = 1'b1;
        if (su_any_r) begin
            for (l = 0; l < 8; l = l + 1)
                if (su_we_r[l] && (su_waddr[24*l+3 +: 21] != su_waddr[3 +: 21] || !su_we_r[0])) w_bad_r = 1'b1;
            if (su_waddr[23:14] != 10'd0) w_bad_r = 1'b1;
            if (w1_we && w1_bank_r == su_bank_r) w_coll_r = 1'b1;
        end
        if (w16_we) begin
            if (w16_addr[3:0] != 4'd0 || w16_addr[23:14] != 10'd0) w_bad_r = 1'b1;
            if (w1_we || su_any_r) w_coll_r = 1'b1;
        end
    end
    // landed registers
    reg  [7:0]   lvm_we_q;
    reg  [255:0] l_sud;
    reg  [511:0] l_w16d;
    reg  [31:0]  l_w1d;
    reg  [9:0]   l_r16, l_rsu, l_rw1;
    reg          l_wbad;
    always @(posedge ck) begin
        lvm_we_q <= vm_we; l_sud <= su_wdata; l_w16d <= w16_data; l_w1d <= w1_data;
        l_r16 <= w16_addr[13:4]; l_rsu <= su_waddr[13:4]; l_rw1 <= w1_addr[13:4];
        l_wbad <= w_bad_r || w_coll_r;
    end
    assign lvm_we = lvm_we_q;
    wire [1:0] l_s16, l_ssu, l_sw1;
    qfd_dv_s7_kff #(.W(2), .ID(900)) u_s16 (.ck(ck), .d(s16_r), .q(l_s16));
    qfd_dv_s7_kff #(.W(2), .ID(901)) u_ssu (.ck(ck), .d(ssu_r), .q(l_ssu));
    qfd_dv_s7_kff #(.W(2), .ID(902)) u_sw1 (.ck(ck), .d(sw1_r), .q(l_sw1));
    wire [1:0] l_we = l_s16 | l_ssu | l_sw1;
    wire [9:0] l_row [0:1];
    assign l_row[0] = l_s16[0] ? l_r16 : l_ssu[0] ? l_rsu : l_rw1;
    assign l_row[1] = l_s16[1] ? l_r16 : l_ssu[1] ? l_rsu : l_rw1;
    // kept per-(bank, slot) controls: lane one-hot (each bit drives 32 data AND pins), w16 / w1 selects, mask
    wire [255:0] wb_d [0:1];
    wire [255:0] wb_m [0:5];                 // [2*replica + bank]: one mask net per replica (32 macro pins each)
    wire [5:0] l_s16m;                       // w16 mask term per replica x bank
    qfd_dv_s7_kff #(.W(6), .ID(903)) u_s16m (.ck(ck), .d({3{s16_r}}), .q(l_s16m));
    generate for (gb = 0; gb < 2; gb = gb + 1) begin : g_wb
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_s
            wire [7:0] lw;
            wire l16, lw1;
            wire [2:0] lmx;
            qfd_dv_s7_kff #(.W(8), .ID(1000 + 16*gb + gs)) u_win (.ck(ck), .d(win_r[gb][gs]), .q(lw));
            qfd_dv_s7_kff #(.W(1), .ID(1100 + 16*gb + gs)) u_16 (.ck(ck), .d(w16_we), .q(l16));
            qfd_dv_s7_kff #(.W(1), .ID(1200 + 16*gb + gs)) u_w1 (.ck(ck), .d(gw1_r[gb][gs]), .q(lw1));
            qfd_dv_s7_kff #(.W(3), .ID(1300 + 16*gb + gs)) u_m (.ck(ck), .d({3{gmx_r[gb][gs]}}), .q(lmx));
            reg [31:0] dsel;
            always @(*) begin
                dsel = ({32{lw1}} & l_w1d) | ({32{l16}} & l_w16d[256*gb + 32*gs +: 32]);
                for (l = 0; l < 8; l = l + 1) dsel = dsel | ({32{lw[l]}} & l_sud[32*l +: 32]);
            end
            assign wb_d[gb][32*gs +: 32] = dsel;
            assign wb_m[0 + gb][32*gs +: 32] = {32{l_s16m[0 + gb] | lmx[0]}};
            assign wb_m[2 + gb][32*gs +: 32] = {32{l_s16m[2 + gb] | lmx[1]}};
            assign wb_m[4 + gb][32*gs +: 32] = {32{l_s16m[4 + gb] | lmx[2]}};
        end
    end endgenerate
    // ================================================================ VM reads: 3 replicas x 2 banks (unchanged)
    wire [2:0] rq_re = {c_re[0], b_re[0], a_re[0]};
    wire [24*3-1:0] rq_a0 = {c_addr[23:0], b_addr[23:0], a_addr[23:0]};
    wire [3*256*2-1:0] vm_rd;
    generate for (op = 0; op < 3; op = op + 1) begin : g_rep
        for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
            ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck),
                .r_ce_in(rq_re[op] && rq_a0[24*op+3] == bk[0] && !(l_we[bk] && l_row[bk] == rq_a0[24*op+4 +: 10])),
                .r_addr_in(rq_a0[24*op+4 +: 10]),
                .rd_out(vm_rd[(2*op+bk)*256 +: 256]),
                .w_ce_in(l_we[bk]), .w_addr_in(l_row[bk]), .wd_in(wb_d[bk]), .w_mask_in(wb_m[2*op + bk]),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate
    // stage 1 (macro read edge): bank + lane offsets; stage 2: capture flops at the macro pins + KEPT one-hot selects
    reg  [2:0]    s1_bank;
    reg  [3*24-1:0] s1_off;
    reg  [3*512-1:0] cap;
    always @(posedge ck) begin
        s1_bank <= {c_addr[3], b_addr[3], a_addr[3]};
        for (l = 0; l < 8; l = l + 1) begin
            s1_off[3*l +: 3]      <= a_addr[24*l +: 3];
            s1_off[24 + 3*l +: 3] <= b_addr[24*l +: 3];
            s1_off[48 + 3*l +: 3] <= c_addr[24*l +: 3];
        end
        cap <= vm_rd;
    end
    wire [255:0] wsel [0:2];
    generate for (op = 0; op < 3; op = op + 1) begin : g_rsel
        // bank: 16 kept copies, each muxes 16 bits
        for (gk = 0; gk < 16; gk = gk + 1) begin : g_bk
            wire bq;
            qfd_dv_s7_kff #(.W(1), .ID(2000 + 16*op + gk)) u (.ck(ck), .d(s1_bank[op]), .q(bq));
            assign wsel[op][16*gk +: 16] = bq ? cap[512*op + 256 + 16*gk +: 16] : cap[512*op + 16*gk +: 16];
        end
    end endgenerate
    wire [255:0] wa = wsel[0], wbq = wsel[1], wc = wsel[2];
    wire [255:0] wb_sel = (MUT == 5) ? wc : wbq;
    generate for (op = 0; op < 3; op = op + 1) begin : g_rext
        for (gl = 0; gl < 8; gl = gl + 1) begin : g_l
            wire [7:0] dec = 8'd1 << s1_off[24*op + 3*gl +: 3];
            wire [7:0] oh0, oh1;           // two kept copies: bits 15:0 / 31:16
            qfd_dv_s7_kff #(.W(8), .ID(2100 + 16*op + 2*gl)) u0 (.ck(ck), .d(dec), .q(oh0));
            qfd_dv_s7_kff #(.W(8), .ID(2101 + 16*op + 2*gl)) u1 (.ck(ck), .d(dec), .q(oh1));
            wire [255:0] wsrc = (op == 0) ? wa : (op == 1) ? wb_sel : wc;
            reg [31:0] e;
            always @(*) begin
                e = 32'd0;
                for (s = 0; s < 8; s = s + 1)
                    e = e | {({16{oh1[s]}} & wsrc[32*s + 16 +: 16]), ({16{oh0[s]}} & wsrc[32*s +: 16])};
            end
            if (op == 0) begin : g_a assign a_q[32*gl +: 32] = e; end
            else if (op == 1) begin : g_b assign b_q[32*gl +: 32] = e; end
            else begin : g_c assign c_q[32*gl +: 32] = e; end
        end
    end endgenerate
    // ================================================================ CROM: 2 banks x {lo, hi} (unchanged writes)
    wire [4*256-1:0] cr_rd;
    reg  [255:0] cw_lo [0:1], cw_hi [0:1];
    always @(*) begin
        for (b = 0; b < 2; b = b + 1)
            for (l = 0; l < 8; l = l + 1) begin
                cw_lo[b][32*l +: 32] = tw_data[64*(8*b+l) +: 32];
                cw_hi[b][32*l +: 32] = tw_data[64*(8*b+l) + 32 +: 32];
            end
    end
    wire cr_w = tw_we && tw_kind == 2'd1;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_crom
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(cr_re[0] && cr_addr[3] == bk[0]), .r_addr_in(cr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk)*256 +: 256]), .w_ce_in(cr_w), .w_addr_in(tw_addr[9:0]), .wd_in(cw_lo[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(cr_re[0] && cr_addr[3] == bk[0]), .r_addr_in(cr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk+1)*256 +: 256]), .w_ce_in(cr_w), .w_addr_in(tw_addr[9:0]), .wd_in(cw_hi[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire [1:0] c1_bank;                      // 2 kept copies of the stage-1 bank
    qfd_dv_s7_kff #(.W(2), .ID(3300)) u_c1 (.ck(ck), .d({2{cr_addr[3]}}), .q(c1_bank));
    reg [23:0] c1_off;
    reg [1023:0] ccap;
    always @(posedge ck) begin
        for (l = 0; l < 8; l = l + 1) c1_off[3*l +: 3] <= cr_addr[24*l +: 3];
        ccap <= cr_rd;
    end
    wire [255:0] clo, chi;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_cbk
        wire bq_lo, bq_hi;
        qfd_dv_s7_kff #(.W(1), .ID(3000 + gk)) u_lo (.ck(ck), .d(c1_bank[0]), .q(bq_lo));
        qfd_dv_s7_kff #(.W(1), .ID(3100 + gk)) u_hi (.ck(ck), .d(c1_bank[1]), .q(bq_hi));
        assign clo[16*gk +: 16] = bq_lo ? ccap[256*2 + 16*gk +: 16] : ccap[256*0 + 16*gk +: 16];
        assign chi[16*gk +: 16] = bq_hi ? ccap[256*3 + 16*gk +: 16] : ccap[256*1 + 16*gk +: 16];
    end endgenerate
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_cext
        wire [7:0] dec = 8'd1 << c1_off[3*gl +: 3];
        wire [7:0] oh [0:3];               // 4 kept copies: lo 15:0, lo 31:16, hi 15:0, hi 31:16
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_c
            qfd_dv_s7_kff #(.W(8), .ID(3200 + 4*gl + gk)) u (.ck(ck), .d(dec), .q(oh[gk]));
        end
        reg [31:0] lo_e, hi_e;
        always @(*) begin
            lo_e = 32'd0; hi_e = 32'd0;
            for (s = 0; s < 8; s = s + 1) begin
                lo_e = lo_e | {({16{oh[1][s]}} & clo[32*s + 16 +: 16]), ({16{oh[0][s]}} & clo[32*s +: 16])};
                hi_e = hi_e | {({16{oh[3][s]}} & chi[32*s + 16 +: 16]), ({16{oh[2][s]}} & chi[32*s +: 16])};
            end
        end
        assign cr_q[64*gl +: 64] = (MUT == 4) ? {lo_e, hi_e} : {hi_e, lo_e};
    end endgenerate
    // ================================================================ BTAB (SU copy) x 4 banks x 128 x 256
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [8:0] bs_word = bs_addr[8:0];
    wire [4*256-1:0] bt_rd;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(bs_re && bs_word[1:0] == bk[1:0]), .r_addr_in(bs_word[8:2]),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
            .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg [1:0] s1b_bank;
    reg [1023:0] btcap;
    always @(posedge ck) begin s1b_bank <= bs_word[1:0]; btcap <= bt_rd; end
    wire [3:0] bdec = 4'd1 << s1b_bank;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_bsel
        wire [3:0] boh;
        qfd_dv_s7_kff #(.W(4), .ID(4000 + gk)) u (.ck(ck), .d(bdec), .q(boh));
        assign bs_q[16*gk +: 16] = ({16{boh[0]}} & btcap[256*0 + 16*gk +: 16]) | ({16{boh[1]}} & btcap[256*1 + 16*gk +: 16]) |
                                   ({16{boh[2]}} & btcap[256*2 + 16*gk +: 16]) | ({16{boh[3]}} & btcap[256*3 + 16*gk +: 16]);
    end endgenerate
    // ================================================================ PROG: 2 banks x (256 + 201) x 256
    wire pw = tw_we && tw_kind == 2'd3;
    wire [4*256-1:0] p_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_prog
        ot_sram_1r1w_256x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(p_re && p_idx[0] == bk[0]), .r_addr_in(p_idx[8:1]),
            .rd_out(p_rd[(2*bk)*256 +: 256]), .w_ce_in(pw), .w_addr_in(tw_addr[7:0]),
            .wd_in(tw_data[512*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_256x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(p_re && p_idx[0] == bk[0]), .r_addr_in(p_idx[8:1]),
            .rd_out(p_rd[(2*bk+1)*256 +: 256]), .w_ce_in(pw), .w_addr_in(tw_addr[7:0]),
            .wd_in({55'd0, tw_data[512*bk + 256 +: 201]}), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire [3:0] p1_bank;                      // 4 kept stage-1 copies (each feeds 16 stage-2 copies)
    qfd_dv_s7_kff #(.W(4), .ID(5100)) u_p1 (.ck(ck), .d({4{p_idx[0]}}), .q(p1_bank));
    reg [1023:0] pcap;
    always @(posedge ck) pcap <= p_rd;
    wire [511:0] pw2;
    generate for (gk = 0; gk < 64; gk = gk + 1) begin : g_psel
        wire pq;
        qfd_dv_s7_kff #(.W(1), .ID(5000 + gk)) u (.ck(ck), .d(p1_bank[gk / 16]), .q(pq));
        assign pw2[8*gk +: 8] = pq ? pcap[512 + 8*gk +: 8] : pcap[8*gk +: 8];
    end endgenerate
    assign p_q = {pw2[256 +: 201], pw2[255:0]};
    // ================================================================ faults (sticky)
    function automatic bad_vec(input [7:0] re, input [8*24-1:0] ad);
        integer kk;
        begin
            bad_vec = 1'b0;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re[kk] && (ad[24*kk+4 +: 20] != ad[4 +: 20])) bad_vec = 1'b1;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re[kk] && (ad[24*kk+3] != ad[3])) bad_vec = 1'b1;
            if (re[0] && (ad[23:14] != 10'd0)) bad_vec = 1'b1;
            if (re != 8'd0 && !re[0]) bad_vec = 1'b1;
        end
    endfunction
    wire rd_bad = bad_vec(a_re, a_addr) || bad_vec(b_re, b_addr) || bad_vec(c_re, c_addr) ||
                  (cr_re != 8'd0 && (!cr_re[0] || cr_addr[23:14] != 10'd0)) ||
                  (cr_re != 8'd0 && bad_vec(cr_re, cr_addr & {8{24'h003FFF}}));
    wire tw_bad = tw_we && ((tw_kind == 2'd0) || (tw_kind == 2'd1 && tw_addr[23:10] != 0) ||
                            (tw_kind == 2'd2 && (tw_addr[1:0] != 0 || tw_addr[23:9] != 0)) ||
                            (tw_kind == 2'd3 && tw_addr[23:8] != 0));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | rd_bad | l_wbad | tw_bad | (bs_re && bs_addr[23:9] != 0);
endmodule
