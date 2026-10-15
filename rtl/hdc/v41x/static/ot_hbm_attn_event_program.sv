`timescale 1ns/1ps
`default_nettype none
// Real mapped programme SRAM, one immutable event word per absolute cycle.
// Host loads an idle programme bank before launch; execution never stalls.
module ot_hbm_attn_event_program(
 input wire clk,rst_n,input wire program_we,input wire[7:0]program_addr,
 input wire[27:0]program_events,input wire launch,input wire[7:0]program_last,input wire[1:0]program_profile,
 output wire[6:0]events,output reg[7:0]phase,output reg valid,
 output reg running,output reg fault
);
 reg[7:0]pc,last;reg[1:0]profile;wire[255:0]word;
 ot_sram_1r1w_256x256_m2_r2c2 u_program(.clk(clk),.r_ce_in(running),.r_addr_in(pc),.rd_out(word),
  .w_ce_in(program_we),.w_addr_in(program_addr),.wd_in({228'd0,program_events}),.w_mask_in({256{1'b1}}),
  .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 assign events=valid?word[profile*7+:7]:7'd0;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin pc<=0;last<=0;phase<=0;valid<=0;running<=0;fault<=0;profile<=0;end
 else begin
  valid<=running;phase<=pc;
  if(program_we&&(running||valid))fault<=1;
  if(launch)begin if(running||valid)fault<=1;running<=1;pc<=0;last<=program_last;profile<=program_profile;end
  else if(running)begin if(pc==last)running<=0;else pc<=pc+1'b1;end
 end
endmodule
`default_nettype wire
