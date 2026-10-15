`timescale 1ns/1ps

// Physical face omits duplicate buses and full-mask/native constants.
// Native full-sector intent is a semantic property of this master, checked
// against the underlying source at every physical write in its bench.
module qkd_kv_static_writer_native #(parameter integer MUT = 0) (
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
    qkd_kv_static_writer #(.MUT(MUT)) u_writer (
        .ck(ck),
        .rst_n(rst_n),
        .word_valid(word_valid),
        .word_tag(word_tag),
        .word_data(word_data),
        .word_identity(word_identity),
        .word_generation(word_generation),
        .compiled_word_slot(compiled_word_slot),
        .compiled_word_index(compiled_word_index),
        .compiled_identity(compiled_identity),
        .compiled_generation(compiled_generation),
        .es(es),
        .dest_pc(dest_pc),
        .dest_stack(dest_stack),
        .identity(identity),
        .generation(generation),
        .expected_valid(expected_valid),
        .expected_pc(expected_pc),
        .expected_stack(expected_stack),
        .expected_identity(expected_identity),
        .expected_generation(expected_generation),
        .expected_address(expected_address),
        .fault(fault),
        .fault_code(fault_code),
        .write_mask(), .native_kv(), .es_context(), .es_expected_identity());
endmodule
