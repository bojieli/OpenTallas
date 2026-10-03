`timescale 1ns/1ps
// Default-off stateless conversion delegate. Pauli owns every held command,
// protected seat, RF lease and publication ACK. Faulted bytes are never valid.
module ot_gpu_native_conversion #(
    parameter ENABLE = 0, parameter integer LANES = 4
)(
    input wire [5:0] opcode,
    input wire [1:0] dtype, a_type, b_type, c_type,
    input wire a_scalar, b_scalar, c_scalar,
    input wire [LANES-1:0] lane_mask,
    input wire [64*LANES-1:0] a_data, b_data, c_data,
    output wire [64*LANES-1:0] result,
    output reg [1:0] result_type,
    output wire [LANES-1:0] lane_fault,
    output wire supported
);
    import ot_a3_format_pkg::*;
    `include "ot_gpu_native_conversion_abi.svh"
    wire a_numeric = (a_type <= 2'd3);
    wire exponent_integer = (b_type != 2'd0);
    assign supported = ENABLE && (
        (opcode == OP_I2F && a_numeric) ||
        (opcode == OP_F2I && a_type == 2'd0) ||
        (opcode == OP_LDEXP && a_numeric && exponent_integer) ||
        (opcode == OP_FP8_PACK && a_numeric) ||
        (opcode == OP_FP8_UNPACK && a_type != 2'd0));
    always @* begin
        result_type = 2'd0;
        if (opcode == OP_F2I) result_type = 2'd2;
        if (opcode == OP_FP8_PACK) result_type = 2'd3;
    end

    function automatic [31:0] numeric_f32(input [63:0] v, input [1:0] typ);
        reg signbit; reg [63:0] mag, rembits, halfbit;
        reg [24:0] sig; reg [7:0] expbits;
        integer p, i, sh;
        begin
            signbit = 1'b0; mag = v;
            if (typ == 2'd1) mag = {32'd0,v[31:0]};
            if (typ == 2'd3) mag = {56'd0,v[7:0]};
            if (typ == 2'd2) begin
                signbit = v[63]; mag = signbit ? (~v+64'd1) : v;
            end
            p=0; sig=0; rembits=0; halfbit=0; sh=0; expbits=0;
            if (typ == 2'd0) numeric_f32=v[31:0];
            else if (mag == 0) numeric_f32=32'd0;
            else begin
                for (i=0;i<64;i=i+1) if (mag[i]) p=i;
                sh=p-23;
                if (sh>0) begin
                    sig=mag >> sh;
                    rembits=mag & ((64'd1 << sh)-64'd1);
                    halfbit=64'd1 << (sh-1);
                    if (rembits>halfbit || (rembits==halfbit && sig[0])) sig=sig+25'd1;
                    if (sig[24]) begin sig=sig>>1; p=p+1; end
                end else sig=mag << (23-p);
                expbits=p+127;
                numeric_f32={signbit,expbits,sig[22:0]};
            end
        end
    endfunction

    // {fault, int64}. F32's greatest finite representable integer below2^63
    // is legal; either sign at exactly2^63 is illegal in the native VM.
    function automatic [64:0] f32_i64(input [31:0] x);
        reg [63:0] mag; integer e;
        begin
            e=$signed({1'b0,x[30:23]})-127; mag=0;
            if (x[30:23]==8'hff || e>=63) f32_i64={1'b1,64'd0};
            else begin
                if (x[30:23]!=0 && e>=0) begin
                    mag={40'd0,1'b1,x[22:0]};
                    if (e>=23) mag=mag<<(e-23); else mag=mag>>(23-e);
                end
                f32_i64={1'b0,(x[31] ? (~mag+64'd1) : mag)};
            end
        end
    endfunction

    // {fault, binary32}. No canonical-zero override: ldexp preserves sign.
    function automatic [32:0] scale_f32(input [31:0] x, input [31:0] powbits);
        reg [23:0] sig; reg [24:0] rounded;
        reg [63:0] rembits, halfbit;
        reg signed [63:0] target;
        reg [7:0] expbits;
        integer e, p, i, sh;
        begin
            sig=0; rounded=0; rembits=0; halfbit=0;
            target=0; e=0; p=0; sh=0; expbits=0;
            if (x[30:23]==8'hff) begin
                if (x[22:0]!=0) scale_f32={1'b1,x[31:23],(x[22:0] | 23'h400000)};
                else scale_f32={1'b1,x};
            end else if (x[30:0]==0) scale_f32={1'b0,x};
            else begin
                if (x[30:23]==0) begin
                    for(i=0;i<23;i=i+1) if(x[i]) p=i;
                    sig={1'b0,x[22:0]} << (23-p); e=p-149;
                end else begin sig={1'b1,x[22:0]}; e=$signed({1'b0,x[30:23]})-127; end
                target=e;
                target=target+$signed(powbits);
                if (target>127) scale_f32={1'b1,x[31],8'hff,23'd0};
                else if (target>=-126) begin
                    expbits=target+127; scale_f32={1'b0,x[31],expbits,sig[22:0]};
                end else begin
                    if (target < -150) rounded=0;
                    else begin
                        sh=-126-target; rounded={1'b0,sig} >> sh;
                        rembits={40'd0,sig} & ((64'd1<<sh)-64'd1);
                        halfbit=64'd1<<(sh-1);
                        if(rembits>halfbit || (rembits==halfbit && rounded[0])) rounded=rounded+25'd1;
                    end
                    if (rounded[23]) scale_f32={1'b0,x[31],8'd1,23'd0};
                    else scale_f32={1'b0,x[31],8'd0,rounded[22:0]};
                end
            end
        end
    endfunction

    genvar n;
    generate for(n=0;n<LANES;n=n+1) begin: conversion_lane
        wire [63:0] av=a_scalar ? a_data[63:0] : a_data[n*64+:64];
        wire [63:0] bv=b_scalar ? b_data[63:0] : b_data[n*64+:64];
        wire [31:0] af=numeric_f32(av,a_type);
        wire [31:0] packed_value;
        // Reuse original exact RNE E4M3 encoder. Global24 is explicitly
        // delegated to this primitive's constant local encoding0x17.
        ot_gpu_simt_lane pack_lane(.op(8'h17),.x(af),.y(32'd0),
            .imm(32'd0),.lane(8'd0),.uval(32'd0),.z(packed_value));
        reg [63:0] out; reg fault;
        reg [64:0] converted;
        reg [32:0] scaled;
        reg [33:0] decoded;
        always @* begin
            out=0; fault=0; converted=0; scaled=0; decoded=0;
            if(supported && lane_mask[n]) begin
                case(opcode)
                    OP_I2F: out={32'd0,af};
                    OP_F2I: begin converted=f32_i64(af); out=converted[63:0]; fault=converted[64]; end
                    OP_LDEXP: begin
                        scaled=scale_f32(af,b_type==2'd3 ? {24'd0,bv[7:0]} : bv[31:0]);
                        out={32'd0,scaled[31:0]}; fault=scaled[32];
                    end
                    OP_FP8_PACK: begin
                        fault=(af[30:23]==8'hff);
                        out=fault ? 64'd0 : {56'd0,packed_value[7:0]};
                    end
                    OP_FP8_UNPACK: begin
                        decoded=decode_e4m3fn(av[7:0]);
                        out={32'd0,decoded[31:0]}; fault=(decoded[33:32]!=0);
                    end
                    default: begin out=0; fault=0; end
                endcase
            end
        end
        assign result[n*64+:64]=out;
        assign lane_fault[n]=fault;
    end endgenerate
endmodule
