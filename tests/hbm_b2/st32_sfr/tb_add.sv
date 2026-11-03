`timescale 1ns/1ps
// DIE-HBM-61/RTL-ST32: ot_hdc_fp32_add_lat LAT 7 XCUTS=X vs XCUTS=0, y/err/valid_out new(t) == old(t - popcount(X))
module tb;
  parameter int X = 7, DR = 0;
  localparam int SH = (X & 1) + ((X >> 1) & 1) + ((X >> 2) & 1), NCYC = 200000;
  reg clk = 0, rst_n = 0, v = 0; reg [31:0] a = 0, b = 0;
  wire [31:0] yo, yn; wire [1:0] eo, en; wire vo, vn;
  ot_hdc_fp32_add_lat #(.LAT(7), .DRST(DR)) u_o (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(yo), .err(eo), .valid_out(vo));
  ot_hdc_fp32_add_lat #(.LAT(7), .DRST(DR), .XCUTS(X)) u_n (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(yn), .err(en), .valid_out(vn));
  reg [31:0] hy [0:7]; reg [1:0] he [0:7]; reg hv [0:7];
  int checks = 0, errors = 0, nv = 0, nerr = 0, t = 0;
  function automatic [31:0] rf();
    reg [31:0] x; int r; begin
      r = $urandom % 100; x = $urandom;
      if (r < 3) x[30:23] = 8'hff; else if (r < 8) x[30:23] = 8'hfe; else if (r < 12) x[30:0] = 0;
      else if (r < 20) x[30:23] = 0; else if (r < 60) x[30:23] = 8'd120 + ($urandom % 12); else x[30:23] = $urandom;
      rf = x; end
  endfunction
  always #1 clk = ~clk;
  initial begin
    repeat (4) @(negedge clk); rst_n = 1;
    for (int c = 0; c < NCYC; c++) begin
      @(negedge clk); v = (c > 4) && ($urandom % 4 != 0); a = rf(); b = ($urandom % 8 == 0) ? {~a[31], a[30:0]} ^ ($urandom % 16) : rf();
    end
    repeat (20) @(negedge clk);
    $display("ADD_LOCKSTEP X=%0d DRST=%0d SH=%0d checks=%0d errors=%0d valid=%0d err=%0d %s", X, DR, SH, checks, errors, nv, nerr,
             (errors == 0 && nv > 100000 && nerr > 1000) ? "PASS" : "FAIL");
    if (!(errors == 0 && nv > 100000 && nerr > 1000)) $fatal(1, "ADD FAIL");
    $finish;
  end
  always @(posedge clk) begin
    #0.1;
    for (int i = 7; i > 0; i--) begin hy[i] = hy[i-1]; he[i] = he[i-1]; hv[i] = hv[i-1]; end
    hy[0] = yo; he[0] = eo; hv[0] = vo; t++;
    if (rst_n && t > 20) begin
      checks++;
      if (vn !== hv[SH] || (hv[SH] && (yn !== hy[SH] || en !== he[SH]))) begin
        errors++; if (errors < 4) $display("MISMATCH t=%0d v %b/%b y %h/%h e %0d/%0d", t, vn, hv[SH], yn, hy[SH], en, he[SH]);
      end
      if (hv[SH]) nv++; if (hv[SH] && he[SH] != 0) nerr++;
    end
  end
endmodule
