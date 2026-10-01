`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_link_crc32_pipe: the same CRC-32 in two register levels, for 1.2 GHz at
// SS.  The frame is cut into CHUNK-bit pieces; each piece's contribution to
// every CRC bit (the parity of its data bits under the constant mask) is
// computed and registered when en is high, and crc is the XOR of the
// registered partials with the init term -- a ceil(log2(W / CHUNK))-deep XOR
// after the register.  Linear, so bit-identical to ot_link_crc32 of the value
// d had at the en edge.  Latency: crc is valid the cycle after en.
// ---------------------------------------------------------------------------
module ot_link_crc32_pipe #(
    parameter integer W          = 64,
    parameter integer CHUNK      = 256,
    parameter integer MASK_MAX_W = 8192       // above: the serial definition, registered (simulation form, as
                                              // ot_link_crc32's; the very wide Qwen engine frames are never hardened)
) (
    input  wire         clk,
    input  wire         en,
    input  wire [W-1:0] d,
    output wire [31:0]  crc
);
    localparam integer NC = (W + CHUNK - 1) / CHUNK;
    localparam [31:0] POLY = 32'h04C1_1DB7;
    function automatic [31:0] step0(input [31:0] c);
        step0 = {c[30:0], 1'b0} ^ (c[31] ? POLY : 32'h0);
    endfunction
    function automatic [32*W-1:0] masks(input integer dummy);
        reg [31:0] e;
        integer b, i;
        begin
            masks = {32*W{1'b0}};
            e = POLY;
            for (b = 0; b < W; b = b + 1) begin
                for (i = 0; i < 32; i = i + 1) masks[i*W + b] = e[i];
                e = step0(e);
            end
        end
    endfunction
    function automatic [31:0] init_term(input integer dummy);
        reg [31:0] c;
        integer b;
        begin
            c = 32'hFFFF_FFFF;
            for (b = 0; b < W; b = b + 1) c = step0(c);
            init_term = c;
        end
    endfunction
    generate if (W <= MASK_MAX_W) begin : g_par
    localparam [32*W-1:0] M = masks(0);
    localparam [31:0]     I0 = init_term(0);
    reg [31:0] part [0:NC-1];
    genvar c, i;
    for (c = 0; c < NC; c = c + 1) begin : g_c
        localparam integer LO = c * CHUNK;
        localparam integer N = (W - LO < CHUNK) ? (W - LO) : CHUNK;
        wire [31:0] p;
        for (i = 0; i < 32; i = i + 1) begin : g_b
            assign p[i] = ^(d[LO +: N] & M[i*W + LO +: N]);
        end
        always @(posedge clk) if (en) part[c] <= p;
    end
    reg [31:0] x;
    integer k;
    always @(*) begin
        x = I0;
        for (k = 0; k < NC; k = k + 1) x = x ^ part[k];
    end
    assign crc = x;
    end else begin : g_ser
        function automatic [31:0] ser(input [W-1:0] v);
            integer b;
            reg [31:0] q;
            begin
                q = 32'hFFFF_FFFF;
                for (b = W - 1; b >= 0; b = b - 1) q = step0(q) ^ (v[b] ? POLY : 32'h0);
                ser = q;
            end
        endfunction
        reg [31:0] r;
        always @(posedge clk) if (en) r <= ser(d);
        assign crc = r;
    end endgenerate
endmodule
