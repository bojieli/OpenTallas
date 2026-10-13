`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// BENCH COMPOSITION (el1013-qwen-kvstrips 2026-10-13): the near-HBM attention stack with the aggregator built from the
// die masters of rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv, wired as the Qwen ROM TP8 die wires an aggregator
// strip (hub at the N end):
//   8 x ot_qwen_nearhbm_row_engine_h (re-cut H, unchanged), engine 2 r on the W and 2 r + 1 on the E of row r;
//   per row and column (X / Y): 8 qkd_astk_pv -- at every head a level-4 cell (A) and above it the row's second cell
//     (B: row 0 level 5 of rows 0 + 1, row 1 level 6, row 2 level 5 of rows 2 + 3, row 3 level 7);
//   per engine a qkd_astk_ep + 4 x qkd_astk_ex (two a column) between heads 1 and 2 (the lanes cross them);
//   4 x qkd_astk_zn and the
//   qkd_astk_ctl behind slice 7.
// RL registered relay stations stand on every die net that is not an abutment (the design does not depend on RL: run
// the layer bench at RL 1 and RL 3).  Same ports as ot_qwen_nearhbm_attn_stack_h; HD 128, R 8, LFB 4 only.
// ---------------------------------------------------------------------------------------------------------------------
`ifndef KVD_AKRL
`define KVD_AKRL 1
`endif
module ot_qkd_rly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d,
                                                                   output wire [W-1:0] q);
    ot_hdc_delay #(.W(W), .D(D), .RESET(1)) u (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule

module ot_qwen_nearhbm_attn_stack_k #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 8,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter integer ZW = 4,
    parameter integer LFB = 4,
    parameter integer ND = 1,
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [13:0]       T,
    input  wire              q_valid,
    input  wire [5:0]        q_beat,
    input  wire [511:0]      q_data,
    output wire [R-1:0]      req_valid,
    output wire [R-1:0]      req_v,
    output wire [R-1:0]      req_g,
    output wire [13*R-1:0]   req_t,
    input  wire [R-1:0]      rsp_valid,
    input  wire [HD*8*R-1:0] rsp_data,
    input  wire              mi_valid,
    input  wire              mi_g,
    input  wire [1:0]        mi_hh,
    input  wire [31:0]       mi_data,
    output wire              so_valid,
    output wire [1:0]        so_type,
    output wire              so_g,
    output wire [1:0]        so_hh,
    output wire [3:0]        so_k,
    output wire              so_any,
    output wire [31:0]       so_data,
    output wire              pv_valid,
    output wire              pv_g,
    output wire [5:0]        pv_beat,
    output wire [511:0]      pv_data,
    output wire [1:0]        pv_done,
    output wire              fault,
    output wire [15:0]       ev
);
    localparam integer RL = `KVD_AKRL;
    localparam integer NS = 56;                    // lane stations a column: 4 rows x (8 tree cells + 2 x (ep + 2 ex))
    generate if (HD != 128 || R != 8 || LFB != 4 || ND != 1) begin : g_bad
        ot_qwen_nearhbm_attn_stack_k_needs_HD128_R8_LFB4_ND1 u_trap ();
    end endgenerate
    wire [1:0] SS = S;
    // ---- the port --------------------------------------------------------------------------------------------------------
    wire [564:0] ap;
    wire [571:0] cq_o;
    wire [266:0] cx_i;
    wire [5:0]   cco;
    wire [262:0] px, py;
    wire [137:0] czi;
    wire         cfx, cfy, cfz, af;
    qkd_astk_ctl u_ctl (.ck(clk), .rst_n(rst_n), .st(SS), .aq({q_data, q_beat, q_valid, 6'd0, T, start}), .lt(),
        .am({mi_data, mi_hh, mi_g, mi_valid}), .ap(ap), .af(af), .qo(cq_o), .xi(cx_i), .co(cco), .px(px), .py(py),
        .zi(czi), .fx(cfx), .fy(cfy), .fz(cfz));
    assign so_valid = ap[0]; assign so_type = ap[2:1]; assign so_g = ap[3]; assign so_hh = ap[5:4]; assign so_k = ap[9:6];
    assign so_any = ap[10]; assign so_data = ap[42:11]; assign pv_done = ap[44:43]; assign pv_valid = ap[45];
    assign pv_g = ap[46]; assign pv_beat = ap[52:47]; assign pv_data = ap[564:53];
    assign fault = af;
    assign ev = 16'd0;
    // ---- engines and their slices -------------------------------------------------------------------------------------
    wire [424:0]  so_w [0:7];
    wire [633:0]  si_w [0:7];
    wire [4095:0] nb_w [0:7];
    wire [571:0]  qi_w [0:8];                      // qi_w[8] = the port's; slice j takes qi_w[j + 1]
    wire [266:0]  xo_w [0:8];                      // xo_w[0] = 0; slice j takes xo_w[j], gives xo_w[j + 1]
    wire [650:0]  zo_w [0:8];
    wire [521:0]  ro_w [0:8];                      // slice j takes ro_w[j + 1]
    wire [7:0]    cr_w;
    assign xo_w[0] = 267'd0; assign zo_w[0] = 651'd0;
    ot_qkd_rly #(.W(572), .D(RL)) u_rq8 (.clk(clk), .rst_n(rst_n), .d(cq_o), .q(qi_w[8]));
    ot_qkd_rly #(.W(267), .D(RL)) u_rx8 (.clk(clk), .rst_n(rst_n), .d(xo_w[8]), .q(cx_i));
    assign ro_w[8] = {zo_w[8][650:139], zo_w[8][10:7], zo_w[8][6:3], zo_w[8][2], zo_w[8][0]};
    // lanes: column c, station s (bottom to top)
    wire [535:0] U [0:1][0:NS];
    wire [535:0] D [0:1][0:NS];
    wire [262:0] P [0:1][0:NS];
    wire [5:0]   C [0:1][0:NS];
    wire         TU [0:1][0:NS];
    wire         TD [0:1][0:NS];
    wire         F [0:1][0:NS];
    genvar c, r, e, hp, z;
    generate for (c = 0; c < 2; c = c + 1) begin : g_end
        assign U[c][0] = 536'd0; assign P[c][0] = 263'd0; assign TU[c][0] = 1'b0; assign F[c][0] = 1'b0;
        assign D[c][NS] = 536'd0; assign TD[c][NS] = 1'b0;
        ot_qkd_rly #(.W(6), .D(RL)) u_rc (.clk(clk), .rst_n(rst_n), .d(cco), .q(C[c][NS]));
    end endgenerate
    ot_qkd_rly #(.W(263), .D(RL)) u_rpx (.clk(clk), .rst_n(rst_n), .d(P[0][NS]), .q(px));
    ot_qkd_rly #(.W(263), .D(RL)) u_rpy (.clk(clk), .rst_n(rst_n), .d(P[1][NS]), .q(py));
    ot_qkd_rly #(.W(2), .D(RL)) u_rf (.clk(clk), .rst_n(rst_n), .d({F[1][NS], F[0][NS]}), .q({cfy, cfx}));
    generate for (e = 0; e < 8; e = e + 1) begin : g_e
        localparam integer ST = 14 * (e / 2) + 4 + 3 * (e % 2);       // the slice's ep station; its ex leaves are ST + 1, ST + 2
        wire rv, rvv, rg;
        wire [12:0] rt;
        ot_qwen_nearhbm_row_engine_h #(.HD(HD), .S(S), .R(R), .E(e), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .DQ(DQ),
                                     .SCALE(SCALE), .LFB(LFB), .ND(ND)) u_eng (
            .clk(clk), .rst_n(rst_n), .start_in(si_w[e][0]), .T_in(si_w[e][14:1]), .cyc8_in(si_w[e][17:15]),
            .q_valid_in(si_w[e][18]), .q_beat_in(si_w[e][24:19]), .q_data_in(si_w[e][536:25]), .exp_done(si_w[e][568:537]),
            .req_valid(rv), .req_v(rvv), .req_g(rg), .req_t(rt), .rsp_valid_in(rsp_valid[e]),
            .rsp_data_in(rsp_data[HD*8*e +: HD*8]), .er_valid(so_w[e][0]), .er_addr(so_w[e][12:1]),
            .er_data(si_w[e][632:569]), .sc_valid(so_w[e][13]), .sc_addr(so_w[e][25:14]), .sc_data(so_w[e][153:26]),
            .lmax(so_w[e][409:154]), .lmax_any(so_w[e][411:410]), .nb_valid(so_w[e][412]), .nb_beat(so_w[e][416:413]),
            .nb_g(so_w[e][417]), .nb_gam(so_w[e][421:418]), .nb_data(nb_w[e]), .nb_cr(si_w[e][633]),
            .k_done(so_w[e][422]), .v_done(so_w[e][423]), .fault(so_w[e][424]), .ev_k_first(), .ev_v_first());
        assign req_valid[e] = rv; assign req_v[e] = rvv; assign req_g[e] = rg; assign req_t[13*e +: 13] = rt;
        wire [571:0] qo_e;
        wire [266:0] xo_e, xi_e;
        wire [650:0] zo_e, zi_e;
        wire [521:0] ro_e, ri_e;
        wire [263:0] xa;
        wire [135:0] xe;
        ot_qkd_rly #(.W(267), .D(RL)) u_rx (.clk(clk), .rst_n(rst_n), .d(xo_w[e]), .q(xi_e));
        ot_qkd_rly #(.W(651), .D((e % 2) ? 0 : RL)) u_rz (.clk(clk), .rst_n(rst_n), .d(zo_w[e]), .q(zi_e));
        ot_qkd_rly #(.W(522), .D(RL)) u_rr (.clk(clk), .rst_n(rst_n), .d(ro_w[e + 1]), .q(ri_e));
        qkd_astk_ep u_ep (.ck(clk), .rst_n(rst_n), .sq({SS, 3'(e)}), .so(so_w[e]), .si(si_w[e]), .qi(qi_w[e + 1]), .qo(qo_e),
            .xi(xi_e), .xo(xo_e), .zi(zi_e), .zo(zo_e), .ri(ri_e), .ro(ro_e), .xa(xa), .xe(xe), .cr(cr_w[e]),
            .ui0(U[0][ST]), .uo0(U[0][ST+1]), .di0(D[0][ST+1]), .do0(D[0][ST]), .pi0(P[0][ST]), .po0(P[0][ST+1]),
            .ci0(C[0][ST+1]), .co0(C[0][ST]), .tui0(TU[0][ST]), .tuo0(TU[0][ST+1]), .tdi0(TD[0][ST+1]), .tdo0(TD[0][ST]),
            .fi0(F[0][ST]), .fo0(F[0][ST+1]),
            .ui1(U[1][ST]), .uo1(U[1][ST+1]), .di1(D[1][ST+1]), .do1(D[1][ST]), .pi1(P[1][ST]), .po1(P[1][ST+1]),
            .ci1(C[1][ST+1]), .co1(C[1][ST]), .tui1(TU[1][ST]), .tuo1(TU[1][ST+1]), .tdi1(TD[1][ST+1]), .tdo1(TD[1][ST]),
            .fi1(F[1][ST]), .fo1(F[1][ST+1]));
        genvar xh;
        for (xh = 0; xh < 4; xh = xh + 1) begin : g_x                 // heads 0 / 2 in column 0, heads 1 / 3 in column 1
            localparam integer XC = xh % 2;
            localparam integer XS = ST + 1 + xh / 2;
            qkd_astk_ex u_ex (.ck(clk), .rst_n(rst_n), .xa(xa[66*xh +: 66]), .xe(xe[34*xh +: 34]),
                .ui(U[XC][XS]), .uo(U[XC][XS+1]), .di(D[XC][XS+1]), .do_(D[XC][XS]), .pi(P[XC][XS]), .po(P[XC][XS+1]),
                .ci(C[XC][XS+1]), .co(C[XC][XS]), .tui(TU[XC][XS]), .tuo(TU[XC][XS+1]), .tdi(TD[XC][XS+1]), .tdo(TD[XC][XS]),
                .fi(F[XC][XS]), .fo(F[XC][XS+1]));
        end
        ot_qkd_rly #(.W(572), .D(RL)) u_rq (.clk(clk), .rst_n(rst_n), .d(qo_e), .q(qi_w[e]));
        assign xo_w[e + 1] = xo_e; assign zo_w[e + 1] = zo_e; assign ro_w[e] = ro_e;
    end endgenerate
    // ---- the tree cells ----------------------------------------------------------------------------------------------------
    wire [1:0] cra_w [0:3];                        // [row][column 0 only is used]
    wire [1:0] crb_w [0:3];
    generate for (r = 0; r < 4; r = r + 1) begin : g_r
        for (c = 0; c < 2; c = c + 1) begin : g_c
            wire [9:0] nco_w [0:3];
            wire [9:0] ndo_w [0:3];
            wire [3:0] cra_h, crb_h;
            for (hp = 0; hp < 4; hp = hp + 1) begin : g_h
                localparam integer ST = 14 * r + ((hp < 2) ? 2 * hp : 10 + 2 * (hp - 2));
                localparam integer FAR = (hp == 0 || hp == 3) ? 1 : 0;
                localparam integer NEAR = (hp == 0) ? 1 : 2;            // the cell the far one takes its control from
                // level-4 cell: the head's 16 kk slots of this column, kk = 4 (m / 2) + 2 c + m % 2
                wire [511:0] wa, wb;
                genvar m;
                for (m = 0; m < 16; m = m + 1) begin : g_m
                    assign wa[32*m +: 32] = nb_w[2*r][1024*hp + 32*(4*(m/2) + 2*c + (m%2)) +: 32];
                    assign wb[32*m +: 32] = nb_w[2*r+1][1024*hp + 32*(4*(m/2) + 2*c + (m%2)) +: 32];
                end
                wire [9:0] nc = FAR ? nco_w[NEAR] : so_w[2*r][421:412];
                wire [9:0] nd = FAR ? ndo_w[NEAR] : so_w[2*r+1][421:412];
                wire [133:0] lo_a, lo_b;
                // A: y to the B cell above (rows 0, 2) or into the down lane (rows 1, 3)
                localparam [1:0] YM_A = (r == 1 || r == 3) ? 2'd2 : 2'd0;
                localparam [2:0] ATH_A = 2 * r, BTH_A = 2 * r + 1;
                qkd_astk_pv u_a (.ck(clk), .rst_n(rst_n),
                    .cfg({1'b0, 1'(FAR), BTH_A, ATH_A, YM_A, 2'd0, 2'd0, 2'd0, 2'(hp)}),
                    .wa(wa), .wb(wb), .nc(nc), .nd(nd), .nco(nco_w[hp]), .ndo(ndo_w[hp]), .cra(cra_h[hp]), .crb(crb_h[hp]),
                    .li(134'd0), .lo(lo_a), .ui(U[c][ST]), .uo(U[c][ST+1]), .di(D[c][ST+1]), .do_(D[c][ST]),
                    .pi(P[c][ST]), .po(P[c][ST+1]), .ci(C[c][ST+1]), .co(C[c][ST]), .tui(TU[c][ST]), .tuo(TU[c][ST+1]),
                    .tdi(TD[c][ST+1]), .tdo(TD[c][ST]), .fi(F[c][ST]), .fo(F[c][ST+1]));
                // B: row 0 level 5 (a local, b down lane, y up); row 1 level 6 (a up, b down, y up);
                //    row 2 level 5 (a local, b down, y down); row 3 level 7 (up lane, the P.V lane)
                localparam [1:0] LVL_B = (r == 0 || r == 2) ? 2'd1 : (r == 1) ? 2'd2 : 2'd3;
                localparam [1:0] AM_B = (r == 0 || r == 2) ? 2'd0 : 2'd1;
                localparam [1:0] BM_B = (r == 3) ? 2'd0 : 2'd2;
                localparam [1:0] YM_B = (r == 0 || r == 1) ? 2'd1 : (r == 2) ? 2'd2 : 2'd0;
                localparam [2:0] ATH_B = (r == 2) ? 3'd4 : 3'd0;
                localparam [2:0] BTH_B = (r == 0) ? 3'd2 : (r == 1) ? 3'd4 : (r == 2) ? 3'd6 : 3'd0;
                qkd_astk_pv u_b (.ck(clk), .rst_n(rst_n),
                    .cfg({1'b0, 1'b0, BTH_B, ATH_B, YM_B, BM_B, AM_B, LVL_B, 2'(hp)}),
                    .wa(512'd0), .wb(512'd0), .nc(10'd0), .nd(10'd0), .nco(), .ndo(), .cra(), .crb(),
                    .li(lo_a), .lo(lo_b), .ui(U[c][ST+1]), .uo(U[c][ST+2]), .di(D[c][ST+2]), .do_(D[c][ST+1]),
                    .pi(P[c][ST+1]), .po(P[c][ST+2]), .ci(C[c][ST+2]), .co(C[c][ST+1]), .tui(TU[c][ST+1]), .tuo(TU[c][ST+2]),
                    .tdi(TD[c][ST+2]), .tdo(TD[c][ST+1]), .fi(F[c][ST+1]), .fo(F[c][ST+2]));
            end
            if (c == 0) begin : g_cr
                assign cr_w[2*r] = cra_h[1]; assign cr_w[2*r+1] = crb_h[1];
            end
        end
    end endgenerate
    // ---- the Z tree behind slice 7 ------------------------------------------------------------------------------------------
    wire [137:0] zn_w [0:4];
    wire [4:0]   zf_w;
    assign zn_w[0] = {zo_w[8][138:11], zo_w[8][10:7], zo_w[8][6:3], zo_w[8][2], zo_w[8][0]};
    assign zf_w[0] = 1'b0;
    generate for (z = 0; z < 4; z = z + 1) begin : g_z
        qkd_astk_zn u_zn (.ck(clk), .rst_n(rst_n), .zc({2'(z), SS}), .tc(cq_o[14:0]), .zi(zn_w[z]), .zo(zn_w[z+1]),
                          .fi(zf_w[z]), .fo(zf_w[z+1]));
    end endgenerate
    assign czi = zn_w[4]; assign cfz = zf_w[4];
endmodule
