`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, HKV-HROOTK2 2026-10-19 (OT_KV_HROOT_LAND=1): the stack root tile qkd_kvs_hroot with EVERY PIN REGISTERED
// AT ITS FACE (owner rules: register every tile pin; cycles acceptable; reach 405 um with repeaters inside registered hops).
// The kit qkd_kvs_hroot_k1-6355d06bd closed (TT +77.62 / FF +16.39) but failed the native pin audit: the single-flop
// feed-through relays sat mid-span (capture 452.7 ps at i_ctl[5], launch 418.4 ps) and the es edge word h reached the
// chain-head register through the head() logic (no capture flop at the i_ctl pins).
//
//   qkd_kv_stack_relays_l  = qkd_kv_stack_relays with TWO register stages per word: a capture register at the input
//                            pin (fan from i_ctl[HW +: FW], g from i_g, r from i_r) and a launch register at the output
//                            pin(s).  The wire between them is one full reg -> reg cycle (repeated, <= ~512 um).
//                            Every relay word is ONE EDGE LATER than qkd_kv_stack_relays.
//   qkd_kv_es_fan_stack_bl = a capture register on h (beside the i_ctl pins) + qkd_kv_es_fan_stack_b (its chain-head
//                            register d is the o_pc launch register).  The strap 'stack' is registered too (a die
//                            constant: no age).  d is qkd_kv_es_fan_stack_b's d ONE EDGE LATER.
//
// Exactness: pure delay; tools/qwen_kv_die/hroot_land_bench.py checks the landed tile in lockstep against the unlanded
// tile fed with every data input one edge late (all outputs equal every edge).  Compiler: +1 edge on each hroot word
// (kv_static_die.HROOT_LAND_EDGES).  Static: no credit, ready, wait or arbitration.
// MUT (bench only): relays_l 1 = the fan word one bit low, 2 = the r word not landed (one stage);
//                   es_fan_stack_bl 1 = stack compare bit 0 inverted (inner), 2 = h not landed.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kv_stack_relays_l #(parameter integer HW = 783, FW = 1, GW = 1, RW = 1, MUT = 0) (
    input  wire            ck,
    input  wire [HW+FW-1:0] dn,
    input  wire [GW-1:0]   g_i,
    input  wire [RW-1:0]   r_i,
    output reg  [FW-1:0]   fan,
    output reg  [GW-1:0]   g,
    output reg  [RW-1:0]   r
);
    reg [FW-1:0] fan_c;     // capture registers (input pins)
    reg [GW-1:0] g_c;
    reg [RW-1:0] r_c;
    always @(posedge ck) begin
        fan_c <= dn[HW - ((MUT == 1) ? 1 : 0) +: FW];
        g_c <= g_i;
        r_c <= r_i;
        fan <= fan_c;       // launch registers (output pins)
        g <= g_c;
        r <= (MUT == 2) ? r_i : r_c;
    end
endmodule

module qkd_kv_es_fan_stack_bl #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [1:0]      stack,         // identity strap: WS 0, WN 1, ES 2, EN 3
    input  wire [783:0]    h,
    output wire [779:0]    d
);
    reg [783:0] h_c;        // capture registers (i_ctl pins)
    reg [1:0]   s_c;
    always @(posedge ck) begin
        h_c <= h;
        s_c <= stack;
    end
    qkd_kv_es_fan_stack_b #(.MUT(MUT == 1 ? 1 : 0)) u_st (.ck(ck), .rst_n(rst_n), .stack(s_c),
                                                          .h((MUT == 2) ? h : h_c), .d(d));
endmodule
