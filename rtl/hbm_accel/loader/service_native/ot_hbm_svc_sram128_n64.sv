// LH-BW SAFE n64 (10-19): 128-entry x W-bit 1R1W store built from ceil(W/64) ot_sram_1r1w2c_128x64_m1 macros.
// Replaces the 128x256 r2c2 macro in the SAFE PC controller: that macro has 410/409 signal pins on its 41.064 um
// W/E faces (10 pins/um, SAFE item 6 limit 6/um) and most of its 256 data/mask bits were tied (79-, 30- and 21-bit
// words). The 128x64 macro has 105 pins per 27.576 um face (3.8 pins/um). Same synchronous registered read on the
// same edge, same write; both macro clocks are the one tile clock. Read and write of the same address on one edge is
// not relied upon (the controller forwards those cases); no added cycle.
// L2H-BW (10-19): P192=1 selects ot_sram_1r1w_128x64_m1_p192 (same generator, same TT/FF/SS timing, one clock pin,
// signal contacts spread at 0.192 um = 5.2 contacts/um on each W/E face; the 2c family packs 105 contacts at 0.096 um,
// 10.5/um locally, c1f1c2c0c).  P192=0 keeps the 2c macro byte-for-byte (default: all existing users unchanged).
module ot_hbm_svc_sram128_n64 #(parameter integer W = 64, parameter integer P192 = 0) (
    input  wire         clk,
    input  wire         r_ce,
    input  wire [6:0]   r_addr,
    output wire [W-1:0] rd,
    input  wire         w_ce,
    input  wire [6:0]   w_addr,
    input  wire [W-1:0] wd
);
    localparam integer N = (W + 63) / 64;
    wire [N*64-1:0] rd_pad;
    for (genvar i = 0; i < N; i = i + 1) begin : M
        // columns beyond W in the last macro are never written (mask 0) and never read
        wire [63:0] d, m;
        for (genvar j = 0; j < 64; j = j + 1) begin : B
            if (i * 64 + j < W) begin : U
                assign d[j] = wd[i*64+j]; assign m[j] = 1'b1;
            end else begin : Z
                assign d[j] = 1'b0; assign m[j] = 1'b0;
            end
        end
        if (P192 != 0) begin : P
            ot_sram_1r1w_128x64_m1_p192 u_m(
                .clk(clk),
                .r_ce_in(r_ce), .r_addr_in(r_addr), .rd_out(rd_pad[i*64 +: 64]),
                .w_ce_in(w_ce), .w_addr_in(w_addr), .wd_in(d), .w_mask_in(m));
        end else begin : C
            ot_sram_1r1w2c_128x64_m1 u_m(
                .wclk(clk), .rclk(clk),
                .r_ce_in(r_ce), .r_addr_in(r_addr), .rd_out(rd_pad[i*64 +: 64]),
                .w_ce_in(w_ce), .w_addr_in(w_addr), .wd_in(d), .w_mask_in(m));
        end
    end
    assign rd = rd_pad[W-1:0];
endmodule
