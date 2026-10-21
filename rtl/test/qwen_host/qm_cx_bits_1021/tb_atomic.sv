`timescale 1ns/1ps
module tb_atomic;
 parameter integer MUT=0;
 reg wc=0,rc=0,wn=0,rn=0,wr=0,rd=0;
 reg[63:0]wd=0;
 wire full,ovf,empty;wire[4:0]freed,count;wire[63:0]head,local_valid;reg[63:0]captured,want_capture;reg cap_valid=0;
 integer errors=0,wp=0,rp=0,epochs=0,checks=0,wcy=0,rcy=0;
 reg[63:0]expected[0:16383];reg[63:0]lfsr=64'h13579bdf02468ace;
 always #5 wc=~wc;always #7 rc=~rc;
 qkc_afifo_bits_1021 #(.W(64),.AW(4),.SKEW_SYNC(1),.MUT_UNCOORD(MUT)) dut(
  .wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(full),.wfreed(freed),.ovf(ovf),
  .rclk(rc),.rrst_n(rn),.rd(rd),.rempty(empty),.rdata(head),.rd_valid(local_valid),.rcount(count));
 for(genvar b=0;b<64;b=b+1)begin:g_local_capture
  always @(posedge rc)if(rd&&local_valid[b])captured[b]<=head[b];
 end
 always @(posedge rc or negedge rn)
  if(!rn)cap_valid<=0;else begin cap_valid<=rd&&!empty;end
 always @(negedge rc)if(cap_valid&&captured!==want_capture)errors=errors+1;
 always @(posedge wc or negedge wn)
  if(!wn)wp=0;else if(wr&&!full)begin expected[wp]=wd;wp=wp+1;end
 always @(posedge rc or negedge rn)
  if(!rn)rp=0;else if(rd&&!empty)begin
   want_capture<=expected[rp];
   checks=checks+1;
   if(rp>=wp||head!==expected[rp])begin errors=errors+1;if(errors<5)$display("atomic word mismatch t=%0t idx=%0d gold=%h got=%h",$time,rp,expected[rp],head);end
   rp=rp+1;
  end
 always @(negedge wc)begin
  wcy=wcy+1;lfsr={lfsr[62:0],lfsr[63]^lfsr[62]^lfsr[60]^lfsr[59]};wd=lfsr;wr=wn&&!full&&(wcy%9!=0);
 end
 always @(negedge rc)begin rcy=rcy+1;rd=rn&&(rcy%7!=0);end
 for(genvar b=1;b<64;b=b+1)begin:g_ptr_check
  always @(negedge wc)if(wn&&dut.g_bit[b].g_generic.u_fifo.wbin!==dut.g_bit[0].g_generic.u_fifo.wbin)errors=errors+1;
  always @(negedge rc)if(rn&&dut.g_bit[b].g_generic.u_fifo.rbin!==dut.g_bit[0].g_generic.u_fifo.rbin)errors=errors+1;
 end
 initial begin
  #43;wn=1;#4;rn=1;
  #14000;wn=0;rn=0;wr=0;rd=0;epochs=epochs+1;
  #61;wn=1;#4;rn=1;
  #14000;
  if(errors==0&&checks>500)$display("CX_BITS_ATOMIC PASS MUT=%0d skew_sync=1 checks=%0d resets=%0d",MUT,checks,epochs+1);
  else $display("CX_BITS_ATOMIC FAIL MUT=%0d errors=%0d checks=%0d",MUT,errors,checks);
  if(errors!=0)$fatal(1,"non-atomic FIFO word");$finish;
 end
endmodule
