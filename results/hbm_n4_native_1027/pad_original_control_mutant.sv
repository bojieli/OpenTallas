`timescale 1ns/1ps
module ot_hnx_fused_pad_original #(parameter integer WC = 15) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    k,
    input  wire [WC-1:0] dc,
    input  wire [255:0]  dd,
    output wire [WC-1:0] qc,
    output wire [255:0]  qd
);
    reg [4:0] wp; reg [5:0] fill; reg ok_q;
    wire [4:0] ra = 5'(wp - 5'(k) + 5'd1);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= '0; fill <= '0; ok_q <= 1'b0; end
        else begin
            wp <= wp + 5'd1;
            if (fill != 6'd63) fill <= fill + 6'd1;
            ok_q <= (fill + 6'd1 >= k);                  // the slot read at this edge was written after reset
        end
    wire [255:0] rdd; wire [63:0] rdc;
    ot_sram_1r1w_128x256_m1_r2c2 u_d (.clk(clk), .r_ce_in(1'b1), .r_addr_in({2'b00, ra}), .rd_out(rdd),
        .w_ce_in(1'b1), .w_addr_in({2'b00, wp}), .wd_in(dd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w2c_32x64_m1 u_c (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(rdc),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in({{(64 - WC){1'b0}}, dc}), .w_mask_in({64{1'b1}}));
    reg [WC-1:0] c1; reg [255:0] d1;
    always @(posedge clk or negedge rst_n) if (!rst_n) c1 <= '0; else c1 <= dc;
    always @(posedge clk) d1 <= dd;
    assign qc = (k == 6'd0) ? dc : (k == 6'd1) ? c1 : (ok_q ? rdc[WC-1:0] : {WC{1'b0}});
    assign qd = (k == 6'd0) ? dd : (k == 6'd1) ? d1 : rdd;
endmodule
