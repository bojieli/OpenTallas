`timescale 1ns/1ps
// DIE-HBM-61/RTL-ST32: lockstep new (SFR) subtree32 master vs the 10-31 master, declared shift map:
// sum / valid_out / node_fault: new(t) == old(t - SH), SH = 2.  sum compared when valid.
module tb;
  localparam int SH = 2, NCYC = 6000;
  reg clk = 0, rst_n = 0, valid_in = 0; reg [1023:0] data = 0;
  wire [31:0] s_o, s_n; wire v_o, v_n; wire [30:0] f_o, f_n;
  old_ot_hbm_hc_subtree32_core u_old (.clk(clk), .data(data), .node_fault(f_o), .rst_n(rst_n), .sum(s_o), .valid_in(valid_in), .valid_out(v_o));
  ot_hbm_hc_subtree32_core     u_new (.clk(clk), .data(data), .node_fault(f_n), .rst_n(rst_n), .sum(s_n), .valid_in(valid_in), .valid_out(v_n));
  reg [31:0] hs [0:SH]; reg hv [0:SH]; reg [30:0] hf [0:SH];
  int checks = 0, errors = 0, nval = 0, nfault = 0, cyc = 0;
  function automatic [31:0] rf(input int mode);
    reg [31:0] x; int r; begin
      r = $urandom % 1000; x = $urandom;
      if (r < 8) x[30:23] = 8'hff;                    // inf / nan -> nonfinite err
      else if (r < 20) x[30:23] = 8'hfe;              // overflow candidates
      else if (r < 30) x[30:0] = 0;                   // zero
      else if (r < 40) x[30:23] = 0;                  // subnormal
      else x[30:23] = 8'd100 + ($urandom % 50);       // normal, close exponents
      rf = x; end
  endfunction
  always #1 clk = ~clk;
  initial begin
    repeat (5) @(negedge clk); rst_n = 1;
    for (cyc = 0; cyc < NCYC; cyc++) begin
      @(negedge clk);
      valid_in = (cyc < 10) ? 1'b0 : (cyc % 300 < 200) ? ($urandom % 3 != 0) : 1'b0;
      for (int w = 0; w < 32; w++) data[w*32 +: 32] = rf(0);
    end
    repeat (60) @(negedge clk);
    $display("ST32_LOCKSTEP SH=%0d checks=%0d errors=%0d valid=%0d fault_cycles=%0d %s", SH, checks, errors, nval, nfault,
             (errors == 0 && nval > 1000 && nfault > 50) ? "PASS" : "FAIL");
    if (!(errors == 0 && nval > 1000 && nfault > 50)) $fatal(1, "ST32 FAIL");
    $finish;
  end
  int t = 0;
  always @(posedge clk) begin
    #0.1;
    for (int i = SH; i > 0; i--) begin hs[i] = hs[i-1]; hv[i] = hv[i-1]; hf[i] = hf[i-1]; end
    hs[0] = s_o; hv[0] = v_o; hf[0] = f_o; t++;
    if (rst_n && t > SH + 8) begin
      checks++;
      if (v_n !== hv[SH] || f_n !== hf[SH] || (hv[SH] && s_n !== hs[SH])) begin
        errors++; if (errors < 5) $display("MISMATCH t=%0d v %b/%b f %h/%h s %h/%h", t, v_n, hv[SH], f_n, hf[SH], s_n, hs[SH]);
      end
      if (hv[SH]) nval++; if (|hf[SH]) nfault++;
    end
  end
endmodule
