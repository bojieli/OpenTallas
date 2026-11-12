// HBM-HUB-RTL-1 11-12: the scorer W-glue fault term, before (pinned) and after (non-latching) the loop hoist.
module wf_old #(parameter integer TP=96)(input wire bv_r,input wire h_r,input wire [7:0] bi_r,input wire [11:0] nk_r,input wire [4395:0] kl_r,output reg wf);
 always @* begin
  wf=0;
  if(bv_r)begin
   if(nk_r>2736||bi_r>170)wf=1;
   for(integer j=0;j<4;j=j+1)if(!kl_r[j*1099]||kl_r[j*1099+1+:10]!==10'((4*int'(h_r)+j)*128+int'(bi_r)))wf=1;
  end
 end
endmodule
module wf_new #(parameter integer TP=96)(input wire bv_r,input wire h_r,input wire [7:0] bi_r,input wire [11:0] nk_r,input wire [4395:0] kl_r,output reg wf);
 always @* begin
  wf=0;
  if(bv_r&&(nk_r>2736||bi_r>170))wf=1;
  for(integer j=0;j<4;j=j+1)if((!kl_r[j*1099]||kl_r[j*1099+1+:10]!==10'((4*int'(h_r)+j)*128+int'(bi_r))))wf=1;
 end
endmodule
