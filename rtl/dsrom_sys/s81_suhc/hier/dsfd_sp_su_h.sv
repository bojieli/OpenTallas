`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_su_h (s81-suhc-hier-1011, 2026-10-11): the S81 SU slab master rebuilt as a hierarchical slab.  Same pins
// and adapter as dsfd_sp_su (contract su_hc v2: c_cmd / c_done / inp / VM rd S_RD rows / VM wr S_WR rows / flt /
// online / fcode); inside, one control tile and NT hardened engine tiles on two registered chains:
//
//   pins -> pin flops -> ot_s81_su_hctl (adapter-side job control, VM read issue, VM write port)
//       down chain (VM response rows + job announce, S_RD x 512 b): ctl -> QN -> KV -> QB 0..NQB-1 -> SW 0..NSW-1
//                                                                       -> SM 0..NSM-1   (a register a tile hop)
//       up chain (S_WR write row slots, each tile its own slot window): SM .. -> QN -> ctl -> VM write pin flops
//   regional reset: pin -> relay -> ctl, then tile to tile (two-flop relays)
//
// Tile decomposition (production params): QN norm (256 lanes, D 1,280, the q gain sets), KV norm (512 lanes, RoPE
// tail, the kv gain sets), QB x 2 (16 blocks each), SW x 4 (256 lanes each), SM x 4 (4 heads x 16 lanes each).
// The values are those of dsfd_sp_su (bit-exact gate tools/s81_suhc/su_gate.py --hier); added latency: the chain
// hops (a cycle a tile each way) and the norm tiles' ready round trip.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_su_h #(
    parameter integer QN_N = 256, KV_N = 512, QB_NB = 32, SW_W = 1024, SM_H = 16, SM_LPH = 16, SM_NVMAX = 40,
    parameter integer S_RD = 16, S_WR = 16, LM = 5, LA = 4, OQ = 1024, MUT = 0, AMUT = 0,
    parameter integer NQB = 2,
    parameter integer NSW = (SW_W >= 256) ? SW_W / 256 : 1,
    parameter integer NSM = (SM_H >= 4) ? SM_H / 4 : 1
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
    wire e_v, e_r, d_v, a_flt, c_flt;
    wire [83:0] e_d;
    wire [7:0]  d_t;
    reg inp_q;
    reg s0, s1;                                        // slab reset relay (pin)
    always @(posedge sk or negedge srs) if (!srs) begin s0 <= 1'b0; s1 <= 1'b0; end else begin s0 <= 1'b1; s1 <= s0; end
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    // pin flops: VM responses
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    always @(posedge sk) rs_d_q <= rs_d;
    always @(posedge sk or negedge s1) if (!s1) rs_v_q <= 0; else rs_v_q <= rs_v;

    // chains: index i = the input of tile i (down) / the output of tile i (up); dn[NTL] / up[NTL] the far end
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
    assign rst[0] = s1;

    wire [31:0] jobs;
    wire        bsy;
    ot_s81_su_hctl #(.QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H), .SM_LPH(SM_LPH),
                     .S_RD(S_RD), .S_WR(S_WR), .NSW(NSW), .NQB(NQB), .MUT(MUT)) u_core (
        .clk(sk), .rst_n(s1), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs),
        .dn_st(dst[0]), .dn_kind(dkd[0]), .dn_gsel(dgs[0]), .dn_fp4(df4[0]), .dn_jid(dji[0]), .dn_v(dv[0]),
        .dn_ph(dph[0]), .dn_idx(dix[0]), .dn_d(dd[0]),
        .up_v(uv[0]), .up_a(ua[0]), .up_m(um[0]), .up_d(ud[0]), .up_fu(ufu[0]), .up_fo(ufo[0]), .up_alive(ual[0]),
        .up_den(ude[0]), .up_rdy(urd[0]), .up_rjid(urj[0]));
    assign flt = a_flt | c_flt;

    genvar t;
    generate for (t = 0; t < NTL; t = t + 1) begin : g_t
        localparam integer TK = (t == 0) ? 0 : (t == 1) ? 1 : (t < 2 + NQB) ? 2 : (t < 2 + NQB + NSW) ? 3 : 4;
        localparam integer TI = (t < 2) ? 0 : (t < 2 + NQB) ? t - 2 : (t < 2 + NQB + NSW) ? t - 2 - NQB : t - 2 - NQB - NSW;
        localparam integer NT = (t < 2) ? 1 : (t < 2 + NQB) ? NQB : (t < 2 + NQB + NSW) ? NSW : NSM;
        ot_s81_su_tile #(.TK(TK), .TI(TI), .NT(NT), .QN_N(QN_N), .KV_N(KV_N), .QB_NB(QB_NB), .SW_W(SW_W), .SM_H(SM_H),
                         .SM_LPH(SM_LPH), .SM_NVMAX(SM_NVMAX), .S_RD(S_RD), .S_WR(S_WR), .LM(LM), .LA(LA), .MUT(MUT)) u_tile (
            .clk(sk), .rst_in(rst[t]), .rst_out(rst[t + 1]),
            .dn_st_i(dst[t]), .dn_kind_i(dkd[t]), .dn_gsel_i(dgs[t]), .dn_fp4_i(df4[t]), .dn_jid_i(dji[t]),
            .dn_v_i(dv[t]), .dn_ph_i(dph[t]), .dn_idx_i(dix[t]), .dn_d_i(dd[t]),
            .dn_st_o(dst[t + 1]), .dn_kind_o(dkd[t + 1]), .dn_gsel_o(dgs[t + 1]), .dn_fp4_o(df4[t + 1]),
            .dn_jid_o(dji[t + 1]), .dn_v_o(dv[t + 1]), .dn_ph_o(dph[t + 1]), .dn_idx_o(dix[t + 1]), .dn_d_o(dd[t + 1]),
            .up_v_i(uv[t + 1]), .up_a_i(ua[t + 1]), .up_m_i(um[t + 1]), .up_d_i(ud[t + 1]), .up_fu_i(ufu[t + 1]),
            .up_fo_i(ufo[t + 1]), .up_alive_i(ual[t + 1]), .up_den_i(ude[t + 1]), .up_rdy_i(urd[t + 1]),
            .up_rjid_i(urj[t + 1]),
            .up_v_o(uv[t]), .up_a_o(ua[t]), .up_m_o(um[t]), .up_d_o(ud[t]), .up_fu_o(ufu[t]), .up_fo_o(ufo[t]),
            .up_alive_o(ual[t]), .up_den_o(ude[t]), .up_rdy_o(urd[t]), .up_rjid_o(urj[t]));
    end endgenerate
endmodule
