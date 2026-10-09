`timescale 1ns/1ps
// Atomic cumulativepop transport. Independent pclk/coreclk, oneevent peredge.
// Both resets assert before training; dst admission follows both releases.
// No repeated pulse synchronizer; Gray count retains every unconsumed event.
module ot_hbm_retry_pop_cdc #(
 parameter CAPACITY=256,CW=$clog2(CAPACITY)+2
)(
 input wire s_clk,s_rst_n,s_pop,
 input wire d_clk,d_rst_n,
 output wire d_pop,output reg fault,output wire[CW-1:0] pending
);
 reg[CW-1:0] s_count,s_gray;
 wire[CW-1:0] s_next=s_count+1'b1;
 always@(posedge s_clk or negedge s_rst_n)begin
 if(!s_rst_n)begin s_count<=0;s_gray<=0;end
 else if(s_pop)begin
`ifndef OT_HBM_RETRY_POP_MUT_DROP
 s_count<=s_next;s_gray<=s_next^(s_next>>1);
`endif
end
 end
 (* async_reg="true" *)reg[CW-1:0] sync1,sync2;
 reg[CW-1:0] consumed;
 wire[CW-1:0] observed;
 for(genvar b=0;b<CW;b=b+1)begin:g_binary
 assign observed[b]=^sync2[CW-1:b];end
 assign pending=observed-consumed;
 assign d_pop=d_rst_n && !fault && pending!=0 && pending<=CAPACITY;
 always@(posedge d_clk or negedge d_rst_n)begin
 if(!d_rst_n)begin sync1<=0;sync2<=0;consumed<=0;fault<=0;end
 else begin
 sync1<=s_gray;sync2<=sync1;
 if(pending>CAPACITY)fault<=1;
 if(d_pop)consumed<=consumed+1'b1;
 end end
 initial if(CAPACITY<2||(CAPACITY&(CAPACITY-1)))$fatal(1,"invalid CDC retained debt capacity");
endmodule
