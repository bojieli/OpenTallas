`timescale 1ns/1ps
module tb_s81ph_gbx_pipeline_pair;
 parameter integer CH=100, BOARD=0, N=1200;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 wire [511:0] tx[0:1]; wire [514:0] rx[0:1];
 reg [511:0] history[0:1][0:CH-1];
 wire [1:0] ir,ov; reg[1:0] iv=0,orr=0;
 reg[552:0] id[0:1]; wire[552:0] od[0:1]; wire[2:0] fault[0:1];
 integer sent[0:1], got[0:1]; integer cycle=0, stalls=0;
 function automatic [552:0] payload(input integer side, input integer n);
  reg[551:0] d; integer j;
  begin d=0;for(j=0;j<18;j++)d=(d<<32)|552'(32'hdeadbeef ^ (n*32'h9e3779b9) ^ (side<<28) ^ j); return {n%11==10,d};end
 endfunction
 genvar g;
 generate for(g=0;g<2;g++) begin: lanes
  assign rx[g]={1'b0,1'b1,history[1-g][CH-1],1'b1};
  ot_s81ph_coll_lane #(.CH_UCIE(100),.CH_BOARD(400),.SRAM(1)) u(
   .clk,.rs_n(rst_n),.ch_b(1'(BOARD)),.rx(rx[g]),.tx(tx[g]),.tf(),
   .lo_v(iv[g]),.lo_r(ir[g]),.lo_d(id[g]),.li_v(ov[g]),.li_r(orr[g]),.li_d(od[g]),.flt(fault[g]));
  integer k;
  always @(posedge clk) begin
   history[g][0]<=tx[g];for(k=1;k<CH;k++)history[g][k]<=history[g][k-1];
  end
 end endgenerate
 integer i,j;
 initial begin
  for(i=0;i<2;i++)begin sent[i]=0;got[i]=0;id[i]=0;for(j=0;j<CH;j++)history[i][j]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  repeat(4)@(negedge clk); // Respect the lane two-flop local reset release before valid/ready accounting.
  while(got[0]<N||got[1]<N)begin
   for(i=0;i<2;i++)begin iv[i]=sent[i]<N;id[i]=payload(i,sent[i]);orr[i]=(cycle%73>16);end
   @(posedge clk);
   for(i=0;i<2;i++)begin
    if(iv[i]&&ir[i])sent[i]++;
    if(iv[i]&&!ir[i])stalls++;
    if(ov[i]&&orr[i])begin
     if(od[i]!==payload(1-i,got[i]))$fatal(1,"payload/order mismatch side%0d record%0d got%h expected%h",i,got[i],od[i],payload(1-i,got[i]));
     got[i]++;
    end
    if(fault[i])$fatal(1,"lane fault side%0d code%0d",i,fault[i]);
   end
   @(negedge clk);cycle++;
   if(cycle>100000)$fatal(1,"protocol deadlock sent%0d/%0d received%0d/%0d",sent[0],sent[1],got[0],got[1]);
  end
  $display("PAIR PASS CH=%0d BOARD=%0d records=%0d/%0d cycles=%0d stalls=%0d timeouts=%0d/%0d",CH,BOARD,got[0],got[1],cycle,stalls,lanes[0].u.u_ep.st_timeouts,lanes[1].u.u_ep.st_timeouts);$finish;
 end
endmodule
