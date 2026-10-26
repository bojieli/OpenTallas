`timescale 1ns/1ps
// Component boundary inputs only: production VP owns all storage and read latency.
module tb_kv_vp;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0,cv=0,swv=0,probe=0; reg[159:0]cd=0;
 reg[9:0]swa=0,pa=0;reg[255:0]swd=0;reg[7:0]swm=255;
 wire sv,busy,done,kfault,vfault,xrv,xwv,xqv;wire[159:0]sd;
 wire[9:0]xra,xwa;wire[7:0]xwm;wire[255:0]xwd,xqd;
 wire drop=$test$plusargs("MUT_DROP_EXP") && xwa>=704 && xwa<708;
 ot_s81sl_vp vp(.clk(clk),.rst_n(rst_n),.c_v(cv),.c_d(cd),
 .sw_v(swv),.sw_a(swa),.sw_m(swm),.sw_d(swd),.cw_v(2'b0),.cw_a(24'b0),.cw_d(64'b0),
 .s_v(sv),.s_d(sd),.x_rv(xrv|probe),.x_ra(probe?pa:xra),.x_qv(xqv),.x_qd(xqd),
 .x_wv(xwv&&!drop),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd),.hq_v(1'b0),.hq_d(256'b0),.fault(vfault));
 ot_s81sl_kv_leaf dut(.clk(clk),.rst_n(rst_n),.c_v(sv),.c_d(sd),.busy(busy),.done(done),.fault(kfault),
 .x_rv(xrv),.x_ra(xra),.x_qv(xqv),.x_qd(xqd),.x_wv(xwv),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd));
 reg[127:0]gainmem[0:1023],kvmem[0:1023];reg[511:0]expected[0:24];
 integer cycle=0,i,j,bad=0,writes=0,events=0,firstage=-1,lastage=-1;
 integer reqcycle[0:2047],nr=0,nq=0;reg checking=0;
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;
  if(xrv|probe)begin reqcycle[nr]=cycle;nr=nr+1;end
  if(xqv)begin
   if(cycle-reqcycle[nq]!=4)$fatal(1,"VP extension response age=%0d expected4",cycle-reqcycle[nq]);
   nq=nq+1;
  end
  if(checking&&xwv)writes=writes+1;
 end
 always @(negedge clk)if(checking)for(integer k=0;k<16;k=k+1)if(dut.ov[k])begin
  events=events+1;if(firstage<0)firstage=dut.age;lastage=dut.age;
  if(dut.received!=74)$fatal(1,"result before all74 reads");
 end
 task preload(input bit gain);
  begin
   // Write native pairs through production VP pin registers and SRAM macros.
   for(integer r=0;r<1024;r=r+2)begin
    @(negedge clk);swv=1;swa=r;swd=gain?{gainmem[r+1],gainmem[r]}:{kvmem[r+1],kvmem[r]};
   end
   @(negedge clk);swv=0;repeat(8)@(negedge clk);
  end
 endtask
 task job(input[3:0]kind,input[9:0]ibase);
  reg[127:0]im;integer start;
  begin
   im=0;im[3:0]=kind;im[31:16]=1024;
   @(negedge clk);cd={im,8'd32,ibase,10'd672,4'd15};cv=1;start=cycle;
   @(negedge clk);cv=0;
   wait(done);@(negedge clk);
   $display("KV_VP_JOB kind=%0d adapter_finish_age=%0d vp_command_elapsed=%0d",kind,dut.age,cycle-start);
   if(kfault||vfault)$fatal(1,"production source fault");
  end
 endtask
 initial begin
  $readmemh("gain_vm.mem",gainmem);$readmemh("kv_vm.mem",kvmem);$readmemh("expected.mem",expected);
  repeat(64)@(negedge clk);rst_n=1;repeat(128)@(negedge clk);
  preload(1);job(7,676);preload(0);checking=1;job(1,692);checking=0;
  repeat(8)@(negedge clk);
  // Read back via production extension port, after the fixed drain has ended.
  for(i=0;i<50;i=i+1)begin
   @(negedge clk);probe=1;pa=672+2*i;
   @(negedge clk);probe=0;
   wait(xqv);@(negedge clk);
   for(j=0;j<8;j=j+1)if(i/2!=8||((i%2)*8+j)<8)
    if(xqd[32*j+:32]!==expected[i/2][32*((i%2)*8+j)+:32])begin
     if(bad<8)$display("KV_VP mismatch pair=%0d word=%0d got=%h want=%h",i,j,xqd[32*j+:32],expected[i/2][32*((i%2)*8+j)+:32]);bad=bad+1;
    end
   @(negedge clk);
  end
  repeat(8)@(negedge clk);
  $display("KV_VP events=%0d pair_writes=%0d bad=%0d vpfault=%0d kvfault=%0d first_result_age=%0d last_result_age=%0d requests=%0d responses=%0d",events,writes,bad,vfault,kfault,firstage,lastage,nr,nq);
  if(events!=26||writes!=52||bad||vfault||kfault||nr!=nq)$fatal(1,"KV_VP FAIL");
  $display("KV_VP PASS realVP SRAM extension4 D512 norm/RoPE/QDQ masked exponent readback");$finish;
 end
 initial begin repeat(8000)@(negedge clk);$fatal(1,"finite fixed calendar timeout");end
endmodule
