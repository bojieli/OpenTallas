// DIE-HBM-66 11-05 (COORD, Sinkhorn option A): HBM tail Sinkhorn hard core, S81's row-pipelined ot_hdc_sinkhorn_fsr in one core.
// Replaces ot_hdc_sk_step0_en_phys + ot_hdc_sk_steady_en: every path is single-cycle, no enable, no multicycle.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_hc_tail_sk_fsr #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD,
    parameter integer MUT = 0,
    parameter integer MUT_Q4 = 0
) (
    input  wire         clk, rst_n,
    input  wire         in_valid,
    input  wire [511:0] in_e,
    output wire         in_ready,
    output wire         out_valid,
    output wire [511:0] y,
    output wire         fault
);
    // landing: one master + 8 kept same-edge copies of the valid (S81 tail form); in_e is stable from launch to capture
    (* keep = 1 *) reg iv;
    wire [7:0] vin;
    always @(posedge clk) iv <= in_valid;
    genvar n;
    generate for (n = 0; n < 8; n = n + 1) begin : g_v
        (* keep = 1 *) ot_skf_kr #(.W(1)) u_k (.clk(clk), .d(in_valid), .q(vin[n]));
    end endgenerate
    ot_hdc_sinkhorn_fsr #(.ITERS(ITERS), .EPS(EPS), .MUT(MUT), .MUT_Q4(MUT_Q4), .NVIN(8), .OH(0), .FQ(1)) u_sinkh (
        .clk(clk), .rst_n(rst_n), .rst_n2(rst_n), .in_valid(iv), .vin(vin), .in_ready(in_ready), .in_e(in_e),
        .out_valid(out_valid), .y(y), .fault(fault), .busy());
endmodule
// Same face-stage mechanism as ot_hbm_hc_tail_unit_static_ce_phys (face_shell CELL_SV: one unreset flop on every bus).
module ot_hbm_hc_tail_unit_static_fsr_phys #(parameter MUT_PRE=0,SMUT=0,MUT_SK=0)(input clk,rst_n,launch,input[767:0]mixes,bases,input[95:0]scales,output result_v,output[767:0]result,output fault);
wire li;wire[767:0]mi,bi;wire[95:0]si;wire rv,ff;wire[767:0]rr;
ot_hbm_ce_face_reg a(clk,launch,li);ot_hbm_ce_face_reg#(768)b(clk,mixes,mi);ot_hbm_ce_face_reg#(768)c(clk,bases,bi);ot_hbm_ce_face_reg#(96)d(clk,scales,si);
wire iv_o,ird_i,ov_i,sf_i;wire[511:0]ie_o,y_i;wire en_nc;
ot_hbm_hc_tail_rest_core_fsr#(.MUT_PRE(MUT_PRE),.SMUT(SMUT))u(.clk(clk),.rst_n(rst_n),.launch(li),.mixes(mi),.bases(bi),.scales(si),.result_v(rv),.result(rr),.fault(ff),.sk_en_sk(en_nc),.sk_in_valid(iv_o),.sk_in_e(ie_o),.sk_in_ready(ird_i),.sk_out_valid(ov_i),.sk_fault(sf_i),.sk_y(y_i));
ot_hbm_ce_face_reg l(clk,rv,result_v);ot_hbm_ce_face_reg#(768)m(clk,rr,result);ot_hbm_ce_face_reg n(clk,ff,fault);
// rest output face -> core input face
wire iv,iv1;wire[511:0]ie,ie1;
ot_hbm_ce_face_reg f(clk,iv_o,iv);ot_hbm_ce_face_reg#(512)g(clk,ie_o,ie);ot_hbm_ce_face_reg q1(clk,iv,iv1);ot_hbm_ce_face_reg#(512)q4(clk,ie,ie1);
wire ird1,ov1,sf1;wire[511:0]y1;
ot_hbm_hc_tail_sk_fsr#(.MUT(MUT_SK))ss(.clk(clk),.rst_n(rst_n),.in_valid(iv1),.in_e(ie1),.in_ready(ird1),.out_valid(ov1),.y(y1),.fault(sf1));
// core output face -> rest input face
wire ird,ov,sf;wire[511:0]y;
ot_hbm_ce_face_reg q5(clk,ird1,ird);ot_hbm_ce_face_reg q9(clk,ov1,ov);ot_hbm_ce_face_reg#(512)q10(clk,y1,y);ot_hbm_ce_face_reg q11(clk,sf1,sf);
ot_hbm_ce_face_reg h(clk,ird,ird_i);ot_hbm_ce_face_reg i(clk,ov,ov_i);ot_hbm_ce_face_reg j(clk,sf,sf_i);ot_hbm_ce_face_reg#(512)k(clk,y,y_i);
endmodule
`default_nettype wire
