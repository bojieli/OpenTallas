`timescale 1ns/1ps
module tb_hgi_coll_vm_idx_ingress;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,mode=0;reg [3:0] ev=0,vv=0,iv=0;reg [2179:0] vd=0,id=0;
 wire [3:0] ov;wire [2179:0] od;wire fault;
 reg [3:0] oldv=0;reg [2179:0] oldd=0;integer checks=0;
 ot_hgi_coll_vm_idx_ingress #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.mode_idx(mode),.expected_v(ev),
 .vm_v(vv),.idx_v(iv),.vm_d(vd),.idx_d(id),.out_v(ov),.out_d(od),.fault(fault));
 task step(input bit m,input [3:0] e,input [3:0] v,input [3:0] i,input integer n);
  begin
   @(negedge clk);mode=m;ev=e;vv=v;iv=i;
   for(integer b=0;b<2180;b=b+1)begin vd[b]=((b+n*31)^(n>>(b%5)))&1;id[b]=~vd[b];end
   @(posedge clk);#1;
   if(ov!==oldv)$fatal(1,"registered ingress validity timing");
   for(integer l=0;l<4;l=l+1)if(oldv[l]&&od[l*545+:545]!==oldd[l*545+:545])$fatal(1,"typed ingress mode/data timing");
   oldv=m?i:v;oldd=m?id:vd;checks++;
  end
 endtask
 task reset;
  begin @(negedge clk);rst_n=0;mode=0;ev=0;vv=0;iv=0;oldv=0;oldd=0;repeat(3)@(negedge clk);rst_n=1;end
 endtask
 initial begin
  reset();
  for(integer c=0;c<64;c=c+1)begin
   if(c%2==0)step(0,4'(c),4'(c),0,c);else step(1,4'(c),0,4'(c),c);
  end
  step(0,0,0,0,64);step(0,0,0,0,65);if(fault)$fatal(1,"legal typed mode calendar fault");
  step(0,1,1,1,66);step(0,0,0,0,67);if(!fault)$fatal(1,"inactive IDX producer conflict undetected");
  // A sticky fault must not shift subsequent legal mode/data launches.
  step(1,15,0,15,68);step(0,15,15,0,69);step(0,0,0,0,70);
  if(!fault)$fatal(1,"sticky fault lost");
  reset();step(1,2,0,1,71);step(0,0,0,0,72);if(!fault)$fatal(1,"selected bitmap mismatch undetected");
  $display("VM_IDX_INGRESS PASS checks%0d actualwidth4x545 fixed2edges_to_downstream_capture",checks);$finish;
 end
endmodule
