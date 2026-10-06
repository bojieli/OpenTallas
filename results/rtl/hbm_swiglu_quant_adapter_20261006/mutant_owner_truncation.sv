`timescale 1ns/1ps
// Port-only join from the fused-stream operand/quant ABI to the adopted engine.
// Replace the selected SwiGLU producer; do not instantiate a second producer.
// The caller owns the existing protected descriptor, input stream and finite
// landing. Hold held_frame and lim throughout the command; landing_index is the
// caller's ordered output cursor (NOT the current input beat). No metadata copy,
// FIFO, extra traverse, clock crossing or arithmetic is introduced here.
// launch_permit blocks NEW work only. Accepted, nonelastic outputs still drain
// during warm/veto; the parent retains its reservation until actual publication
// ACK and producer/consumer drain, not merely q_valid. Root POR only.
module ot_hbm_integrated_swiglu_quant_adapter #(
 parameter integer ENABLE=0, N=1024, ROUTED=1
)(
 input wire clk,por_n,
 input wire launch_permit,landing_reserved,in_valid,
 output wire in_ready,
 input wire [72:0] held_frame,
 input wire [7:0] landing_index,
 input wire [31:0] lim,
 // Exact existing stream layout: plane0 G, plane1 U, plane2 routing weight;
 // plane3 belongs to other stream kinds and is deliberately unused here.
 input wire [4*N*32-1:0] operands,
 output wire q_valid,
 output wire [72:0] q_frame,
 output wire [7:0] q_index,
 output wire [N*8-1:0] q_codes,
 output wire [(N/32)*10-1:0] q_exp,
 output wire [N*16-1:0] q_bf16,
 output wire fault
);
 generate if(!ENABLE) begin:g_off
  assign in_ready=0;assign q_valid=0;assign q_frame=0;assign q_index=0;
  assign q_codes=0;assign q_exp=0;assign q_bf16=0;assign fault=0;
 end else begin:g_on
  initial begin
   if(N<32 || N%32!=0) $fatal(1,"SwiGLU quant adapter requires complete 32-word blocks");
  end
  wire engine_fault;
  assign in_ready=por_n && launch_permit && landing_reserved;
  // Source-pinned adoption278a274e7: LM5/LA4/QLAT5, 33/23 priced hub cuts.
  // Its y is quantised/dequantised BF16; it is NOT the prequant norm/VM y_data.
  ot_dsrom_su_swiglu #(.W(N),.ROUTED(ROUTED),.LM(5),.LA(4),
                        .QLAT(5),.NIN(33),.NOUT(23)) producer (
   .clk(clk),.rst_n(por_n),.v(in_valid && in_ready),
   .g(operands[0+:N*32]),.u(operands[N*32+:N*32]),
   .w(operands[2*N*32+:N*32]),.lim(lim),
   .vo(q_valid),.q(q_codes),.e(q_exp),.y(q_bf16),.fault(engine_fault));
  assign q_frame={1'b0,held_frame[71:0]};
  assign q_index=landing_index;
  // Uninitialised non-valid pipeline data is never a published fault.
  assign fault=q_valid && engine_fault;
 end endgenerate
endmodule
