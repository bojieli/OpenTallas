`timescale 1ns/1ps
// Physical wrapper: one full-width (545 b) II=1 refill collective packet SRAM queue, DEPTH 256
// (the RXAW=8 receive buffer; the AW=6 queues use the same three 256x256 macros with 64 entries).
// The raw reset port enters through a local async-assert / 2-edge-release synchroniser (rst_s), as on the die.
module hfd_coll_pkt_fifo_ii1(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
 (* ASYNC_REG="TRUE" *) reg [1:0] rst_s;
 always @(posedge clk or negedge rst_n)if(!rst_n)rst_s<=2'b00;else rst_s<={rst_s[0],1'b1};
 ot_hbm_collective_packet_fifo_refill #(.ENABLE(1),.DEPTH(256)) u_q(.clk(clk),.rst_n(rst_s[1]),.push(push),.din(din),
  .ready(ready),.pop(pop),.valid(valid),.dout(dout),.fault(fault),.count(count));
endmodule
