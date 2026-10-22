`timescale 1ns/1ps
// KV-BIND4 10-19: qkd_rst_region_pr_h273 with a dedicated output launch register (native-pin successor).
// Same ports / straps / faces / release calendar / HOLD 273 as qkd_rst_region_pr_h273 (bench: cycle-identical output);
// the core is qkd_rst_region_po (kept b_pin twin drives only pin b, b_int feeds the hold logic), so the output pin net
// carries no internal loads (h273 view: pin b launch 223.8 ps TT > 220 native budget).  dly straps: kept pin captures
// (as qkd_rst_region_pr).  MUT 4: legacy 8-bit hold truncation; MUT 5: pin twin one edge late (both must FAIL).
module qkd_rst_region_pr_h273b #(parameter integer MUT = 0) (
    input  wire       ck,
    input  wire       por_n,
    input  wire       a,
    input  wire [7:0] dly,
    output wire       b
);
    (* keep *) reg [7:0] dly_pin;
    always @(posedge ck) dly_pin <= dly;
    qkd_rst_region_po #(.IGNORE(255), .HOLD(273), .MUT((MUT == 4 || MUT == 5) ? MUT : 0), .DW(8)) u_core (
        .ck(ck), .por_n(por_n), .a(a), .dly(dly_pin), .b(b));
endmodule
