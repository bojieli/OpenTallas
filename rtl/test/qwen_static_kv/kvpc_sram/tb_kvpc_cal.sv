`timescale 1ps/1fs
// KV-PC5 10-20: lockstep miter, original qkd_controller_hbm_calendar (REF) vs the native32 successor qkd_kvpc_s_calendar
// (DUT, clone file).  Directed-random programme: configure all 32 halves (random order, repeats, small timing fields so
// events fire), seal, go when idle, with low-probability illegal writes / seals / gos (faults) and random mid resets.
// Every output compared every hck edge.  KVPC_MUT 1 / 2 = DUT calendar MUT (wait + 1 / burst reload 0): must FAIL.
`ifndef KVPC_MUT
`define KVPC_MUT 0
`endif
module tb_kvpc_cal;
  reg hck = 0; always #512 hck = ~hck;
  reg rst_n = 0, cfg_we = 0, seal = 0, go = 0;
  reg [4:0] cfg_addr = 0; reg [63:0] cfg_data = 0; reg [15:0] epoch = 0; reg [5:0] layer = 0;
  wire r_own, d_own, r_rd, d_rd, r_sc, d_sc, r_wc, d_wc, r_raw, d_raw, r_f, d_f, r_i, d_i;
  wire [42:0] r_cmd, d_cmd; wire [15:0] r_ep, d_ep;
  qkd_controller_hbm_calendar #(.N(16), .ROW0(64), .MUT(0)) u_ref (.hck(hck), .rst_n(rst_n), .cfg_we(cfg_we),
    .cfg_addr(cfg_addr), .cfg_data(cfg_data), .seal(seal), .go(go), .epoch(epoch), .layer(layer),
    .static_cmd_owner(r_own), .static_cmd(r_cmd), .reserved_rd(r_rd), .reserved_static_col(r_sc),
    .reserved_write_col(r_wc), .static_epoch(r_ep), .expected_raw_valid(r_raw), .fault(r_f), .idle(r_i));
  qkd_kvpc_s_calendar #(.N(16), .ROW0(64), .MUT(`KVPC_MUT)) u_dut (.hck(hck), .rst_n(rst_n), .cfg_we(cfg_we),
    .cfg_addr(cfg_addr), .cfg_data(cfg_data), .seal(seal), .go(go), .epoch(epoch), .layer(layer),
    .static_cmd_owner(d_own), .static_cmd(d_cmd), .reserved_rd(d_rd), .reserved_static_col(d_sc),
    .reserved_write_col(d_wc), .static_epoch(d_ep), .expected_raw_valid(d_raw), .fault(d_f), .idle(d_i));
  wire [63:0] r_all = {r_own, r_cmd, r_rd, r_sc, r_wc, r_raw, r_f, r_i, r_ep};
  wire [63:0] d_all = {d_own, d_cmd, d_rd, d_sc, d_wc, d_raw, d_f, d_i, d_ep};
  integer t, bad = 0, chk = 0, cmds = 0, gos = 0, faults = 0, seed, k, edges;
  reg [31:0] seen;
  always @(negedge hck) begin
    chk = chk + 1;
    if (r_cmd != 0) cmds = cmds + 1;
    if (r_all !== d_all) begin bad = bad + 1;
      if (bad < 8) $display("MISMATCH t=%0d ref %h dut %h", t, r_all, d_all); end
  end
  function [63:0] rec(input integer r);   // small timing fields: wait[15:0] < 8, left < 6, burst cfg < 4, reload < 8
    reg [63:0] d; begin d = {$urandom, $urandom};
      d[15:0] = $urandom % 8; d[25:16] = $urandom % 6; d[29:26] = $urandom % 4; d[37:30] = $urandom % 8;
      rec = d; end
  endfunction
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1; k = $urandom(seed);
    if (!$value$plusargs("edges=%d", edges)) edges = 60000;
    repeat (6) @(negedge hck); rst_n = 1;
    t = 0;
    while (t < edges) begin
      // configure: random-order writes until all 32 halves were written (repeats allowed)
      seen = 0;
      while (seen != 32'hffffffff && t < edges) begin
        @(negedge hck); t = t + 1;
        cfg_we = ($urandom % 4) != 0; cfg_addr = $urandom % 32; cfg_data = cfg_addr[4] ? {$urandom, $urandom} : rec(0);
        // the high half: bit 84 (row select), 85 static read, 83:81 mask (one-hot most of the time)
        if (cfg_addr[4]) begin cfg_data[20] = $urandom % 2; cfg_data[21] = $urandom % 2;
          cfg_data[19:17] = (($urandom % 8) == 0) ? $urandom % 8 : (3'b1 << ($urandom % 3)); end
        if (cfg_we) seen[cfg_addr] = 1;
        seal = ($urandom % 200) == 0; go = ($urandom % 300) == 0;
        epoch = $urandom; layer = $urandom;
        if (($urandom % 3000) == 0) begin rst_n = 0; repeat (3) @(negedge hck); rst_n = 1; seen = 0; end
      end
      @(negedge hck); t = t + 1; cfg_we = 0; seal = 1; go = 0;
      @(negedge hck); t = t + 1; seal = 0;
      // run: go when idle, a few times; occasional illegal events
      repeat (6) begin
        repeat ($urandom % 4) begin @(negedge hck); t = t + 1; end
        go = 1; gos = gos + 1; epoch = $urandom; layer = $urandom;
        @(negedge hck); t = t + 1; go = 0;
        repeat (3) begin @(negedge hck); t = t + 1; end
        while (!r_i && t < edges) begin
          @(negedge hck); t = t + 1;
          go = ($urandom % 400) == 0; cfg_we = ($urandom % 400) == 0; seal = ($urandom % 400) == 0;
          cfg_addr = $urandom; cfg_data = rec(0);
        end
        go = 0; cfg_we = 0; seal = 0;
      end
      if (r_f) faults = faults + 1;
      rst_n = 0; repeat (3) @(negedge hck); rst_n = 1; t = t + 4;
    end
    if (bad == 0 && cmds > 0) $display("KVPC_CAL PASS edges=%0d checks=%0d cmd_edges=%0d gos=%0d fault_rounds=%0d errors=0 mut=%0d", t, chk, cmds, gos, faults, `KVPC_MUT);
    else $display("KVPC_CAL FAIL edges=%0d checks=%0d errors=%0d cmd_edges=%0d gos=%0d mut=%0d", t, chk, bad, cmds, gos, `KVPC_MUT);
    $finish;
  end
endmodule
