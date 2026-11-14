`timescale 1ns/1ps
// Storage only: caller owns capacity/admission. Current+previous logical writes
// forward around WREG=1 macro latency; q is head AFTER the current edge.
module ot_s81ph_queue_store #(parameter integer W=592, AW=3, MUT=0)(
 input wire clk, rst_n, push, input wire [AW-1:0] wa,
 input wire [W-1:0] data, input wire [AW-1:0] next_head,
 output wire [W-1:0] head);
 localparam integer NS=(W+15)/16;
 // Physical reset-copy pass must prove independent <=32-load leaves after synth;
 // no delayed reset is inserted into the logical head-visibility contract.
 wire [NS-1:0] reset_copy={NS{rst_n}};
 ot_sram_showahead_1r1w #(.W(W),.AW(AW),.WREG(1),.MUT(MUT)) u_mem(
 .clk(clk),.rst_n(reset_copy),.we(push),.wa(wa),.wd(data),.ra(next_head),.q(head));
endmodule
