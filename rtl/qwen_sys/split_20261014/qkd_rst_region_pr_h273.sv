`timescale 1ns/1ps
// KV-HEALTH 10-19: the regional reset root of the MU release die with the sized hold (owner 10-19: "size the HOLD
// counters for 273, no 8-bit wrap; default-on for the MU release build").  A re-asserted host reset keeps the region low
// for >= 273 core edges, which covers the 263-edge requirement of the per-layer health retirement contract (fault-source
// clear + longest health-plane path + 64 cross-root skew; kv_retirement_contract.py) -- HOLD 128 is no proof for a
// 197-edge plane.  Same ports / straps / release calendar as qkd_rst_region_pr; only HOLD differs (9-bit hold counter).
module qkd_rst_region_pr_h273 #(parameter integer MUT = 0) (
    input  wire       ck,
    input  wire       por_n,
    input  wire       a,
    input  wire [7:0] dly,
    output wire       b
);
    localparam integer HOLD_EFF = (MUT == 4) ? (273 & 255) : 273;
    qkd_rst_region_pr #(.IGNORE(255), .HOLD(HOLD_EFF), .MUT((MUT == 4) ? 0 : MUT), .DW(8)) u_pr (
        .ck(ck), .por_n(por_n), .a(a), .dly(dly), .b(b));
endmodule
