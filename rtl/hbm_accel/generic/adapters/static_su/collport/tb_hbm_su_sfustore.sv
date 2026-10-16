`timescale 1ns/1ps
module tb_hbm_su_sfustore #(parameter integer MUT=0);
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [15:0] vi_re=0,kv_we=0;reg [383:0] vi_addr=0,kv_waddr=0;reg [511:0] kv_wdata=0;
wire [511:0] vi_q;wire fault;
ot_hbm_su_static_sfustore #(.QID(2),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.clk_bank({16{clk}}),.clk_bank_macro({16{clk}}),.vi_re(vi_re),.vi_addr(vi_addr),.vi_q(vi_q),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.fault(fault));
function automatic [23:0] addr(input integer lane,row);addr=(lane | (2<<14) | ((row&127)<<7) | ((row>>7)<<16));endfunction
function automatic [31:0] data(input integer lane,row);data=32'h3f010203 ^(lane*32'h101011)^(row*32'h10001);endfunction
task tick;@(posedge clk);#1;endtask
initial begin
 repeat(4)tick();@(negedge clk);rst_n=1;
 // Each lane has its own SRAM; visit every physical row including high row bits.
 for(integer r=0;r<512;r=r+37)begin
  @(negedge clk);kv_we='1;
  for(integer n=0;n<16;n=n+1)begin kv_waddr[24*n+:24]=addr(n,r);kv_wdata[32*n+:32]=data(n,r);end
  tick();@(negedge clk);kv_we=0;tick();
 end
 for(integer r=0;r<512;r=r+37)begin
  @(negedge clk);vi_re='1;for(integer n=0;n<16;n=n+1)vi_addr[24*n+:24]=addr(n,r);
  tick();@(negedge clk);vi_re=0;tick();tick();
  for(integer n=0;n<16;n=n+1)if(vi_q[32*n+:32]!==data(n,r))$fatal(1,"SFUSTORE mismatch lane%0d row%0d actual%x expected%x",n,r,vi_q[32*n+:32],data(n,r));
  if(fault)$fatal(1,"SFUSTORE unexpected fault");
 end
 // Address identity fault is observed without rescheduling a service.
 @(negedge clk);vi_re=1;vi_addr[23:0]=addr(1,37);repeat(3)tick();if(!fault)$fatal(1,"SFUSTORE missing identity fault");
 @(negedge clk);rst_n=0;vi_re=0;repeat(3)tick();@(negedge clk);rst_n=1;
 vi_re=1;vi_addr[23:0]=addr(0,37)|(1<<23);repeat(3)tick();if(!fault)$fatal(1,"SFUSTORE missing high-read-address fault");
 @(negedge clk);rst_n=0;vi_re=0;repeat(3)tick();@(negedge clk);rst_n=1;
 kv_we=1;kv_waddr[23:0]=addr(0,37)|(1<<23);repeat(3)tick();if(!fault)$fatal(1,"SFUSTORE missing high-write-address fault");
 $display("SFUSTORE PASS 224 lane-rows exact read n+2, identity/highread/highwrite faults");$finish;
end
endmodule
