`default_nettype none
// Actual fixed3edge blockmax/newest path. Layout perquadrant matches69b
// payload {ids2x17,vals2x16,lv2,last1}, plusquarter2+valid1 =>72b.
module ot_hbm_idx_candidate_static #(parameter integer MUT=0)(
 input wire[3:0]clk,input wire rst_n,input wire[19:0]position,input wire enable,
 input wire[2439:0]scores,
 output wire[287:0]candidates
);
 function automatic [15:0] orderkey(input[15:0]x);orderkey=x[15]?~x:(x^16'h8000);endfunction
 for(genvar q=0;q<4;q=q+1)begin:gq
  reg[15:0]a[0:7],b[0:3],c[0:1];
  reg[2:0]v,last;
  reg[33:0]ids0,ids1,ids2;
  wire[609:0]s=scores[q*610+:610];
  wire[15:0]lv=s[33:18];
  wire[255:0]vals=s[289:34];
  wire[319:0]ids=s[609:290];
  wire[255:0]pinned;
  for(genvar l=0;l<16;l=l+1)begin:pinlane
   wire newest=(l%8==0)&&lv[l]&&(ids[l*20+3+:17]==position[19:3]);
   assign pinned[l*16+:16]=!lv[l]?16'hff80:((newest&&MUT!=1)?16'h7f80:vals[l*16+:16]);
  end
  always @(posedge clk[q] or negedge rst_n)begin
   if(!rst_n)begin v<=0;last<=0;ids0<=0;ids1<=0;ids2<=0;end
   else begin
    v<={v[1:0],s[0]&&enable};last<={last[1:0],s[1]};
    ids0<={ids[163+:17],ids[3+:17]};ids1<=ids0;ids2<=ids1;
    for(integer i=0;i<8;i=i+1)a[i]<=(orderkey(pinned[i*32+:16])>=orderkey(pinned[i*32+16+:16]))?pinned[i*32+:16]:pinned[i*32+16+:16];
    for(integer i=0;i<4;i=i+1)b[i]<=(orderkey(a[2*i])>=orderkey(a[2*i+1]))?a[2*i]:a[2*i+1];
    for(integer i=0;i<2;i=i+1)c[i]<=(orderkey(b[2*i])>=orderkey(b[2*i+1]))?b[2*i]:b[2*i+1];
   end
  end
  assign candidates[q*72+:72]={ids2,{c[1],c[0]},(c[1]!=16'hff80),(c[0]!=16'hff80),2'(q),last[2],v[2]};
 end
endmodule
`default_nettype wire
