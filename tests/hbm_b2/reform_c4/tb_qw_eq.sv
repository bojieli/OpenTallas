`timescale 1ns/1ps
// DIE-HBM-61/RTL-C4 lockstep EQ: ot_hgi_qw_dec (new, BQS6=1) vs ot_hgi_qw_dec_old (origin/main), declared shift 0 on
// every port (vo, y when vo, fault, decode_fault).  Random legal/illegal headers, op 4/5/6, finite/zero/neg/nonfinite x.
module tb;
  reg clk = 0, rst_n = 0, v = 0;
  reg [127:0] header; reg [1023:0] x;
  wire vo_n, f_n, df_n, vo_o, f_o, df_o; wire [511:0] y_n, y_o;
  ot_hgi_qw_dec     dn (.clk(clk), .rst_n(rst_n), .v(v), .header(header), .x(x), .vo(vo_n), .y(y_n), .fault(f_n), .decode_fault(df_n));
  ot_hgi_qw_dec_old do_ (.clk(clk), .rst_n(rst_n), .v(v), .header(header), .x(x), .vo(vo_o), .y(y_o), .fault(f_o), .decode_fault(df_o));
  always #1 clk = ~clk;
  integer cyc = 0, errs = 0, nvo = 0, nb = 0, nf = 0, k, seed;
  function [31:0] rf(input integer m);
    reg [7:0] e; reg [22:0] f; reg s; integer r;
    begin
      r = $urandom % 100; s = $urandom; f = $urandom;
      if (r < 5) e = 0; else if (r < 7) e = 8'hFF; else if (r < 20) e = 8'd110 + ($urandom % 20); else e = 8'd118 + ($urandom % 24);
      if (r == 50) f = 0;
      rf = {s, e, f};
      if (m == 1 && e == 8'hFF) rf = {s, 8'd127, f};
    end
  endfunction
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    k = $urandom(seed);
    header = 0; x = 0;
    repeat (5) @(negedge clk); rst_n = 1;
    repeat (6000) begin
      @(negedge clk);
      v = ($urandom % 3) != 0;
      header = {$urandom, $urandom, $urandom, $urandom};
      header[127:124] = (($urandom % 20) == 0) ? 4'd3 : 4'd4;
      case ($urandom % 4) 0: header[123:118] = 6'd4; 1: header[123:118] = 6'd5; default: header[123:118] = 6'd6; endcase
      if (($urandom % 15) != 0) header[71:64] = 8'd16;
      for (k = 0; k < 32; k = k + 1) x[32*k +: 32] = rf(($urandom % 4) != 0);
    end
    repeat (40) @(negedge clk);
    $display("QW_EQ checks=%0d errors=%0d vo=%0d bq_beats=%0d faults=%0d %s", cyc, errs, nvo, nb, nf, errs == 0 && nvo > 1000 && nf > 10 ? "PASS" : "FAIL");
    $finish;
  end
  always @(posedge clk) if (rst_n) begin
    cyc = cyc + 1;
    if (v && header[127:124] == 4 && header[123:118] == 6 && header[71:64] == 16) nb = nb + 1;
    if (vo_o) nvo = nvo + 1;
    if (f_o) nf = nf + 1;
    if (vo_n !== vo_o || f_n !== f_o || df_n !== df_o || (vo_o && y_n !== y_o)) begin
      errs = errs + 1;
      if (errs < 4) $display("MISMATCH t=%0t vo %b/%b f %b/%b df %b/%b ydiff=%0d", $time, vo_n, vo_o, f_n, f_o, df_n, df_o, (y_n !== y_o));
    end
  end
endmodule
