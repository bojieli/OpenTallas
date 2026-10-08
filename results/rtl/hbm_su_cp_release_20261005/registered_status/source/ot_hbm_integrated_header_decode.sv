`timescale 1ns/1ps
// Three immutable W6 header words: PC64, frame low64, frame high64.
// Syndrome/parity capture precedes correction/extraction. No decode64 call on
// the corrected-data register input; original CP checks the registered result
// before dispatch and continues to check the held full tuple during ownership.
module ot_hbm_integrated_header_decode(
 input wire clk,por_n,i_v,output wire i_r,input wire [215:0] i_code,
 output wire o_v,input wire o_r,output wire [191:0] o_data,output wire o_bad
);
 localparam [1:0] READY=0,CORRECT=1,RETURN=2;
 reg [1:0] state;
 reg [71:0] held_code[0:2];reg [6:0] held_syndrome[0:2];reg [2:0] held_overall;
 reg [191:0] data_q;reg bad_q;
 function automatic [6:0] syndrome(input [71:0] code);
  reg [6:0] s;integer k,p;
  begin
   s=0;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)
    if((p&(1<<k))!=0)s[k]=s[k]^code[p-1];
   syndrome=s;
  end
 endfunction
 function automatic [63:0] extract(input [71:0] code);
  reg [63:0] d;integer p,j;
  begin
   d=0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin d[j]=code[p-1];j=j+1;end
   extract=d;
  end
 endfunction
 wire [2:0] word_bad;wire [191:0] corrected;
 for(genvar k=0;k<3;k=k+1)begin:words
  wire [6:0] s=held_syndrome[k];
  wire correct=s!=0&&held_overall[k]&&s<=71;
  wire [71:0] corrected_code=correct?(held_code[k]^(72'b1<<(s-7'd1))):held_code[k];
  assign word_bad[k]=s!=0&&(!held_overall[k]||s>71);
  assign corrected[k*64+:64]=extract(corrected_code);
 end
 assign i_r=state==READY;assign o_v=state==RETURN;
 assign o_data=data_q;assign o_bad=bad_q;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   state<=READY;data_q<=0;bad_q<=0;held_overall<=0;
   for(integer k=0;k<3;k=k+1)begin held_code[k]<=0;held_syndrome[k]<=0;end
  end else case(state)
   READY:if(i_v&&i_r)begin
    for(integer k=0;k<3;k=k+1)begin
     held_code[k]<=i_code[k*72+:72];held_syndrome[k]<=syndrome(i_code[k*72+:72]);
     held_overall[k]<=^i_code[k*72+:72];
    end
    bad_q<=0;state<=CORRECT;
   end
   CORRECT:begin data_q<=corrected;bad_q<=|word_bad;state<=RETURN;end
   RETURN:if(o_r)state<=READY;
   default:begin bad_q<=1;state<=RETURN;end
  endcase
 end
endmodule
