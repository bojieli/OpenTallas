`timescale 1ns/1ps
`default_nettype none
// Physical leaf boundary: sample at n, actual SRAM read/write at n+1,
// registered data/return pins at n+2. Payload is not reset. The compiler
// prices both read edges and the +1 write commit; there is no retry path.
module ot_hbm_su_static_pinned_bank #(
 parameter integer READERS=6,RB=9,MUT_COHERENCE=0,MUT_RETURN=0
)(
 input wire clk,rst_n,
 input wire[READERS-1:0]read_v,input wire[READERS*RB-1:0]read_addr,
 output reg[READERS*32-1:0]read_data,output wire[READERS-1:0]read_return,
 input wire write_v,input wire[RB-1:0]write_addr,input wire[31:0]write_data
);
 reg[READERS-1:0]r_pin,r_macro,r_return,r_late;
 reg[READERS*RB-1:0]a_pin;
 reg w_pin;reg[RB-1:0]wa_pin;reg[31:0]wd_pin;
 wire[READERS*32-1:0]raw_data;
 always @(posedge clk)begin
  a_pin<=read_addr;wa_pin<=write_addr;wd_pin<=write_data;read_data<=raw_data;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin r_pin<=0;r_macro<=0;r_return<=0;r_late<=0;w_pin<=0;end
  else begin r_pin<=read_v;r_macro<=r_pin;r_return<=r_macro;r_late<=r_return;w_pin<=write_v;end
 end
 assign read_return=MUT_RETURN!=0?r_late:r_return;
 ot_hbm_su_static_replicated_bank #(.READERS(READERS),.RB(RB),.MUT_COHERENCE(MUT_COHERENCE))u_data(
  .clk(clk),.read_v(r_pin),.read_addr(a_pin),.read_data(raw_data),
  .write_v(w_pin),.write_addr(wa_pin),.write_data(wd_pin));
endmodule
`default_nettype wire
