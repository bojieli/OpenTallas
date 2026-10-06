`timescale 1ps/1ps
// CLAUDE HBM-ABSTRACTS (svcidx): bench of the INTERIM index-quarter view (one seed; $fatal on any mismatch / timeout)
//   a0..a3 packets -> t_su lane 0 (a0, a1) / lane 1 (a2, a3), each packet exactly once, in order per row
//   k words (forwarded, 1.024 ns) -> t_vm = k[511:0] ^ k[1023:512], every word once, in order
module tb_hfd_index_q;
  reg ck = 0, fk = 0, rst = 0;
  always #417 ck = ~ck;           // clk_stream 0.833 ns
  always #512 fk = ~fk;           // forwarded key clock (stream service clk_hbm 1.024 ns)
  reg [528:0] a [0:3]; reg [1023:0] kd;
  wire [1057:0] t_su; wire [511:0] t_vm;
  hfd_index_q dut (.a0(a[0]), .a1(a[1]), .a2(a[2]), .a3(a[3]), .ck(ck), .k({fk, fk, kd}), .rst(rst), .t_su(t_su), .t_vm(t_vm));
  integer err = 0, i, sent [0:3], got [0:3], ks = 0, kg = 0, n;
  reg [527:0] exp [0:3][0:255]; reg [511:0] kexp [0:4095];
  reg [511:0] vm_prev;
  initial begin for (i = 0; i < 4; i = i + 1) begin a[i] = 0; sent[i] = 0; got[i] = 0; end kd = 0; end
  // attention rows: sparse packets (<= 1 in 3 cycles per row on average)
  always @(posedge ck) if (rst) for (i = 0; i < 4; i = i + 1) begin
    if (sent[i] < 64 && ($urandom % 5 == 0)) begin : s
      reg [527:0] d; d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                          $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
      a[i] <= {d, 1'b1}; exp[i][sent[i]] = d; sent[i] = sent[i] + 1;
    end else a[i] <= {a[i][528:1], 1'b0};
  end
  // lanes: the packet must be the next one of row 2g or 2g+1
  always @(posedge ck) for (n = 0; n < 2; n = n + 1) if (t_su[n*529]) begin : c
    reg [527:0] d; d = t_su[n*529+1 +: 528];
    if (got[2*n] < sent[2*n] && d === exp[2*n][got[2*n]]) got[2*n] = got[2*n] + 1;
    else if (got[2*n+1] < sent[2*n+1] && d === exp[2*n+1][got[2*n+1]]) got[2*n+1] = got[2*n+1] + 1;
    else begin err = err + 1; $display("ERR lane %0d unexpected packet", n); end
  end
  // keys: a new word every forwarded cycle
  always @(posedge fk) if (rst && ks < 400) begin : kk
    reg [1023:0] w; integer j; for (j = 0; j < 32; j = j + 1) w[j*32 +: 32] = $urandom;
    kd <= w; kexp[ks] = w[511:0] ^ w[1023:512]; ks = ks + 1;
  end
  always @(posedge ck) if (rst && t_vm !== vm_prev) begin
    vm_prev <= t_vm;
    if (kg < ks && t_vm === kexp[kg]) kg = kg + 1;
    else begin err = err + 1; $display("ERR t_vm word %0d mismatch", kg); end
  end
  initial begin
    vm_prev = {512{1'bx}};
    repeat (6) @(posedge ck); rst = 1;
    fork : w
      begin wait (got[0] + got[1] + got[2] + got[3] == 256 && kg >= 390); repeat (40) @(posedge ck); disable w; end
      begin repeat (40000) @(posedge ck); $display("ERR timeout got %0d %0d %0d %0d keys %0d/%0d", got[0], got[1], got[2], got[3], kg, ks); err = err + 1; disable w; end
    join
    $display("IDXQ_BENCH packets=%0d keys=%0d errors=%0d", got[0] + got[1] + got[2] + got[3], kg, err);
    if (err != 0) $fatal(1, "IDXQ_BENCH FAIL");
    $display("IDXQ_BENCH PASS"); $finish;
  end
endmodule
