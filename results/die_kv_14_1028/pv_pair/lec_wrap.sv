// DIE-KV-14b RTL proof wrappers: same boundary as ot_qwen_tp8_pv_slice_t; the lc copy pins are driven from the
// command bits they copy (bc[17] issue, bc[18] capture), as the column wires them.
`timescale 1ns/1ps
module lec_gold(input wire clk,rst_n,input wire[255:0] pv2,input wire[31:0] pe2,input wire[22:0] bc,
 output wire[511:0] ts,output wire fault);
 ot_qwen_tp8_pv_slice_t #(.RESET_PIN(1)) u(.clk(clk),.rst_n(rst_n),.pv2(pv2),.pe2(pe2),.bc(bc),.ts(ts),.fault(fault));
endmodule
module lec_gate #(parameter integer MUT_LC=0)(input wire clk,rst_n,input wire[255:0] pv2,input wire[31:0] pe2,
 input wire[22:0] bc,output wire[511:0] ts,output wire fault);
 ot_qwen_tp8_pv_slice_lc_t #(.RESET_PIN(1),.G(4),.MUT_LC(MUT_LC)) u(.clk(clk),.rst_n(rst_n),.pv2(pv2),.pe2(pe2),.bc(bc),
  .bcx({{3{bc[18]}},{3{bc[17]}}}),.ts(ts),.fault(fault));
endmodule
