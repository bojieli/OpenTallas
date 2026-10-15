`timescale 1ns/1ps
// Actual fixed capture transport. Source ports and per-source capture lane /
// storage slot come from the compiler. Up to3 records per destination bank.
// No arbitration: duplicate destination+capture-lane is a schedule fault.
// Source sampledE0 ->registered outputE1 ->receiving write storage sampleE2.
// One8bank quarter leaf has~11400clock sinks for48source records, below15k.
module dsfd_vm_static_wdispatch128 #(
 parameter integer NSRC=48,parameter integer NBANK=8,parameter integer BANK_BASE=0)(
 input wire ck,rst_n,
 input wire [NSRC-1:0] i_v,input wire [14*NSRC-1:0] i_row,
 input wire [4*NSRC-1:0] i_mask,input wire [128*NSRC-1:0] i_data,
 input wire [8*NSRC-1:0] i_tag,input wire [2*NSRC-1:0] i_capture_lane,i_storage_slot,
 output reg [3*NBANK-1:0] o_v,output reg [6*NBANK-1:0] o_slot,
 output reg [42*NBANK-1:0] o_row,output reg [12*NBANK-1:0] o_mask,
 output reg [384*NBANK-1:0] o_data,output reg [24*NBANK-1:0] o_tag,
 output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg [NSRC-1:0] qv;reg [14*NSRC-1:0] qr;reg [4*NSRC-1:0] qm;
 reg [128*NSRC-1:0] qd;reg [8*NSRC-1:0] qt;reg [2*NSRC-1:0] ql,qs;
 always @(posedge ck or negedge rn)if(!rn)qv<=0;else qv<=i_v;
 always @(posedge ck)begin qr<=i_row;qm<=i_mask;qd<=i_data;qt<=i_tag;ql<=i_capture_lane;qs<=i_storage_slot;end
 wire [3*NBANK-1:0] hit,dup;
 genvar g;generate for(g=0;g<3*NBANK;g=g+1)begin:record
  reg h,d;reg [13:0] r;reg [3:0] m;reg [127:0] w;reg [7:0] t;reg [1:0] s;
  reg [4:0] b;integer c;
  always @*begin
   h=0;d=0;r=0;m=0;w=0;t=0;s=0;b=0;
   for(c=0;c<NSRC;c=c+1)begin
    b=qr[14*c+:5]^{qr[14*c+5+:3],2'b00};
    if(qv[c] && b==BANK_BASE+g/3 && ql[2*c+:2]==g%3)begin
     if(h)d=1;h=1;r=r|qr[14*c+:14];m=m|qm[4*c+:4];
     w=w|qd[128*c+:128];t=t|qt[8*c+:8];s=s|qs[2*c+:2];
    end
   end
  end
  assign hit[g]=h;assign dup[g]=d;
  always @(posedge ck)begin
   o_row[14*g+:14]<=r;o_mask[4*g+:4]<=m;o_data[128*g+:128]<=w;o_tag[8*g+:8]<=t;
`ifdef OT_VM_WDISPATCH_MUT_SLOT
   o_slot[2*g+:2]<=s^2'd1;
`else
   o_slot[2*g+:2]<=s;
`endif
  end
 end endgenerate
 reg bad;reg [4:0] bank;integer c;
 always @*begin
  bad=|dup;bank=0;
  for(c=0;c<NSRC;c=c+1)begin
   bank=qr[14*c+:5]^{qr[14*c+5+:3],2'b00};
   if(qv[c] && bank>=BANK_BASE && bank<BANK_BASE+NBANK && ql[2*c+:2]>=3)bad=1;
  end
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin o_v<=0;fault<=0;end else begin o_v<=hit;fault<=fault|bad;end
endmodule
