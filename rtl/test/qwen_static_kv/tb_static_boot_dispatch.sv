`timescale 1ns/1ps
module tb_static_boot_dispatch #(parameter integer MUT=0,NEG=0);
 reg ck=0;always #5 ck=~ck;
 reg rst=0;reg[142:0]pr=0;reg[3:0]target=1;reg ready=0,source_fault=0,active=0;
 reg[15:0]epoch=123;reg[63:0]digest=0;reg[159:0]applied=0;reg[2:0]configured=0;
 wire lw,ww,ow;wire[8:0]la;wire[7:0]wa,ga;wire[1:0]oa;wire[63:0]ld,wd,gd,cd;wire[31:0]od,lwe,fwe;
 wire[127:0]cwe,last;wire[4:0]ca;wire setup,fault;wire[7:0]code;wire[15:0]ie;wire[63:0]id;
 qkd_static_kv_boot_dispatch #(.MUT(MUT))dut(.ck(ck),.rst_n(rst),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),.boot_image_fault(source_fault),.boot_image_epoch(epoch),.boot_image_digest(digest),.execution_active(active),.sink_applied(applied),.local_configured(configured),.sink_fault(1'b0),.layer_we(lw),.layer_addr(la),.layer_data(ld),.writer_we(ww),.writer_addr(wa),.writer_data(wd),.ownership_we(ow),.ownership_addr(oa),.ownership_data(od),.landing_we(lwe),.front_we(fwe),.group_addr(ga),.group_data(gd),.controller_we(cwe),.controller_addr(ca),.controller_data(cd),.controller_last(last),.setup_ready(setup),.fault(fault),.fault_code(code),.installed_epoch(ie),.installed_isa_digest(id));
 integer t,a,n,total=0;reg[31:0]group_gold;reg[127:0]pc_gold;
 function automatic[63:0]value(input integer t,input integer a);value=(t==3)?64'(a):64'h1234567800000000^(64'(t)<<32)^64'(a);endfunction
 task tick;begin @(posedge ck);#1;end endtask
 task check_word(input integer t,input integer a);begin
  if({lw,ww,ow,lwe!=0,fwe!=0,cwe!=0}!=={t==1,t==2,t==3,t==4,t==5,t>=6})$fatal(1,"wrong actual configuration target");
  if(t==1&&(la!=9'(a)||ld!=value(t,a)))$fatal(1,"layer data differs");
  if(t==2&&(wa!=8'(a)||wd!=value(t,a)))$fatal(1,"writer data differs");
  if(t==3&&(oa!=2'(a)||od!=32'(value(t,a))))$fatal(1,"ownership data differs");
  if(t==4||t==5)begin group_gold=32'b1<<(a/6);if((t==4?lwe:fwe)!=group_gold||ga!=8'(a%6)||gd!=value(t,a))$fatal(1,"actual group/local address differs");end
  if(t>=6)begin pc_gold=128'b1<<(32*(t-6)+a/32);if(cwe!=pc_gold||ca!=5'(a%32)||cd!=value(t,a)||last!=((a%32==31)?pc_gold:128'd0))$fatal(1,"actual PC/local address/seal differs");end
  total=total+1;
 end endtask
 initial begin
  repeat(3)tick();@(negedge ck);rst=1;tick();
  if(NEG!=0)begin
   @(negedge ck);
   if(NEG==1)begin target=2;pr[74]=1;pr[63:0]=55;end
   if(NEG==2)ready=1;
   if(NEG==3)begin pr[74]=1;pr[63:0]=55;end
   if(NEG==4)begin active=1;pr[74]=1;end
   if(NEG==5)pr[142]=1;
   tick();
   if(NEG==3)begin @(negedge ck);epoch=124;pr[73:64]=1;tick();end
   if(lw||ww||ow||lwe!=0||fwe!=0||cwe!=0)$fatal(1,"forbidden configuration escaped rejected replay");
   if(!fault)$fatal(1,"missing exact target/order/epoch/runtime fault");
   $display("PASS boot dispatcher rejected invalid replay NEG=%0d",NEG);$finish;
  end
  for(t=1;t<=9;t=t+1)begin
   case(t)1:n=327;2:n=181;3:n=4;4,5:n=192;default:n=1024;endcase
   @(negedge ck);ready=0;target=4'(t);
   for(a=0;a<n;a=a+1)begin
    pr=0;pr[74]=1;pr[73:64]=10'(a);pr[63:0]=value(t,a);tick();check_word(t,a);@(negedge ck);
   end
   pr=0;tick();@(negedge ck);ready=1;digest=64'(t);tick();tick();if(fault)$fatal(1,"valid exact replay faulted %h",code);
  end
  @(negedge ck);ready=0;target=0;tick();@(negedge ck);ready=1;digest=64'h123456789abcdef0;configured=7;tick();tick();
  if(setup)$fatal(1,"claimed setup before actual HBM applications");
  @(negedge ck);applied={160{1'b1}};tick();if(!setup||ie!=123||id!=digest)$fatal(1,"actual authorized setup failed");
  @(negedge ck);ready=0;tick();if(setup)$fatal(1,"new BEGIN did not revoke setup");
  source_fault=1;tick();if(!fault)$fatal(1,"HOST source fault lost");
  $display("PASS actual boot dispatch nine configuration images %0d writes, all128PC/32group targets, actual application guard",total);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
