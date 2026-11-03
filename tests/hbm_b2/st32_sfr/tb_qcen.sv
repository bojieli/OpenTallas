`timescale 1ns/1ps
// DIE-HBM-61/RTL-ST32: qcen SFR 0 vs SFR 1 lockstep (W 128, TLA 7, DRLY 2, CHX 11 = the subtree32 generator params).
// Declared map: ps_v / ps / ps_f: SFR1 SXC7(t) == SFR0(t - 17) (ps when valid); every other output shift 0.
module tb;
  localparam int SH = 17, NCYC = 4000, W = 128;
  reg clk = 0, rst_n = 0;
  reg d_v = 0, d_ss = 0; reg [7:0] d_nv = 0; reg [9:0] d_wa = 0, d_xa = 0;
  reg i_v = 0, i_kind = 0; reg [1:0] i_slot = 0; reg [4:0] i_lo = 0; reg [5:0] i_w = 0; reg [11:0] i_cnt = 0; reg [9:0] i_word = 0;
  reg x_v = 0; reg [1:0] x_beat = 0; reg [9:0] x_word = 0; reg [W*32:0] s_i = 0; reg [7:0] wfault_i = 0;
  `define OUTS(p) wire [7:0] p``rst_b; wire p``bd_v, p``bd_ss; wire [7:0] p``bd_nv; wire [9:0] p``bd_wa, p``bd_xa; \
    wire [13:0] p``wc_w, p``wc_n, p``wc_e, p``wc_s; wire p``ps_v, p``ps_f, p``fault; wire [31:0] p``ps;
  `OUTS(o_) `OUTS(n_)
  `define INST(P, p) ot_hbm_hc_qcen_static #(.W(128), .TLA(7), .DRLY(2), .CHX(11), .SFR(P), .SXC(P ? 7 : 0)) u_``p ( \
    .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .i_v(i_v), .i_kind(i_kind), \
    .i_slot(i_slot), .i_lo(i_lo), .i_w(i_w), .i_cnt(i_cnt), .i_word(i_word), .x_v(x_v), .x_beat(x_beat), .x_word(x_word), \
    .s_i(s_i), .wfault_i(wfault_i), .rst_b(p``_rst_b), .bd_v(p``_bd_v), .bd_ss(p``_bd_ss), .bd_nv(p``_bd_nv), .bd_wa(p``_bd_wa), \
    .bd_xa(p``_bd_xa), .wc_w(p``_wc_w), .wc_n(p``_wc_n), .wc_e(p``_wc_e), .wc_s(p``_wc_s), .ps_v(p``_ps_v), .ps(p``_ps), \
    .ps_f(p``_ps_f), .fault(p``_fault));
  `INST(0, o) `INST(1, n)
  wire [7+1+1+8+20+56+1-1:0] so = {o_rst_b, o_bd_v, o_bd_ss, o_bd_nv, o_bd_wa, o_bd_xa, o_wc_w, o_wc_n, o_wc_e, o_wc_s, o_fault};
  wire [7+1+1+8+20+56+1-1:0] sn = {n_rst_b, n_bd_v, n_bd_ss, n_bd_nv, n_bd_wa, n_bd_xa, n_wc_w, n_wc_n, n_wc_e, n_wc_s, n_fault};
  reg hv [0:SH]; reg hf [0:SH]; reg [31:0] hp [0:SH];
  int checks = 0, errors = 0, nval = 0, nfault = 0, t = 0;
  function automatic [31:0] rf();
    reg [31:0] x; int r; begin
      r = $urandom % 1000; x = $urandom;
      if (r < 3) x[30:23] = 8'hff; else if (r < 8) x[30:23] = 8'hfe; else if (r < 15) x[30:0] = 0;
      else x[30:23] = 8'd100 + ($urandom % 40);
      rf = x; end
  endfunction
  always #1 clk = ~clk;
  initial begin
    repeat (5) @(negedge clk); rst_n = 1;
    for (int c = 0; c < NCYC; c++) begin
      @(negedge clk);
      d_v = ($urandom % 4 == 0); d_ss = $urandom; d_nv = $urandom; d_wa = $urandom; d_xa = $urandom;
      i_v = ($urandom % 50 == 0); i_kind = $urandom; i_slot = $urandom; i_lo = $urandom; i_w = $urandom; i_cnt = $urandom;
      i_word = $urandom; x_v = $urandom; x_beat = $urandom; x_word = $urandom; wfault_i = ($urandom % 500 == 0) ? 8'h1 : 8'h0;
      for (int w = 0; w < W; w++) s_i[w*32 +: 32] = rf();
      s_i[W*32] = ($urandom % 200 == 0);
    end
    repeat (120) @(negedge clk);
    $display("QCEN_LOCKSTEP SH=%0d checks=%0d errors=%0d ps_valid=%0d ps_f=%0d %s", SH, checks, errors, nval, nfault,
             (errors == 0 && nval > 500 && nfault > 20) ? "PASS" : "FAIL");
    if (!(errors == 0 && nval > 500 && nfault > 20)) $fatal(1, "QCEN FAIL");
    $finish;
  end
  always @(posedge clk) begin
    #0.1;
    for (int i = SH; i > 0; i--) begin hv[i] = hv[i-1]; hf[i] = hf[i-1]; hp[i] = hp[i-1]; end
    hv[0] = o_ps_v; hf[0] = o_ps_f; hp[0] = o_ps; t++;
    if (rst_n && t > SH + 8) begin
      checks++;
      if (sn !== so || n_ps_v !== hv[SH] || n_ps_f !== hf[SH] || (hv[SH] && n_ps !== hp[SH])) begin
        errors++; if (errors < 5) $display("MISMATCH t=%0d psv %b/%b psf %b/%b ps %h/%h side %0d", t, n_ps_v, hv[SH], n_ps_f, hf[SH], n_ps, hp[SH], sn !== so);
      end
      if (hv[SH]) nval++; if (hf[SH]) nfault++;
    end
  end
endmodule
