`timescale 1ns/1ps
// Combinational stage4 subnormal encoder; no state, clock or engine-interface change.
// PREPARE ONLY: contextual stage4 SS/FF/slot closure OPEN. The caller handles nf/zero/overflow/normal.
module ot_v41_bmul_subnormal_rne_prepare (
    input wire sign_i,
    input wire signed [10:0] biased_i,
    input wire [23:0] sig_i,
    output wire [31:0] y
);
    wire signed [10:0] shift_full = 11'sd1 - biased_i;
    wire in_range = shift_full >= 11'sd1 && shift_full <= 11'sd24;
    // Classify at full signed width before narrowing. Invalid shifts use safe indexes.
    wire [4:0] shift_q = in_range ? shift_full[4:0] : 5'd1;
    wire [4:0] guard_index = shift_q - 5'd1;
    wire [23:0] retained = in_range ? (sig_i >> shift_q) : 24'd0;
    wire guard_bit = in_range && sig_i[guard_index];
    wire [23:0] sticky_terms;
    genvar k;
    generate for(k=0;k<24;k=k+1) begin : g_sticky
        assign sticky_terms[k] = in_range && (k < guard_index) && sig_i[k];
    end endgenerate
    wire sticky_bit = |sticky_terms;
    wire increment = guard_bit && (sticky_bit || retained[0]);
    wire [23:0] rounded;
    wire rounded_co;
    ot_v41_inc #(.W(24)) u_round (.a(retained), .inc(increment), .y(rounded), .co(rounded_co));
    // rounded[23] naturally encodes minimum normal; exact/underflow zero is canonical+0.
    assign y = (!in_range || rounded == 24'd0) ? 32'd0 : {sign_i, 7'd0, rounded};
endmodule
