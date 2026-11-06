#!/usr/bin/env python3
"""Add opt-in real PMA HOST-peer KS stimulus to the pinned V1c diagnostic TB."""
from pathlib import Path
import argparse
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
s=a.input.read_text()
def one(old,new):
 global s
 if s.count(old)!=1:raise SystemExit('unsupported TB: expected one '+old[:70])
 s=s.replace(old,new,1)
one('`timescale 1ns/1ps','`timescale 1ns/1fs')
one('  s81_bound_top dut (','''  // The original 1ps precision rounded 416.5ps halves to417ps. Native mode is833ps exact.
  longint native_ks_last_fs = -1; integer native_ks_period_reports = 0;
  always @(posedge clk) begin : native_clock_period_check
    longint now_fs;
    now_fs = longint'($realtime * 1.0e6);
    if (native_ks_last_fs >= 0) begin
      if (now_fs-native_ks_last_fs != 833000) $fatal(1,"native diagnostic clock period is not833000fs");
      if (native_ks_period_reports == 0) $display("NATIVE_KS_PERIOD_FS %0d",now_fs-native_ks_last_fs);
      native_ks_period_reports = native_ks_period_reports + 1;
    end
    native_ks_last_fs=now_fs;
  end
  bit native_ks_link = 0;
  initial native_ks_link = $test$plusargs("NATIVE_KS_LINK");
  reg native_ks_send = 0; reg [52:0] native_ks_word = 0;
  wire [543:0] native_ks_pma0,native_ks_pma1;
  wire native_ks_queued,native_ks_accepted; wire [5:0] native_ks_fault;
  ot_tb_s81_native_ks_peer native_peer(.clk(clk),.rst_n(rst_n && native_ks_link),
    .send(native_ks_send),.ks(native_ks_word),.pma_from_die0(lk_EN0_pma_tx),.pma_from_die1(lk_EN1_pma_tx),
    .pma_die_tck0(lk_EN0_pma_tck[0]),.pma_die_tck1(lk_EN1_pma_tck[0]),
    .pma_to_die0(native_ks_pma0),.pma_to_die1(native_ks_pma1),
    .queued(native_ks_queued),.accepted(native_ks_accepted),.fault(native_ks_fault));
  always @* begin
    lk_EN0_pma_rx = native_ks_link ? native_ks_pma0 : 544'd0;
    lk_EN1_pma_rx = native_ks_link ? native_ks_pma1 : 544'd0;
  end
  s81_bound_top dut (''')
one('initial begin if ($value$plusargs("KS=%d", ksm)) ; #1;', 'initial begin if ($value$plusargs("KS=%d", ksm)) ; if ($test$plusargs("NATIVE_KS_LINK")) ksm=2; #1;')
one('if (ksm != 0) begin $display("TB_S81_DIE KS mode: %0d valid host words", nhv); force dut.seqhost.u_u_seqhost.u.u_u.f_ks = ksw; end', 'if (ksm != 0) begin $display("TB_S81_DIE KS mode: %0d valid host words native_link=%0d", nhv, native_ks_link); if (!native_ks_link) force dut.seqhost.u_u_seqhost.u.u_u.f_ks = ksw; end')
one("    ksw <= 53'd0;", "    ksw <= 53'd0; native_ks_send <= 0;")
old='    if (launch0 >= 0 && t_ks < 0 && cyc + 1 == launch0) begin ksw <= {1\'b1, 10\'d37, 21\'d1000, 21\'d5000}; t_ks = cyc + 1; $display("PROG KS %0d", t_ks); end'
new='''    if (launch0 >= 0 && t_ks < 0 && cyc + 1 == launch0) begin
      if (native_ks_link) begin
        native_ks_word <= {1'b1,10'd37,21'd1000,21'd5000}; native_ks_send <= 1;
        $display("NATIVE_KS_QUEUE %0d",cyc+1);
      end else begin ksw <= {1'b1,10'd37,21'd1000,21'd5000}; t_ks=cyc+1; $display("PROG KS %0d",t_ks); end
    end
    if (native_ks_link && t_ks < 0 && dut.seqhost.u_u_seqhost.u.u_u.f_ks[52] === 1'b1) begin
      t_ks=cyc+1; $display("PROG KS %0d",t_ks);
      $display("NATIVE_KS_RECEIVED %0d word %h peer_fault %h",t_ks,dut.seqhost.u_u_seqhost.u.u_u.f_ks,native_ks_fault);
    end'''
one(old,new)
a.output.write_text(s)
print('NATIVE_KS_LINK_TB',a.output)
