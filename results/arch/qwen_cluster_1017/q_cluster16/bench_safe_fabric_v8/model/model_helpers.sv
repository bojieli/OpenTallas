
`timescale 1ns/1ps
module cb16_model_reset #(parameter EDGES=2)(input ck,d,output q);
 wire[EDGES:0]s;assign s[0]=d;
 genvar j;generate for(j=0;j<EDGES;j=j+1)begin:g reg v;always@(posedge ck)v<=s[j];assign s[j+1]=v;end endgenerate
 assign q=s[EDGES];
endmodule
module cb16_model_hw #(parameter W=258)(input ck,rsi,input[W-1:0]i,output[4*W-1:0]bank,output[139:0]epo,output[43:0]vld);
 qfd_c_land_safe_w #(.W(W)) a(ck,rsi,i,bank,vld);
 reg[31:0]cycle=0;always@(posedge ck)cycle<=cycle+1'b1;
 reg[2:0]wc;reg[2:0]tag[0:3];reg[31:0]born[0:3];
 always@(posedge ck)if(!a.g_slice[0].u.r2)wc<=0;else begin tag[wc%4]<=wc;born[wc%4]<=cycle;wc<=wc+1'b1;end
 genvar s;generate for(s=0;s<4;s=s+1)begin:t assign epo[35*s+:35]={born[s],tag[s]};end endgenerate
endmodule
module cb16_model_hr #(parameter W=258,K=2)(input ck,rsi,input[4*W-1:0]bank,input[139:0]epo,input[43:0]vld,output[W-1:0]o);
 qfd_c_land_safe_r #(.W(W),.K(K)) a(ck,rsi,bank,vld,o);
 reg[2:0]rc;wire[2:0]expected=rc-K;wire[1:0]slot=expected[1:0];
 reg[31:0]cycle=0;always@(posedge ck)cycle<=cycle+1'b1;
 always@(posedge ck)begin
  if(!a.g_slice[0].u.r2)rc<=0;else rc<=rc+1'b1;
  if(a.g_slice[0].u.warm&&vld[slot]&&(epo[slot*35+:3]!==expected||cycle-epo[slot*35+3+:32]!=K))
   $fatal(1,"SAFE_PARENT_EPOCH %m slot%0d tag%0d expected%0d absoluteage%0d K%0d",slot,epo[slot*35+:3],expected,cycle-epo[slot*35+3+:32],K);
 end
endmodule
module cb16_model_w #(parameter W=516,D=4)(input ck,input[1:0]rsi,input[W-1:0]i,output[4*W-1:0]bank,output[279:0]epo,output[87:0]vld);
 localparam H=W/2;wire[4*H-1:0]b0,b1;
 cb16_model_hw #(.W(H)) a(ck,rsi[0],i[H-1:0],b0,epo[139:0],vld[43:0]);
 cb16_model_hw #(.W(H)) b(ck,rsi[1],i[W-1:H],b1,epo[279:140],vld[87:44]);
 genvar s;generate for(s=0;s<4;s=s+1)begin:g assign bank[s*W+:H]=b0[s*H+:H];assign bank[s*W+H+:H]=b1[s*H+:H];end endgenerate
endmodule
module cb16_model_r #(parameter W=516,D=4,K=2)(input ck,input[1:0]rsi,input[4*W-1:0]bank,input[279:0]epo,input[87:0]vld,output[W-1:0]o);
 localparam H=W/2;wire[4*H-1:0]b0,b1;
 genvar s;generate for(s=0;s<4;s=s+1)begin:g assign b0[s*H+:H]=bank[s*W+:H];assign b1[s*H+:H]=bank[s*W+H+:H];end endgenerate
 cb16_model_hr #(.W(H),.K(K)) a(ck,rsi[0],b0,epo[139:0],vld[43:0],o[H-1:0]);
 cb16_model_hr #(.W(H),.K(K)) b(ck,rsi[1],b1,epo[279:140],vld[87:44],o[W-1:H]);
endmodule
