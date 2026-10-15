`timescale 1ns/1ps
// Fixed two-edge bank scatter. No ready, credits, arbitration or retry exists.
// The compiler assigns <=8 requests to each row[1:0] lane on this serial edge.
// Input index=8*lane+k; a request on the wrong lane or two requests to one
// physical bank is a schedule defect, reported as fault. No request is delayed.
// Each instance transports one128b slice; four instances have identical control.
// Two aligned16-row dense/QR packets can occupy one32-bank service edge.
module dsfd_vm_static_scatter #(parameter integer DW=128)(
 input wire ck,rst_n,
 input wire [31:0] i_v,i_we,
 input wire [447:0] i_row,
 input wire [127:0] i_mask,
 input wire [32*DW-1:0] i_data,
 input wire [255:0] i_tag,
 output reg [31:0] o_v,o_we,
 output reg [287:0] o_addr,
 output reg [127:0] o_mask,
 output reg [32*DW-1:0] o_data,
 output reg [255:0] o_tag,
 output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];

 reg [31:0] vq,weq;reg [447:0] rowq;reg [127:0] mq;
 reg [32*DW-1:0] dq;reg [255:0] tq;
 always @(posedge ck or negedge rn)if(!rn)vq<=0;else vq<=i_v;
 always @(posedge ck)begin weq<=i_we;rowq<=i_row;mq<=i_mask;dq<=i_data;tq<=i_tag;end
 integer b,k,j,n; reg [13:0] row; reg [4:0] bank;
 reg bad;reg [31:0] nv,nwe;reg [287:0] na;reg [127:0] nm;
 reg [32*DW-1:0] nd;reg [255:0] nt;
 always @*begin
  nv=0;nwe=0;na=0;nm=0;nd=0;nt=0;bad=0;
  for(b=0;b<32;b=b+1)begin
   n=0;
   for(k=0;k<8;k=k+1)begin
    j=8*(b%4)+k;row=rowq[14*j+:14];
`ifdef OT_VM_SCATTER_MUT_HASH
    bank=row[4:0];
`else
    bank=row[4:0] ^ {row[7:5],2'b00};
`endif
    if(vq[j] && row[1:0]!=(j/8))bad=1;
    if(vq[j] && bank==b)begin
     n=n+1;nwe[b]=weq[j];na[9*b+:9]=row[13:5];nm[4*b+:4]=mq[4*j+:4];
`ifdef OT_VM_SCATTER_MUT_DATA
     nd[DW*b+:DW]=dq[DW*(8*(b%4)+((k+1)%8))+:DW];
`else
     nd[DW*b+:DW]=dq[DW*j+:DW];
`endif
     nt[8*b+:8]=tq[8*j+:8];
    end
   end
   nv[b]=(n==1);if(n>1)bad=1;
  end
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin o_v<=0;fault<=0;end
  else begin o_v<=nv;fault<=fault|bad;end
 end
 always @(posedge ck)begin o_we<=nwe;o_addr<=na;o_mask<=nm;o_data<=nd;o_tag<=nt;end
endmodule
