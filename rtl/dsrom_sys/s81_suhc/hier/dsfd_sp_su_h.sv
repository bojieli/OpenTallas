`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the S81 SU slab master rebuilt as a hierarchical slab.  Same pins
// and adapter as dsfd_sp_su (contract su_hc v2: c_cmd / c_done / inp / VM rd S_RD rows / VM wr S_WR rows / flt /
// online / fcode); inside, one control tile and NT hardened engine tiles on two registered chains:
//
//   pins -> root tile ot_s81_su_root (adapter, pin flops, ot_s81_su_hctl job control / VM read issue / VM write port)
//       down spine (VM response rows + job announce, S_RD x 512 b): relay stations at the stops QN, KV, QB 0..NQB-1,
//         SW 0..NSW-1, SM 0..NSM-1 (one register a stop); each tile taps its stop
//       up spine (S_WR write row slots): a relay station a stop merges that tile's registered slots into its window
//   regional reset: pin -> relay -> ctl; a reset spine station a stop -> the tile's own two-flop relay
// Tiles carry one copy of each bus (no pass-through): pins = the down tap + its own write slots + status.
//
// Tile decomposition (production params): QN norm (256 lanes, D 1,280, the q gain sets), KV norm (512 lanes, RoPE
// tail, the kv gain sets), QB x 4 (8 blocks each), SW x 8 (128 lanes each), SM x 8 (2 heads x 16 lanes each).
// The values are those of dsfd_sp_su (bit-exact gate tools/s81_suhc/su_gate.py --hier); added latency: the chain
// hops (a cycle a tile each way) and the norm tiles' ready round trip.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_su_h #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0,
    // lane-group tiles (production: QB 4 x 8 blocks, SW 8 x 128 lanes, SM 8 x 2 heads; sized for <= ~600-um tiles)
    parameter integer NQB = (QB_NB >= 32) ? QB_NB / 8 : 2,
    parameter integer NSW = (SW_W >= 128) ? SW_W / 128 : 1,
    parameter integer NSM = (SM_H >= 2) ? SM_H / 2 : 1
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
    localparam integer NTL = 2 + NQB + NSW + NSM;
    // spines: stop t = tile t.  Down: dn[t] is the relay register at stop t (dn[0] the control tile's output
    // register); the tile taps it and the next stop re-registers it.  Up: up[t] is the relay register at stop t,
    // = up[t + 1] with tile t's registered write slots merged into its window; up[0] feeds the control tile.
    wire                  dst [0:NTL];
    wire [3:0]            dkd [0:NTL];
    wire [1:0]            dgs [0:NTL];
    wire                  df4 [0:NTL];
    wire [7:0]            dji [0:NTL];
    wire [S_RD-1:0]       dv  [0:NTL];
    wire                  dph [0:NTL];
    wire [15:0]           dix [0:NTL];
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
    ot_s81_su_root #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                     .S_RD(S_RD), .S_WR(S_WR), .NSW(NSW), .NQB(NQB), .MUT(MUT), .AMUT(AMUT)) u_root (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt), .online(online), .fcode(fcode),
        .rst_o(rst[0]),
        .dn_st(dst[0]), .dn_kind(dkd[0]), .dn_gsel(dgs[0]), .dn_fp4(df4[0]), .dn_jid(dji[0]), .dn_v(dv[0]),
        .dn_ph(dph[0]), .dn_idx(dix[0]), .dn_d(dd[0]),
        .up_v(uv[0]), .up_a(ua[0]), .up_m(um[0]), .up_d(ud[0]), .up_fu(ufu[0]), .up_fo(ufo[0]), .up_alive(ual[0]),
        .up_den(ude[0]), .up_rdy(urd[0]), .up_rjid(urj[0]));

    genvar t;
    generate for (t = 0; t < NTL; t = t + 1) begin : g_t
        localparam integer TK = (t == 0) ? 0 : (t == 1) ? 1 : (t < 2 + NQB) ? 2 : (t < 2 + NQB + NSW) ? 3 : 4;
        localparam integer TI = (t < 2) ? 0 : (t < 2 + NQB) ? t - 2 : (t < 2 + NQB + NSW) ? t - 2 - NQB : t - 2 - NQB - NSW;
        localparam integer NT = (t < 2) ? 1 : (t < 2 + NQB) ? NQB : (t < 2 + NQB + NSW) ? NSW : NSM;
        localparam integer WS = (TK <= 1) ? S_WR : S_WR / NT, W0 = (TK <= 1) ? 0 : TI * WS;
        wire [WS-1:0] o_v; wire [WS*14-1:0] o_a; wire [WS*16-1:0] o_m; wire [WS*512-1:0] o_d;
        wire o_fu, o_fo, o_alive, o_den, o_rdy; wire [7:0] o_rjid;
        ot_s81_su_tile #(.TK(TK), .TI(TI), .NT(NT), .QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H),
                         .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .LM(LM), .LA(LA), .MUT(MUT)) u_tile (
            .clk(sk), .rst_in(rst[t]),
            .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
            .dn_v_i(dv[t]), .dn_ph_i(dph[t]), .dn_idx_i(dix[t]), .dn_d_i(dd[t]),
            .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
            .o_rdy(o_rdy), .o_rjid(o_rjid));
        // reset spine station
        reg rs_q;
        always @(posedge sk or negedge rst[t]) if (!rst[t]) rs_q <= 1'b0; else rs_q <= 1'b1;
        assign rst[t + 1] = rs_q;
        // down spine relay station
        reg dst_q; reg [3:0] dkd_q; reg [1:0] dgs_q; reg df4_q; reg [7:0] dji_q; reg [S_RD-1:0] dv_q; reg dph_q;
        reg [15:0] dix_q; reg [S_RD*512-1:0] dd_q;
        always @(posedge sk) begin dkd_q <= dkd[t]; dgs_q <= dgs[t]; df4_q <= df4[t]; dji_q <= dji[t]; dph_q <= dph[t];
                                   dix_q <= dix[t]; dd_q <= dd[t]; end
        always @(posedge sk or negedge rst[t]) if (!rst[t]) begin dst_q <= 1'b0; dv_q <= 0; end
                                               else begin dst_q <= dst[t]; dv_q <= dv[t]; end
        assign dst[t + 1] = dst_q; assign dkd[t + 1] = dkd_q; assign dgs[t + 1] = dgs_q; assign df4[t + 1] = df4_q;
        assign dji[t + 1] = dji_q; assign dv[t + 1] = dv_q; assign dph[t + 1] = dph_q; assign dix[t + 1] = dix_q;
        assign dd[t + 1] = dd_q;
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
endmodule
