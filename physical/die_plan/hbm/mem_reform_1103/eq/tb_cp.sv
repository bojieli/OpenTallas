`timescale 1ns/1ps
// DIE-HBM-61/MEM lockstep bench for the ot_hbm_host_cp_rxs memory leaves: ot_hbm_host_landing256 (2x 256x256) and
// ot_qkvd_llr_replay_sram_leaf at W 306/141/138/30/16 (QD 64).  Random in_v/out_ready and random leaf we/wa/ra/din;
// every output printed every cycle; r2c2 and right-width builds must print identical traces.
module tb;
  reg clk = 0, rst_n = 0; always #1 clk = ~clk;
  reg in_v, out_ready; reg [544:0] in_data; wire out_v, pop, fault; wire [511:0] out_data;
  ot_hbm_host_landing256 #(.PINREG(1)) land (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_data(in_data), .out_v(out_v),
    .out_data(out_data), .out_ready(out_ready), .pop(pop), .fault(fault));
  reg we; reg [5:0] wa, ra; reg [305:0] din;
  wire [305:0] d306; wire [140:0] d141; wire [137:0] d138; wire [29:0] d30; wire [15:0] d16;
  ot_qkvd_llr_replay_sram_leaf #(.W(306), .QD(64), .MUT(`TB_MUT)) l306 (.ck(clk), .we(we), .wa(wa), .ra(ra), .din(din), .dout(d306));
  ot_qkvd_llr_replay_sram_leaf #(.W(141), .QD(64), .MUT(`TB_MUT)) l141 (.ck(clk), .we(we), .wa(wa), .ra(ra), .din(din[140:0]), .dout(d141));
  ot_qkvd_llr_replay_sram_leaf #(.W(138), .QD(64), .MUT(`TB_MUT)) l138 (.ck(clk), .we(we), .wa(wa), .ra(ra), .din(din[137:0]), .dout(d138));
  ot_qkvd_llr_replay_sram_leaf #(.W(30), .QD(64), .MUT(`TB_MUT)) l30 (.ck(clk), .we(we), .wa(wa), .ra(ra), .din(din[29:0]), .dout(d30));
  ot_qkvd_llr_replay_sram_leaf #(.W(16), .QD(64), .MUT(`TB_MUT)) l16 (.ck(clk), .we(we), .wa(wa), .ra(ra), .din(din[15:0]), .dout(d16));
  integer cyc, seed, k, nov; reg [575:0] r;
  initial begin
    seed = `TB_SEED; nov = 0; in_v = 0; out_ready = 0; in_data = 0; we = 0; wa = 0; ra = 0; din = 0;
    repeat (3) @(posedge clk); rst_n = 1;
    for (cyc = 0; cyc < `TB_CYC; cyc = cyc + 1) begin
      @(negedge clk);
      for (k = 0; k < 18; k = k + 1) r[k*32 +: 32] = $random(seed);
      in_v = (cyc % 900) < 450 ? (($random(seed) & 3) != 0) : (($random(seed) & 7) == 0);  // fill phases / drain phases
      out_ready = (cyc % 900) < 450 ? (($random(seed) & 7) == 0) : (($random(seed) & 3) != 0);
      in_data = r[544:0]; din = r[305:0]; we = $random(seed); wa = $random(seed); ra = $random(seed);
      @(posedge clk); #0.1;
      if (out_v) nov = nov + 1;
      $display("%0d %b%b%b %h %h %h %h %h %h", cyc, out_v, pop, fault, out_data, d306, d141, d138, d30, d16);
    end
    $display("COVER out_v_cycles=%0d", nov);
    $finish;
  end
endmodule
