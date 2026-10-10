`timescale 1ns/1ps
`default_nettype none
// HGI-1 VM-512 helpers (hgi-1010/f, 2026-10-10): one sector = 8 FP32 words, each with its own (39,32) SECDED code
// (the H matrix of ot_hgi_vm_core: data bit i -> the i-th 7-bit column of weight 3; check-bit errors have weight-1
// syndromes).  ot_hgi_vm_enc8: 256 data -> 312 stored bits (word w at [39w +: 39] = {chk 7, data 32}).
// ot_hgi_vm_dec8: 312 stored -> 256 corrected data, per-word corrected (ce) and uncorrectable (ue) flags.
// MUT (bench): 1 = the decoder does not correct.
module ot_hgi_vm_enc8 (
    input  wire [255:0] d,
    output wire [311:0] q
);
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [7*32-1:0] rows_all(input integer dummy);
        integer i, j; reg [7*32-1:0] r; reg [6:0] cv;
        begin r = '0; for (i = 0; i < 32; i = i + 1) begin cv = colv(i); for (j = 0; j < 7; j = j + 1) r[j*32 + i] = cv[j]; end
              rows_all = r; end
    endfunction
    localparam [7*32-1:0] ROWM = rows_all(0);
    genvar w, j;
    for (w = 0; w < 8; w = w + 1) begin : g_w
        assign q[w*39 +: 32] = d[w*32 +: 32];
        for (j = 0; j < 7; j = j + 1) begin : g_c
            assign q[w*39 + 32 + j] = ^(d[w*32 +: 32] & ROWM[j*32 +: 32]);
        end
    end
endmodule

module ot_hgi_vm_dec8 #(
    parameter integer MUT = 0
) (
    input  wire [311:0] q,
    output reg  [255:0] d,
    output reg  [7:0]   ce,
    output reg  [7:0]   ue
);
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [32*7-1:0] cols_all(input integer dummy);
        integer i; reg [32*7-1:0] r;
        begin r = '0; for (i = 0; i < 32; i = i + 1) r[i*7 +: 7] = colv(i); cols_all = r; end
    endfunction
    localparam [32*7-1:0] COLS = cols_all(0);
    function automatic [7*32-1:0] rows_all(input integer dummy);
        integer i, j; reg [7*32-1:0] r;
        begin r = '0; for (j = 0; j < 7; j = j + 1) for (i = 0; i < 32; i = i + 1) r[j*32 + i] = COLS[i*7 + j]; rows_all = r; end
    endfunction
    localparam [7*32-1:0] ROWM = rows_all(0);
    always @* begin
        for (integer w = 0; w < 8; w = w + 1) begin : g_w
            reg [6:0] syn; reg [31:0] x; reg hit;
            x = q[w*39 +: 32];
            for (integer j = 0; j < 7; j = j + 1) syn[j] = ^(x & ROWM[j*32 +: 32]) ^ q[w*39 + 32 + j];
            hit = 1'b0;
            for (integer i = 0; i < 32; i = i + 1)
                if (syn == COLS[i*7 +: 7]) begin if (MUT != 1) x[i] = ~x[i]; hit = 1'b1; end
            if (syn == 7'd1 || syn == 7'd2 || syn == 7'd4 || syn == 7'd8 || syn == 7'd16 || syn == 7'd32 || syn == 7'd64)
                hit = 1'b1;
            d[w*32 +: 32] = x;
            ce[w] = (syn != 7'd0) && hit;
            ue[w] = (syn != 7'd0) && !hit;
        end
    end
endmodule

// One destination sector of a DMA beat: chunk k of the raw source sector, converted to 8 FP32 words (spec 6.5;
// machine.py decode_fmt).  fmt 0 FP32 / 5 U32: the sector unchanged (k must be 0); 1 BF16: halfwords 8k .. 8k+7 widened;
// 2 FP8E4M3 / 4 INT8 / 6 UE8M0: bytes 8k .. 8k+7; 3 FP4E2M1: nibbles 8k .. 8k+7 (byte 4k + w/2, low nibble first).
// UE8M0 x -> 2^(x - 127) (x = 255 -> NaN 0x7FC00000; x = 0 -> 2^-127 = 0x00400000).
// MUT (bench): 5 BF16 chunk k^1; 6 E4M3 subnormal exponent off by one; 9 UE8M0 x = 0 -> +0.
module ot_hgi_vm_conv8 #(
    parameter integer MUT = 0
) (
    input  wire [255:0] raw,
    input  wire [2:0]   fmt,
    input  wire [2:0]   k,
    output reg  [255:0] o
);
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (integer b = 0; b < 8; b = b + 1) if (a[b]) p = b[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p} + ((MUT == 6) ? 8'd1 : 8'd0),
                              ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [31:0] ue8_f(input [7:0] x);
        if (x == 8'hFF) ue8_f = 32'h7FC00000;
        else if (x == 8'd0) ue8_f = (MUT == 9) ? 32'd0 : 32'h00400000;
        else ue8_f = {1'b0, x, 23'd0};
    endfunction
    function automatic [31:0] fp4_f(input [3:0] c);
        reg [1:0] e; reg m;
        begin
            e = c[2:1]; m = c[0];
            if (e == 2'd0) fp4_f = m ? {c[3], 31'h3F000000} : {c[3], 31'd0};
            else fp4_f = {c[3], 8'd126 + {6'd0, e}, m, 22'd0};
        end
    endfunction
    always @* begin
        reg [2:0] kk; reg [7:0] b; reg [15:0] h; reg [3:0] n;
        kk = (MUT == 5 && fmt == 3'd1) ? (k ^ 3'd1) : k;
        o = 256'd0;
        for (integer w = 0; w < 8; w = w + 1) begin
            b = raw[({6'd0, kk[1:0]} * 8 + w) * 8 +: 8];
            h = raw[({5'd0, kk[0]} * 8 + w) * 16 +: 16];
            n = raw[({5'd0, kk} * 8 + w) * 4 +: 4];
            case (fmt)
                3'd1: o[w*32 +: 32] = {h, 16'd0};
                3'd2: o[w*32 +: 32] = e4m3_f(b);
                3'd3: o[w*32 +: 32] = fp4_f(n);
                3'd4: o[w*32 +: 32] = i8_f(b);
                3'd6: o[w*32 +: 32] = ue8_f(b);
                default: o[w*32 +: 32] = raw[w*32 +: 32];
            endcase
        end
    end
endmodule
`default_nettype wire
