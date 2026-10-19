`timescale 1ns/1ps
// Exact captured safe-FO leaf; private width-only physical-memory adaptation.
module ot_qkvd_llr_replay_sram_leaf_sf137_private #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0, GB = 16, MUTFO = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    generate if (W != 137 || QD != 64 || QA != 6 || GB != 16) begin : g_bad_shape
        OT_PRIVATE_REPLAY137_REQUIRES_W137_QD64_QA6_GB16 u_bad_shape ();
    end endgenerate
    localparam integer NG = (W + GB - 1) / GB;
    (* keep = "true", dont_touch = "true" *) reg wq;
    (* keep = "true", dont_touch = "true" *) reg [QA-1:0] aq;
    reg [W-1:0] dq, dqq;
    wire [136:0] mr;
`ifdef OT_QKD_REPLAY_HIT_MUT
    wire h0 = we && wa != ra;   // negative control: corrupt current-age selection
`else
    wire h0 = we && wa == ra;
`endif
    wire h1 = wq && aq == ra;
    // as built: dout <= hit_age0 ? dq : hit_age1 ? dqq : macro, with hit_age0 <= h0, hit_age1 <= h1 at this edge
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0] s_dq;
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0] s_dqq;
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0] s_mr;
    (* keep = "true", dont_touch = "true" *) always @(posedge ck) begin
        wq <= we; aq <= wa; dq <= din; dqq <= dq;
        s_dq <= {NG{h0}}; s_dqq <= {NG{!h0 && h1}}; s_mr <= {NG{!h0 && !h1}};
    end
    ot_sram_1r1w_64x137_m1_r2c2_p192 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in(dq),
        .w_mask_in({137{1'b1}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(16'd0));
    genvar g;
    for (g = 0; g < NG; g = g + 1) begin : g_sel
        localparam integer LO = g * GB;
        localparam integer WG = (LO + GB <= W) ? GB : W - LO;
        wire a = (MUTFO == 2 && g == 3) ? s_dqq[g] : s_dq[g];
        wire b = (MUTFO == 2 && g == 3) ? s_dq[g] : s_dqq[g];
        always @(posedge ck)
            dout[LO +: WG] <= (({WG{a}} & dq[LO +: WG]) | ({WG{b}} & dqq[LO +: WG]) | ({WG{s_mr[g]}} & mr[LO +: WG])) ^
                ((MUT != 0 && g == 0) ? {{(WG-1){1'b0}}, 1'b1} : {WG{1'b0}});
    end
`ifdef OT_FO_CHECK
    reg fo_armed = 1'b0;
    always @(posedge ck) begin
        if (fo_armed && (s_dq !== {NG{s_dq[0]}} || s_dqq !== {NG{s_dqq[0]}} || s_mr !== {NG{s_mr[0]}}))
            $display("FO_COPY_MISMATCH %m t=%0t", $time);
        fo_armed <= 1'b1;
    end
`endif
endmodule

// Distinct private four-bank component: 548 live bits, no extra edge or control.
module ot_qkvd_llr_replay_four_sf137_private #(parameter integer MUTFO=0) (
 input wire ck, we,
 input wire [5:0] wa, ra,
 input wire [547:0] din,
 output wire [547:0] dout
);
 genvar b;
 for (b=0; b<4; b=b+1) begin : g_bank
  ot_qkvd_llr_replay_sram_leaf_sf137_private #(.MUTFO(MUTFO)) u_leaf
   (.ck(ck),.we(we),.wa(wa),.ra(ra),.din(din[137*b +:137]),.dout(dout[137*b +:137]));
 end
endmodule
