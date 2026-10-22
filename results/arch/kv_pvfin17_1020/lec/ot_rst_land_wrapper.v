// KV-PVFIN17 10-20: re-created shell of physical/common_flow/ot_pin_regs.tcl (OT_RST_LAND=1) for the closed route
// qkd_pv_ctl_tbf1-f2-7f399ebf5 (routed netlist carries rst_n__ot_rl0 / rst_n__ot_rl1); same form as the P216 receipt shell.
module ot_qwen_tp8_pv_wide_ctl_tbf (clk, rst_n, cfg_fia, pair_id, start, context_len, epoch, in_valid, in_t, in_epoch, req_valid, req_t, cmd, col_valid, col_fault, out_epoch, fault, busy, out_age);
  input clk;
  input rst_n;
  (* keep *) reg [0:0] rst_n__ot_rl0;
  always @(posedge clk) rst_n__ot_rl0 <= rst_n;
  (* keep *) reg [0:0] rst_n__ot_rl1;
  always @(posedge clk) rst_n__ot_rl1 <= rst_n__ot_rl0;
  input [7:0] cfg_fia;
  input pair_id;
  input start;
  input [13:0] context_len;
  input [15:0] epoch;
  input [7:0] in_valid;
  input [111:0] in_t;
  input [127:0] in_epoch;
  output [7:0] req_valid;
  output [111:0] req_t;
  output [59:0] cmd;
  input [31:0] col_valid;
  input [31:0] col_fault;
  output [15:0] out_epoch;
  output fault;
  output busy;
  output [15:0] out_age;
  ot_qwen_tp8_pv_wide_ctl_tbf__ot_pr_core u_ot_pr_core (.clk(clk), .rst_n(rst_n__ot_rl1), .cfg_fia(cfg_fia), .pair_id(pair_id), .start(start), .context_len(context_len), .epoch(epoch), .in_valid(in_valid), .in_t(in_t), .in_epoch(in_epoch), .req_valid(req_valid), .req_t(req_t), .cmd(cmd), .col_valid(col_valid), .col_fault(col_fault), .out_epoch(out_epoch), .fault(fault), .busy(busy), .out_age(out_age));
endmodule
