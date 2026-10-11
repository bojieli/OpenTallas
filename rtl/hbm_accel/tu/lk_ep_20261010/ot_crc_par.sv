`timescale 1ns/1ps
// ot_crc_par ([link] 2026-10-10): parallel CRC as a balanced XOR matrix.  crc[k] = ^(d & MASK_k) ^ CST[k], where the masks
// are the LFSR's linear map computed at elaboration (MSB-first, the same CRC as the serial loop c = {c, 0} ^ (c[N-1] ^ d[i]
// ? POLY : 0) from INIT).  The serial-loop form synthesised as a ~W-deep chain (hfd_lk_ep ac60951fc preroute
// a_h -> b_f -4,178 ps); this form is ceil(log2(W)) XOR levels.
module ot_crc_par #(
    parameter integer W = 583,
    parameter integer N = 14,
    parameter [N-1:0] POLY = 14'h0805,
    parameter [N-1:0] INIT = {N{1'b1}}
) (
    input  wire [W-1:0] d,
    output wire [N-1:0] crc
);
    // m[j] = mask of data bits feeding state bit j; s[j] = constant part (from INIT)
    function automatic [N*W+N-1:0] lfsr_map(input integer dummy);
        reg [N*W-1:0] m, nm;
        reg [N-1:0] s, ns;
        reg [W-1:0] fbm; reg fbs;
        integer i, j;
        begin
            m = {N*W{1'b0}};
            s = INIT;
            for (i = W - 1; i >= 0; i = i - 1) begin
                fbm = m[(N-1)*W +: W]; fbm[i] = ~fbm[i]; fbs = s[N-1];
                nm = {m[(N-1)*W-1:0], {W{1'b0}}};
                ns = {s[N-2:0], 1'b0};
                for (j = 0; j < N; j = j + 1) if (POLY[j]) begin nm[j*W +: W] = nm[j*W +: W] ^ fbm; ns[j] = ns[j] ^ fbs; end
                m = nm; s = ns;
            end
            lfsr_map = {s, m};
        end
    endfunction
    localparam [N*W+N-1:0] MAP = lfsr_map(0);
    genvar k;
    generate for (k = 0; k < N; k = k + 1) begin : g_b
        assign crc[k] = (^(d & MAP[k*W +: W])) ^ MAP[N*W + k];
    end endgenerate
endmodule
