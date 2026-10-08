`timescale 1ns/1ps
// Physical wrapper: one full-width (545 b) II=1 refill collective packet SRAM queue, DEPTH 256
// (the RXAW=8 receive buffer; the AW=6 queues use the same three 256x256 macros with 64 entries).
module hfd_coll_pkt_fifo_ii1(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
 ot_hbm_collective_packet_fifo_refill #(.ENABLE(1),.DEPTH(256)) u_q(.*);
endmodule
// Same shape at II=3 (reference route for the refill's cost; never adopted on its own).
module hfd_coll_pkt_fifo_ii3(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
 ot_hbm_collective_packet_fifo #(.ENABLE(1),.DEPTH(256)) u_q(.*);
endmodule
