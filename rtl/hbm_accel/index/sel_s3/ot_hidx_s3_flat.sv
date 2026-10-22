`default_nettype none
// L2H-IDXSEL s3: FLAT wires-only parent of the landed IDX selector (input of tools/landed_parent/lp.py, spec
// tools/landed_parent/specs/hidx_sel_s3.json -> rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp.sv).  One ctl tile
// (u_ctl) + four instances of ONE quadrant tile (u_q0..u_q3).  The line ports are split per quadrant so every port has
// one region (in_line_<q> / selected_v_<q> / selected_line_<q> live on the quadrant's clock, the control word, k and
// fault on the ctl clock); the die master ot_hbm_idx_selector_s3 concatenates them back to the die's port list.
// ctl <-> quadrant is a LOOP (cw/thr/ties out, ret/qf back): lp.py reschedule mode, every landed net +3 edges, handed to
// the IDX compiler (sel_in 7, sel_choose_rt 8).  DMUT is a bench-only design mutant (0 in every kit).
module ot_hidx_s3_flat #(parameter integer DMUT=0)(
 input wire clk,
 input wire rst_n,
 input wire [3:0] op,
 input wire [1:0] pass,
 input wire [7:0] addr,
 input wire [9:0] k,
 input wire [591:0] in_line_0,
 input wire [591:0] in_line_1,
 input wire [591:0] in_line_2,
 input wire [591:0] in_line_3,
 output wire selected_v_0,
 output wire selected_v_1,
 output wire selected_v_2,
 output wire selected_v_3,
 output wire [591:0] selected_line_0,
 output wire [591:0] selected_line_1,
 output wire [591:0] selected_line_2,
 output wire [591:0] selected_line_3,
 output wire fault
);
 wire [13:0] cw;
 wire [15:0] thr;
 wire [13:0] ties_0, ties_1, ties_2, ties_3;
 wire [24:0] ret_0, ret_1, ret_2, ret_3;
 wire qf_0, qf_1, qf_2, qf_3;
 ot_hidx_s3_ctl #(.DMUT(DMUT)) u_ctl (.clk(clk), .rst_n(rst_n), .op(op), .pass(pass), .addr(addr), .k(k), .cw(cw), .thr(thr),
  .ties_0(ties_0), .ties_1(ties_1), .ties_2(ties_2), .ties_3(ties_3), .ret_0(ret_0), .ret_1(ret_1), .ret_2(ret_2),
  .ret_3(ret_3), .qf_0(qf_0), .qf_1(qf_1), .qf_2(qf_2), .qf_3(qf_3), .fault(fault));
 ot_hidx_s3_q #(.DMUT(DMUT)) u_q0 (.clk(clk), .rst_n(rst_n), .cw(cw), .thr(thr), .ties(ties_0), .in_line(in_line_0),
  .ret(ret_0), .qfault_o(qf_0), .selected_v_o(selected_v_0), .selected_line_o(selected_line_0));
 ot_hidx_s3_q #(.DMUT(DMUT)) u_q1 (.clk(clk), .rst_n(rst_n), .cw(cw), .thr(thr), .ties(ties_1), .in_line(in_line_1),
  .ret(ret_1), .qfault_o(qf_1), .selected_v_o(selected_v_1), .selected_line_o(selected_line_1));
 ot_hidx_s3_q #(.DMUT(DMUT)) u_q2 (.clk(clk), .rst_n(rst_n), .cw(cw), .thr(thr), .ties(ties_2), .in_line(in_line_2),
  .ret(ret_2), .qfault_o(qf_2), .selected_v_o(selected_v_2), .selected_line_o(selected_line_2));
 ot_hidx_s3_q #(.DMUT(DMUT)) u_q3 (.clk(clk), .rst_n(rst_n), .cw(cw), .thr(thr), .ties(ties_3), .in_line(in_line_3),
  .ret(ret_3), .qfault_o(qf_3), .selected_v_o(selected_v_3), .selected_line_o(selected_line_3));
endmodule
`default_nettype wire
