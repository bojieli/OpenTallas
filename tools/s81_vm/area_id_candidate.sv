`timescale 1ns/1ps
// Isolated compact-ID candidate, outside the production RTL inventory.
// Each bank/lane selector record is {valid,sourceID[5:0]}.
// Legal schedules are payload-exact. Duplicate seats select the last source
// and raise sticky fault; invalid schedules guarantee faults, not OR payloads.
// Functional clock ties in its bench are not a physical clock-delivery claim.
// Source sample E0 -> select pin E1 -> stripe pin E2 -> mux E3 -> slot E4.
// Drain descriptor sampled E4 -> registered drain output E5. II remains one.
module s81_area_selector #(parameter NSRC=53, BASE=0)(
 input wire ck,rst_n,input wire [NSRC-1:0] i_v,
 input wire [14*NSRC-1:0] i_row,input wire [2*NSRC-1:0] i_lane,
 output reg [24*7-1:0] o_sel,output reg fault);
 reg [NSRC-1:0] vq;reg [14*NSRC-1:0] rq;reg [2*NSRC-1:0] lq;
 reg [24*7-1:0] sel;reg bad;integer s,g,n;reg [4:0] b;
 always @(posedge ck)begin rq<=i_row;lq<=i_lane;end
 always @(posedge ck or negedge rst_n)if(!rst_n)vq<=0;else vq<=i_v;
 always @*begin
  sel=0;bad=0;b=0;n=0;
  for(g=0;g<24;g=g+1)begin
   n=0;
   for(s=0;s<NSRC;s=s+1)begin
    b=rq[14*s+:5]^{rq[14*s+5+:3],2'b00};
    if(vq[s] && b==BASE+g/3 && lq[2*s+:2]==g%3)begin sel[g*7+:6]=s;sel[g*7+6]=1;n=n+1;end
   end
   if(n>1)bad=1;
  end
  for(s=0;s<NSRC;s=s+1)begin
   b=rq[14*s+:5]^{rq[14*s+5+:3],2'b00};
   if(vq[s] && b>=BASE && b<BASE+8 && lq[2*s+:2]>=3)bad=1;
  end
 end
 always @(posedge ck or negedge rst_n)if(!rst_n)begin o_sel<=0;fault<=0;end
 else begin
`ifdef S81_AREA_MUT_SELECTOR
  o_sel<={sel[24*7-2:0],sel[24*7-1]};
`else
  o_sel<=sel;
`endif
  fault<=fault|bad;
 end
endmodule

module s81_area_stripe #(parameter NSRC=53,W=16)(
 input wire ck,rst_n,input wire [W*NSRC-1:0] i_data,
 input wire [24*7-1:0] i_sel,
 input wire [7:0] i_drain_v,input wire [15:0] i_drain_slot,
 output reg [7:0] o_v,output reg [8*W-1:0] o_data,output reg fault);
 reg [W*NSRC-1:0] d0,d1,d2;reg [24*7-1:0] sq;
 reg [7:0] dv;reg [15:0] ds;reg [23:0] cv,valid;
 reg [W-1:0] chosen[0:23],storage[0:23];
 reg [24*W-1:0] muxed;reg [23:0] hits;
 integer g,s,b,c;reg bad;reg [23:0] vn;
 always @(posedge ck)begin d0<=i_data;d1<=d0;d2<=d1;ds<=i_drain_slot;end
 always @(posedge ck or negedge rst_n)if(!rst_n)begin sq<=0;dv<=0;cv<=0;end
 else begin sq<=i_sel;dv<=i_drain_v;cv<=hits;end
 always @*begin
  muxed=0;hits=0;
  for(g=0;g<24;g=g+1)for(s=0;s<NSRC;s=s+1)if(sq[g*7+6] && sq[g*7+:6]==s)begin
   hits[g]=1;muxed[g*W+:W]=muxed[g*W+:W]|d2[s*W+:W];
  end
 end
 always @(posedge ck)begin
  for(integer k=0;k<24;k=k+1)begin
   chosen[k]<=muxed[k*W+:W];
   if(cv[k])storage[k]<=chosen[k];
  end
  for(integer k=0;k<8;k=k+1)begin
   o_data[k*W+:W]<=0;
   for(integer l=0;l<3;l=l+1)if(ds[2*k+:2]==l)o_data[k*W+:W]<=storage[3*k+l];
  end
`ifdef S81_AREA_MUT_DATA
  o_data[0]<=~storage[ds[1:0]][0];
`endif
 end
 always @*begin
  vn=valid;bad=0;
  for(b=0;b<8;b=b+1)if(dv[b])begin
   if(ds[2*b+:2]>=3)bad=1;
   else begin if(!valid[3*b+ds[2*b+:2]])bad=1;vn[3*b+ds[2*b+:2]]=0;end
  end
  for(c=0;c<24;c=c+1)if(cv[c])begin
   if(vn[c])bad=1;vn[c]=1;
  end
 end
 always @(posedge ck or negedge rst_n)if(!rst_n)begin valid<=0;fault<=0;o_v<=0;end
 else begin
  valid<=vn;fault<=fault|bad;
  for(integer k=0;k<8;k=k+1)o_v[k]<=dv[k] && ds[2*k+:2]<3 && valid[3*k+ds[2*k+:2]];
 end
endmodule

// Full shape:53 sources x128 data,8 banks x3 slots,all row/mask/tag retained.
module s81_area_quarter #(parameter NSRC=53,BASE=0)(
 input wire ck_sel,ck_meta,input wire [7:0] ck_data,input wire rst_n,
 input wire [NSRC-1:0] i_v,input wire [14*NSRC-1:0] i_row,
 input wire [2*NSRC-1:0] i_lane,input wire [4*NSRC-1:0] i_mask,
 input wire [8*NSRC-1:0] i_tag,input wire [128*NSRC-1:0] i_data,
 input wire [7:0] i_drain_v,input wire [15:0] i_drain_slot,
 output wire [7:0] o_v,output wire [111:0] o_row,output wire [31:0] o_mask,
 output wire [63:0] o_tag,output wire [1023:0] o_data,output wire fault);
 wire [24*7-1:0] sel;wire fs,fm;wire [7:0] fd;
 wire [26*NSRC-1:0] mi;wire [207:0] mo;
 s81_area_selector #(.NSRC(NSRC),.BASE(BASE)) u_sel(ck_sel,rst_n,i_v,i_row,i_lane,sel,fs);
 genvar s,k;
 generate for(s=0;s<NSRC;s=s+1)begin
  assign mi[26*s+:26]={i_tag[8*s+:8],i_mask[4*s+:4],i_row[14*s+:14]};
 end
 for(k=0;k<8;k=k+1)begin
  assign {o_tag[8*k+:8],o_mask[4*k+:4],o_row[14*k+:14]}=mo[26*k+:26];
  wire [16*NSRC-1:0] di;wire [127:0] dout;wire [7:0] unused_v;
  for(s=0;s<NSRC;s=s+1)begin assign di[16*s+:16]=i_data[128*s+16*k+:16];end
  s81_area_stripe #(.NSRC(NSRC),.W(16)) u_data(ck_data[k],rst_n,di,sel,i_drain_v,i_drain_slot,unused_v,dout,fd[k]);
  for(s=0;s<8;s=s+1)begin assign o_data[128*s+16*k+:16]=dout[16*s+:16];end
 end endgenerate
 s81_area_stripe #(.NSRC(NSRC),.W(26)) u_meta(ck_meta,rst_n,mi,sel,i_drain_v,i_drain_slot,o_v,mo,fm);
 assign fault=fs|fm|(|fd);
endmodule
