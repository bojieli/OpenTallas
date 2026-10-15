`timescale 1ns/1ps
// One independently clocked static scatter colour. Inputs are records8*LANE+k;
// outputs are banks LANE+4*k. Same two registered edges as the whole scatter.
// No input-register replication, waiting, arbitration, credits or ready.
module dsfd_vm_static_scatter_lane #(parameter integer DW=128,parameter integer LANE=0)(
 input wire ck,rst_n,input wire [7:0] i_v,i_we,
 input wire [111:0] i_row,input wire [31:0] i_mask,
 input wire [8*DW-1:0] i_data,input wire [63:0] i_tag,
 output reg [7:0] o_v,o_we,output reg [71:0] o_addr,
 output reg [31:0] o_mask,output reg [8*DW-1:0] o_data,
 output reg [63:0] o_tag,output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg [7:0] vq,weq;reg [111:0] rowq;reg [31:0] mq;
 reg [8*DW-1:0] dq;reg [63:0] tq;
 always @(posedge ck or negedge rn)if(!rn)vq<=0;else vq<=i_v;
 always @(posedge ck)begin weq<=i_we;rowq<=i_row;mq<=i_mask;dq<=i_data;tq<=i_tag;end
 integer b,k,n;reg [13:0] row;reg [4:0] bank;
 reg bad;reg [7:0] nv,nwe;reg [71:0] na;reg [31:0] nm;
 reg [8*DW-1:0] nd;reg [63:0] nt;
 always @*begin
  nv=0;nwe=0;na=0;nm=0;nd=0;nt=0;bad=0;row=0;bank=0;n=0;
  for(b=0;b<8;b=b+1)begin
   n=0;
   for(k=0;k<8;k=k+1)begin
    row=rowq[14*k+:14];
`ifdef OT_VM_SCATTER_LANE_MUT_HASH
    bank=row[4:0];
`else
    bank=row[4:0]^{row[7:5],2'b00};
`endif
    if(vq[k] && row[1:0]!=LANE)bad=1;
    if(vq[k] && bank==4*b+LANE)begin
     n=n+1;nwe[b]=weq[k];na[9*b+:9]=row[13:5];nm[4*b+:4]=mq[4*k+:4];
`ifdef OT_VM_SCATTER_LANE_MUT_DATA
     nd[DW*b+:DW]=dq[DW*((k+1)%8)+:DW];
`else
     nd[DW*b+:DW]=dq[DW*k+:DW];
`endif
     nt[8*b+:8]=tq[8*k+:8];
    end
   end
   nv[b]=(n==1);if(n>1)bad=1;
  end
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin o_v<=0;fault<=0;end else begin o_v<=nv;fault<=fault|bad;end
 always @(posedge ck)begin o_we<=nwe;o_addr<=na;o_mask<=nm;o_data<=nd;o_tag<=nt;end
 initial if(LANE<0 || LANE>3)$error("scatter lane outside0..3");
endmodule
