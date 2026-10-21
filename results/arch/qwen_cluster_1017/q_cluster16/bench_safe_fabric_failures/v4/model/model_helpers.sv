
`timescale 1ns/1ps
module cb16_model_reset #(parameter EDGES=2)(input ck,d,output q);
 wire[EDGES:0]s;assign s[0]=d;
 genvar j;generate for(j=0;j<EDGES;j=j+1)begin:g
  reg v;always@(posedge ck)v<=s[j];assign s[j+1]=v;
 end endgenerate
 assign q=s[EDGES];
endmodule
module cb16_model_w #(parameter W=516,D=4)(input ck,rsi,input[W-1:0]i,output[4*W-1:0]bank,output[11:0]epo,output[87:0]vld);
 localparam H=W/2;wire[4*H-1:0]b0,b1;wire[43:0]v0,v1;
 qfd_c_land_safe_w #(.W(H)) a(ck,rsi,i[H-1:0],b0,v0);
 qfd_c_land_safe_w #(.W(H)) b(ck,rsi,i[W-1:H],b1,v1);
 genvar s;generate for(s=0;s<4;s=s+1)begin:g
  assign bank[s*W+:H]=b0[s*H+:H];assign bank[s*W+H+:H]=b1[s*H+:H];
 end endgenerate
 assign vld={v1,v0};
 reg[2:0]wc;reg[2:0]tag[0:3];integer z;
 always@(posedge ck)if(!a.g_slice[0].u.r2)wc<=0;else begin tag[wc%4]<=wc;wc<=wc+1'b1;end
 generate for(s=0;s<4;s=s+1)begin:t assign epo[3*s+:3]=tag[s];end endgenerate
endmodule
module cb16_model_r #(parameter W=516,D=4,K=2)(input ck,rsi,input[4*W-1:0]bank,input[11:0]epo,input[87:0]vld,output[W-1:0]o);
 localparam H=W/2;wire[4*H-1:0]b0,b1;
 genvar s;generate for(s=0;s<4;s=s+1)begin:g
  assign b0[s*H+:H]=bank[s*W+:H];assign b1[s*H+:H]=bank[s*W+H+:H];
 end endgenerate
 qfd_c_land_safe_r #(.W(H),.K(K)) a(ck,rsi,b0,vld[43:0],o[H-1:0]);
 qfd_c_land_safe_r #(.W(H),.K(K)) b(ck,rsi,b1,vld[87:44],o[W-1:H]);
 reg[2:0]rc;wire[2:0]expected=rc-K;wire[1:0]slot=expected[1:0];
 always@(posedge ck)begin
  if(!a.g_slice[0].u.r2)rc<=0;else rc<=rc+1'b1;
  if(a.g_slice[0].u.warm&&vld[slot]&&epo[slot*3+:3]!==expected)
   $fatal(1,"SAFE_PARENT_EPOCH %m slot%0d tag%0d expected%0d",slot,epo[slot*3+:3],expected);
 end
endmodule
