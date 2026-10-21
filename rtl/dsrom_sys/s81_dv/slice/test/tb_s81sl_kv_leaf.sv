`timescale 1ns/1ps
module tb_s81sl_kv_leaf;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,c_v=0;reg[159:0]c_d=0;
 wire busy,done,fault,xrv,xwv;wire[9:0]xra,xwa;wire[7:0]xwm;wire[255:0]xwd;
 reg xqv=0;reg[255:0]xqd=0;
 reg[127:0]mem[0:1023];reg[127:0]gainmem[0:1023],kvmem[0:1023];reg[511:0]exp[0:24];
 ot_s81sl_kv_leaf dut(.clk(clk),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.busy(busy),.done(done),.fault(fault),
 .x_rv(xrv),.x_ra(xra),.x_qv(xqv),.x_qd(xqd),.x_wv(xwv),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd));
 integer cycle=0,i,j,writes=0,ev=0,firstev=-1,lastread=-1,bad=0,first_age=-1,last_age=-1;
 reg checking=0;
 always @(posedge clk)begin
  xqv<=xrv;
  if(xrv)begin xqd<={mem[xra+1],mem[xra]};lastread=cycle;end
  if(xwv)begin
   writes=writes+1;
   for(integer k=0;k<8;k=k+1)if(xwm[k] && !($test$plusargs("MUT_DROP_EXP") && xwa>=704 && xwa<708))mem[xwa+k/4][32*(k%4)+:32]<=xwd[32*k+:32];
  end
 end
 always @(negedge clk)if(rst_n)begin
  cycle=cycle+1;
  if(checking)for(integer q=0;q<16;q=q+1)if(dut.ov[q])begin
   ev=ev+1;if(firstev<0)begin firstev=cycle;first_age=dut.age;end last_age=dut.age;
   if(dut.received!=74)$fatal(1,"KV_LEAF output before all input reads consumed");
  end
 end
 task job(input[3:0]kind,input[9:0]ibase);
  reg[127:0]im;
  begin
   im=0;im[3:0]=kind;im[31:16]=1024;
   @(negedge clk);c_d={im,8'd32,ibase,10'd672,4'd15};c_v=1;
   @(negedge clk);c_v=0;
   wait(done);@(negedge clk);
   $display("KV_LEAF_JOB kind=%0d finish_age=%0d cycle=%0d",kind,dut.age,cycle);
   if(fault)$fatal(1,"KV_LEAF job fault kind=%0d",kind);
  end
 endtask
 initial begin
  $readmemh("gain_vm.mem",gainmem);$readmemh("kv_vm.mem",kvmem);$readmemh("expected.mem",exp);
  for(i=0;i<1024;i=i+1)mem[i]=gainmem[i];
  repeat(64)@(negedge clk);rst_n=1;repeat(128)@(negedge clk);
  if($test$plusargs("BAD_ALIGN") || $test$plusargs("BAD_BOUND"))begin
   @(negedge clk);c_d={96'd0,16'd1024,16'd1,8'd32,10'd692,10'd672,4'd15};
   if($test$plusargs("BAD_ALIGN"))c_d[13:4]=673;else c_d[23:14]=900;
   c_v=1;@(negedge clk);c_v=0;repeat(4)@(negedge clk);
   if(!fault || busy || writes)$fatal(1,"KV_BAD_ADDRESS guard failed");
   $display("KV_BAD_ADDRESS REJECTED with no job or writes");$finish;
  end
  job(7,676);
  for(i=0;i<1024;i=i+1)mem[i]=kvmem[i];
  writes=0;checking=1;
  job(1,692);
  repeat(4)@(negedge clk);
  for(i=0;i<25;i=i+1)for(j=0;j<16;j=j+1)if(i!=8||j<8)begin
   if(mem[672+4*i+j/4][32*(j%4)+:32]!==exp[i][32*j+:32])begin
    if(bad<8)$display("KV_LEAF mismatch row=%0d word=%0d got=%h want=%h",i,j,mem[672+4*i+j/4][32*(j%4)+:32],exp[i][32*j+:32]);
    bad=bad+1;
   end
  end
  $display("KV_LEAF D512 events=%0d vm_pair_writes=%0d first_event=%0d last_input_read=%0d bad=%0d fault=%0d cycles=%0d first_result_age=%0d last_result_age=%0d",ev,writes,firstev,lastread,bad,fault,cycle,first_age,last_age);
  if(ev!=26||writes!=52||bad||fault||firstev<=lastread)$fatal(1,"KV_LEAF FAIL");
  $display("KV_LEAF PASS actual production KV512 normalization/RoPE/QDQ through native VM pairs");$finish;
 end
 initial begin repeat(5000)@(negedge clk);$fatal(1,"KV_LEAF finite calendar failed");end
endmodule
