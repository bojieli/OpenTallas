// Edge trace of every observable issuer output for the v1 -> v2 differential (issue_v2_diff_gate.sh).
module tb_s81_fixed_issue_trace;
 always @(posedge tb_s81_fixed_issue.clk) begin #2;
  if(tb_s81_fixed_issue.tick>=990) $display("T %0d %h %h %b%b%b %h %b %h %0d %0d %b",tb_s81_fixed_issue.tick,tb_s81_fixed_issue.cv,tb_s81_fixed_issue.cd,
   tb_s81_fixed_issue.done,tb_s81_fixed_issue.kdone,tb_s81_fixed_issue.slot,tb_s81_fixed_issue.ktok,tb_s81_fixed_issue.fault,tb_s81_fixed_issue.code,
   tb_s81_fixed_issue.nj,tb_s81_fixed_issue.nc,tb_s81_fixed_issue.busy);
 end
endmodule
