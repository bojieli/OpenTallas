// Source twin of SUVM7 control; opt-in, not adopted. Original source SHA256 608178187e433430b9371f49cc19bc649e9ebc6d59a1d3595043dfce0d102edd
// Inputs/state +3 and outputs +1 => visible command/record price +4 (c_su2->6). BTAB bypasses this block.
// Model: tools/uarch_model.py qwen_su8_control_model; actual source proof/census required before any gate.
`timescale 1ns/1ps
(* keep_hierarchy = "yes" *) module qfd_dv_su8_kff #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule

(* keep_hierarchy = "yes" *) module qfd_dv_su8_kffr #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire rn, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck or negedge rn) if (!rn) q <= {W{1'b0}}; else q <= d;
endmodule


module qfd_dv_s5_su8 #(parameter integer MUT=0)(input wire ck,rst_n,
    input wire start,
    input wire [456:0] si,
    input wire l_retire,
    input wire l_last,
    input wire [7:0] l_fault,
    input wire [7:0] kv_we,
    input wire rd_v,
    input wire red_busy,
    input wire red_fault,
    input wire [7:0] lvm_we,
    output wire [242:0] gb,
    output wire [2:0] gv,
    output wire [7:0] lv1,
    output wire [767:0] pd1,
    output wire su_nr,
    output wire su_idle,
    output wire su_fault,
    output wire [15:0] su_prog,
    output wire [15:0] su_rows);

    wire c_start;
    wire [456:0] c_si;
    wire [0:0] c_l_retire;
    wire [0:0] c_l_last;
    wire [7:0] c_l_fault;
    wire [7:0] c_kv_we;
    wire c_rd_v;
    wire c_red_busy;
    wire c_red_fault;
    wire [7:0] c_lvm_we;
    wire [242:0] c_gb;
    wire [2:0] c_gv;
    wire [7:0] c_lv1;
    wire [767:0] c_pd1;
    wire c_su_nr;
    reg c_su_idle;
    reg c_su_fault;
    reg [15:0] c_su_prog;
    reg [15:0] c_su_rows;
qfd_dv_su8_kff #(.W(487),.ID(9000)) u_input_pins (.ck(ck),.d({start,si,l_retire,l_last,l_fault,kv_we,rd_v,red_busy,red_fault,lvm_we}),.q({c_start,c_si,c_l_retire,c_l_last,c_l_fault,c_kv_we,c_rd_v,c_red_busy,c_red_fault,c_lvm_we}));
wire start_d1, start_d2, aligned_start;
assign aligned_start = MUT==2 ? start_d1 : start_d2;
qfd_dv_su8_kff #(.W(1),.ID(9001)) u_start1 (.ck(ck),.d(c_start),.q(start_d1));
qfd_dv_su8_kff #(.W(1),.ID(9002)) u_start2 (.ck(ck),.d(start_d1),.q(start_d2));
    localparam integer SW = 8, LS = 3, NW = 18, AW = 24, WR = 16;
    // ---------------------------------------------------------------------------------------------- reset (0 edges)
    localparam integer NR2 = 6, NRC = 10;
    reg rs1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    wire [NR2-1:0] rst_k;                     // rs2 replicas (= qfd_dv_s5_rst2 output)
    wire [NRC-1:0] rc_k;                      // rc replicas (= su8 RTREE control reset copy)
    genvar gi;
    generate for (gi = 0; gi < NR2; gi = gi + 1) begin : g_rs2
        qfd_dv_su8_kffr #(.W(1), .ID(gi)) u (.ck(ck), .rn(rst_n), .d(rs1), .q(rst_k[gi]));
    end
    for (gi = 0; gi < NRC; gi = gi + 1) begin : g_rc
        qfd_dv_su8_kffr #(.W(1), .ID(gi)) u (.ck(ck), .rn(rst_k[gi % NR2]), .d(1'b1), .q(rc_k[gi]));
    end endgenerate
    wire rg;
    qfd_dv_su8_kffr #(.W(1), .ID(100)) u_rg (.ck(ck), .rn(rst_k[0]), .d(1'b1), .q(rg));

    // ---------------------------------------------------------------------------------------------- su_go (c_su + 2)
    localparam integer NFA = 31;               // accept-only field chunks (12 b)
    localparam integer NCH = 32;               // active-updated register chunks (8 b: cur 12, row 12, rrow 3, v 2, o 2, cls 1)
    localparam integer NXS = 8;                // lane copies of the stride fields (12 b select groups)
    localparam integer NACC = NFA + NCH + 10 + NXS; // + act_next A, vl_next A, ol_next/gvr, first_mark, c_su_prog, r_mark, c_su_rows, su_go, act_next B, vl_next B
    wire c_su = aligned_start;
    wire [2:0] sg0;
    generate for (gi = 0; gi < 3; gi = gi + 1) begin : g_sg0
        qfd_dv_su8_kffr #(.W(1), .ID(200 + gi)) u (.ck(ck), .rn(rst_k[1]), .d(c_su), .q(sg0[gi]));
    end endgenerate
    wire [NACC-1:0] acc_k;
    generate for (gi = 0; gi < NACC; gi = gi + 1) begin : g_acc
        qfd_dv_su8_kffr #(.W(1), .ID(300 + gi)) u (.ck(ck), .rn(rst_k[2 + (gi % 4)]), .d(sg0[gi % 3]), .q(acc_k[gi]));
    end endgenerate
    wire su_go = acc_k[NFA + NCH + 7];        // c_su_idle, c_su_nr / fault

    // ---------------------------------------------------------------------------------------------- program word
    
    wire [NW-1:0] i_nout = c_si[18:1], i_nin = c_si[36:19];
    wire          i_asrc = c_si[37], i_bsrc = c_si[110], i_csrc = c_si[183];
    wire [AW-1:0] i_abase = c_si[61:38], i_aso = c_si[85:62], i_asi = c_si[109:86];
    wire [AW-1:0] i_bbase = c_si[134:111], i_bso = c_si[158:135], i_bsi = c_si[182:159];
    wire [AW-1:0] i_cbase = c_si[207:184], i_cso = c_si[231:208], i_csi = c_si[255:232];
    wire [1:0]    i_ma = c_si[257:256], i_mb = c_si[259:258];
    wire [2:0]    i_ad = c_si[262:260], i_sfu = c_si[265:263];
    wire          i_mc = c_si[266], i_md = c_si[267];
    wire [1:0]    i_dst = c_si[269:268];
    wire [AW-1:0] i_dbase = c_si[293:270], i_dso = c_si[317:294], i_dsi = c_si[341:318];
    wire [1:0]    i_red = c_si[343:342];
    wire          i_redsq = c_si[344];
    wire [AW-1:0] i_rbase = c_si[368:345], i_rso = c_si[392:369];
    wire [31:0]   i_imm1 = c_si[424:393], i_imm2 = c_si[456:425];
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
    wire act_nextB = acc_k[NFA + NCH + 8] ? 1'b1 : (act_k[NACT-6] && vl_k[NVL-4] && o_last_r) ? 1'b0 : act_k[NACT-6];
    generate for (gi = 0; gi < NACT; gi = gi + 1) begin : g_act
        qfd_dv_su8_kffr #(.W(1), .ID(400 + gi)) u (.ck(ck), .rn(rc_k[gi % 4]), .d((gi % 2) ? act_nextB : act_nextA), .q(act_k[gi]));
    end endgenerate
    // the active-updated registers (chunked, each chunk with its own accept / active / v_last copies)
    reg  [NW-1:0] o, v;
    reg  [AW-1:0] rowa, rowb, rowc, rowd, cura, curb, curc, curd, rrow;
    wire          acc1 = acc_k[NFA + NCH + 1];
    wire          vl_stepA = (v + 2 == nvec_r), vl_one = (nvec_r == 1), vl_inA = (nvec_in == 1);
    wire          vl_nextA = acc1 ? vl_inA : act_k[NACT-2] ? (!vl_k[NVL-2] ? vl_stepA : vl_one) : vl_k[NVL-2];
    wire          vl_nextB = acc_k[NFA + NCH + 9] ? vl_inA : act_k[NACT-6] ? (!vl_k[NVL-4] ? vl_stepA : vl_one) : vl_k[NVL-4];
    generate for (gi = 0; gi < NVL; gi = gi + 1) begin : g_vl
        qfd_dv_su8_kff #(.W(1), .ID(500 + gi)) u (.ck(ck), .d((gi % 2) ? vl_nextB : vl_nextA), .q(vl_k[gi]));
    end endgenerate
    wire          acc2 = acc_k[NFA + NCH + 2];
    wire          ol_next = acc2 ? (i_nout == 1) : (act_k[NACT-3] && vl_k[NVL-3]) ? (o + 2 == nout_r) : o_last_r;
    qfd_dv_su8_kff #(.W(1), .ID(600)) u_ol (.ck(ck), .d(ol_next), .q(o_last_r));
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
        assign xs_nx[12*gc +: 12] = acc_k[NFA + NCH + 10 + gc] ? xs_in[12*gc +: 12] : xs_cur[12*gc +: 12];
    end endgenerate
    wire [4*AW-1:0] cur_l [0:3];
    wire [4*AW-1:0] xs_l [0:7];
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_curl
        qfd_dv_su8_kff #(.W(4*AW), .ID(650 + gc)) u (.ck(ck), .d(cur_nx), .q(cur_l[gc]));
    end
    for (gc = 0; gc < 8; gc = gc + 1) begin : g_xsl
        wire [4*AW-1:0] lane_offsets;
        for (genvar field = 0; field < 4; field = field + 1) begin : g_offset
            qfd_dv_su8_stride #(.K(gc)) u_off (.x(xs_nx[24*field +: 24]), .y(lane_offsets[24*field +: 24]));
        end
        qfd_dv_su8_kff #(.W(4*AW), .ID(660 + gc)) u (.ck(ck), .d(lane_offsets), .q(xs_l[gc]));
    end endgenerate
    wire retire = c_l_retire[0];
    wire emit_i = act_k[NACT-4];                 // inflight
    wire emit_c = act_k[NACT-5];                 // counters + group relay valid
    wire ready = !act_k[NACT-3 - 0] && ((i_sfu == cls) || (inflight == 0));
    always @(posedge ck or negedge rc_k[1])
        if (!rc_k[1]) inflight <= 8'd0;
        else inflight <= inflight + (emit_i ? 8'd1 : 8'd0) - (retire ? 8'd1 : 8'd0);

    // ---------------------------------------------------------------------------------------------- group relay (kept)
    (* keep *) reg [242:0] gbr;
    (* keep *) reg [2:0]   gvr;
    always @(posedge ck or negedge rg) if (!rg) gvr <= 3'd0; else gvr <= {emit_c, acc_k[NFA + NCH + 2], vl_k[NVL-1]};
    always @(posedge ck) gbr <= {v, fin_th, rrow, asi, bsi, csi, dsi, asrc, bsrc, csrc, mc, md, redsq,
                                 ma, mb, dst, red, ad, cls, i_sfu, imm1, imm2};
    assign c_gb = gbr;
    assign c_gv = gvr;

    // ---------------------------------------------------------------------------------------------- lanes, stage 1
    localparam integer LMUT = 0;
    genvar gl;
    generate for (gl = 0; gl < SW; gl = gl + 1) begin : g_lane
        wire live = ({1'b0, v} << LS) + gl < {1'b0, nin_r};
        wire [AW-1:0] lcura = cur_l[gl/2][72 +: 24], lcurb = cur_l[gl/2][48 +: 24], lcurc = cur_l[gl/2][24 +: 24], lcurd = cur_l[gl/2][0 +: 24];
        wire [AW-1:0] lasi = xs_l[gl][72 +: 24], lbsi = xs_l[gl][48 +: 24], lcsi = xs_l[gl][24 +: 24], ldsi = xs_l[gl][0 +: 24];
        wire [AW-1:0] tcura, tcurb, tcurc, tcurd;
        wire [23:0] a_offset = (MUT == 1 && gl == 3) ? (lasi << 1) : lasi;
        qfd_dv_su8_add u_a (.a(lcura), .b(a_offset), .ci(1'b0), .y(tcura));
        qfd_dv_su8_add u_b (.a(lcurb), .b(lbsi), .ci(1'b0), .y(tcurb));
        qfd_dv_su8_add u_c (.a(lcurc), .b(lcsi), .ci(1'b0), .y(tcurc));
        qfd_dv_su8_add u_d (.a(lcurd), .b(ldsi), .ci(1'b0), .y(tcurd));
        qfd_dv_su8_kffr #(.W(1), .ID(700 + gl)) u_lv (.ck(ck), .rn(rc_k[2 + (gl % 2)]), .d(live), .q(c_lv1[gl]));
        reg [4*AW-1:0] pdr;
        always @(posedge ck) pdr <= {tcura, tcurb, tcurc, tcurd};
        assign c_pd1[96*gl +: 96] = pdr;
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
        if (!rc_k[8]) begin first_mark <= 0; c_su_prog <= 0; end
        else begin
            if (acc_k[NFA + NCH + 3]) first_mark <= n_emit;
            if (acc_k[NFA + NCH + 4]) c_su_prog <= 0; else c_su_prog <= done_n[15] ? 16'd0 : done_n;
        end
    always @(posedge ck or negedge rc_k[5])
        if (!rc_k[5]) begin r_emit <= 0; r_retire <= 0; end
        else begin
            r_emit <= r_emit + ((act_k[NACT-1] && vl_k[NVL-3]) ? 16'd1 : 16'd0);
            r_retire <= r_retire + ((retire && c_l_last[0]) ? 16'd1 : 16'd0);
        end
    always @(posedge ck or negedge rc_k[9])
        if (!rc_k[9]) begin r_mark <= 0; c_su_rows <= 0; end
        else begin
            if (acc_k[NFA + NCH + 5]) r_mark <= r_emit;
            if (acc_k[NFA + NCH + 6]) c_su_rows <= 0; else c_su_rows <= rdone_n[15] ? 16'd0 : rdone_n;
        end
    // landed write enables (the VM write bundle lands one edge late: idle sees the landed bundle)
    
    wire idle_c = !act_k[NACT-2] && inflight == 0 && !(|c_lvm_we) && !(|c_kv_we) && !c_rd_v && !c_red_busy;
    always @(posedge ck or negedge rc_k[6])
        if (!rc_k[6]) c_su_idle <= 1'b1;
        else c_su_idle <= idle_c && !su_go;
    reg fault_q;
    wire nr_c = su_go && !ready;
    always @(posedge ck or negedge rc_k[7]) begin
        if (!rc_k[7]) begin fault_q <= 1'b0; c_su_fault <= 1'b0; end
        else begin
            fault_q <= fault_q || nr_c || (|c_l_fault) || c_red_fault;
            c_su_fault <= fault_q;
        end
    end
    qfd_dv_su8_kffr #(.W(1), .ID(800)) u_nq (.ck(ck), .rn(rst_k[0]), .d(nr_c), .q(c_su_nr));


qfd_dv_su8_kff #(.W(1057),.ID(9010)) u_output_pins (.ck(ck),.d({c_gb,c_gv,c_lv1,c_pd1,c_su_nr,c_su_idle,c_su_fault,c_su_prog,c_su_rows}),.q({gb,gv,lv1,pd1,su_nr,su_idle,su_fault,su_prog,su_rows}));
endmodule

//24-bit carry-prefix address addition; modulo2^24, preserving the source widths.
module qfd_dv_su8_add(input wire [23:0] a,b,input wire ci,output wire [23:0] y);
    (* keep *) wire [23:0] p [0:5];
    (* keep *) wire [23:0] g [0:5];
    assign p[0]=a^b; assign g[0]=a&b;
    genvar l,j;
    generate for(l=0;l<5;l=l+1)begin:g_l
        for(j=0;j<24;j=j+1)begin:g_b
            if(j>=(1<<l))begin
                assign g[l+1][j]=g[l][j]|(p[l][j]&g[l][j-(1<<l)]);
                assign p[l+1][j]=p[l][j]&p[l][j-(1<<l)];
            end else begin assign g[l+1][j]=g[l][j]; assign p[l+1][j]=p[l][j]; end
        end
    end endgenerate
    wire [23:0] carry;
    assign carry[0]=ci;
    generate for(j=1;j<24;j=j+1)begin:g_c
        assign carry[j]=g[5][j-1]|(p[5][j-1]&ci);
    end endgenerate
    assign y=p[0]^carry;
endmodule

module qfd_dv_su8_stride #(parameter integer K=0)(input wire [23:0] x,output wire [23:0] y);
    generate
        if(K==0)assign y=24'd0;
        else if(K==1)assign y=x;
        else if(K==2)assign y=x<<1;
        else if(K==4)assign y=x<<2;
        else if(K==3)qfd_dv_su8_add u (.a(x<<1),.b(x),.ci(1'b0),.y(y));
        else if(K==5)qfd_dv_su8_add u (.a(x<<2),.b(x),.ci(1'b0),.y(y));
        else if(K==6)qfd_dv_su8_add u (.a(x<<2),.b(x<<1),.ci(1'b0),.y(y));
        else if(K==7)qfd_dv_su8_add u (.a(x<<3),.b(~x),.ci(1'b1),.y(y));
        else initial $error("invalid lane multiplier");
    endgenerate
endmodule
