`timescale 1ns/1ps
// TOK-QWEN-7 10-29: closed-loop check of the ordered D2D boot event against the HOST programme commit.
// program_ready = local install && committed, and committed needs the peer witness record, which the d2d calendar
// carries only after the boot epoch (boot_begin -> KV fwd_epoch -> KV dcal epoch_go -> witness slots). Mode 0 (fixed, as
// qkd_host_root_admission_obsx_bo1_c45): installed = setup && program_installed_local && START -> one epoch after
// START, then the witness commits and program_ready rises. Mode 1 (old predicate: program_ready) must deadlock.
module tb_boot_witness_loop;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst_n=0,request=0,setup=0,local_inst=0,start=0,running=0,committed=0;
 integer mode=0,cyc=0,first_epoch=-1,first_commit=-1,epochs=0;
 wire program_ready=local_inst&&committed;
 wire installed=setup&&(mode==1?program_ready:local_inst)&&start;
 wire epoch_go;
 qkd_d2d_boot_event_bridge #(.ENABLE(1)) dut(ck,rst_n,request,installed,epoch_go);
 // calendar: runs from the epoch; a witness slot every 64 edges carries the peer commit of the installed programme
 always @(posedge ck)if(rst_n)begin
  if(epoch_go)running<=1;
  if(running&&cyc%64==0&&local_inst)committed<=1;
 end
 initial begin
  void'($value$plusargs("MODE=%d",mode));repeat(8)@(negedge ck);rst_n=1;
  for(cyc=0;cyc<4000;cyc=cyc+1)begin
   @(negedge ck);request=(cyc==100);
   if(cyc==300)setup=1;if(cyc==400)local_inst=1;if(cyc==450)start=1;
   #0.01;
   if(epoch_go)begin epochs++;if(first_epoch<0)first_epoch=cyc;end
   if(committed&&first_commit<0)first_commit=cyc;
  end
  case(mode)
   0:if(epochs!=1||first_epoch<450||first_commit<first_epoch||!program_ready)$fatal(1,"FIXED_ORDER_BAD epochs%0d first%0d commit%0d",epochs,first_epoch,first_commit);
   1:if(epochs!=0||committed)$fatal(1,"OLD_PREDICATE_DEADLOCK_NOT_SHOWN epochs%0d",epochs);
  endcase
  $display("BOOT_WITNESS_LOOP_EXPECTED mode%0d epochs%0d first_epoch%0d first_commit%0d program_ready%0d",mode,epochs,first_epoch,first_commit,program_ready);$finish;
 end
endmodule
