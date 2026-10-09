`timescale 1ns/1ps
// Physical/exactness vehicle for the opt-in G12 frontend. The legacy engine is
// unchanged and selects this vehicle only after its gates pass.
module ot_hgi_att_row_sources_p #(
    parameter integer MUT_RING_ZERO=0, MUT_DROP_C=0, MUT_C_REVERSE=0
)(
    input wire clk,rst_n,cmd_v,ring,
    output wire cmd_r,
    input wire [19:0] pos1,b_n,b_m,c_n,
    input wire c_id_v,output wire c_id_r,input wire [31:0] c_id,
    output wire row_v,input wire row_r,
    output wire row_source,row_last,
    output wire [19:0] row_index,
    output wire [20:0] row_ordinal,
    output wire busy,done,fault
);
    ot_hgi_att_row_sources #(.ENABLE_G12(1),.MUT_RING_ZERO(MUT_RING_ZERO),.MUT_DROP_C(MUT_DROP_C),.MUT_C_REVERSE(MUT_C_REVERSE)) u_rows(
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_r(cmd_r),.ring(ring),.pos1(pos1),.b_n(b_n),.b_m(b_m),.c_n(c_n),
        .c_id_v(c_id_v),.c_id_r(c_id_r),.c_id(c_id),
        .legacy_v(1'b0),.legacy_r(),.legacy_source(1'b0),.legacy_last(1'b0),.legacy_row(20'b0),.legacy_ordinal(21'b0),
        .row_v(row_v),.row_r(row_r),.row_source(row_source),.row_last(row_last),.row_index(row_index),.row_ordinal(row_ordinal),
        .busy(busy),.done(done),.fault(fault));
endmodule
