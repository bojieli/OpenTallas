`timescale 1ns/1fs
`default_nettype none
// Low-latency candidate: real immutable full-word slots, explicit compiler starts.
// Average frequency ratio WI*w_frequency == WO*r_frequency is mandatory.
// Per-slot ownership toggles cross two actual registers; no dynamic issue/stall.
// Failure observes a bad reservation, never repairs it or reschedules traffic.
module ot_hbm_pma_stream_gearbox #(
 parameter integer WI=544,WO=512,SLOTS=16,MUT=0
)(input wire wclk,rclk,rst_n,w_start,r_start,input wire [WI-1:0] d,
 input wire observed_v,output reg [WO-1:0] q,output reg q_v,
 output reg w_fault,r_fault);
 localparam integer AW=$clog2(SLOTS);
 reg [WI-1:0] slot[0:SLOTS-1];
 reg [SLOTS-1:0] done,consumed,done_s1,done_s2,cons_s1,cons_s2;
 reg wa,ra;reg [AW-1:0] wb,rb;
 integer offset;
 wire [AW-1:0] next_rb=rb+1'b1;
 wire [2*WI-1:0] joined={slot[next_rb],slot[rb]};
 initial begin
  if(WO>2*WI || SLOTS<4 || (1<<AW)!=SLOTS)$fatal(1,"unsupported stream geometry");
 end
 always @(posedge wclk or negedge rst_n)
 if(!rst_n)begin wa<=0;wb<=0;done<=0;cons_s1<=0;cons_s2<=0;w_fault<=0;end
 else begin
  cons_s1<=consumed;cons_s2<=cons_s1;
  if(w_start && wa)w_fault<=1;
  if(w_start || wa)begin
   wa<=1;
   if(!observed_v || done[wb]!=cons_s2[wb])w_fault<=1;
   slot[wb]<=d;done[wb]<=~done[wb];wb<=wb+1'b1;
  end
 end
 always @(posedge rclk or negedge rst_n)
 if(!rst_n)begin ra<=0;rb<=0;offset<=0;consumed<=0;done_s1<=0;done_s2<=0;r_fault<=0;q_v<=0;q<=0;end
 else begin
  done_s1<=done;done_s2<=done_s1;q_v<=0;
  if(r_start && ra)r_fault<=1;
  if(r_start || ra)begin
   ra<=1;q_v<=1;
   if(done_s2[rb]==consumed[rb])r_fault<=1;
   if(offset+WO>WI && done_s2[next_rb]==consumed[next_rb])r_fault<=1;
   q<=(joined >> offset) ^ ((MUT==1 && offset==WI-32)?{{(WO-1){1'b0}},1'b1}:{WO{1'b0}});
   if(offset+WO>=2*WI)begin
    consumed[rb]<=done_s2[rb];consumed[next_rb]<=done_s2[next_rb];
    rb<=rb+2;offset<=offset+WO-2*WI;
   end else if(offset+WO>=WI)begin
    consumed[rb]<=done_s2[rb];rb<=rb+1'b1;offset<=offset+WO-WI;
   end else offset<=offset+WO;
  end
 end
endmodule
`default_nettype wire
