`timescale 1ns/1ps
// Independent future-address walk for admitted LQ8 operations. Geometry comes
// from admission (division performed once there, never on the per-word path).
// Advance only when a downstream request slot is reserved. Arithmetic may lag
// arbitrarily behind this cursor. clear aborts the generation at any position.
// Weight scale rows correspond to lane-local columns (LQ8 block_rows_b = 1).
module ot_a3_lq8_operand_cursor #(
    parameter integer INTERLEAVE=3
)(
    input wire clk,rst_n,clear,start,
    input wire [31:0] cfg_generation,
    input wire [15:0] cfg_rows,cfg_local_cols,cfg_depth_words,
    input wire [15:0] cfg_rows_per_scale_a,
    input wire [15:0] cfg_scale_stride_a,cfg_scale_stride_b,
    input wire [15:0] cfg_groups_per_scale_a,cfg_groups_per_scale_b,
    input wire [31:0] cfg_a_base,cfg_s_base,cfg_ws_base,cfg_w_base,
    output wire request_valid,
    input wire request_ready,
    output reg [31:0] generation,
    output wire [31:0] a_address,s_address,ws_address,
    output reg [31:0] w_address,
    output wire last,
    output reg active,
    output reg invalid_geometry
);
    localparam integer IW=(INTERLEAVE<2)?1:$clog2(INTERLEAVE);
    reg [15:0] rows_left,cols_left,cols_q,depth_q,kg;
    reg [IW-1:0] col;
    reg [15:0] rpb_a,rows_in_scale,sa_stride,sb_stride,bwa,bwb,kga,kgb;
    reg [15:0] ksa,ksb;
    reg [31:0] a_base,s_base,ws_cursor;
    reg [31:0] ws_columns[0:INTERLEAVE-1];
    wire [15:0] pass_cols=(cols_left<16'(INTERLEAVE))?cols_left:16'(INTERLEAVE);
    wire end_col=16'(col)==pass_cols-1'b1;
    wire end_k=kg==depth_q-1'b1;
    wire end_row=cols_left<=16'(INTERLEAVE);
    reg [31:0] ws_base_q;
    assign request_valid=rst_n && !clear && active;
    assign a_address=a_base+{16'b0,kg};
    assign s_address=s_base+{16'b0,ksa};
    assign ws_address=(kg==0?ws_cursor:ws_columns[col])+{16'b0,ksb};
    assign last=end_col && end_k && end_row && rows_left==1;
    integer i;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;invalid_geometry<=0;generation<=0;
            rows_left<=0;cols_left<=0;cols_q<=0;depth_q<=0;kg<=0;col<=0;
            rpb_a<=0;rows_in_scale<=0;sa_stride<=0;sb_stride<=0;bwa<=0;bwb<=0;
            kga<=0;kgb<=0;ksa<=0;ksb<=0;a_base<=0;s_base<=0;ws_cursor<=0;
            ws_base_q<=0;w_address<=0;
            for(i=0;i<INTERLEAVE;i=i+1)ws_columns[i]<=0;
        end else if(clear)begin active<=0;invalid_geometry<=0;end
        else if(start && !active)begin
            invalid_geometry<=cfg_rows==0 || cfg_local_cols==0 || cfg_depth_words==0 || cfg_rows_per_scale_a==0;
            active<=cfg_rows!=0 && cfg_local_cols!=0 && cfg_depth_words!=0 && cfg_rows_per_scale_a!=0;
            generation<=cfg_generation;
            rows_left<=cfg_rows;cols_left<=cfg_local_cols;cols_q<=cfg_local_cols;
            depth_q<=cfg_depth_words;kg<=0;col<=0;
            rpb_a<=cfg_rows_per_scale_a;rows_in_scale<=0;
            sa_stride<=cfg_scale_stride_a;sb_stride<=cfg_scale_stride_b;
            bwa<=cfg_groups_per_scale_a;bwb<=cfg_groups_per_scale_b;
            kga<=0;kgb<=0;ksa<=0;ksb<=0;
            a_base<=cfg_a_base;s_base<=cfg_s_base;ws_cursor<=cfg_ws_base;
            ws_base_q<=cfg_ws_base;w_address<=cfg_w_base;
        end else if(request_valid && request_ready)begin
            w_address<=w_address+1'b1;
            if(kg==0)begin
                ws_columns[col]<=ws_cursor;
                ws_cursor<=ws_cursor+{16'b0,sb_stride};
            end
            if(end_col)begin
                col<=0;
                if(end_k)begin
                    kg<=0;kga<=0;kgb<=0;ksa<=0;ksb<=0;
                    if(end_row)begin
                        cols_left<=cols_q;ws_cursor<=ws_base_q;
                        if(rows_left==1)active<=0;
                        else begin
                            rows_left<=rows_left-1'b1;
                            a_base<=a_base+{16'b0,depth_q};
                            if(rows_in_scale==rpb_a-1'b1)begin
                                rows_in_scale<=0;s_base<=s_base+{16'b0,sa_stride};
                            end else rows_in_scale<=rows_in_scale+1'b1;
                        end
                    end else cols_left<=cols_left-pass_cols;
                end else begin
                    kg<=kg+1'b1;
                    if(bwa!=0)begin
                        if(kga==bwa-1'b1)begin kga<=0;ksa<=ksa+1'b1;end
                        else kga<=kga+1'b1;
                    end
                    if(bwb!=0)begin
                        if(kgb==bwb-1'b1)begin kgb<=0;ksb<=ksb+1'b1;end
                        else kgb<=kgb+1'b1;
                    end
                end
            end else col<=col+1'b1;
        end
    end
endmodule
