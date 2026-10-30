// ---------------------------------------------------------------------------
// 1.2 GHz (0.833 ns at ASAP7 SS, 60 ps setup uncertainty) binary32 add and multiply for the DS HBM accelerator's
// serial unit (ot_hdc_v41x_vec, hbm-fmax-su 2026-10-04).  Bit for bit and cycle for cycle (at their LAT) the
// adder of ot_hdc_fp32_add_fast / ot_hdc_fp32_add_lat and the multiplier of ot_hdc_fp32_mul_fast /
// ot_hdc_fp32_mul_lat (rtl/test/tb_su_fp32_f12.sv); only the register boundaries move.
//
// Every cut point is optional (CUTS bit k, LAT = 1 + popcount(CUTS)); the output register is always there.
//   adder      bit 0  after the decode / magnitude compare / exponent differences        (= add_lat C_A)
//              bit 1  after the alignments and the swap pick                             (= add_lat s1)
//              bit 2  after the 28-bit sum and difference                                 (= add_lat C_B)
//              bit 3  after the sentinel leading-zero count                               (= add_lat C_D)
//              bit 4  after the cancellation shift and the exponent adjust                (= add_lat s2)
//              bit 5  after the rounding increment                                        (= add_lat C_C)
//              bit 6  after the decode and the exponent differences, BEFORE the magnitude compare (new; the lane's
//                     LAT-5 adder 7'b1101010: lane operand mux + decode + differences | compare, alignments, swap |
//                     add, LZC | shift, round | encode)
//     add_lat LAT 3 is CUTS 6'b010010; the f12 LAT-4 adder is 6'b101010: decode..swap | add, LZC | shift,
//     round | encode -- the rounding increment moves in front of s2 so the encode stage carries only the
//     exponent carry and the refusals.
//   multiplier bit 0  after the decode and the fraction leading-zero counts (new)
//              bit 1  after the normalise shift and the powers                           (= mul_lat C1)
//              bit 2  after the AND rows and three carry-save levels (24 -> 8)            (= mul_lat s1)
//              bit 3  after two more carry-save levels (8 -> 4) (new)
//              bit 4  after four carry-save levels (8 -> 2) and the masks                 (= mul_lat C2)
//              bit 5  after the 48-bit prefix add                                         (= mul_lat s2)
//              bit 6  after the select / subnormal shift / round and sticky bits          (= mul_lat C3)
//              bit 7  after the rounding increment                                        (= mul_lat C4)
//     mul_lat LAT 3 is CUTS 8'b00100100; the f12 LAT-5 multiplier is 8'b01101010.
// Timing changes that keep the function: the subnormal input normalisation counts the FRACTION's leading zeros
// (a_lz = 1 + clz23(frac) below an exponent field of 0: the same count, the field decode off the count's path);
// the multiplier's encode takes the two exponent fields and overflow flags (with and without the rounding
// carry) precomputed in the stage before; every increment is ot_hdc_inc_k (rtl/hdc/ot_hdc_prefix.sv); only
// the valid bits are reset (the data registers of add_lat / mul_lat cut bundles reset too: their contents
// never reach y without a valid, and y / err / valid_out reset as before).
// Needs rtl/hdc/ot_hdc_fastfp.sv (ot_hdc_lzc32, ot_hdc_mul24_rows) and rtl/hdc/ot_hdc_prefix.sv.
// ---------------------------------------------------------------------------

// a W-bit bundle with its valid bit (bit W-1), registered when CUT = 1 (the valid reset to 0), else a wire
module ot_hdc_f12_cut #(parameter integer W = 2, parameter integer CUT = 0) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT) begin : g_r
        reg         v;
        reg [W-2:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) v <= 1'b0;
            else v <= d[W-1];
        end
        always @(posedge clk) r <= d[W-2:0];
        assign q = {v, r};
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule
