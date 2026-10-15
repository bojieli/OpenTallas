`timescale 1ns/1ps
`default_nettype none
module ot_s81_pq_calendar_rom #(
 parameter integer ACTION_BITS=72,
 parameter string ACTION_IMAGE="",TIME_IMAGE=""
)(input wire ck,rst_n,prime,stage_start,input wire[11:0]base,input wire[12:0]length,
 output wire[ACTION_BITS-1:0]action,output wire active,primed,fault);
 wire[11:0]addr;wire[71:0]a,t;
 ot_rom_4096x72_m8 #(.VIAMAP(ACTION_IMAGE),.INSTANCE("pq_calendar_action"))u_action(.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(a));
 ot_rom_4096x72_m8 #(.VIAMAP(TIME_IMAGE),.INSTANCE("pq_calendar_time"))u_time(.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(t));
 ot_s81_pq_calendar_reader #(.ACTION_BITS(ACTION_BITS)) u_reader(.ck(ck),.rst_n(rst_n),.prime(prime),.stage_start(stage_start),.base(base),.length(length),
 .rom_addr(addr),.rom_action(a),.rom_time(t),.action(action),.active(active),.primed(primed),.fault(fault));
endmodule
`default_nettype wire
