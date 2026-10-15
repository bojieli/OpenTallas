`timescale 1ns/1ps
module tb_qkd_host_boot_dispatch_lifecycle;
 parameter MUT=0;
 reg ck=0;always #5 ck=~ck;reg rn=0,release_boot=0;reg[289:0]ing=0;
 wire ic;wire[289:0]kv;wire[282:0]hb;reg kcr=0,hcr=0;reg[127:0]acks=0;
 wire image_check,prefix,fault;wire[31:0]issued,landed;integer kvn=0,hbn=0,ends=0;integer c=0;
 reg[127:0]ad[0:7];
 qkd_host_boot_dispatch #(.MUT(MUT))dut(ck,ck,rn,release_boot,ing,ic,kv,kcr,hb,hcr,image_check,acks,prefix,landed,issued,fault);
 always @(posedge ck)begin
  c++;kcr<=kv[0];hcr<=hb[0];acks<=ad[7];ad[0]<=0;for(integer k=1;k<8;k++)ad[k]<=ad[k-1];
  if(kv[0])begin if(kv[33:2]!=32'hffffffff)begin kvn++;ad[0][kv[8:2]]<=1;end end
  if(hb[0])begin if(hb[1])ends++;else begin hbn++;ad[0][hb[8:2]]<=1;end end
  if(rn&&fault)$fatal(1,"unexpected lifecycle fault");
 end
 task word(input[31:0]addr,input[255:0]data);
  @(negedge ck);ing={data,addr,1'b1,1'b1};@(negedge ck);ing=0;
 endtask
 initial begin
  for(integer i=0;i<8;i++)ad[i]=0;repeat(3)@(negedge ck);rn=1;
  word(32'h80000001,256'h5);word(32'hffffffff,256'h64);word(32'h00000002,256'h6);
  wait(ends==1);repeat(20)@(negedge ck);
  if(kvn!=0||hbn!=1||!image_check||landed!=1)$fatal(1,"new payload escaped unaccepted image barrier");
  release_boot=1;@(negedge ck);release_boot=0;
  wait(kvn==1);wait(landed==2);word(32'hffffffff,256'h99);
  repeat(20)@(negedge ck);
  if(ends!=1||image_check)$fatal(1,"KV-only warm marker started a new embedding image check");
  $display("PASS dispatcher holds payload until image barrier accepted; KV-only warm marker reuses valid image");$finish;
 end
 initial begin #3000;$fatal(1,"watchdog");end
endmodule
