`timescale 1ns/1ps
// Additive explicit I8 source-profile delegate. Original converter is unchanged.
// a_type describes the carrier. (U8, a_signed_i8=1) is semantic I8, never U8.
// Pauli must capture/protect this mask and match independent immutable profile
// before GO. No profile may be inferred from bytes, shape or command offers.
module ot_gpu_native_conversion_i8 #(
    parameter ENABLE=0, parameter integer LANES=4
)(
    input wire [5:0] opcode,
    input wire [1:0] dtype,a_type,b_type,c_type,
    input wire a_scalar,b_scalar,c_scalar,
    input wire a_signed_i8,
    input wire [LANES-1:0] lane_mask,
    input wire [64*LANES-1:0] a_data,b_data,c_data,
    output wire [64*LANES-1:0] result,
    output wire [1:0] result_type,
    output wire [LANES-1:0] lane_fault,
    output wire supported
);
    `include "ot_gpu_native_conversion_abi.svh"
    wire profile_legal = !a_signed_i8 || (opcode==OP_I2F && a_type==2'd3);
    wire [64*LANES-1:0] signed_input;
    wire core_supported;
    genvar i;
    generate for(i=0;i<LANES;i=i+1) begin: signed_byte
        // Raw bits only: literal signed byte -> two's-complement I64 wiring.
        assign signed_input[i*64+:64] = a_signed_i8 ?
            {{56{a_data[i*64+7]}},a_data[i*64+:8]} : a_data[i*64+:64];
    end endgenerate
    ot_gpu_native_conversion #(.ENABLE(ENABLE),.LANES(LANES)) conversion(
        .opcode(opcode),.dtype(dtype),.a_type(a_signed_i8 ? 2'd2 : a_type),
        .b_type(b_type),.c_type(c_type),.a_scalar(a_scalar),.b_scalar(b_scalar),
        .c_scalar(c_scalar),.lane_mask(profile_legal ? lane_mask : {LANES{1'b0}}),
        .a_data(signed_input),.b_data(b_data),.c_data(c_data),
        .result(result),.result_type(result_type),.lane_fault(lane_fault),
        .supported(core_supported));
    assign supported=core_supported && profile_legal;
endmodule
