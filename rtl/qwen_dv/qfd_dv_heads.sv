`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_heads -- the Q-DV slice's x-delivery face (dv2r8f2: the head row is the slice row; the slice hosts the four
// column heads of its quad).  Existing RTL, unchanged (rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv):
//   ot_qfd_xs_tap   x 1   (STATIC_SCHEDULE 1, NATIVE_AFFINE 1, as qfd_xcol): arm descriptor xpf, x writes, {ib, go}
//                          -> the 1,567-b head-row word {fill, ib, go}
//   ot_qfd_xhead    x 4   (NH 8, NATIVE_AFFINE 1): column slice control and the N / S corridor words {tag, xl, ib, go}
//   ot_qfd_xs_leaf  x 32  (8 per column: two write chains of 4): the column's x slots
// Source of the x writes: the slice's stream x words (64 BF16, aligned beat), presented as a 64-lane write of
// {bf16, 16'h0}.  Every production op rounds (xpf_round 1), and RNE16 of a BF16 value is that value, so the
// operand each tile receives is bit-identical to the central tap fed with the FP32 x (bench tb_qfd_dv_heads).
// The tap's 16-lane attention-return port is not used: in DV the attention return reaches the heads as stream x
// words like every other producer (aw_v = 0 is a schedule constant of this composition, not a missing path).
// Column c of the die = 4 sid + i (dv2r8f2 order), tile ids by the die's TIDM 1 map (ot_qwen_me_array_dvm_w12.tid,
// NCOL 48, NH 8).  Corridor words: n_d[i] -> band-2 cluster bc face, s_d[i] -> band-1 cluster bc face.
// =====================================================================================================================
module qfd_dv_heads #(
    parameter integer AW = 24, NW = 18, XCW = 12, NH = 8, NCOLD = 48,
    parameter integer TAP_MUT = 0, HEAD_MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    // arm descriptor {round, k, split, xks, xcs, xbase, v} and {ib, go} (the hr bundle, pin-registered by the top)
    input  wire [71:0]   xpf,
    input  wire [3*NW+13*AW+13:0] gi,
    // x writes (64 lanes, element sw_a + l)
    input  wire          sw_v,
    input  wire [AW-1:0] sw_a,
    input  wire [63:0]   sw_m,
    input  wire [64*32-1:0] sw_d,
    input  wire          fe_i,                     // an x-delivery schedule fault seen by the top
    output wire [4*(1+(3*NW+13*AW+13)+128+8)-1:0] n_d,
    output wire [4*(1+(3*NW+13*AW+13)+128+8)-1:0] s_d,
    output wire          fault
);
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer HW  = 1 + IBW + (2 + AW + 2 * XCW + 4 + NW + 1) + (2 + (AW - 6) + 6 + 64 + 1024);
    localparam integer CW  = 1 + IBW + 128 + 8;
    function automatic integer tid(input integer c, input integer r);
        integer dr, bc, br, lbc, lbr, blk, z, p, i;
        begin
            dr = (r < NH) ? NH + r : NH - 1 - (r - NH);
            bc = (NCOLD >= 4) ? 4 : NCOLD; br = (2 * NH >= 4) ? 4 : 2 * NH;
            lbc = (bc >= 4) ? 2 : (bc >= 2) ? 1 : 0; lbr = (br >= 4) ? 2 : (br >= 2) ? 1 : 0;
            blk = (c / bc) * (2 * NH / br) + dr / br;
            z = 0; p = 0;
            for (i = 0; i < 2; i = i + 1) begin
                if (i < lbc) begin z = z | (((c % bc) >> i) & 1) << p; p = p + 1; end
                if (i < lbr) begin z = z | (((dr % br) >> i) & 1) << p; p = p + 1; end
            end
            tid = bc * br * blk + z;
        end
    endfunction
    // the strap's tile ids, held in registers (static after reset)
    reg [4*16*2*NH-1:0] tids;
    integer ci, ri;
    always @(posedge ck)
        for (ci = 0; ci < 4; ci = ci + 1)
            for (ri = 0; ri < 2 * NH; ri = ri + 1)
                tids[(ci * 2 * NH + ri) * 16 +: 16] <= 16'(tid(4 * sid + ci, ri));
    // ---------------------------------------------------------------- corridor station tags (QW-XHEAD 10-19)
    // The die's cluster master (qfd_c_b16_dv) numbers its row stations sidx = {far, q} (near) / {far, ~q} (far) along its
    // own bc run (row q = q-th station from the slice), and its tiles carry strap 16 cid + morton(c, q).  The heads'
    // logical stations (tid above) are N s -> die row NH + s, S s -> die row NH-1-s, so the line for logical station s
    // must carry the tag of the physical station whose strap is tid(s): N far (s >= 4) and S near (s < 4) are row-
    // reversed -> tag = s ^ 3 there, s elsewhere.  Pure relabelling of the 3-bit tag fields (static per side, no flop,
    // no edge).  XT1 witness (as-built): S station 0 served tile 26's x (chunks 104..107) to tile 16 (strap 16, ROM 16).
    wire [4*CW-1:0] n_raw, s_raw;
    function automatic [7:0] retag(input [7:0] t, input integer side_s);
        reg [2:0] a, b;
        begin
            a = t[2:0]; b = t[6:4];
            if (side_s ? !a[2] : a[2]) a = a ^ 3'd3;
            if (side_s ? !b[2] : b[2]) b = b ^ 3'd3;
            retag = {t[7], b, t[3], a};
        end
    endfunction
    genvar tc;
    generate for (tc = 0; tc < 4; tc = tc + 1) begin : g_retag
        assign n_d[tc*CW +: CW] = {retag(n_raw[tc*CW + 1 + IBW + 128 +: 8], 0), n_raw[tc*CW +: 1 + IBW + 128]};
        assign s_d[tc*CW +: CW] = {retag(s_raw[tc*CW + 1 + IBW + 128 +: 8], 1), s_raw[tc*CW +: 1 + IBW + 128]};
    end endgenerate
    // ---------------------------------------------------------------- tap
    wire [HW-1:0] hw, he;
    wire          tap_fault;
    wire [4:0]    fch;
    wire [4*NH-1:0] lq_bad_all;
    ot_qfd_xs_tap #(.AW(AW), .NW(NW), .XCW(XCW), .STATIC_SCHEDULE(1), .NATIVE_AFFINE(1), .MUT(TAP_MUT)) u_tap (
        .clk(ck), .rst_n(rst_n),
        .xpf_v(xpf[0]), .xpf_xbase(xpf[1 +: AW]), .xpf_xcs(xpf[1+AW +: XCW]), .xpf_xks(xpf[1+AW+XCW +: XCW]),
        .xpf_split(xpf[1+AW+2*XCW +: 4]), .xpf_k(xpf[1+AW+2*XCW+4 +: NW]), .xpf_round(xpf[1+AW+2*XCW+4+NW]),
        .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .aw_v(1'b0), .aw_a({AW{1'b0}}), .aw_m(16'd0), .aw_d(512'd0),
        .gi(gi), .hw(hw), .he(he), .fw_i(|lq_bad_all), .fe_i(fe_i), .fault(tap_fault));
    assign fch[4] = tap_fault;
    // ---------------------------------------------------------------- four columns
    genvar c, h, j;
    generate for (c = 0; c < 4; c = c + 1) begin : g_col
        wire [1:0]    lw_v, lc_v, lw_ep, lc_ep;
        wire [11:0]   lw_off;
        wire [127:0]  lw_m;
        wire [2047:0] lw_d;
        wire [NH*18-1:0] lw_ctl;
        wire [NH-1:0] lr_v, lr_t, lr_ep, lq_v, lq_bad;
        wire [NH*28-1:0] lr_p;
        wire [NH*64-1:0] lq;
        assign lq_bad_all[NH*c +: NH] = lq_bad;
        ot_qfd_xhead #(.AW(AW), .NW(NW), .XCW(XCW), .NH(NH), .NATIVE_AFFINE(1), .MUT(HEAD_MUT)) u_head (
            .ck(ck), .rst_n(rst_n), .tids(tids[c*16*2*NH +: 16*2*NH]), .fault_i(fch[c+1]),
            .a_d(hw), .a_r(), .b_d(), .b_r(1'b1),
            .n_d(n_raw[c*CW +: CW]), .n_r(1'b1), .s_d(s_raw[c*CW +: CW]), .s_r(1'b1),
            .lw_v(lw_v), .lw_ep(lw_ep), .lw_off(lw_off), .lw_m(lw_m), .lw_d(lw_d), .lw_ctl(lw_ctl),
            .lc_v(lc_v), .lc_ep(lc_ep), .lr_v(lr_v), .lr_t(lr_t), .lr_ep(lr_ep), .lr_p(lr_p),
            .lq(lq), .lq_v(lq_v), .lq_bad(lq_bad), .fault(fch[c]));
        localparam integer NCH = NH / 2;
        for (h = 0; h < 2; h = h + 1) begin : g_ch
            wire          cv [0:NCH];
            wire          cep [0:NCH];
            wire          wv [0:NCH];
            wire          wep [0:NCH];
            wire [5:0]    woff [0:NCH];
            wire [63:0]   wm [0:NCH];
            wire [1023:0] wd [0:NCH];
            wire [NCH*18-1:0] wc [0:NCH];
            assign cv[0] = lc_v[h]; assign cep[0] = lc_ep[h]; assign wv[0] = lw_v[h]; assign wep[0] = lw_ep[h];
            assign woff[0] = lw_off[6*h +: 6]; assign wm[0] = lw_m[64*h +: 64]; assign wd[0] = lw_d[1024*h +: 1024];
            assign wc[0] = lw_ctl[h*NCH*18 +: NCH*18];
            for (j = 0; j < NCH; j = j + 1) begin : g_leaf
                localparam integer LF = h * NCH + j;
                ot_qfd_xs_leaf #(.NCH(NCH)) u_leaf (.clk(ck), .rst_n(rst_n),
                    .w_v(wv[j]), .w_ep(wep[j]), .w_off(woff[j]), .w_m(wm[j]), .w_d(wd[j]), .w_ctl(wc[j]),
                    .c_v(cv[j]), .c_ep(cep[j]),
                    .wo_v(wv[j+1]), .wo_ep(wep[j+1]), .wo_off(woff[j+1]), .wo_m(wm[j+1]), .wo_d(wd[j+1]),
                    .wo_ctl(wc[j+1]), .co_v(cv[j+1]), .co_ep(cep[j+1]),
                    .r_v(lr_v[LF]), .r_t(lr_t[LF]), .r_ep(lr_ep[LF]), .r_p(lr_p[28*LF +: 28]),
                    .q_v(lq_v[LF]), .q(lq[64*LF +: 64]), .q_bad(lq_bad[LF]));
            end
        end
    end endgenerate
    assign fault = fch[0];
endmodule
