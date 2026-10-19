module ot_qkvd_llr_replay_sram_leaf_sf #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0, GB = 16, MUTFO = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    localparam integer NG = (W + GB - 1) / GB;
    (* keep = "true", dont_touch = "true" *) reg wq;
    (* keep = "true", dont_touch = "true" *) reg [QA-1:0] aq;
    reg [W-1:0] dq, dqq;
    wire [511:0] mr;
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
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}},dq}),
        .w_mask_in({{(512-W){1'b0}},{W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
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
