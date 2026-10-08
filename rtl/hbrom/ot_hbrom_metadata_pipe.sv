`timescale 1ns/1ps
// Registered control only; two physical chains, stage-local comparison, no added cycle.
module ot_hbrom_metadata_pipe #(parameter integer W=1,D=1)(
 input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q,
 output wire [D:0] taps,output wire fault);
 generate if(D==0) begin:g_wire
   assign q=d;assign taps=d[0];assign fault=0;
 end else begin:g_pipe
   (* keep *) reg [W-1:0] a[1:D];
   (* keep *) reg [W-1:0] b[1:D];
   wire [D-1:0] bad;
   integer k;
   always @(posedge clk or negedge rst_n) begin
     if(!rst_n) for(k=1;k<=D;k=k+1) a[k]<=0;
     else begin a[1]<=d;for(k=2;k<=D;k=k+1) a[k]<=a[k-1];end
   end
   integer j;
   always @(posedge clk or negedge rst_n) begin
     if(!rst_n) for(j=1;j<=D;j=j+1) b[j]<=0;
     else begin b[1]<=d;for(j=2;j<=D;j=j+1) b[j]<=b[j-1];end
   end
   assign taps[0]=d[0];
   genvar i;for(i=1;i<=D;i=i+1) begin:g_compare
     assign bad[i-1]=(a[i]!=b[i]);assign taps[i]=a[i][0];
   end
   (* keep *) reg poison_a,poison_b;
   always @(posedge clk or negedge rst_n) if(!rst_n) poison_a<=0;else poison_a<=poison_a|poison_b|(|bad);
   always @(posedge clk or negedge rst_n) if(!rst_n) poison_b<=0;else poison_b<=poison_b|poison_a|(|bad);
   assign fault=(|bad)|poison_a|poison_b;
   assign q=a[D];
 end endgenerate
endmodule
