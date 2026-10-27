`timescale 1ns/1ps
// MU-QWEN-HOST 10-18: per-user KV base on the Qwen KV die (4-slot static calendar), two new combinational leaves.
//
// Today the KV row is hardwired: write row = 64 + layer (qkd_kv_static_writer :85, expected_address [28:10]) and the
// read row = ROW0 64 + layer (qkd_controller_hbm_calendar active_row, carried in the 43-bit static_cmd).  No job word,
// layer programme or calendar word carries a base, and the host's kv_base never reaches the KV die, so "absolute
// per-user bases in the job word" would need new fields in closed leaves.  Instead user u's rows sit at a fixed
// 256-row stride: row = 64 + layer + 256*u (u < 4: rows 64..99, 320..355, 576..611, 832..867; the embedding table
// starts at row 24,427).  Because every KV row is < 256, the base is a pure bit insertion into row[9:8] (no adder,
// no carry, no added logic depth), and row[7:0] is unchanged, so the closed qkd_ctrl_pc_host_static_core read-return
// tag (row[7:0] - ROW0 = layer) stays exact.  Bytes a user a KV die: 36 x 8,192 x 2 x 128 B = 72 MiB; 4 users 288 MiB.
//
//   qkd_kv_mu_wrow: write side, between qkd_kv_static_writer (es lanes, expected_address) and the es fan-out / the
//                   native writer's expected-address check (parent qkd_kvs_ctl, RTL-only).
//   qkd_kv_mu_rrow: read side, between qkd_controller_hbm_calendar.static_cmd and the PC controller (parent
//                   qkd_static_kv_pc_path_nc, RTL-only); offsets only KV descriptors (op 0 desc / 3 context desc) whose
//                   row is a KV row (row[18:8] == 0), never embedding rows, go or write commands.
// user: the user whose stage the writer / calendar is serving, held for the stage (from the host step's user, which
// ot_qfd_pkgctl MU puts on hc pos[17:16]).  MU 0: both leaves are wires (bit-identical to today).
// range_fault (comb): a write row outside the KV window (row[18:8] != 0) under MU -- the compiler's row map broke.
module qkd_kv_mu_wrow #(parameter integer MU = 0, parameter integer NL = 4) (
    input  wire [1:0]        user,
    input  wire [NL*288-1:0] es_i,
    input  wire [28:0]       xa_i,          // expected_address {row19, bank5, column5}
    output wire [NL*288-1:0] es_o,
    output wire [28:0]       xa_o,
    output wire              range_fault
);
    wire [1:0] u = (MU != 0) ? user : 2'd0;
    genvar q;
    wire [NL-1:0] hi;
    generate for (q = 0; q < NL; q = q + 1) begin : g_lane
        // lane = {s_v, s_we, addr29 = {bank5, column5, row19}, data256, w_v}; row = lane[275:257]
        assign es_o[q*288 +: 257]       = es_i[q*288 +: 257];
        assign es_o[q*288+257 +: 8]     = es_i[q*288+257 +: 8];
        assign es_o[q*288+265 +: 2]     = es_i[q*288+265 +: 2] | u;
        assign es_o[q*288+267 +: 21]    = es_i[q*288+267 +: 21];
        assign hi[q] = es_i[q*288] && es_i[q*288+265 +: 11] != 0;
    end endgenerate
    assign xa_o = {xa_i[28:20], xa_i[19:18] | u, xa_i[17:0]};
    assign range_fault = (MU != 0) && (|hi);
endmodule

module qkd_kv_mu_rrow #(parameter integer MU = 0) (
    input  wire [1:0]  user,
    input  wire [42:0] cmd_i,               // {first sector10, command32 = {op2, n11, row19}, bit0}
    output wire [42:0] cmd_o
);
    wire [1:0]  op  = cmd_i[32:31];
    wire [18:0] row = cmd_i[19:1];
    wire kv = (MU != 0) && (op == 2'd0 || op == 2'd3) && row[18:8] == 0;
    assign cmd_o = {cmd_i[42:11], cmd_i[10:9] | (kv ? user : 2'd0), cmd_i[8:0]};
endmodule
