`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// q13-ectl 2026-10-13: the Qwen3-8B ROM TP8 die cell `qkd_ectl` (contract results/arch/hier_contract_1012/
// qwen_rom_tp8.json v3, 32 slots ectl_*): the near-HBM row-engine control tile ot_qwen_nearhbm_ectl_h behind the
// contract's aggregated pin names.  Wiring only (no logic, no register): every bus is the LSB-first concatenation of
// the RTL ports in the order of tools/qwen_kv_die/kv_die.py BINDINGS['qkd_ectl'] (the head tile's ti / e / s words use
// the same order), so the hardened view carries exactly the slot's pins:
//   S: e0 e1 s0 s1 t0 rst_n   N: e2 e3 s2 s3 t1 ck   W: rq rs   E: si so
//   t0 / t1 [1558:0] = {q_data 512, q_beat 6, q_valid, lt 12, row 1024, c 4}       (heads 0 / 1, heads 2 / 3)
//   e0..e3  [15:0]   = e of head 0..3                 s0..s3 [33:0] = {g_f, sc_f, sc 32} of head 0..3
//   rq [15:0] = {req_t 13, req_g, req_v, req_valid}   rs [1024:0] = {rsp_data 1024, rsp_valid}
//   si [633:0] = {nb_cr, er_data 64, exp_done 32, q_data 512, q_beat 6, q_valid, cyc8 3, T 14, start}
//   so [424:0] = {fault, v_done, k_done, nb_gam 4, nb_g, nb_beat 4, nb_valid, lmax_any 2, lmax 256, sc_data 128,
//                 sc_addr 12, sc_valid, er_addr 12, er_valid}
// The bench cycle markers ev_k_first / ev_v_first are debug-only and stay inside.  The slot structure of the control
// tile (pin stages, relays) is selected by `KVD_ECTL_SLOT, which this cell requires.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ectl #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 8,
    parameter integer E = 0,
    parameter integer DQ = 128
) (
    input  wire          ck,
    input  wire          rst_n,
    output wire [15:0]   e0, e1, e2, e3,
    input  wire [33:0]   s0, s1, s2, s3,
    output wire [1558:0] t0, t1,
    output wire [15:0]   rq,
    input  wire [1024:0] rs,
    input  wire [633:0]  si,
    output wire [424:0]  so
);
`ifndef KVD_ECTL_SLOT
    initial begin $display("qkd_ectl: build with +define+KVD_ECTL_SLOT"); $finish; end
`endif
    wire        ev_k_first, ev_v_first;
    ot_qwen_nearhbm_ectl_h #(.HD(HD), .S(S), .R(R), .E(E), .DQ(DQ)) u_ectl (
        .clk(ck), .rst_n(rst_n),
        .start_in(si[0]), .T_in(si[14:1]), .cyc8_in(si[17:15]), .q_valid_in(si[18]), .q_beat_in(si[24:19]),
        .q_data_in(si[536:25]), .exp_done(si[568:537]), .er_data(si[632:569]), .nb_cr(si[633]),
        .req_valid(rq[0]), .req_v(rq[1]), .req_g(rq[2]), .req_t(rq[15:3]),
        .rsp_valid_in(rs[0]), .rsp_data_in(rs[1024:1]),
        .er_valid(so[0]), .er_addr(so[12:1]), .sc_valid(so[13]), .sc_addr(so[25:14]), .sc_data(so[153:26]),
        .lmax(so[409:154]), .lmax_any(so[411:410]), .nb_valid(so[412]), .nb_beat(so[416:413]), .nb_g(so[417]),
        .nb_gam(so[421:418]), .k_done(so[422]), .v_done(so[423]), .fault(so[424]),
        .ev_k_first(ev_k_first), .ev_v_first(ev_v_first),
        .t0_c(t0[3:0]), .t0_row(t0[1027:4]), .t0_lt(t0[1039:1028]), .t0_qv(t0[1040]), .t0_qb(t0[1046:1041]),
        .t0_qd(t0[1558:1047]),
        .t1_c(t1[3:0]), .t1_row(t1[1027:4]), .t1_lt(t1[1039:1028]), .t1_qv(t1[1040]), .t1_qb(t1[1046:1041]),
        .t1_qd(t1[1558:1047]),
        .t0_e({e1, e0}), .t1_e({e3, e2}),
        .ts0_sc({s1[31:0], s0[31:0]}), .ts0_sf({s1[32], s0[32]}), .ts0_gf({s1[33], s0[33]}),
        .ts1_sc({s3[31:0], s2[31:0]}), .ts1_sf({s3[32], s2[32]}), .ts1_gf({s3[33], s2[33]}));
endmodule
