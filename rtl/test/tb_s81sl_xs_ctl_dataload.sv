`timescale 1ns/1ps
// S81-TYPES-7-LEC 11-08: lock-step bench, xs_ctl before (module renamed ot_s81sl_xs_ctl_old, from the parent commit) vs after
// the load-every-edge data registers. 200k cycles, random calendar/ROM/go, three 70-cycle warm resets, zero power-up.
// Checks: q_consume / b_consume / fault equal on EVERY edge; every output equal from 16 edges after rst_n release
// (rst_n -> rst_c relay 6 edges + 8-edge data pipe + margin). Result 11-08: 0 errors; mutants r2_b1<-blk0, r3_b0<-r2_b1,
// hv one stage early all caught (199746 / 199746 / 44690 errors). Build: verilator 5.032 --binary --timing --x-initial 0.
module tb;
  reg clk = 0, rst_n = 0;
  reg calendar_v, go, rom_gobf; reg [74:0] calendar_action; reg [9:0] i_ph; reg [2:0] i_np; reg [47:0] rom_sq;
  wire qa, qb, ba, bb, fa, fb; wire [47:0] hwa, hwb; wire [35:0] hia, hib; wire [15:0] b0a, b0b, b1a, b1b;
  wire [609:0] bca, bcb;
  ot_s81sl_xs_ctl_old A (.clk(clk), .rst_n(rst_n), .calendar_v(calendar_v), .calendar_action(calendar_action), .go(go),
    .i_ph(i_ph), .i_np(i_np), .rom_gobf(rom_gobf), .rom_sq(rom_sq), .q_consume(qa), .b_consume(ba), .hw_o(hwa),
    .h_hi_o(hia), .h_b0_o(b0a), .h_b1_o(b1a), .bc_hr_o(bca), .fault(fa));
  ot_s81sl_xs_ctl B (.clk(clk), .rst_n(rst_n), .calendar_v(calendar_v), .calendar_action(calendar_action), .go(go),
    .i_ph(i_ph), .i_np(i_np), .rom_gobf(rom_gobf), .rom_sq(rom_sq), .q_consume(qb), .b_consume(bb), .hw_o(hwb),
    .h_hi_o(hib), .h_b0_o(b0b), .h_b1_o(b1b), .bc_hr_o(bcb), .fault(fb));
  integer cyc = 0, since = 0, nchk_all = 0, nchk_flag = 0, err = 0, nv = 0;
  always #1 clk = ~clk;
  function automatic [74:0] ract(); ract = {$urandom, $urandom, $urandom} & {2'b00, {73{1'b1}}}; endfunction
  initial begin
    calendar_v = 0; go = 0; rom_gobf = 0; calendar_action = 0; i_ph = 0; i_np = 0; rom_sq = 0;
    repeat (200000) begin
      @(negedge clk);
      cyc = cyc + 1;
      // warm resets: 70-cycle windows at cycles 0, 50000, 120000
      rst_n = !((cyc < 70) || (cyc >= 50000 && cyc < 50070) || (cyc >= 120000 && cyc < 120070));
      since = rst_n ? since + 1 : 0;
      calendar_v = ($urandom % 3) != 0; calendar_action = ract(); go = ($urandom % 4) == 0;
      i_ph = $urandom; i_np = $urandom; rom_gobf = $urandom; rom_sq = {$urandom, $urandom};
      @(posedge clk); #0.1;
      if (qa !== qb || ba !== bb || fa !== fb) begin err = err + 1; if (err < 5) $display("FLAG MISMATCH cyc %0d", cyc); end
      nchk_flag = nchk_flag + 1;
      if (qa) nv = nv + 1;
      if (since >= 16) begin
        nchk_all = nchk_all + 1;
        if (hwa !== hwb || hia !== hib || b0a !== b0b || b1a !== b1b || bca !== bcb) begin
          err = err + 1; if (err < 5) $display("DATA MISMATCH cyc %0d since %0d", cyc, since); end
      end
    end
    $display("RESULT checks_flags %0d checks_all %0d q_consume_events %0d errors %0d", nchk_flag, nchk_all, nv, err);
    $finish;
  end
endmodule
