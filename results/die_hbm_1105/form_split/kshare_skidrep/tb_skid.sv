`timescale 1ns/1ps
module tb;
  logic clk=0, rst_n=0; always #1 clk=~clk;
  integer cyc=0, errs=0;
  `define INST(W,MO,MN) \
  logic iv_``W; logic [W-1:0] id_``W; logic or_``W; wire ir_o_``W, ov_o_``W, ir_n_``W, ov_n_``W; wire [W-1:0] od_o_``W, od_n_``W; \
  skid_old #(.WIDTH(W),.MUT(MO)) o_``W(.clk(clk),.rst_n(rst_n),.in_v(iv_``W),.in_r(ir_o_``W),.in_data(id_``W),.out_v(ov_o_``W),.out_r(or_``W),.out_data(od_o_``W)); \
  ot_hbm_svc_pin_skid2 #(.WIDTH(W),.MUT(MN)) n_``W(.clk(clk),.rst_n(rst_n),.in_v(iv_``W),.in_r(ir_n_``W),.in_data(id_``W),.out_v(ov_n_``W),.out_r(or_``W),.out_data(od_n_``W)); \
  always @(negedge clk) begin iv_``W = ($urandom%4)!=0; or_``W = ($urandom%3)!=0; for (int k=0;k<W;k++) id_``W[k] = $urandom%2; \
    if (cyc>3 && (ir_o_``W!==ir_n_``W || ov_o_``W!==ov_n_``W || od_o_``W!==od_n_``W)) begin errs++; if (errs<5) $display("MISMATCH W=%0d cyc=%0d", W, cyc); end end
  `INST(277,`MO,`MN)
  `INST(286,`MO,`MN)
  `INST(340,`MO,`MN)
  `INST(5,`MO,`MN)
  always @(negedge clk) begin cyc<=cyc+1; rst_n <= (cyc%997)>=2; if (cyc==200000) begin $display("SKID LOCKSTEP %s errs=%0d", errs?"FAIL":"PASS", errs); $finish; end end
endmodule
