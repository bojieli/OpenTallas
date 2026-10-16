`timescale 1ns/1ps
// wb_ready is pin-captured in the vp4 controller (H-HARDEN 10-15 r4): a write-back not ready at the first drain is an
// exceptional fault reported exactly ONE edge after the cursor reference (fed DESC_LAT=4 later); normal runs unchanged.
module tb_dma_vp4_wbready_fault;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;reg [31:0] cycle=0;reg wbr=0;
 reg mv_v=0;reg [226:0] mv=0;reg [31:0] issue_at=0,drain_at=0;
 reg dv[1:4];reg [226:0] dm[1:4];reg [31:0] di[1:4],dd[1:4];
 always @(posedge clk)begin cycle<=cycle+1;dv[1]<=mv_v;dm[1]<=mv;di[1]<=issue_at;dd[1]<=drain_at;
  for(integer k=2;k<=4;k=k+1)begin dv[k]<=dv[k-1];dm[k]<=dm[k-1];di[k]<=di[k-1];dd[k]<=dd[k-1];end end
 wire fa,fb;wire [2055:0] rr;wire [135:0] rqa;reg [6:0] response_v[0:7];
 always @(posedge clk)for(integer b=0;b<8;b=b+1)response_v[b]<=rst_n?{response_v[b][5:0],rqa[b*17+16]}:7'b0;
 for(genvar b=0;b<8;b=b+1)begin:R assign rr[b*257+:257]={response_v[b][6],256'd0};end
 ot_hgi_dma_back_static_cursor ref_i(.clk(clk),.rst_n(rst_n),.cycle(cycle),.mv_v(dv[4]),.mv(dm[4]),.issue_at(di[4]),.drain_at(dd[4]),
  .mv_wb_bank(1'b0),.mv_wb_epoch(16'd0),.mv_fault(fa),.rq(rqa),.rr(rr),.wb_ready(wbr),.wa(12'd0));
 ot_hgi_dma_back_static_vp4_controller dut(.clk(clk),.rst_n(rst_n),.cycle_in(cycle),.mv_v(mv_v),.mv(mv),.issue_at(issue_at),.drain_at(drain_at),
  .mv_wb_bank(1'b0),.mv_wb_epoch(16'd0),.mv_fault(fb),.rr_valid_i({rr[7*257+256],rr[6*257+256],rr[5*257+256],rr[4*257+256],rr[3*257+256],rr[2*257+256],rr[1*257+256],rr[256]}),.wb_ready(wbr),.wa(12'd0));
 integer ta=-1,tb=-1,checks=0;
 always @(negedge clk)if(rst_n)begin if(fa&&ta<0)ta=cycle;if(fb&&tb<0)tb=cycle;end
 function automatic [226:0] descriptor(input integer nsec,input integer rows);
  descriptor={21'(nsec*8),20'(rows),16'd1,32'(nsec*32),40'h100000,3'd0,2'd0,16'd1,32'(((nsec+7)/8)*64),40'd0,3'd0,2'd1};
 endfunction
 task automatic go(input reg ready);begin
  wbr=ready;ta=-1;tb=-1;rst_n=0;repeat(2)@(negedge clk);#1;rst_n=1;repeat(4)@(negedge clk);
  #1;mv=descriptor(16,2);issue_at=cycle+6;drain_at=cycle+16;mv_v=1;@(negedge clk);#1;mv_v=0;repeat(40)@(negedge clk);
 end endtask
 initial begin
  for(integer b=0;b<8;b=b+1)response_v[b]=0;
  for(integer k=1;k<=4;k=k+1)begin dv[k]=0;dm[k]=0;di[k]=0;dd[k]=0;end
  go(1);if(ta>=0||tb>=0)$fatal(1,"ready run faulted ref%0d dut%0d",ta,tb);checks++;
  go(0);if(ta<0)$fatal(1,"reference saw no not-ready fault");checks++;
  if(tb!==ta+1)$fatal(1,"not-ready fault edge dut%0d ref%0d (want ref+1)",tb,ta);checks++;
  $display("DMA_WBREADY_FAULT_PASS checks=%0d ref_edge=%0d dut_edge=%0d fault_extra_edges=1 normal_extra_edges=0",checks,ta,tb);$finish;
 end
endmodule
