// Diagnostic ONLY: unchanged retained W64 DEPTH4 FIFO; expected reset-contract failures.
// Uses same related /3,/4 divider waveform as pinned W18 bench. No successor hardware.
`timescale 1ps/1ps
module tb_retained_ratio_fifo_reset;
 logic vco=0,fclk=0,sclk=0; integer nv=0;
 always #139 vco=~vco;
 always @(posedge vco) begin
  nv<=nv+1;
  if(nv%3==0) fclk<=1; else if(nv%3==2) fclk<=0;
  if(nv%4==0) sclk<=1; else if(nv%4==2) sclk<=0;
 end
 logic wrst=0,rrst=0,wv=0,wr,rv,rr=1;logic[63:0] wd=0,rd;
 ot_chip_v41_ratio_fifo #(.W(64),.DEPTH(4)) dut(.wclk(fclk),.wrst_n(wrst),.w_v(wv),.w_rdy(wr),.w_d(wd),.rclk(sclk),.rrst_n(rrst),.r_v(rv),.r_rdy(rr),.r_d(rd));
 integer stale=0;
 initial begin
  repeat(2) @(negedge fclk);wv=1;wd=64'h123;
  @(posedge fclk);#1;
  if(wr!==1 || dut.wp!==0 || dut.mem[0]!==64'h123) $fatal(1,"write reset witness absent");
  $display("WITNESS_WRITE_RESET ready=1 wp=0 mem0=0000000000000123");
  @(negedge fclk);wv=0;
  #5000;wrst=1;rrst=1;
  @(negedge fclk);wv=1;wd=64'h42;
  @(posedge fclk);if(!wr) $fatal(1,"fixture expected ready");
  @(negedge fclk);wv=0;
  wait(rv);@(posedge sclk);
  if(rd!==64'h42) $fatal(1,"actual payload incorrect");
  repeat(3) @(negedge sclk);
  if(rv!==0 || dut.wp!==1 || dut.rp!==1) $fatal(1,"fixture did not drain");
  rrst=0;repeat(2) @(negedge sclk);rrst=1;
  repeat(8) begin
   @(posedge sclk);
   if(rv && rr) begin
    if(rd!==64'h42) $fatal(1,"unexpected replay data");
    stale=stale+1;
   end
  end
  if(stale!=1) $fatal(1,"expected exactly one stale replay, got %0d",stale);
  $display("WITNESS_READER_ONLY_RESET retired=0000000000000042 new_writes=0 stale_replays=1");
  $display("PASS_EXPECTED_RETAINED_RESET_GAPS_NOT_CDC_QUALIFICATION");$finish;
 end
 initial begin #1000000;$fatal(1,"diagnostic event bound exceeded");end
endmodule
