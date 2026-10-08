`timescale 1ns/1ps
// PIN-REGISTERED + MACRO-INPUT-REGISTERED (WREG=1) VARIANT of the hfd_coll_pkt_fifo_ii1 physical wrapper (drive-0532 2026-10-08): same top name
// and ports; every input lands in a flop, every output leaves a flop; ready = registered level with a 2-slot
// reserve, valid/pop = credit flow (pop is a credit-return pulse, OCR=8 consumer slots).  See
// ot_hbm_collective_packet_fifo_ii1r.sv.  The raw reset enters through the local 2-edge-release synchroniser.
module hfd_coll_pkt_fifo_ii1(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
 (* ASYNC_REG="TRUE" *) reg [1:0] rst_s;
 always @(posedge clk or negedge rst_n)if(!rst_n)rst_s<=2'b00;else rst_s<={rst_s[0],1'b1};
 ot_hbm_collective_packet_fifo_ii1r #(.DEPTH(256),.OCR(8),.WREG(1)) u_q(.clk(clk),.rst_n(rst_s[1]),.push(push),.din(din),
  .ready(ready),.pop(pop),.valid(valid),.dout(dout),.fault(fault),.count(count));
endmodule
