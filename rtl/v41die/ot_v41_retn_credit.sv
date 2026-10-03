`timescale 1ns/1ps
// Explicit successor selection; legacy module and default caller unchanged.
module ot_v41_retn_credit #(
    parameter integer RD=4, OUTD=4, RST=1, BYPASS=1
)(
    input wire clk,rst_n,a_v,b_v,a_e,b_e,
    input wire [31:0] a_t,a_d,b_t,b_d,
    input wire o_credit,
    output wire a_ready,b_ready,a_credit,b_credit,
    output wire o_v,o_e, output wire [31:0] o_t,o_d,
    output wire fault,quiet,
    output wire [31:0] peak_a,peak_b,credit_stalls
);
    wire ov,oe,nquiet; wire [31:0] ot,od;
    ot_v41_ret_credit_node #(.RD(RD),.OUTD(OUTD),.BYPASS(BYPASS)) u_n(
        .clk(clk),.rst_n(rst_n),.a_v(a_v),.a_t(a_t),.a_d(a_d),.a_e(a_e),
        .b_v(b_v),.b_t(b_t),.b_d(b_d),.b_e(b_e),
        .o_v(ov),.o_t(ot),.o_d(od),.o_e(oe),.o_credit(o_credit),
        .a_ready(a_ready),.b_ready(b_ready),.a_credit(a_credit),.b_credit(b_credit),
        .fault(fault),.quiet(nquiet),.peak_a(peak_a),.peak_b(peak_b),.credit_stalls(credit_stalls));
    wire [64:0] rq;
    ot_hdc_delay #(.W(65),.D(RST)) u_d(.clk(clk),.rst_n(rst_n),.d({ot,od,oe}),.q(rq));
    wire [RST:0] rv; assign rv[0]=ov;
    genvar g;
    generate for(g=0;g<RST;g=g+1) begin:g_r
        reg v; always @(posedge clk or negedge rst_n) if(!rst_n) v<=0; else v<=rv[g];
        assign rv[g+1]=v;
    end endgenerate
    assign o_v=rv[RST]; assign {o_t,o_d,o_e}=rq;
    assign quiet=nquiet && rv==0;
endmodule
