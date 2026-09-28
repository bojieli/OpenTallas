`timescale 1ns/1ps
// One packed V4.1 QE word, assembled from physical 256-bit sectors in
// increasing sector address order, to the core's 16-lane x 272-bit port.
// FP8 requires 17 sectors and is unchanged. FP4 requires 9 sectors; each
// lane's 16 low-nibble-first code bytes expand into 32 zero-extended code
// bytes, followed by the checkpoint's signed 16-bit block exponent.
//
// This is combinational to preserve the QE's one-cycle ROM-read contract when
// driven by a synchronous macro. Its path from macro Q through expansion to
// the core is NOT characterized or timed by this module's functional gate.
// A cluster must place/route it beside its local QE port and prove timing.
module ot_hdc_v41x_qe_sector_expand (
    input  wire          in_valid,
    input  wire          in_fp4,
    input  wire [16:0]   in_sector_valid,
    input  wire [4351:0] in_packed,
    output wire          out_valid,
    output wire          out_fault,
    output reg  [4351:0] out_word
);
    wire sectors_ok = in_fp4 ? (&in_sector_valid[8:0]) : (&in_sector_valid);
    assign out_valid = in_valid && sectors_ok;
    assign out_fault = in_valid && !sectors_ok;
    integer lane, col;
    always @* begin
        out_word = 4352'b0;
        if (out_valid) begin
            if (!in_fp4) out_word = in_packed;
            else begin
                for (lane = 0; lane < 16; lane = lane + 1) begin
                    for (col = 0; col < 32; col = col + 1)
                        out_word[lane*272 + col*8 +: 4] = in_packed[lane*144 + col*4 +: 4];
                    out_word[lane*272 + 256 +: 16] = in_packed[lane*144 + 128 +: 16];
                end
            end
        end
    end
endmodule
