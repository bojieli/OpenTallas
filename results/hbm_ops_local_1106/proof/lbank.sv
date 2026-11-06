module ot_hgi_su_lbank #(
    parameter integer RB = 13,             // log2 words in the bank
    parameter integer MACRO = 1,           // 1: ot_sram_1r1w_1024x256 rows (RB = 13); 0: behavioural
    parameter integer LAT = 0              // bench mutant (behavioural banks): 1 = read latency 2 edges, 2 = 0 edges
) (
    input  wire          clk,
    input  wire          re,
    input  wire [RB-1:0] ra,
    output wire [31:0]   rd,
    input  wire          we,
    input  wire [RB-1:0] wa,
    input  wire [31:0]   wd
);
    reg [2:0] ks;
    always @(posedge clk) if (re) ks <= ra[2:0];
    wire [255:0] wm = {224'd0, 32'hFFFF_FFFF} << {wa[2:0], 5'd0};
    generate if (MACRO && RB == 13) begin : g_m
        wire [255:0] ro;
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00), .rr_addr(18'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 12) begin : g_m12       // 512 rows: the 1,024-row macro, upper half unused
        wire [255:0] ro;
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in({1'b0, ra[RB-1:3]}), .rd_out(ro),
            .w_ce_in(we), .w_addr_in({1'b0, wa[RB-1:3]}), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 11) begin : g_m11
        wire [255:0] ro;
        ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 10) begin : g_m10
        wire [255:0] ro;
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 9) begin : g_m9
        // 512 words occupy the lower 64 rows; the upper 64 physical rows are unused.
        wire [255:0] ro;
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in({1'b0, ra[RB-1:3]}), .rd_out(ro),
            .w_ce_in(we), .w_addr_in({1'b0, wa[RB-1:3]}), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO) begin : g_unsupported_macro
        initial $fatal(1, "ot_hgi_su_lbank: unsupported MACRO=1 RB=%0d", RB);
        assign rd = 32'd0;
    end else begin : g_b
        reg [31:0] m [0:(1 << RB) - 1];
        reg [31:0] q, q2;
        always @(posedge clk) begin if (re) q <= m[ra]; q2 <= q; if (we) m[wa] <= wd; end
        assign rd = (LAT == 1) ? q2 : (LAT == 2) ? m[ra] : q;
    end endgenerate
endmodule