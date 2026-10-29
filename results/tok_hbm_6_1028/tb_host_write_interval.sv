`timescale 1ns/1ps
// TOK-HBM-6: measure host_write_interval (edges per accepted F24 write) on the real ingress at max AXI rate
// (AW and W presented together, bready=1, no idle between writes). Prints edges between consecutive cfg_v (= 8 writes).
module tb_host_write_interval;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,av=0,wv=0;reg[11:0]aa=0;reg[31:0]wd=0;
 wire awr,wr,bv,arr,rv,cv,dv,lv,hf;wire[1:0]bres;wire[31:0]rd;wire[7:0]tg;wire[11:0]ad,db;wire[12:0]dl;wire[15:0]lo;wire[255:0]da;
 ot_hbm_host_static_ingress dut(.clk(clk),.rst_n(rst_n),.s_awvalid(av),.s_awready(awr),.s_awaddr(aa),.s_wvalid(wv),.s_wready(wr),
  .s_wdata(wd),.s_wstrb(4'hf),.s_bvalid(bv),.s_bready(1'b1),.s_bresp(bres),.s_arvalid(1'b0),.s_arready(arr),.s_araddr(12'h0),
  .s_rvalid(rv),.s_rready(1'b1),.s_rdata(rd),.block_ready(1'b0),.program_active(1'b0),.program_fault(1'b0),
  .cfg_v(cv),.cfg_target(tg),.cfg_addr(ad),.cfg_data(da),.desc_v(dv),.desc_base(db),.desc_limit(dl),.desc_loops(lo),.launch_v(lv),.fault(hf));
 integer cy=0,last=-1,n=0,mn=1<<30,mx=0,wlast=-1,wmn=1<<30,wmx=0;
 always @(posedge clk)begin cy=cy+1;
  if(cv)begin if(last>=0)begin if(cy-last<mn)mn=cy-last;if(cy-last>mx)mx=cy-last;end last=cy;n=n+1;end
  if(bv)begin if(wlast>=0)begin if(cy-wlast<wmn)wmn=cy-wlast;if(cy-wlast>wmx)wmx=cy-wlast;end wlast=cy;end
 end
 task w(input[11:0]a,input[31:0]d);begin
  @(negedge clk);aa=a;wd=d;av=1;wv=1;
  fork begin do @(posedge clk);while(!awr);@(negedge clk);av=0;end begin do @(posedge clk);while(!wr);@(negedge clk);wv=0;end join
  while(!bv)@(negedge clk);
 end endtask
 initial begin repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  w(12'hf20,32'd48);for(integer k=0;k<8*6;k=k+1)w(12'hf24,k);repeat(10)@(negedge clk);
  if(hf)$fatal(1,"fault");
  $display("HOST_WRITE_INTERVAL bvalid-to-bvalid min %0d max %0d edges; cfg_v-to-cfg_v min %0d max %0d edges (8 writes); cfg_v count %0d",wmn,wmx,mn,mx,n);$finish;end
endmodule
