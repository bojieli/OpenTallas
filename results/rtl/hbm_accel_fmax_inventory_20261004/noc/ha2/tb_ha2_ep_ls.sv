`timescale 1ns/1ps
// Lockstep checker of ot_ha2_owner_reduce against the UNMODIFIED ot_ha2_ar_endpoint (noc fmax closure).
// Drop-in replacement of tb_ha2_ar.sv's tb_ha2_ep wrapper (mk_ls_tb.sh rewrites the tb to instantiate this):
// the successor is fed the endpoint's own internal arrivals (h_v/h_d, rb_pop && !kind with rb_head) and its
// packed results {r_v, r_m, r_d} are compared every cycle with the endpoint's, delayed by SLOTREG cycles.
`ifndef HA2_SLOTREG
`define HA2_SLOTREG 1
`endif
module tb_ha2_ep_ls (
    input  wire clk, rst_n, input wire [7:0] rank, input wire go,
    output wire [`HA2_INJ*16-1:0] inj_idx, output wire [`HA2_INJ-1:0] inj_rd,
    input  wire [`HA2_INJ*32*`HA2_LANES-1:0] inj_data,
    output wire [`HA2_GS+`HA2_NG-3:0] tx_valid, output wire [(`HA2_GS+`HA2_NG-2)*(32*`HA2_LANES+25)-1:0] tx_flit,
    input  wire [`HA2_GS+`HA2_NG-3:0] cr_ret,
    input  wire [`HA2_GS+`HA2_NG-3:0] rx_valid, input wire [(`HA2_GS+`HA2_NG-2)*(32*`HA2_LANES+25)-1:0] rx_flit,
    output wire [`HA2_GS+`HA2_NG-3:0] rx_credit,
    output wire [`HA2_DEL-1:0] del_valid, output wire [`HA2_DEL*(32*`HA2_LANES+25)-1:0] del_flit,
    output wire fault, output wire [31:0] stat_credit_stall
);
    /*verilator hier_block*/
    localparam integer NP = `HA2_GS + `HA2_NG - 2, FW = 32 * `HA2_LANES, PWT = FW + 25, SR = `HA2_SLOTREG;
    ot_ha2_ar_endpoint #(.ENABLE(1), .GS(`HA2_GS), .NG(`HA2_NG), .NC(`HA2_NC), .NOG(`HA2_NOG), .E(`HA2_E),
        .LANES(`HA2_LANES), .ONESHOT(`HA2_ONESHOT), .BF16(`HA2_BF16), .INJ(`HA2_INJ), .DEL(`HA2_DEL),
        .HUBW(`HA2_HUBW), .RXAW(`HA2_RXAW), .QAW(`HA2_QAW), .LAT(`HA2_LAT))
      u (.clk(clk), .rst_n(rst_n), .rank(rank), .go(go), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_data(inj_data),
         .tx_valid(tx_valid), .tx_flit(tx_flit), .cr_ret(cr_ret), .rx_valid(rx_valid), .rx_flit(rx_flit),
         .rx_credit(rx_credit), .del_valid(del_valid), .del_flit(del_flit), .fault(fault),
         .stat_credit_stall(stat_credit_stall));
    // the endpoint's arrivals
    reg [NP-1:0]     pv;
    reg [NP*PWT-1:0] pf;
    always @* for (integer p = 0; p < NP; p = p + 1) begin
        pf[p*PWT +: PWT] = u.g_on.rb_head[p];
        pv[p] = u.g_on.rb_pop[p] && !u.g_on.rb_head[p][PWT-1];
    end
    wire s_v, s_dupe, s_iss;
    wire [15:0] s_m;
    wire [FW-1:0] s_d;
    ot_ha2_owner_reduce #(.GS(`HA2_GS), .NC(`HA2_NC), .E(`HA2_E), .LANES(`HA2_LANES), .ONESHOT(`HA2_ONESHOT),
        .BF16(`HA2_BF16), .INJ(`HA2_INJ), .NP(NP), .LAT(`HA2_LAT), .SLOTREG(SR))
      s (.clk(clk), .rst_n(rst_n), .rank(rank), .h_v(u.g_on.h_v), .h_d(u.g_on.h_d), .p_v(pv), .p_flit(pf),
         .r_v(s_v), .r_m(s_m), .r_d(s_d), .dupe(s_dupe), .issue_o(s_iss));
    // reference delayed by SR cycles
    reg [SR:0]        dv;
    reg [16+FW-1:0]   dd [0:SR];
    always @* begin dv[0] = u.g_on.r_v; dd[0] = {u.g_on.r_m, u.g_on.r_d}; end
    always @(posedge clk) for (integer i = 1; i <= SR; i = i + 1) begin dv[i] <= dv[i-1]; dd[i] <= dd[i-1]; end
    integer cmp = 0, mis = 0, ref_n = 0, issues = 0;
    always @(posedge clk) if (rst_n) begin
        if (s_iss) issues = issues + 1;
        if (dv[SR]) ref_n = ref_n + 1;
        if (s_v !== dv[SR] || (s_v && ({s_m, s_d} !== dd[SR])) || s_dupe !== u.g_on.dupe) begin
            mis = mis + 1;
            if (mis < 5) $display("HA2LSMISMATCH rank=%0d t=%0t sv=%0d rv=%0d", rank, $time, s_v, dv[SR]);
        end
        if (s_v) cmp = cmp + 1;
    end
    final $display("HA2LS rank=%0d slotreg=%0d results_compared=%0d ref_results=%0d issues=%0d mismatches=%0d",
                   rank, SR, cmp, ref_n, issues, mis);
endmodule
