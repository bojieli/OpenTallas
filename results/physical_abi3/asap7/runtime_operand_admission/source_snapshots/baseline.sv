`timescale 1ns/1ps
// Capture and prepare cursor geometry once per operation. Two restoring
// dividers share the numerator and take 16 steps, with no combinational divide.
// This validates geometry, not arithmetic formats: the caller also requires
// LQ8's successful format/shape admission before launching this record.
module ot_a3_lq8_operand_admission #(
    parameter integer LANES=8
)(
    input wire clk,rst_n,clear,
    input wire command_valid,
    output wire command_ready,
    input wire [31:0] cfg_generation,
    input wire [15:0] cfg_rows,cfg_cols,cfg_depth,
    input wire [7:0] cfg_group,
    input wire cfg_scale_a,cfg_scale_b,
    input wire [15:0] cfg_block_a,cfg_block_b,cfg_block_rows_a,
    input wire [31:0] cfg_a_base,cfg_s_base,cfg_ws_base,cfg_w_base,
    output reg record_valid,
    input wire record_ready,
    output reg geometry_error,
    output reg [31:0] stream_words,
    output reg [31:0] generation,a_base,s_base,ws_base,w_base,
    output reg [15:0] rows,local_cols,depth_words,rows_per_scale_a,
    output reg [15:0] scale_stride_a,scale_stride_b,groups_per_scale_a,groups_per_scale_b
);
    localparam integer LG=$clog2(LANES);
    reg calculating;
    // Separate products across admission edges; never put two multipliers
    // in series on a request/issue path. Preserve the full 48-bit extent.
    reg [31:0] output_elements;
    reg [47:0] stream_extent;
    wire [48:0] stream_limit={17'b0,w_base}+{1'b0,stream_extent};
    reg [4:0] step;
    reg [15:0] numerator,divisor_a,divisor_b,remainder_a,remainder_b,quotient_a,quotient_b;
    reg scaled_a,scaled_b,invalid_q;
    wire [16:0] shifted_a={remainder_a,numerator[15]};
    wire [16:0] shifted_b={remainder_b,numerator[15]};
    wire fits_a=shifted_a>={1'b0,divisor_a};
    wire fits_b=shifted_b>={1'b0,divisor_b};
    wire [1:0] group_shift=cfg_group==4?2'd2:cfg_group==2?2'd1:2'd0;
    wire block_bad_a=cfg_block_a==0 ||
        (group_shift==1 && cfg_block_a[0]) || (group_shift==2 && |cfg_block_a[1:0]);
    wire block_bad_b=cfg_block_b==0 ||
        (group_shift==1 && cfg_block_b[0]) || (group_shift==2 && |cfg_block_b[1:0]);
    // Widen before rounding K up: 65535+3 must not wrap at 16 bits.
    wire [16:0] rounded_depth={1'b0,cfg_depth}+
        (cfg_group==4?17'd3:cfg_group==2?17'd1:17'd0);
    assign command_ready=rst_n && !clear && !calculating && !record_valid;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            calculating<=0;record_valid<=0;geometry_error<=0;step<=0;
            output_elements<=0;stream_extent<=0;stream_words<=0;
            numerator<=0;divisor_a<=0;divisor_b<=0;remainder_a<=0;remainder_b<=0;
            quotient_a<=0;quotient_b<=0;scaled_a<=0;scaled_b<=0;invalid_q<=0;
            generation<=0;a_base<=0;s_base<=0;ws_base<=0;w_base<=0;
            rows<=0;local_cols<=0;depth_words<=0;rows_per_scale_a<=0;
            scale_stride_a<=0;scale_stride_b<=0;groups_per_scale_a<=0;groups_per_scale_b<=0;
        end else if(clear)begin calculating<=0;record_valid<=0;geometry_error<=0;end
        else begin
            if(record_valid && record_ready)record_valid<=0;
            if(command_valid && command_ready)begin
                calculating<=1;step<=0;geometry_error<=0;
                generation<=cfg_generation;rows<=cfg_rows;local_cols<=cfg_cols>>LG;
                depth_words<=16'(rounded_depth>>group_shift);
                rows_per_scale_a<=cfg_block_rows_a==0?16'd1:cfg_block_rows_a;
                a_base<=cfg_a_base;s_base<=cfg_s_base;ws_base<=cfg_ws_base;w_base<=cfg_w_base;
                groups_per_scale_a<=cfg_scale_a?cfg_block_a>>group_shift:16'd0;
                groups_per_scale_b<=cfg_scale_b?cfg_block_b>>group_shift:16'd0;
                scaled_a<=cfg_scale_a;scaled_b<=cfg_scale_b;
                divisor_a<=cfg_block_a;divisor_b<=cfg_block_b;numerator<=cfg_depth;
                remainder_a<=0;remainder_b<=0;quotient_a<=0;quotient_b<=0;
                invalid_q<=cfg_rows==0 || cfg_cols==0 || cfg_depth==0 ||
                    (cfg_cols & 16'(LANES-1))!=0 ||
                    (cfg_group!=1 && cfg_group!=2 && cfg_group!=4) ||
                    (cfg_scale_a && block_bad_a) || (cfg_scale_b && block_bad_b);
            end else if(calculating)begin
                if(step==18)begin
                    calculating<=0;record_valid<=1;
                    geometry_error<=invalid_q || (scaled_a && remainder_a!=0) || (scaled_b && remainder_b!=0) ||
                        stream_extent==0 || |stream_extent[47:32] || stream_limit>49'h100000000;
                    stream_words<=stream_extent[31:0];
                    scale_stride_a<=scaled_a?quotient_a:16'd0;
                    scale_stride_b<=scaled_b?quotient_b:16'd0;
                end else if(step==16)begin
                    output_elements<=32'(rows)*32'(local_cols);step<=17;
                end else if(step==17)begin
                    stream_extent<=48'(output_elements)*48'(depth_words);step<=18;
                end else begin
                    remainder_a<=fits_a?shifted_a[15:0]-divisor_a:shifted_a[15:0];
                    remainder_b<=fits_b?shifted_b[15:0]-divisor_b:shifted_b[15:0];
                    quotient_a<={quotient_a[14:0],fits_a};quotient_b<={quotient_b[14:0],fits_b};
                    numerator<={numerator[14:0],1'b0};step<=step+1'b1;
                end
            end
        end
    end
endmodule
