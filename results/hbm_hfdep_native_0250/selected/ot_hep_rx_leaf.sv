module ot_hep_rx_leaf #(parameter integer W = 306, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          we,
    input  wire [5:0]    wa,
    input  wire [5:0]    ra,
    input  wire [W-1:0]  din,
    output reg  [W-1:0]  dout
);
    reg wq; reg [5:0] aq; reg [W-1:0] dq;
    wire [511:0] mr;
    always @(posedge ck) begin wq <= we; aq <= wa; dq <= din; end
    ot_sram_1r1w_64x512_m1_r2c2 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in({{(512-W){1'b0}}, dq}),
        .w_mask_in({{(512-W){1'b0}}, {W{1'b1}}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(18'd0));
    always @(posedge ck) dout <= mr[W-1:0] ^ (MUT != 0 ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
endmodule
