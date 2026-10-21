`timescale 1ns/1ps
// S81-CTRL 10-17: dsfd_ctrl_rg2, the REGIONAL S81 HBM controller of the S81-DV die (p4g SPEC (3), p4i bind owner
// S81-CTRL): 16 of these replace the 8.5 mm dsfd_ctrl strip, each 531.25 x 250 um on the PHY N face, serving the two
// pseudo-channels 2k, 2k+1 of the HBM3E PHY (ot_hbm3e_phy_v41x_aw30_e8p5) and talking to its regional service slice
// (dsdv_svc_rs k) over one rq link (682 b) and one rd link (562 b).
//
// Derived from the S81-PH controller (dsfd_ctrl = 32 x dsfd_ctrl_pc + dsfd_ctrl_ctr): the per-PC channel
// ot_s81ph_ctrl_pc is instantiated UNCHANGED twice, so the PHY-side protocol, the CDC and the per-PC latencies are those
// of the benched controller (tb_dsfd_ctrl).  What is regional:
//   * reset: rst_n is this region's reset-relay leaf (die dsfd_rly_1_WN tree); each PC channel synchronises it into
//     cks and ckh (2-flop async-assert / sync-release) -- no die-wide synchronous reset, no PHY reset register (the
//     PHY's rst_n is its own region's relay leaf on the die);
//   * status: the two PC chains {fault, live} merge in one register into rd[561:560] (fault = request overflow,
//     live = both PC HBM-side resets released); the die-wide status is the S81 fault tree's job, not a 16-tile chain.
//
// FLOW CONTROL (owner 10-14/10-15, hbm-static-onchip): only at the HBM boundary.  The PHY face keeps the PHY's
// valid/ready (k_v/k_rdy, kr_v/kr_rdy) -- DRAM latency is not schedulable.  The die face has NO ready and never stalls:
// every rq word is accepted into the per-PC request buffer (DQ entries, statically sized; a word beyond it is dropped
// and raises the sticky fault -- a fault check, not a scheduling mechanism); every landed response is delivered on rd
// the cycle it is ready (rv).  rk / wd are the HBM-boundary returns of the elastic KV-HBM boundary (one rk per request
// the PHY has taken, one wd per completed write): the service slice uses them as its buffer-block ready checks.
//
// Pins (owner pin-register rule): every die-face input is captured in a flop at the pin and every output is a flop
// (inside the per-PC channel, plus the status register here).
// S81-SAFE-FIX/CTRL 10-19 (c1/c2 routes missed TT -6.38 in->reg on k_rdy): the per-PC channel is now ot_s81ph_ctrl_pcr
// (the safe redesign; ot_s81ph_ctrl_pc is unchanged for the closed S81-PH views): k_rdy lands in a flop at the PHY face
// (no exception left), the issue is present-then-decide (<= 1 request / 2 ckh per PC, same PHY valid/ready contract),
// and the hold-register enable and FIFO read selects are replicated per 32-bit group as kept copies (<= ~32 loads).
//
// Port bundles:
//   rq[341p +: 341]  = PC p request {wdata 256, wstrb 32, tag 17, len 4, addr 30, we, v}           (p = 0, 1)
//   rd[280p +: 280]  = PC p {wd, rk, rv, beat 4, tag 17, data 256} (data at the LSBs)
//   rd[561:560]      = {fault, live}
//   ck_o             = forwarded clock of the rd link (as the dsfd_dvrly_* stations: ck through two kept inverters)
//   k_* / kr_*       = the PHY K/KR ports of PCs 2k (index 0) and 2k+1 (index 1), packed exactly as the PHY's 32-PC
//                      buses: the die binds PHY k_v[2k +: 2] <-> k_v[1:0], k_addr[60k +: 60] <-> k_addr[59:0], ...
`default_nettype none
module dsfd_ctrl_rg2 #(
    parameter integer DQ = 8,      // request buffer entries per PC (the svc's static per-PC request budget)
    parameter integer DR = 8       // response landing entries per PC
) (
    input  wire           clk,       // stream clock (cks): this region's die clock
    input  wire           ckh,       // HBM clock: the PHY's clock
    input  wire           rst_n,     // regional reset-relay leaf, active low, asynchronous assert
    input  wire [681:0]   rq,
    output wire [561:0]   rd,
    output wire           ck_o,      // forwarded clock of the rd link (clk through the kept ckinv pair, non-inverted)
    // PHY face (2 PCs)
    output wire [1:0]     k_v,
    input  wire [1:0]     k_rdy,
    output wire [59:0]    k_addr,
    output wire [7:0]     k_len,
    output wire [33:0]    k_tag,
    output wire [1:0]     k_we,
    output wire [511:0]   k_wdata,
    output wire [63:0]    k_wstrb,
    input  wire [1:0]     k_wr_done,
    input  wire [1:0]     kr_v,
    output wire [1:0]     kr_rdy,
    input  wire [33:0]    kr_tag,
    input  wire [7:0]     kr_beat,
    input  wire [511:0]   kr_data
);
    wire [1:0] co0, co1;
    wire [1:0] s_ovf;
    genvar p;
    generate for (p = 0; p < 2; p = p + 1) begin : g_pc
        wire [1:0] ci = (p == 0) ? 2'b01 : co0;    // PC 1's chain input = PC 0's chain output (neutral {0, 1} at PC 0)
        wire [1:0] co;
        wire        rk_w, rv_w, wd_w, kv_w, kwe_w;
        wire [255:0] rdat;
        wire [16:0]  rtag;
        wire [3:0]   rbeat;
        ot_s81ph_ctrl_pcr #(.DQ(DQ), .DR(DR)) u_pc (
            .cks(clk), .ckh(ckh), .rst(rst_n), .ci(ci), .co(co),
            .rq(rq[p*341 +: 341]), .rk(rk_w), .rv(rv_w), .r_data(rdat), .r_tag(rtag), .r_beat(rbeat), .wd(wd_w),
            .s_ovf(s_ovf[p]),
            .k_v(k_v[p]), .k_rdy(k_rdy[p]), .k_addr(k_addr[p*30 +: 30]), .k_len(k_len[p*4 +: 4]),
            .k_tag(k_tag[p*17 +: 17]), .k_we(k_we[p]), .k_wdata(k_wdata[p*256 +: 256]), .k_wstrb(k_wstrb[p*32 +: 32]),
            .k_wr_done(k_wr_done[p]), .kr_v(kr_v[p]), .kr_rdy(kr_rdy[p]), .kr_tag(kr_tag[p*17 +: 17]),
            .kr_beat(kr_beat[p*4 +: 4]), .kr_data(kr_data[p*256 +: 256]));
`ifdef S81CTRL_MUT_RD
        assign rd[p*280 +: 280] = {rk_w, wd_w, rv_w, rbeat, rtag, rdat};      // mutant: rk / wd swapped in the rd word
`else
        assign rd[p*280 +: 280] = {wd_w, rk_w, rv_w, rbeat, rtag, rdat};
`endif
        if (p == 0) begin : g_c0 assign co0 = co; end
        else        begin : g_c1 assign co1 = co; end
    end endgenerate
    // regional status register: PC 1's chain already folds PC 0 ({fault | , live &}); one more flop at the pin.
    wire srst_n;
    ot_s81ph_sync u_srs (.clk(clk), .rst_n(rst_n), .d(1'b1), .q(srst_n));
    reg [1:0] st;
    always @(posedge clk or negedge srst_n)
        if (!srst_n) st <= 2'b00;
        else st <= co1;
    assign rd[561:560] = st;
    // neighbour-relative clocking (die standard): the rd link's hop-0 station captures on this forwarded clock
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(clk), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
`default_nettype wire
