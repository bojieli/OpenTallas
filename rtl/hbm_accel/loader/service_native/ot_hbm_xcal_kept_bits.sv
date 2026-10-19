`timescale 1ns/1ps
`default_nettype none
// Preserved actual one-bit FF boundaries. No delayed shadow state.
(* keep_hierarchy = 1 *) module ot_hbm_xcal_kept_bit(input wire clk,d,output reg q);
 always @(posedge clk)q<=d;
endmodule
(* keep_hierarchy = 1 *) module ot_hbm_xcal_kept_rbit(input wire clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=d;
endmodule
// Each branch is the second stage of the existing root release, not an extra stage.
(* keep_hierarchy = 1 *) module ot_hbm_xcal_reset_branch(input wire clk,rst_n,phase0,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=phase0;
endmodule
`default_nettype wire
