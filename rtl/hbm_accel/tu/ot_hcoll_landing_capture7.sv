`timescale 1ns/1ps
// Actual per-port head snapshot root. Three native data/metadata stages carry
// one coherent seven-head window. Seven lookahead heads cover the six-edge
// registered pop/publication/snapshot round trip without losing CAP8 credits.
module ot_hcoll_landing_capture7(
 input wire clk,rst_n,valid,fault,input wire[3814:0]heads,input wire[7:0]epoch,input wire[3:0]count,
 output wire out_valid,out_fault,output wire[3814:0]out_heads,output wire[7:0]out_epoch,output wire[3:0]out_count
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 reg[3814:0]h[0:2];reg[7:0]e[0:2];reg[3:0]n[0:2];reg[2:0]v,f;
 always @(posedge clk)begin
  h[0]<=heads;e[0]<=epoch;n[0]<=count;
  for(integer i=1;i<3;i=i+1)begin h[i]<=h[i-1];e[i]<=e[i-1];n[i]<=n[i-1];end
 end
 always @(posedge clk or negedge rr[0])if(!rr[0])begin v<=0;f<=0;end else begin v<={v[1:0],valid};f<={f[1:0],fault};end
 assign out_heads=h[2];assign out_epoch=e[2];assign out_count=n[2];assign out_valid=v[2];assign out_fault=f[2];
endmodule
