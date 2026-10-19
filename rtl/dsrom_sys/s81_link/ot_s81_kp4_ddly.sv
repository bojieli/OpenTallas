`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_ddly (S81-KP4 2026-10-17): received-word delay hard tile of the S81 KP4 decoder cluster ot_s81_kp4_dec:
// one 64 x 546 1R1W SRAM (ot_sram_1r1w2c_64x546_m1, both ports on clk) written and read every cycle at a fixed
// distance DD = 55 (a free-running pointer: no enables, no flow control).  Word k of a frame enters at T + k (pure RTL
// time base) and leaves the macro read port at T + 56 + k.  The words and the corrections reach ot_s81_kp4_dout over
// the same number of tile seams (dsyn -> ddly -> dout, dsyn -> dchn -> dout), so DD does not depend on the seam
// latency.  The tile's pin registers register w_d and r_d; r_d is the macro read port itself.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_ddly #(parameter integer DD = 55) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [543:0]  w_d,
    output wire [543:0]  r_d
);
    wire [0:0] rs_n;
    ot_s81_kp4_rst #(.NL(1)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    reg  [5:0] ptr;
    always @(posedge clk) if (!rs_n[0]) ptr <= 6'd0; else ptr <= ptr + 6'd1;
    wire [5:0] rd_d = ptr - DD[5:0];
    wire [545:0] d_rd;
    ot_sram_1r1w2c_64x546_m1 u_dmem (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(rd_d), .rd_out(d_rd),
        .w_ce_in(1'b1), .w_addr_in(ptr), .wd_in({2'b00, w_d}), .w_mask_in({546{1'b1}}));
    assign r_d = d_rd[543:0];
endmodule
