`timescale 1ns/1ps
// L2H-PSLICE 10-19 (r8, per-leaf command ports; copy of tb_hbm_su_programme_pslice_c5_flat_eq): the wires-only flat parent
// ot_hbm_su_programme_pslice_c5_flat8 (lp.py input) == ot_hbm_su_programme_pslice_c5
// (generate form, MUT 0), cycle for cycle on every output.  MUT (passed to pslice_c5) != 0 must FAIL (e.g. 1 = phase).
module tb_hbm_su_programme_pslice_c5_flat8_eq;
  parameter integer MUT = 0;
  reg clk = 1'b0;  always #0.5 clk = ~clk;
  reg rst_n = 1'b0, cfg_we = 1'b0, start = 1'b0;
  reg [15:0] cfg_bank = 0, length = 0;  reg [6:0] cfg_row = 0;  reg [255:0] cfg_data = 0;
  wire a_busy, a_valid, a_done, a_fault, b_busy, b_valid, b_done, b_fault;
  wire [15:0] a_ei, b_ei;  wire [2421:0] a_cmd, b_cmd;
  wire [255:0] b_c0, b_c1, b_c2, b_c3, b_c4, b_c5, b_c6, b_c7, b_c8;  wire [117:0] b_c9;
  assign b_cmd = {b_c9, b_c8, b_c7, b_c6, b_c5, b_c4, b_c3, b_c2, b_c1, b_c0};   // the per-leaf command split re-assembled
  ot_hbm_su_programme_pslice_c5 #(.MUT(MUT)) u_ref (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_bank(cfg_bank),
    .cfg_row(cfg_row), .cfg_data(cfg_data), .start(start), .length(length), .busy(a_busy), .valid(a_valid), .done(a_done),
    .fault(a_fault), .edge_index(a_ei), .command(a_cmd));
  ot_hbm_su_programme_pslice_c5_flat8 u_flat (.clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_bank(cfg_bank),
    .cfg_row(cfg_row), .cfg_data(cfg_data), .start(start), .length(length), .busy(b_busy), .valid(b_valid), .done(b_done),
    .fault(b_fault), .edge_index(b_ei), .command_c0(b_c0), .command_c1(b_c1), .command_c2(b_c2), .command_c3(b_c3), .command_c4(b_c4), .command_c5(b_c5), .command_c6(b_c6), .command_c7(b_c7), .command_c8(b_c8), .command_c9(b_c9));
  integer cyc, bad = 0, nc = 0, nv = 0, nf = 0, nz = 0;
  initial begin
    for (cyc = 0; cyc < 20000; cyc = cyc + 1) begin
      @(negedge clk);
      if (cyc == 16) rst_n = 1'b1;
      cfg_we = (cyc < 8000) ? (($urandom % 2) == 0) : (($urandom % 100) == 0);  cfg_bank = {11'($urandom % 10), 5'($urandom % 7)};  cfg_row = 7'($urandom);
      cfg_data = {8{$urandom}};  start = (cyc >= 8000) && (($urandom % 40) == 0);  length = 16'(1 + $urandom % 120);
      if (cyc > 20) begin
        nc = nc + 1;  nv = nv + a_valid;  nf = nf + a_fault;  nz = nz + (a_valid && a_cmd != 0);
        if ({a_busy, a_valid, a_done, a_fault, a_ei, a_cmd} !== {b_busy, b_valid, b_done, b_fault, b_ei, b_cmd}) begin
          bad = bad + 1;
          if (bad <= 5) $display("FLAT_EQ_MISMATCH cycle=%0d busy %b/%b valid %b/%b fault %b/%b", cyc, a_busy, b_busy,
                                 a_valid, b_valid, a_fault, b_fault);
        end
      end
    end
    if (bad == 0) $display("FLAT_EQ PASS MUT=%0d compared=%0d valid_cycles=%0d nonzero_cmd=%0d fault_cycles=%0d", MUT, nc, nv, nz, nf);
    else $display("FLAT_EQ FAIL MUT=%0d mismatches=%0d of %0d", MUT, bad, nc);
    $finish;
  end
endmodule
