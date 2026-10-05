`timescale 1ps/1fs
// Lockstep equivalence bench: r0 KV write-back unit (sha256 baeca01c..., renamed copy ot_hbm_accel_dskv_wb_r0_ref)
// vs the edited ot_hbm_accel_dskv_wb, same random inputs (rows of every kind/slot/ratio with random 544-byte
// data, shadow loads, random positions and dies, write-network back-pressure, ACK counts); every output compared
// on every cycle, except that the write payload (wq_pc/bank/row/col/data) is compared only while wq_v is high:
// it is qualified by wq_v (r0 also drives don't-care payload while idle; r1 differs there in the S_MAP cycle).  Verilator 5.050 --binary --timing.  Plusargs +SEED +CYC; -G STACK, RP (1/RP row offer prob).
module tb_dskv_wb_lockstep;
  parameter integer STACK = 1, RP = 3, POSMODE = 0;
  reg clk = 0, rst_n = 0;
  always #417 clk = ~clk;
  reg [6:0] die; reg [19:0] pos; reg row_v, row_r2, sh_v, wq_r; reg [1:0] row_kind; reg [5:0] row_slot; reg [2:0] sh_slot;
  reg [4351:0] row_data, sh_data; reg [5:0] ack_n;
  wire [347:0] oa, ob;
  ot_hbm_accel_dskv_wb_r0_ref #(.ENABLE(1),.STACK(STACK)) a(.clk(clk),.rst_n(rst_n),.die(die),.pos(pos),.row_v(row_v),
    .row_kind(row_kind),.row_slot(row_slot),.row_r2(row_r2),.row_data(row_data),.row_r(oa[0]),.sh_v(sh_v),.sh_slot(sh_slot),
    .sh_data(sh_data),.wq_v(oa[1]),.wq_pc(oa[6:2]),.wq_bank(oa[11:7]),.wq_row(oa[30:12]),.wq_col(oa[35:31]),.wq_data(oa[291:36]),
    .wq_r(wq_r),.ack_n(ack_n),.issued(oa[307:292]),.acked(oa[323:308]),.fence_ok(oa[324]));
  ot_hbm_accel_dskv_wb_flat #(.ENABLE(1),.STACK(STACK)) b(.clk(clk),.rst_n(rst_n),.die(die),.pos(pos),.row_v(row_v),
    .row_kind(row_kind),.row_slot(row_slot),.row_r2(row_r2),.row_data(row_data),.row_r(ob[0]),.sh_v(sh_v),.sh_slot(sh_slot),
    .sh_data(sh_data),.wq_v(ob[1]),.wq_pc(ob[6:2]),.wq_bank(ob[11:7]),.wq_row(ob[30:12]),.wq_col(ob[35:31]),.wq_data(ob[291:36]),
    .wq_r(wq_r),.ack_n(ack_n),.issued(ob[307:292]),.acked(ob[323:308]),.fence_ok(ob[324]));
  assign oa[347:325] = 0; assign ob[347:325] = 0;
  integer seed, cyc, i, k, mism = 0, rows = 0, emits = 0, shl = 0, keys = 0;
  function automatic integer rnd(input integer m); rnd = $urandom % m; endfunction
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("CYC=%d", cyc)) cyc = 200000;
    void'($urandom(seed));
    die = 0; pos = 0; row_v = 0; row_r2 = 0; sh_v = 0; wq_r = 0; row_kind = 0; row_slot = 0; sh_slot = 0;
    row_data = 0; sh_data = 0; ack_n = 0;
    repeat (3) @(posedge clk); #10 rst_n = 1;
    for (i = 0; i < cyc; i = i + 1) begin
      @(negedge clk);
      if ({oa[347:292], oa[1:0]} !== {ob[347:292], ob[1:0]} || (oa[1] && oa[291:2] !== ob[291:2])) begin mism = mism + 1; if (mism < 10) $display("MISMATCH cyc=%0d a=%h b=%h", i, oa, ob); end
      if (row_v && oa[0]) begin rows = rows + 1; if (row_kind == 2) keys = keys + 1; end
      if (sh_v && oa[0] == 1'b0 && a.on.st == 0) shl = shl + 1;
      if (oa[1] && wq_r) emits = emits + 1;
      // a token's position and die change rarely (static per token)
      if (rnd(2000) == 0 || i == 0) begin
        pos = (POSMODE == 1) ? 20'hFFFFF : 20'($urandom);
        die = (rnd(4) == 0) ? 7'd31 : 7'(rnd(96));
      end
      row_v = rnd(RP) == 0; row_kind = 2'(rnd(3)); row_slot = 6'(rnd(40)); row_r2 = rnd(2);
      for (k = 0; k < 136; k = k + 1) row_data[32*k +: 32] = $urandom;
      sh_v = rnd(40) == 0; sh_slot = 3'(rnd(8));
      for (k = 0; k < 136; k = k + 1) sh_data[32*k +: 32] = $urandom;
      wq_r = rnd(4) != 0; ack_n = 6'(rnd(3));
    end
    $display("SUMMARY dskv_wb_lockstep STACK=%0d RP=%0d POSMODE=%0d seed=%0d cycles=%0d mismatches=%0d rows=%0d keys=%0d emits=%0d verdict=%s",
             STACK, RP, POSMODE, seed, cyc, mism, rows, keys, emits, (mism == 0) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
