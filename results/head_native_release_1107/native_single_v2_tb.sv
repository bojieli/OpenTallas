`timescale 1ps/1fs
// One actual production wrapper/codec/FIFO: the minimum native-leaf reset vehicle.
module tb_head_native_release;
 parameter integer HOLD=64, IGNORE_LOCK=0;
 parameter real PHASE=0.0;
 reg clk=0,pck=0,run_pck=0,rst=1,lock=1;
 always #416.5 clk=~clk;
 initial begin #PHASE; forever begin #416.62495; if(run_pck)pck=~pck;else pck=0;end end
 wire [513:0] out; wire [543:0] pma;wire tck;
 ot_s81hd_serdes_link_ls #(.LOCKSAFE(1),.HOLD_EDGES(HOLD)) head
 (.ck(clk),.rst_n(rst),.pma_lock(IGNORE_LOCK?1'b1:lock),.coll_i0(512'd0),
 .coll_o0(out),.pma_tx(pma),.pma_tck(tck),.pma_rx(544'd0),.pma_rck(pck));
 wire guard=head.core_rst_n, native_reset=head.u_link.rn_r;
 wire leaf_reset=head.u_link.u_dec.u_chn.rst_n;
 wire leaf_clock=head.u_link.u_dec.u_chn.clk;
 integer n,epoch,checks=0;
 // Both clock edges and stopped-clock intervals: posedge-only samples alias equal levels.
 always @(leaf_clock or pck) begin #0.01; if($time>1 && leaf_clock!==pck) $fatal(1,"native leaf clock binding differs");end
 always @(leaf_reset or native_reset) begin #0.01; if($time>1 && leaf_reset!==native_reset) $fatal(1,"native leaf reset binding differs");end
 task held;
 begin
  if({guard,native_reset,leaf_reset}!==3'd0 || out[511:0]!==512'd2 || out[513:512]!==0)
   $fatal(1,"unsafe reset while recovered clock stopped epoch=%0d",epoch);
 end endtask
 task resume;
 begin
  run_pck=1;
  for(n=1;n<=68;n=n+1)begin
   @(posedge pck);#0.1;checks=checks+1;
   if(leaf_clock!==pck || leaf_reset!==native_reset)$fatal(1,"native leaf binding differs");
   if(n<66 && guard!==0)$fatal(1,"early guard release n=%0d",n);
   if(n==66 && guard!==1)$fatal(1,"late guard release");
   if(n<68 && native_reset!==0)$fatal(1,"early native release n=%0d",n);
   if(n==68 && native_reset!==1)$fatal(1,"late native release");
  end
  $display("HEAD_RELEASE epoch=%0d guard_rck_edge=66 native_rck_edge=68",epoch);
 end endtask
 initial begin
  epoch=0;#1 rst=0;#2;held();rst=1;
  repeat(8)@(posedge clk);#1;held();resume();
  repeat(32)@(posedge pck);@(negedge pck);run_pck=0;
  #2000;epoch=1;lock=0;#1;held();lock=1;
  repeat(8)@(posedge clk);#1;held();resume();
  repeat(32)@(posedge pck);@(negedge pck);run_pck=0;
  #2000;epoch=2;rst=0;#1;held();rst=1;
  repeat(8)@(posedge clk);#1;held();resume();
  $display("HEAD_NATIVE_RELEASE PASS checks=%0d actual_codec_and_fifo=1 leaf_binding=1",checks);
  $finish;
 end
 initial begin #10000000;$fatal(1,"fixture did not finish");end
endmodule
