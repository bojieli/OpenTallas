// ot_v41_bmul2 vs ot_hdc_bmul: every significand pair x sign under six exponent pairs, then 4M random BF16 pairs; y and
// fault must match every cycle (W10b: 4,393,224 cycles, 0 mismatches, Verilator 5.050).
// verilator --binary --timing --top-module tb rtl/test/tb_v41_bmul2_equiv.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bmul2.sv
module tb;
  reg clk = 0, rst_n = 0, v = 0; reg [15:0] a, b;
  wire [31:0] y0, y1; wire f0, f1;
  ot_hdc_bmul u0 (.clk(clk), .rst_n(rst_n), .v(v), .a({a,16'd0}), .b({b,16'd0}), .y(y0), .fault(f0));
  ot_v41_bmul2 u1 (.clk(clk), .rst_n(rst_n), .v(v), .a({a,16'd0}), .b({b,16'd0}), .y(y1), .fault(f1));
  always #1 clk = ~clk;
  longint n = 0, bad = 0; integer i, j, e;
  reg [15:0] exps [0:5];
  always @(posedge clk) if (rst_n) begin n++; if (y0 !== y1 || f0 !== f1) begin bad++; if (bad < 5) $display("MISMATCH a=%h b=%h %h/%h %b/%b", a, b, y0, y1, f0, f1); end end
  initial begin
    exps[0] = 16'h3F80; exps[1] = 16'h0080; exps[2] = 16'h0000; exps[3] = 16'h7F00; exps[4] = 16'hC000; exps[5] = 16'h1F80;
    repeat (3) @(negedge clk); rst_n = 1; v = 1;
    for (e = 0; e < 6; e++) for (i = 0; i < 256; i++) for (j = 0; j < 256; j++) begin
      @(negedge clk); a = (exps[e] & 16'hFF80) | i[6:0] | (i[7] << 15); b = (exps[(e+1)%6] & 16'hFF80) | j[6:0] | (j[7] << 15); end
    for (i = 0; i < 4000000; i++) begin @(negedge clk); a = $urandom; b = $urandom; end
    repeat (8) @(negedge clk);
    $display("compared %0d cycles, %0d mismatches", n, bad); $finish;
  end
endmodule
