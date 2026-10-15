`timescale 1ns/1ps
// Native fixed two-edge read-command scatter. Each lane's eight compiler-assigned
// records target distinct banks. No data path, ready, queue or retry is present.
module dsfd_vm_static_rscatter(
 input wire ck,rst_n,input wire [31:0] i_v,input wire [447:0] i_row,input wire [255:0] i_tag,
 output reg [31:0] o_v,output reg [287:0] o_addr,output reg [255:0] o_tag,output reg fault
);
 reg [1:0] reset_release;
 always @(posedge ck or negedge rst_n)if(!rst_n)reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg [31:0] vq;reg [447:0] rq;reg [255:0] tq;
 always @(posedge ck or negedge rn)if(!rn)vq<=0;else vq<=i_v;
 always @(posedge ck)begin rq<=i_row;tq<=i_tag;end
 reg [31:0] nv;reg [287:0] na;reg [255:0] nt;reg bad;
 integer b,k,j,n;reg [13:0] r;reg [4:0] bank;
 always @*begin
  nv=0;na=0;nt=0;bad=0;
  for(b=0;b<32;b=b+1)begin
   n=0;
   for(k=0;k<8;k=k+1)begin
    j=8*(b%4)+k;r=rq[14*j+:14];bank=r[4:0]^{r[7:5],2'b00};
    if(vq[j] && r[1:0]!=(j/8))bad=1;
    if(vq[j] && bank==b)begin
     n=n+1;na[9*b+:9]=r[13:5];
`ifdef OT_VM_RSCATTER_MUT_TAG
     nt[8*b+:8]=tq[8*j+:8]^8'h01;
`else
     nt[8*b+:8]=tq[8*j+:8];
`endif
    end
   end
   nv[b]=(n==1);if(n>1)bad=1;
  end
 end
 always @(posedge ck or negedge rn)if(!rn)begin o_v<=0;fault<=0;end else begin o_v<=nv;fault<=fault|bad;end
 always @(posedge ck)begin o_addr<=na;o_tag<=nt;end
endmodule
