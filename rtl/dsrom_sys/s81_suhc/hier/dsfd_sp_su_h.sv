`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the S81 SU slab master rebuilt as a hierarchical slab.  Same pins
// and adapter as dsfd_sp_su (contract su_hc v2: c_cmd / c_done / inp / VM rd S_RD rows / VM wr S_WR rows / flt /
// online / fcode); inside, one control tile and NT hardened engine tiles on two registered chains:
//
//   pins -> NPO pin owners ot_s81_su_pin (stacked along the VM pin edge, each its slots' pin flops / registers) and the
//           control tile ot_s81_su_ctl (adapter, ot_s81_su_hctl job control / VM read issue / completion)
//       down spine (VM response rows + job announce, S_RD x 512 b): relay stations at the stops QN, KV, QB 0..NQB-1,
//         SW 0..NSW-1, SM 0..NSM-1 (one register a stop); each tile taps its stop
//       up spine (S_WR write row slots): a relay station a stop merges that tile's registered slots into its window
//   regional reset: pin -> relay -> ctl; a reset spine station a stop -> the tile's own two-flop relay
// Tiles carry one copy of each bus (no pass-through): pins = the down tap + its own write slots + status.
//
// Tile decomposition (production params): QN norm x 2 (128 lanes, D 1,280, its q gain set slice), KV norm x 2 (256
// lanes, the RoPE tail in the second, its kv gain set slice), QB x 4 (8 blocks each), SW x 8 (128 lanes each), SM x 8
// (2 heads x 16 lanes each); a norm's group sums of squares meet in its head tile over a registered rung (the golden's
// top tree level, left + right), the rstd returns the same way.
// The values are those of dsfd_sp_su (bit-exact gate tools/s81_suhc/su_gate.py --hier); added latency: the chain
// hops (a cycle a tile each way) and the norm tiles' ready round trip.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_su_h #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0,
    // lane-group tiles (production: QN 2 x 128 lanes, KV 2 x 256 lanes, QB 4 x 8 blocks, SW 8 x 128 lanes, SM 8 x 2
    // heads; pin owners 4 x (4 read + 4 write slots); every tile <= ~600 x 600 um)
    parameter integer NQN = (QN_N >= 256) ? 2 : 1,
    parameter integer NKV = (KV_N >= 128) ? 2 : 1,
    parameter integer NQB = (QB_NB >= 32) ? QB_NB / 8 : 2,
    parameter integer NSW = (SW_W >= 128) ? SW_W / 128 : 1,
    parameter integer NSM = (SM_H >= 2) ? SM_H / 2 : 1,
    parameter integer NPO = (S_RD >= 16 && S_WR >= 16) ? 4 : 1
) (
    input  wire                cck, crs,
    input  wire                sk, srs,
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode
);
    localparam integer NTL = NQN + NKV + NQB + NSW + NSM;
    localparam integer KR = S_RD / NPO, KW = S_WR / NPO;
    // spines: stop t = tile t.  Down: dn[t] is the relay register at stop t (dn[0]: the pin owners' row registers +
    // the control tile's job announce); the tile taps it and the next stop re-registers it.  Up: up[t] is the relay
    // register at stop t, = up[t + 1] with tile t's registered write slots merged into its window; up[0]: the wide
    // part to the pin owners (each its slice), the status to the control tile.
    wire                  dst [0:NTL];
    wire [3:0]            dkd [0:NTL];
    wire [1:0]            dgs [0:NTL];
    wire                  df4 [0:NTL];
    wire [7:0]            dji [0:NTL];
    wire [S_RD-1:0]       dv  [0:NTL];
    wire [S_RD*512-1:0]   dd  [0:NTL];
    wire [S_WR-1:0]       uv  [0:NTL];
    wire [S_WR*14-1:0]    ua  [0:NTL];
    wire [S_WR*16-1:0]    um  [0:NTL];
    wire [S_WR*512-1:0]   ud  [0:NTL];
    wire                  ufu [0:NTL], ufo [0:NTL], ual [0:NTL], ude [0:NTL], urd [0:NTL];
    wire [7:0]            urj [0:NTL];
    wire                  rst [0:NTL];
    assign uv[NTL] = 0; assign ua[NTL] = 0; assign um[NTL] = 0; assign ud[NTL] = 0;
    assign ufu[NTL] = 1'b0; assign ufo[NTL] = 1'b0; assign ual[NTL] = 1'b1; assign ude[NTL] = 1'b1;
    assign urd[NTL] = 1'b0; assign urj[NTL] = 8'd0;

    // ------------------------------------------------------------------ control tile
    wire [S_RD-1:0]    c_rq_v;
    wire [S_RD*14-1:0] c_rq_row;
    wire [S_RD-1:0]    p_rv;
    wire [S_RD*30-1:0] p_rf;
    wire [S_WR-1:0]    p_uv;
    wire               rst_c;
    ot_s81_su_ctl #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                    .S_RD(S_RD), .S_WR(S_WR), .NSW(NSW), .NQB(NQB), .NQN(NQN), .NKV(NKV), .MUT(MUT), .AMUT(AMUT)) u_ctl (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .flt(flt), .online(online), .fcode(fcode), .rst_o(rst_c),
        .p_rq_v(c_rq_v), .p_rq_row(c_rq_row), .p_rv(p_rv), .p_rf(p_rf), .p_uv(p_uv),
        .dn_st(dst[0]), .dn_kind(dkd[0]), .dn_gsel(dgs[0]), .dn_fp4(df4[0]), .dn_jid(dji[0]),
        .up_fu(ufu[0]), .up_fo(ufo[0]), .up_alive(ual[0]), .up_den(ude[0]), .up_rdy(urd[0]), .up_rjid(urj[0]));
    // reset spine head
    reg rs0;
    always @(posedge sk or negedge rst_c) if (!rst_c) rs0 <= 1'b0; else rs0 <= 1'b1;
    assign rst[0] = rs0;

    // ------------------------------------------------------------------ pin owners (+ a relay station each seam way)
    genvar o;
    generate for (o = 0; o < NPO; o = o + 1) begin : g_po
        reg  [KR-1:0]    rq_v_r;  reg [KR*14-1:0] rq_row_r;
        wire [KR-1:0]    rv;      wire [KR*30-1:0] rf;   wire [KW-1:0] uvo;
        reg  [KR-1:0]    rv_r;    reg [KR*30-1:0] rf_r;  reg [KW-1:0] uv_r;
        always @(posedge sk) begin rq_row_r <= c_rq_row[KR * 14 * o +: KR * 14]; rf_r <= rf; end
        always @(posedge sk or negedge rs0)
            if (!rs0) begin rq_v_r <= 0; rv_r <= 0; uv_r <= 0; end
            else begin rq_v_r <= c_rq_v[KR * o +: KR]; rv_r <= rv; uv_r <= uvo; end
        assign p_rv[KR * o +: KR] = rv_r; assign p_rf[KR * 30 * o +: KR * 30] = rf_r; assign p_uv[KW * o +: KW] = uv_r;
        ot_s81_su_pin #(.KR(KR), .KW(KW)) u_po (
            .clk(sk), .rst_in(rs0),
            .rq_v(rq_v[KR * o +: KR]), .rq_row(rq_row[KR * 14 * o +: KR * 14]), .rs_v(rs_v[KR * o +: KR]),
            .rs_d(rs_d[KR * 512 * o +: KR * 512]), .wq_v(wq_v[KW * o +: KW]), .wq_row(wq_row[KW * 14 * o +: KW * 14]),
            .wq_mask(wq_mask[KW * 16 * o +: KW * 16]), .wq_d(wq_d[KW * 512 * o +: KW * 512]),
            .dn_v(dv[0][KR * o +: KR]), .dn_d(dd[0][KR * 512 * o +: KR * 512]),
            .up_v(uv[0][KW * o +: KW]), .up_a(ua[0][KW * 14 * o +: KW * 14]), .up_m(um[0][KW * 16 * o +: KW * 16]),
            .up_d(ud[0][KW * 512 * o +: KW * 512]),
            .c_rq_v(rq_v_r), .c_rq_row(rq_row_r), .c_rv(rv), .c_rf(rf), .c_uv(uvo));
    end endgenerate

    // ------------------------------------------------------------------ engine tiles
    // norm rungs: the group partial of tile t (TI 1) to its head (t - 1), the head's rstd back (registered relays)
    wire        xpv [0:NTL]; wire [7:0] xpi [0:NTL]; wire [31:0] xpd [0:NTL];   // tile t's outputs
    wire        xrv [0:NTL]; wire [31:0] xrd [0:NTL];
    genvar t;
    generate for (t = 0; t < NTL; t = t + 1) begin : g_t
        localparam integer B1 = NQN, B2 = NQN + NKV, B3 = B2 + NQB, B4 = B3 + NSW;
        localparam integer TK = (t < B1) ? 0 : (t < B2) ? 1 : (t < B3) ? 2 : (t < B4) ? 3 : 4;
        localparam integer TI = (t < B1) ? t : (t < B2) ? t - B1 : (t < B3) ? t - B2 : (t < B4) ? t - B3 : t - B4;
        localparam integer NT = (t < B1) ? NQN : (t < B2) ? NKV : (t < B3) ? NQB : (t < B4) ? NSW : NSM;
        localparam integer WS = S_WR / NT, W0 = TI * WS;
        wire [WS-1:0] o_v; wire [WS*14-1:0] o_a; wire [WS*16-1:0] o_m; wire [WS*512-1:0] o_d;
        wire o_fu, o_fo, o_alive, o_den, o_rdy; wire [7:0] o_rjid;
        // rung relays: into a head (TK <= 1, TI 0) from t + 1; into a member (TI 1) from t - 1
        reg ipv, irv; reg [7:0] ipi; reg [31:0] ipd, ird;
        if (TK <= 1 && TI == 0 && NT == 2) begin : g_rh
            always @(posedge sk) begin ipi <= xpi[t + 1]; ipd <= xpd[t + 1]; end
            always @(posedge sk or negedge rst[t]) if (!rst[t]) ipv <= 1'b0; else ipv <= xpv[t + 1];
        end else begin : g_rh0
            always @(*) begin ipv = 1'b0; ipi = 8'd0; ipd = 32'd0; end
        end
        if (TK <= 1 && TI == 1) begin : g_rm
            always @(posedge sk) ird <= xrd[t - 1];
            always @(posedge sk or negedge rst[t]) if (!rst[t]) irv <= 1'b0; else irv <= xrv[t - 1];
        end else begin : g_rm0
            always @(*) begin irv = 1'b0; ird = 32'd0; end
        end
        ot_s81_su_tile #(.TK(TK), .TI(TI), .NT(NT), .QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H),
                         .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .LM(LM), .LA(LA), .MUT(MUT)) u_tile (
            .clk(sk), .rst_in(rst[t]),
            .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
            .dn_v_i(dv[t]), .dn_d_i(dd[t]),
            .x_pp_v_i(ipv), .x_pp_i_i(ipi), .x_pp_d_i(ipd), .x_rb_v_i(irv), .x_rb_d_i(ird),
            .x_pp_v_o(xpv[t]), .x_pp_i_o(xpi[t]), .x_pp_d_o(xpd[t]), .x_rb_v_o(xrv[t]), .x_rb_d_o(xrd[t]),
            .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
            .o_rdy(o_rdy), .o_rjid(o_rjid));
        // reset spine station
        reg rs_q;
        always @(posedge sk or negedge rst[t]) if (!rst[t]) rs_q <= 1'b0; else rs_q <= 1'b1;
        assign rst[t + 1] = rs_q;
        // down spine relay station
        reg dst_q; reg [3:0] dkd_q; reg [1:0] dgs_q; reg df4_q; reg [7:0] dji_q; reg [S_RD-1:0] dv_q;
        reg [S_RD*512-1:0] dd_q;
        always @(posedge sk) begin dkd_q <= dkd[t]; dgs_q <= dgs[t]; df4_q <= df4[t]; dji_q <= dji[t]; dd_q <= dd[t]; end
        always @(posedge sk or negedge rst[t]) if (!rst[t]) begin dst_q <= 1'b0; dv_q <= 0; end
                                               else begin dst_q <= dst[t]; dv_q <= dv[t]; end
        assign dst[t + 1] = dst_q; assign dkd[t + 1] = dkd_q; assign dgs[t + 1] = dgs_q; assign df4[t + 1] = df4_q;
        assign dji[t + 1] = dji_q; assign dv[t + 1] = dv_q; assign dd[t + 1] = dd_q;
        // up spine relay station: the tile's window merged in
        integer s;
        reg [S_WR-1:0] uv_q; reg [S_WR*14-1:0] ua_q; reg [S_WR*16-1:0] um_q; reg [S_WR*512-1:0] ud_q;
        reg ufu_q, ufo_q, ual_q, ude_q, urd_q; reg [7:0] urj_q;
        assign uv[t] = uv_q; assign ua[t] = ua_q; assign um[t] = um_q; assign ud[t] = ud_q; assign ufu[t] = ufu_q;
        assign ufo[t] = ufo_q; assign ual[t] = ual_q; assign ude[t] = ude_q; assign urd[t] = urd_q; assign urj[t] = urj_q;
        always @(posedge sk) begin
            for (s = 0; s < S_WR; s = s + 1)
                if (s >= W0 && s < W0 + WS && o_v[s - W0]) begin
                    ua_q[14 * s +: 14] <= o_a[14 * (s - W0) +: 14]; um_q[16 * s +: 16] <= o_m[16 * (s - W0) +: 16];
                    ud_q[512 * s +: 512] <= o_d[512 * (s - W0) +: 512];
                end else begin
                    ua_q[14 * s +: 14] <= ua[t + 1][14 * s +: 14]; um_q[16 * s +: 16] <= um[t + 1][16 * s +: 16];
                    ud_q[512 * s +: 512] <= ud[t + 1][512 * s +: 512];
                end
        end
        always @(posedge sk or negedge rst[t]) begin
            if (!rst[t]) begin uv_q <= 0; ufu_q <= 0; ufo_q <= 0; ual_q <= 0; ude_q <= 0; urd_q <= 0; urj_q <= 0; end
            else begin
                for (s = 0; s < S_WR; s = s + 1) uv_q[s] <= uv[t + 1][s] || (s >= W0 && s < W0 + WS && o_v[s - W0]);
                ufu_q <= ufu[t + 1] || o_fu; ufo_q <= ufo[t + 1] || o_fo; ual_q <= ual[t + 1] && o_alive;
                ude_q <= ude[t + 1] && o_den; urd_q <= urd[t + 1] || o_rdy; urj_q <= o_rdy ? o_rjid : urj[t + 1];
            end
        end
    end endgenerate
    assign xpv[NTL] = 1'b0; assign xpi[NTL] = 8'd0; assign xpd[NTL] = 32'd0;
endmodule
