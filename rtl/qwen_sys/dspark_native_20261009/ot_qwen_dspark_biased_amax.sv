`timescale 1ns/1ps
// Full released vocabulary rank slice: consumes actual already-rounded
// FP32(base logits + W2.W1) from the native SU producer. No duplicate bias
// addition, reordering, host argmax or assumed 50-cycle vocabulary scan.
module ot_qwen_dspark_biased_amax #(parameter integer ENABLE=0, MUT_TIE=0)(
 input wire clk,rst_n,input wire i_v,output wire i_r,
 input wire [2047:0] i_logits,input wire [17:0] i_base,
 input wire [1:0] i_rank,input wire [63:0] i_id,input wire i_last,
 output reg o_v,input wire o_r,output reg [17:0] o_token,
 output reg [31:0] o_value,output reg [63:0] o_id,
 output reg fault
);
 localparam integer ROWS=37984;
 reg [15:0] received;
 reg active,closing;
 reg [63:0] identity;
 reg [1:0] rank;
 wire fire=i_v&&i_r;
 wire final_expected=received==593;
 wire bad_shape=(i_base!=18'(received*64))||(i_last!=final_expected)||
    (active&&((identity!=i_id)||(rank!=i_rank)));
 assign i_r=(ENABLE!=0)&&!fault&&!closing&&!o_v;
 function automatic [31:0] key(input [31:0] x);
  reg [31:0] c;begin c=(x==32'h80000000)?32'b0:x;key=c[31]?~c:c|32'h80000000;end
 endfunction
 reg [31:0] vals[0:5][0:31];
 reg [17:0] ids[0:5][0:31];
 reg valid_lane[0:5][0:31];
 reg [5:0] valid,last;
 reg [63:0] tag[0:5];
 reg have_best;
 reg [31:0] best_val;
 reg [17:0] best_id;
 reg bad_numeric;
 integer l,s;reg [31:0] a,b;reg [17:0] ai,bi;reg av,bv,take_a;
 always @* begin
  bad_numeric=0;
  for(integer n=0;n<64;n=n+1)
   if((!final_expected||n<32)&&i_logits[n*32+23+:8]==8'hff)bad_numeric=1;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin received<=0;active<=0;closing<=0;valid<=0;last<=0;have_best<=0;o_v<=0;fault<=0;end
  else begin
   valid<={valid[4:0],fire&&!bad_shape&&!bad_numeric};
   last<={last[4:0],fire&&i_last};
   if(fire)begin
    if(bad_shape||bad_numeric)fault<=1;
    else begin
     active<=1;received<=received+1'b1;
     if(!active)begin identity<=i_id;rank<=i_rank;end
     if(i_last)closing<=1;
    end
   end
   if(o_v&&o_r)begin o_v<=0;closing<=0;active<=0;received<=0;have_best<=0;end
   if(valid[5]&&!fault)begin
    if(!have_best||key(vals[5][0])>key(best_val)||
       (key(vals[5][0])==key(best_val)&&((MUT_TIE!=0)?ids[5][0]>best_id:ids[5][0]<best_id)))begin
     best_val<=vals[5][0];best_id<=ids[5][0];
    end
    have_best<=1;
    if(last[5])begin
     o_v<=1;o_id<=tag[5];
     if(!have_best||key(vals[5][0])>key(best_val)||
       (key(vals[5][0])==key(best_val)&&((MUT_TIE!=0)?ids[5][0]>best_id:ids[5][0]<best_id)))begin
      o_token<=ids[5][0];o_value<=vals[5][0];
     end else begin o_token<=best_id;o_value<=best_val;end
    end
   end
  end
 end
 always @(posedge clk)begin
  tag[0]<=i_id;
  for(l=0;l<32;l=l+1)begin
   a=i_logits[(2*l)*32+:32];b=i_logits[(2*l+1)*32+:32];
   ai=18'(i_rank*ROWS)+i_base+18'(2*l);bi=ai+1'b1;
   av=!final_expected||2*l<32;bv=!final_expected||2*l+1<32;
   take_a=!bv||(av&&(key(a)>key(b)||(key(a)==key(b)&&MUT_TIE==0)));
   vals[0][l]<=take_a?a:b;ids[0][l]<=take_a?ai:bi;valid_lane[0][l]<=av||bv;
  end
  for(s=1;s<6;s=s+1)begin
   tag[s]<=tag[s-1];
   for(l=0;l<(32>>s);l=l+1)begin
    a=vals[s-1][2*l];b=vals[s-1][2*l+1];ai=ids[s-1][2*l];bi=ids[s-1][2*l+1];
    av=valid_lane[s-1][2*l];bv=valid_lane[s-1][2*l+1];
    take_a=!bv||(av&&(key(a)>key(b)||(key(a)==key(b)&&((MUT_TIE!=0)?ai>bi:ai<bi))));
    vals[s][l]<=take_a?a:b;ids[s][l]<=take_a?ai:bi;valid_lane[s][l]<=av||bv;
   end
  end
 end
endmodule
