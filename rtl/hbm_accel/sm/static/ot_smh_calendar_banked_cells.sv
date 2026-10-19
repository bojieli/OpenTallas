`timescale 1ns/1ps
`default_nettype none
(* keep_hierarchy=1 *) module ot_smh_banked_bit(input wire clk,d,output reg q);
 always @(posedge clk)q<=d;
endmodule
(* keep_hierarchy=1 *) module ot_smh_banked_rbit(input wire clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=d;
endmodule
(* keep_hierarchy=1 *) module ot_smh_banked_reset_branch(input wire clk,rst_n,phase0,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=phase0;
endmodule
// Each4-slot slice stores16bits; replicated local phase controls avoid a wide shared index.
(* keep_hierarchy=1 *) module ot_smh_banked_ring4 #(parameter integer DELAY=2)(
 input wire clk,rst_n,input wire[3:0] din,output wire[3:0] dout);
 reg[3:0] slots[0:3];reg[1:0] phase;
 always @(posedge clk or negedge rst_n)if(!rst_n)phase<=0;else phase<=phase+1'b1;
 always @(posedge clk)slots[phase]<=din;
 wire[1:0] rd_phase=phase-2'(DELAY);
 assign dout=slots[rd_phase];
endmodule
// Preserved local combinational qualifier: mapping must not hoist its common
// legal/busy term into a shared wide mux-enable cone across state slices.
(* keep_hierarchy=1 *) module ot_smh_banked_accept(input wire start,ok,output wire accepted);
 assign accepted=start&&ok;
endmodule
`default_nettype wire
