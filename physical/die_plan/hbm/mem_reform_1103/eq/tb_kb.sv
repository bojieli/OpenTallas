`timescale 1ns/1ps
// DIE-HBM-61/MEM lockstep bench: ot_hnx_idxn_keybuf_slice r2c2 vs right-width build; writes lines 0..170, then
// pre/replay reads (random order, with random live rewrites); key_out + fault printed every cycle.
module tb;
  reg clk = 0, rst_n = 0; always #1 clk = ~clk;
  reg clear, live_v, pre_v, replay_v; reg [7:0] live_index, pre_index, replay_index; reg [1098:0] key_in; reg [2:0] lid;
  wire [1098:0] key_out; wire fault;
  ot_hnx_idxn_keybuf_slice dut (.clk(clk), .rst_n(rst_n), .clear(clear), .strap_lane_id(lid), .live_v(live_v),
    .live_index(live_index), .key_in(key_in), .pre_v(pre_v), .pre_index(pre_index), .replay_v(replay_v),
    .replay_index(replay_index), .key_out(key_out), .fault(fault));
  integer cyc, seed, k; reg [1119:0] r; reg [7:0] last;
  initial begin
    seed = `TB_SEED; lid = 3'd5; clear = 0; live_v = 0; pre_v = 0; replay_v = 0; live_index = 0; pre_index = 0; replay_index = 0; key_in = 0; last = 0;
    repeat (3) @(posedge clk); rst_n = 1;
    for (cyc = 0; cyc < `TB_CYC; cyc = cyc + 1) begin
      @(negedge clk);
      for (k = 0; k < 35; k = k + 1) r[k*32 +: 32] = $random(seed); key_in = r[1098:0];
      if (cyc < 171) begin live_v = 1; live_index = cyc; pre_v = 0; replay_v = 0; end
      else begin
        live_v = ($random(seed) & 7) == 0; live_index = ($random(seed) & 255) % 171;
        replay_v = pre_v; replay_index = pre_index;          // replay the line prefetched last edge
        pre_v = $random(seed) & 1; pre_index = ($random(seed) & 255) % 171;
        if (live_v) begin replay_v = 0; end
      end
      @(posedge clk); #0.1;
      $display("%0d %b %h", cyc, fault, key_out);
    end
    $finish;
  end
endmodule
