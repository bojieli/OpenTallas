`timescale 1ns/1ps
// KV-DOMSPLIT 2026-10-19: landing of W independent, quasi-static LEVEL status bits launched in another clock domain
// (the boot CDCs' sticky applied_hbm / fault_hbm, hck) into the core clock ck of the tile that gathers them, so the gather
// word leaving the tile is single-domain (owner clocking standard: no unlanded cross-domain relay).  Each bit crosses
// independently through a 2-flop async_reg synchroniser (no multi-bit value is reconstructed: every bit is a sticky level
// whose consumer is itself a level observer).  Latency: +2 ck edges.  Reset: asynchronous assert on the core reset.
// MUT (benches only): 1 = one flop stage (a 1-edge landing), 2 = bit 0 not landed (passed through combinationally).
module qkd_kv_lvl_land #(parameter integer W = 1, parameter integer MUT = 0) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    (* async_reg = "true" *) reg [W-1:0] s1;
    (* async_reg = "true" *) reg [W-1:0] s2;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            s1 <= {W{1'b0}};
            s2 <= {W{1'b0}};
        end else begin
            s1 <= d;
            s2 <= s1;
        end
    end
    generate
        if (MUT == 1) begin : g_m1
            assign q = s1;
        end else if (MUT == 2) begin : g_m2
            if (W > 1) begin : g_w
                assign q = {s2[W-1:1], d[0]};
            end else begin : g_1
                assign q = d;
            end
        end else begin : g_land
            assign q = s2;
        end
    endgenerate
endmodule
