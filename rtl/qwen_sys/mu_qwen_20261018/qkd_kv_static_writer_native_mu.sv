`timescale 1ns/1ps
// MU-ADOPT-KV 10-19 (R6 write side, coordinator 0jc): the KV die's static writer role with the per-user KV row.
// The CLOSED writer qkd_kv_static_writer_native is instantiated unchanged; qkd_kv_mu_wrow sits between its es lanes /
// expected_address and the es fan-out (qkd_kv_es_fan_root2_b) + the PCs' native expected-address check.  This wrapper is
// glue of the RTL-only parent qkd_kvs_ctl (the tile generator binds it for the writer role under OT_KV_MU=1), so no
// closed tile changes.  Same ports as qkd_kv_static_writer_native (drop-in role).
//
// Stage user (latched per stage, no new die wire): the user rides in the TAG59 epoch, epoch[1:0] = user (identity bits
// [44:43]; TAG59 = {epoch16, stage6, token18, position13, segment6}).  The host step's user (ot_qfd_pkgctl MU, hc
// pos[17:16]) is put there by the epoch allocator under MU (host contract, see results/rtl/mu_qwen_1018/kv/README.md).
// The writer captures identity / es / expected_* on the same edge of each accepted word, so the user of every es word is
// its own identity's epoch[1:0], and the user of expected_address its own expected_identity's epoch[1:0] (each is the
// stage's latched value, held until the next accepted word).  MU 0: wires (bit-identical to the plain writer role).
// range_fault (a KV write row outside the KV window under MU) sets a sticky flop ORed into fault / fault_code[7] (the
// writer uses code bits [4:0]; its own bits are unchanged).
module qkd_kv_static_writer_native_mu #(parameter integer MUT = 0, parameter integer VMAP = 0, parameter integer MU = 0,
    parameter integer RST_COPIES = 1) (
    input wire ck, rst_n,
    input wire word_valid, input wire [10:0] word_tag,
    input wire [511:0] word_data,
    input wire [58:0] word_identity, input wire [1:0] word_generation,
    input wire compiled_word_slot, input wire [1:0] compiled_word_index,
    input wire [58:0] compiled_identity, input wire [1:0] compiled_generation,
    output wire [4*288-1:0] es,
    output wire [4*5-1:0] dest_pc, output wire [1:0] dest_stack,
    output wire [58:0] identity, output wire [1:0] generation,
    output wire [3:0] expected_valid,
    output wire [4*5-1:0] expected_pc, output wire [1:0] expected_stack,
    output wire [58:0] expected_identity, output wire [1:0] expected_generation,
    output wire [28:0] expected_address,
    output wire fault, output wire [7:0] fault_code
);
    wire [4*288-1:0] es_w;
    wire [28:0] xa_w;
    wire f_w;
    wire [7:0] fc_w;
    qkd_kv_static_writer_native #(.MUT(MUT), .VMAP(VMAP), .RST_COPIES(RST_COPIES)) u_wrn (
        .ck(ck), .rst_n(rst_n), .word_valid(word_valid), .word_tag(word_tag), .word_data(word_data),
        .word_identity(word_identity), .word_generation(word_generation), .compiled_word_slot(compiled_word_slot),
        .compiled_word_index(compiled_word_index), .compiled_identity(compiled_identity),
        .compiled_generation(compiled_generation), .es(es_w), .dest_pc(dest_pc), .dest_stack(dest_stack),
        .identity(identity), .generation(generation), .expected_valid(expected_valid), .expected_pc(expected_pc),
        .expected_stack(expected_stack), .expected_identity(expected_identity),
        .expected_generation(expected_generation), .expected_address(xa_w), .fault(f_w), .fault_code(fc_w));
    wire rf_es, rf_xa;
    wire [4*288-1:0] es_unused;
    wire [28:0] xa_unused;
    // es lanes: user = the es word's identity epoch[1:0]
    qkd_kv_mu_wrow #(.MU(MU), .NL(4)) u_mu_es (.user(identity[44:43]), .es_i(es_w), .xa_i(xa_w),
        .es_o(es), .xa_o(xa_unused), .range_fault(rf_es));
    // expected address: user = the expected identity's epoch[1:0]
    qkd_kv_mu_wrow #(.MU(MU), .NL(4)) u_mu_xa (.user(expected_identity[44:43]), .es_i(es_w), .xa_i(xa_w),
        .es_o(es_unused), .xa_o(expected_address), .range_fault(rf_xa));
    // sticky range fault (MU 0: constant 0, no flop survives synthesis)
    reg rf_q;
    always @(posedge ck or negedge rst_n) if (!rst_n) rf_q <= 1'b0; else if (rf_es) rf_q <= 1'b1;
    assign fault = f_w | rf_q;
    assign fault_code = {fc_w[7] | rf_q, fc_w[6:0]};
endmodule
