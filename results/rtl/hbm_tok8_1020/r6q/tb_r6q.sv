// HBM-TOK8 10-20: TOK.HDS.VEH.2 R6 PROGRAMME_Q1 isolation. The ONLY DUT is the die's SU programme producer
// ot_hbm_su_programme_pslice_c5 (default DICT_CAP, as instantiated by the R6 observer TB p0..p3), loaded with the
// R6 compiler's quarter config (q<Q>/cols/config.mem) and started once; every valid command is compared with the
// compiler's expected quarter image (q<Q>/quarter.mem). Prints first mismatches with the differing field bits.
`timescale 1ns/1ps
module tb;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0, we=0, start=0; reg [15:0] cb=0; reg [6:0] cr=0; reg [255:0] cd=0;
  wire busy, valid, done, fault; wire [15:0] eidx; wire [2421:0] cmd;
  ot_hbm_su_programme_pslice_c5 dut(.clk(clk),.rst_n(rst_n),.cfg_we(we),.cfg_bank(cb),.cfg_row(cr),.cfg_data(cd),
    .start(start),.length(16'd672),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(eidx),.command(cmd));
  reg [279:0] cfg[0:1023]; reg [2421:0] exp_[0:671]; integer ncfg, n=0, bad=0, shown=0, i, b, cyc=0;
  string cfgf, expf; integer GAP;
  initial if (!$value$plusargs("GAP=%d", GAP)) GAP=4;
  always @(posedge clk) cyc<=cyc+1;
  function automatic string field(input integer bit_);
    if (bit_>=680) return "control"; else if (bit_>=440) return "vmr"; else if (bit_>=128) return "vmw";
    else if (bit_>=74) return "rf"; else return "red";
  endfunction
  always @(posedge clk) if (rst_n && valid) $display("R6Q_CMD %0d %0d %h", n, eidx, cmd);
  always @(posedge clk) if (rst_n && valid) begin
    if (eidx != n || cmd !== exp_[n]) begin
      bad = bad + 1;
      if (shown < 6) begin
        shown = shown + 1;
        $display("R6Q_MISMATCH n=%0d edge_index=%0d cyc=%0d", n, eidx, cyc);
        for (b=0; b<2422; b=b+1) if (cmd[b] !== exp_[n][b]) begin
          $display("  bit %0d (%s) got %b exp %b", b, field(b), cmd[b], exp_[n][b]);
        end
      end
    end
    n = n + 1;
  end
  always @(posedge clk) if (rst_n && fault) begin $display("R6Q_FAULT cyc=%0d", cyc); end
  initial begin
    if (!$value$plusargs("CFG=%s", cfgf)) $fatal(1, "+CFG");
    if (!$value$plusargs("EXP=%s", expf)) $fatal(1, "+EXP");
    for (i=0;i<1024;i=i+1) cfg[i] = {280{1'bx}};
    $readmemh(cfgf, cfg); $readmemh(expf, exp_);
    if (!$value$plusargs("NCFG=%d", ncfg)) $fatal(1, "+NCFG (config.mem line count)");
    repeat(4) @(negedge clk); rst_n=1; repeat(12) @(negedge clk);
    for (i=0;i<ncfg;i=i+1) begin we=1; cb=cfg[i][279:264]; cr=cfg[i][262:256]; cd=cfg[i][255:0]; @(negedge clk); end
    we=0; repeat(GAP) @(negedge clk);
    start=1; @(negedge clk); start=0;
    repeat(1200) @(negedge clk);
    $display("R6Q_DONE cfg_rows=%0d commands=%0d mismatches=%0d fault=%b %s", ncfg, n, bad, fault,
             (bad==0 && n==672 && !fault) ? "R6Q_PASS" : "R6Q_FAIL");
    $finish;
  end
endmodule
