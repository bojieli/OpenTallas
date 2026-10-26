// Expected-answer reference for zero-latency forwarding transformation only.
// Frozen prior production leaf before the 2026-10-16 flag pipeline; real macro in both copies.
module qkd_replay_sram_prior_0253 #(
    parameter integer W = 137, QD = 64,
    parameter integer QA = $clog2(QD), MUT = 0
) (
    input wire ck, we,
    input wire [QA-1:0] wa, ra,
    input wire [W-1:0] din,
    output reg [W-1:0] dout
);
    // Real 64x512 SRAM at the native64x137 shape. Unused columns are masked;
    // all readable queue words are written before their valid reservation.
    // Capture write pins, then commit to the SRAM. Track both collision ages
    // because the macro read is synchronous and read-before-write.
    reg wq, wqq;
    reg [QA-1:0] aq, aqq, rq;
    reg [W-1:0] dq, dqq;
    wire [511:0] mr;
    always @(posedge ck) begin
        wq <= we; aq <= wa; dq <= din;
        wqq <= wq; aqq <= aq; dqq <= dq;
        rq <= ra;
    end
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}},dq}),
        .w_mask_in({{(512-W){1'b0}},{W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    always @(posedge ck)
        // A write arriving after this read reservation is forbidden by the
        // compiler ownership check. Bypass only the two captured write ages;
        // raw write pins must not feed the read-output D cones.
        dout <= (wq && aq == rq ? dq :
                 wqq && aqq == rq ? dqq : mr[W-1:0]) ^
            (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});

endmodule
