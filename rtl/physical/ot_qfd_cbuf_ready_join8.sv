`timescale 1ns/1ps
// Dedicated retained-state join, no request-state alias. All source identities
// are captured as one cohort; the controller compares the registered output.
module qfd_cbuf_ready_join8(input wire ck,rst_n,
 input wire[7:0]st_rdy,input wire[47:0]st_rdy_stage,input wire[143:0]st_rdy_tpos,
 input wire[7:0]fault,
 output reg cb_st_rdy,output reg[5:0]cb_st_rdy_stage,output reg[17:0]cb_st_rdy_tpos,
 output reg cb_fault);
 reg[7:0]rdy_q,flt_q;reg[47:0]stage_q;reg[143:0]pos_q;
 always @(posedge ck)begin stage_q<=st_rdy_stage;pos_q<=st_rdy_tpos;cb_st_rdy_stage<=stage_q[5:0];cb_st_rdy_tpos<=pos_q[17:0];end
 integer g;reg same;
 always @*begin same=1;for(g=1;g<8;g=g+1)
  if(stage_q[g*6+:6]!=stage_q[5:0]||pos_q[g*18+:18]!=pos_q[17:0])same=0;end
 always @(posedge ck or negedge rst_n)if(!rst_n)begin rdy_q<=0;flt_q<=0;cb_st_rdy<=0;cb_fault<=0;end
 else begin rdy_q<=st_rdy;flt_q<=fault;cb_st_rdy<=(&rdy_q)&&same&&!(|flt_q);cb_fault<=|flt_q;end
endmodule
