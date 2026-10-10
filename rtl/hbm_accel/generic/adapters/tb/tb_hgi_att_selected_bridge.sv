`timescale 1ns/1ps
module tb_hgi_att_selected_bridge;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,en=1,window=0,rv=0,ready=1;
 reg [34:0] addr=0;reg[7:0] tag=0;
 wire rr,hv,fault;wire[337:0] q;reg[273:0] r=0;
 wire[7:0] ht;wire[255:0] hd;
 ot_hgi_att_selected_bridge u(clk,rst_n,en,window,rv,rr,addr,tag,q,ready,r,hv,ht,hd,fault);
 task reset;
  begin rv=0;r=0;rst_n=0;repeat(2)@(negedge clk);rst_n=1;@(negedge clk);end
 endtask
 task issue(input [34:0] a,input[7:0] t);
  begin addr=a;tag=t;rv=1;#0.1;
   if(rr!==1 || q[335:304]!=={a[26:0],5'd0} || q[15:0]!=={u.launch_epoch,t}) $fatal(1,"request/address/tag");
   @(negedge clk);rv=0;
  end
 endtask
 task response(input[15:0] t,input ue,input good);
  begin r={1'b1,t,ue,{8{32'h12345678}}};#0.1;
   if(good && (hv!==1 || ht!==t[7:0] || hd!=={8{32'h12345678}})) $fatal(1,"completion/data");
   if(!good && hv!==0) $fatal(1,"bad completion escaped");
   @(negedge clk);r=0;end
 endtask
 integer i;
 initial begin
  reset();ready=0;addr=35'd131071;tag=7;rv=1;
  repeat(3) begin @(negedge clk);if(rr!==0 || u.count!==0) $fatal(1,"admission without handshake");end
  ready=1;rv=0;
  for(i=0;i<8;i=i+1) issue(131071-i,i);
  rv=1;addr=0;tag=8;#0.1;if(rr!==0 || q[337]!==0) $fatal(1,"credit overflow");rv=0;
  for(i=7;i>=0;i=i-1) response({8'hA5,8'(i)},0,1);
  if(fault || u.count!==0) $fatal(1,"ledger drain");
  window=1;issue(139263,8'h40);response(16'hA640,0,1);
  reset();window=0;addr=131072;rv=1;@(negedge clk);if(!fault || q[337]) $fatal(1,"C bound alias");
  reset();window=1;addr=139264;rv=1;@(negedge clk);if(!fault) $fatal(1,"window bound alias");
  reset();window=0;issue(0,3);response(16'hA504,0,0);if(!fault)$fatal(1,"wrong identity accepted");
  reset();issue(0,3);response(16'hA503,1,0);if(!fault)$fatal(1,"UE accepted");
  reset();issue(0,3);response(16'hA503,0,1);response(16'hA503,0,0);if(!fault)$fatal(1,"duplicate accepted");
  $display("ATT_SELECTED_BRIDGE PASS handshake,8credits,bounds,identity,UE,duplicate");$finish;
 end
endmodule
