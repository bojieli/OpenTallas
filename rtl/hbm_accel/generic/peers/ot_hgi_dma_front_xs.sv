`timescale 1ns/1ps
`default_nettype none
// el1011-hbm-dmafs 2026-10-12: X2 crossbar SLICE tile of ot_hgi_dma_front (two-level split; hardened once, 4 instances of
// 8 banks).  Per bank: input pin flops (pick xo, lane buffers ls) -> AND-OR rung x2s -> select rung (quarter of the
// source sector by the bank's slot) -> conversion (BF16 << 16, E4M3 exact, NaN -> 0x7FC00000, INT8 exact) -> output
// register at the face; exactly the XP=1 XQ=1 AP=0 X2 of ot_hgi_dma_front, one cycle later.  The format arrives with
// each lane buffer (ls {fmt 3, sector 18, source 256}), so each bank decodes its own registered format.
// Bank b of a slice is VM bank 8s + b: only (bank mod 4) matters (the slot), so all slices are identical.
module ot_hgi_dma_front_xs #(
    parameter integer NIN = 8,
    parameter integer NBS = 8,
    parameter integer MUT = 0
) (
    input  wire                  clk,
    input  wire [NBS*NIN-1:0]    xo,
    input  wire [NIN*277-1:0]    ls,
    output wire [NBS*279-1:0]    wd
);
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
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
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [255:0] conv(input [255:0] s, input [2:0] f, input [1:0] j);
        reg [255:0] o; integer w; reg [7:0] b; reg [15:0] h;
        begin
            o = 256'd0;
            for (w = 0; w < 8; w = w + 1) begin
                case (f)
                    3'd1: begin h = s[({3'd0, j} * 8 + w) * 16 +: 16]; if (MUT == 1) h = s[({3'd0, j} * 8 + (7 - w)) * 16 +: 16];
                                o[w*32 +: 32] = {h, 16'd0}; end
                    3'd2: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = e4m3_f(b); end
                    3'd4: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = i8_f(b); end
                    default: o[w*32 +: 32] = s[w*32 +: 32];
                endcase
            end
            conv = o;
        end
    endfunction
    reg [NBS*NIN-1:0] xo_q; reg [NIN*277-1:0] ls_q;          // input pin flops (data: no reset)
    always @(posedge clk) begin xo_q <= xo; ls_q <= ls; end
    genvar b;
    generate for (b = 0; b < NBS; b = b + 1) begin : bk
        reg [276:0] x2s; reg [255:0] p_s; reg [17:0] p_s18; reg [2:0] p_f; reg [278:0] wl_d, wo_d;
        assign wd[b*279 +: 279] = wo_d;
        always @(posedge clk) begin : x2
            reg [276:0] sv; reg [1:0] e; reg [255:0] x2d; reg [2:0] f;
            sv = 277'd0;
            for (integer i = 0; i < NIN; i = i + 1) if (xo_q[b*NIN + i]) sv = sv | ls_q[i*277 +: 277];
            x2s <= sv;
            x2d = x2s[255:0]; f = x2s[276:274];
            e = 2'(b) - x2s[257:256];
            p_s18 <= x2s[273:256] + {16'd0, e};
            p_f <= f;
            p_s <= (f == 3'd1) ? {128'd0, x2d[{e, 7'd0} +: 128]} :
                   (f == 3'd2 || f == 3'd4) ? {192'd0, x2d[{e, 6'd0} +: 64]} : x2d;
            wl_d <= {p_s18[14:0], conv(p_s, p_f, 2'd0), 8'hFF};
            wo_d <= wl_d;
        end
    end endgenerate
endmodule
`default_nettype wire
