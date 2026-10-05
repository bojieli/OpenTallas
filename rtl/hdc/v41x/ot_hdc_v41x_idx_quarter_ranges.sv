`timescale 1ns/1ps
// Sixteen virtual contiguous ranges for a compact four-stack index scan.
// Context I=4*stack+quarter. The range output is a local-key interval; the
// first superblock's base and skip drive ot_hdc_v41x_idx_kstream_range.
module ot_hdc_v41x_idx_quarter_ranges #(
    parameter integer NW=30,HW=20
) (
    input wire [NW-1:0] i_nkeys,
    input wire [HW-1:0] i_base_block,
    output wire [16*NW-1:0] o_first_local,
    output wire [16*NW-1:0] o_count,
    output wire [16*HW-1:0] o_base_block,
    output wire [16*10-1:0] o_skip
);
    wire [NW-1:0] qs=(i_nkeys>>5)<<3;
    function automatic [NW-1:0] rank(input [NW-1:0] x,input integer stack);
        integer rem,lo;
        begin
            rem=int'(x[5:0]);lo=rem-16*stack;
            if(lo<0) lo=0;
            else if(lo>16) lo=16;
            rank=((x>>6)<<4)+NW'(lo);
        end
    endfunction
    genvar s,q;
    generate for(s=0;s<4;s=s+1) begin:g_stack
        for(q=0;q<4;q=q+1) begin:g_quarter
            localparam integer I=4*s+q;
            wire [NW-1:0] first_global=NW'(q)*qs;
            wire [NW-1:0] len_global=q==3 ? i_nkeys-3*qs : qs;
            wire [NW-1:0] first_local=rank(first_global,s);
            wire [NW-1:0] last_local=rank(first_global+len_global,s);
            wire [HW-1:0] superblock=HW'(first_local>>10);
            assign o_first_local[I*NW +: NW]=first_local;
            assign o_count[I*NW +: NW]=last_local-first_local;
            assign o_base_block[I*HW +: HW]=i_base_block+(superblock<<4)+superblock;
            assign o_skip[I*10 +: 10]=first_local[9:0];
        end
    end endgenerate
endmodule
