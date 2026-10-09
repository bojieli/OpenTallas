// REDESIGN-S81 2026-10-08: transaction-level exactness of the pin-registered r2l / l2r hub end blocks
// (dsfd_glue.sv HEAD) against the pre-redesign masters (old_glue.sv, modules renamed old_*): the same random lane
// stream (valid-tagged words, random gaps) goes into both; the sequence of valid output words must be identical.
// +define+MUT flips bit 7 of the new block's 5th output word (negative control: the bench must FAIL).
`timescale 1ps/1ps
module tb;
  reg cks = 0, ck = 0;           // 1.2 GHz stream (833 ps), 0.9 GHz serial (1111 ps), one PLL: 3:4
  always #416 cks = ~cks;
  always #555 ck  = ~ck;
  reg rst = 0;
  integer seed = 1, n_r2l_old = 0, n_r2l_new = 0, n_l2r_old = 0, n_l2r_new = 0, errs = 0, N = 400;
  // ---- r2l (hcol): lane on cks/fi0 -> serial ck
  reg [513:0] di0 = 0;
  wire [514:0] o_old, o_new;
  old_dsfd_r2l_vr_512x1__hcol u_ro (.ck(ck), .o(o_old), .rs(rst), .di0(di0), .fi0(cks));
  dsfd_r2l_vr_512x1__hcol     u_rn (.ck(ck), .o(o_new), .rs(rst), .di0(di0), .fi0(cks));
  // ---- l2r (hx_W): serial ck -> lane cks
  reg [564:0] i = 0;
  wire [565:0] od_old, od_new; wire [2:0] st_old, st_new; wire fo1, fo2;
  old_dsfd_l2r_vr_564x1__hx_W u_lo (.ck(ck), .cks(cks), .fo(fo1), .i(i), .od(od_old), .rs(rst), .rss(rst), .st(st_old));
  dsfd_l2r_vr_564x1__hx_W     u_ln (.ck(ck), .cks(cks), .fo(fo2), .i(i), .od(od_new), .rs(rst), .rss(rst), .st(st_new));
  reg [511:0] q_r2l_old [0:4095]; reg [511:0] q_r2l_new [0:4095];
  reg [563:0] q_l2r_old [0:4095]; reg [563:0] q_l2r_new [0:4095];
  function [511:0] rnd512; input integer s; integer k; begin for (k = 0; k < 16; k = k + 1) rnd512[32*k +: 32] = $random(seed); end endfunction
  // lane writer: one word every other cks cycle at most (the lane rate into a 3:4 crossing), random gaps
  integer sent_r = 0, sent_l = 0;
  // send only once both crossings are live on both sides (words offered during the start-up handshake are
  // discarded by contract: these masters ignore w_rdy, the lane stream starts after the link reports live)
  wire live = o_old[513] & o_new[513] & st_old[1] & st_new[1];
  reg go = 0; always @(posedge ck) if (live) go <= 1'b1;
  always @(posedge cks) begin
    di0[0] <= rst;
    if (go && sent_r < N && ($random(seed) & 1) && !di0[1]) begin di0[1] <= 1'b1; di0[513:2] <= rnd512(0); sent_r <= sent_r + 1; end
    else di0[1] <= 1'b0;
  end
  always @(posedge ck) begin
    if (go && sent_l < N && ($random(seed) % 3 == 0) && !i[0]) begin i[0] <= 1'b1; i[564:1] <= {rnd512(0), $random(seed), $random(seed)}; sent_l <= sent_l + 1; end
    else i[0] <= 1'b0;
  end
  // collectors
  always @(posedge ck) begin
    if (o_old[0]) begin q_r2l_old[n_r2l_old] = o_old[512:1]; n_r2l_old = n_r2l_old + 1; end
    if (o_new[0]) begin q_r2l_new[n_r2l_new] = o_new[512:1]
`ifdef MUT
      ^ (n_r2l_new == 4 ? 512'h80 : 512'h0)
`endif
      ; n_r2l_new = n_r2l_new + 1; end
  end
  always @(posedge cks) begin
    if (od_old[1]) begin q_l2r_old[n_l2r_old] = od_old[565:2]; n_l2r_old = n_l2r_old + 1; end
    if (od_new[1]) begin q_l2r_new[n_l2r_new] = od_new[565:2]; n_l2r_new = n_l2r_new + 1; end
  end
  integer k;
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    #20000 rst = 1;
    #(N * 6000);
    if (n_r2l_old != N || n_r2l_new != N) begin $display("r2l count old %0d new %0d sent %0d", n_r2l_old, n_r2l_new, N); errs = errs + 1; end
    if (n_l2r_old != N || n_l2r_new != N) begin $display("l2r count old %0d new %0d sent %0d", n_l2r_old, n_l2r_new, N); errs = errs + 1; end
    for (k = 0; k < N; k = k + 1) begin
      if (q_r2l_old[k] !== q_r2l_new[k]) begin if (errs < 5) $display("r2l word %0d differs", k); errs = errs + 1; end
      if (q_l2r_old[k] !== q_l2r_new[k]) begin if (errs < 5) $display("l2r word %0d differs", k); errs = errs + 1; end
    end
    if (st_old !== st_new) $display("note: st differs at end (registered, expected only transiently)");
    $display("SUMMARY r2l %0d/%0d l2r %0d/%0d words, errors %0d", n_r2l_new, N, n_l2r_new, N, errs);
    if (errs == 0) $display("RESULT PASS"); else $display("RESULT FAIL");
    $finish;
  end
endmodule
