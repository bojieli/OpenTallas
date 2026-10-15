`timescale 1ns/1ps
`default_nettype none
// One existing row-congruent A slot: two actual mask ROM macros, 32x256 BF16.
// Request at edge R reserves exactly sixteen response edges R+6 through R+21.
// The compiler provides a request only after that window is empty. Violations
// fault without moving an issued response. No readiness, queue or credits.
module ot_dsrom_markov_weight32_static #(
 parameter INSTANCE="mk", parameter integer ID_W=60,
 parameter integer GLOBAL_ROW0=0, VALID_ROWS=32
)(input wire clk,rst_n,request_slot,input wire[4:0]row,
 input wire[16:0]token,input wire[ID_W-1:0]identity,
 output reg word_v,output reg[255:0]word_data,output reg[3:0]word_beat,
 output reg[16:0]word_row,word_token,output reg[ID_W-1:0]word_identity,
 output reg fault);
 reg issuing;reg[3:0]next_beat;reg[4:0]held_row;
 reg[16:0]held_token;reg[ID_W-1:0]held_id;
 wire issue=request_slot||issuing;
 wire[4:0]ir=request_slot?row:held_row;
 wire[3:0]ib=request_slot?4'd0:next_beat;
 wire[16:0]it=request_slot?token:held_token;
 wire[ID_W-1:0]ii=request_slot?identity:held_id;
 reg re0,re1;reg[11:0]address;
 wire[273:0]q0,q1;
 reg[5:0]valid_pipe;
 reg[3:0]beat_pipe[0:5];reg[16:0]row_pipe[0:5],token_pipe[0:5];
 reg[ID_W-1:0]id_pipe[0:5];
 reg select_read,select_capture;
 reg[255:0]capture_q,pad0,pad1,pad2;
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   issuing<=0;next_beat<=0;held_row<=0;held_token<=0;held_id<=0;
   re0<=0;re1<=0;address<=0;valid_pipe<=0;word_v<=0;word_data<=0;
   word_beat<=0;word_row<=0;word_token<=0;word_identity<=0;fault<=0;
   select_read<=0;select_capture<=0;
   for(i=0;i<6;i=i+1)begin beat_pipe[i]<=0;row_pipe[i]<=0;token_pipe[i]<=0;id_pipe[i]<=0;end
  end else begin
   re0<=issue&&!ib[0];re1<=issue&&ib[0];
   if(issue)address<={4'd0,ir,ib[3:1]};
   select_read<=ib[0];select_capture<=select_read;
   if(request_slot)begin
    if(issuing||(|valid_pipe)||row>=VALID_ROWS||GLOBAL_ROW0+row>=129280||token>=129280)fault<=1;
    held_row<=row;held_token<=token;held_id<=identity;issuing<=1;next_beat<=1;
   end else if(issuing)begin
    if(next_beat==15)issuing<=0;else next_beat<=next_beat+1'b1;
   end
   valid_pipe<={valid_pipe[4:0],issue};beat_pipe[0]<=ib;
   row_pipe[0]<=17'(GLOBAL_ROW0)+ir;token_pipe[0]<=it;id_pipe[0]<=ii;
   for(i=1;i<6;i=i+1)begin beat_pipe[i]<=beat_pipe[i-1];row_pipe[i]<=row_pipe[i-1];token_pipe[i]<=token_pipe[i-1];id_pipe[i]<=id_pipe[i-1];end
   word_v<=valid_pipe[5];word_data<=pad2;word_beat<=beat_pipe[5];
   word_row<=row_pipe[5];word_token<=token_pipe[5];word_identity<=id_pipe[5];
  end
 end
 // ROM q is held across the intervening parity read; capture two edges
 // after the macro read, retaining the actual macro read/capture contract.
 always @(posedge clk)begin capture_q<=select_capture?q1[255:0]:q0[255:0];pad0<=capture_q;pad1<=pad0;pad2<=pad1;end
`ifdef SYNTHESIS
 ot_rom_4096x274_m8 m0(.clk(clk),.ce_in(re0),.addr_in(address),.rd_out(q0));
 ot_rom_4096x274_m8 m1(.clk(clk),.ce_in(re1),.addr_in(address),.rd_out(q1));
`else
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("%s_0",INSTANCE)))m0(.clk(clk),.ce_in(re0),.addr_in(address),.rd_out(q0));
 ot_rom_4096x274_m8 #(.INSTANCE($sformatf("%s_1",INSTANCE)))m1(.clk(clk),.ce_in(re1),.addr_in(address),.rd_out(q1));
`endif
endmodule
`default_nettype wire
