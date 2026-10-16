`timescale 1ns/1ps
// kvsys v1.4.3 regional reset release bench (Q-KVSYS-DIE 2026-10-15): the HOST reset level runs over three relay chains
// of different depth (d = 40 / 150 / 200, relays = reset-less flops with RANDOM power-up contents) into three
// qkd_rst_region roots strapped dly = D - d (D = 200), each driving a local relay tree (L = 5 / 60 / 120 < 128).
// Checks: (1) every load is low from POR release + L + 3 until the host release; (2) every load releases EXACTLY at
// host release + D + 2 + L; (3) a host re-assert reaches every load within d + 2 + L cycles and each region stays low
// >= HOLD cycles; after the host re-release the loads release on the calendar or HOLD, never earlier.
// MUT 1: no ignore window (unflushed chain value may release a region); MUT 2: dly ignored (calendar broken).
module tb_qkd_rst_region;
  parameter integer MUT = 0;
  localparam integer D = 200, HOLD = 128;
  localparam integer NR = 3;
  integer DR [0:NR-1]; integer LR [0:NR-1];
  initial begin DR[0]=40; DR[1]=150; DR[2]=200; LR[0]=5; LR[1]=60; LR[2]=120; end
  reg ck = 0; always #0.5 ck = ~ck;
  reg por_n = 0, host = 0;
  reg [255:0] ch [0:NR-1];         // chain shift registers (bit 0 = first relay)
  reg [127:0] lt [0:NR-1];         // local trees (bit 0 = first relay after the root)
  wire [NR-1:0] rb;
  genvar g;
  generate for (g = 0; g < NR; g = g + 1) begin : gr
    wire a_in = ch[g][DR[g]-1];
    qkd_rst_region #(.MUT(MUT)) u_root (.ck(ck), .por_n(por_n), .a(a_in), .dly(8'(D - DR[g])), .b(rb[g]));
  end endgenerate
  integer i, k, cyc = 0, errs = 0, t_por = 0, t_rel = -1, t_ra = -1, t_rr = -1;
  integer low_since [0:NR-1];
  initial for (i = 0; i < NR; i = i + 1) begin ch[i] = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
                                               lt[i] = {$urandom,$urandom,$urandom,$urandom}; low_since[i] = -1; end
  always @(posedge ck) begin
    for (k = 0; k < NR; k = k + 1) begin ch[k] <= {ch[k][254:0], host}; lt[k] <= {lt[k][126:0], rb[k]}; end
    cyc <= cyc + 1;
  end
  function automatic loadv(input integer r); loadv = lt[r][LR[r]-1]; endfunction
  task automatic check;
    for (k = 0; k < NR; k = k + 1) begin
      // (1) low after local flush until the release calendar
      if (cyc >= t_por + LR[k] + 3 && (t_rel < 0 || cyc < t_rel + D + 2 + LR[k]) && loadv(k) !== 1'b0) begin
        errs = errs + 1; if (errs < 10) $display("ERR early/unflushed release region %0d cyc %0d", k, cyc); end
      // (2) exact calendar release
      if (t_rel >= 0 && t_ra < 0 && cyc >= t_rel + D + 2 + LR[k] && loadv(k) !== 1'b1) begin
        errs = errs + 1; if (errs < 10) $display("ERR late release region %0d cyc %0d (calendar %0d)", k, cyc, t_rel + D + 2 + LR[k]); end
      // (3) re-assert reaches the load within d + 2 + L
      if (t_ra >= 0 && cyc >= t_ra + DR[k] + 2 + LR[k] && (t_rr < 0 || cyc < t_ra + DR[k] + 2 + LR[k] + HOLD) && loadv(k) !== 1'b0) begin
        errs = errs + 1; if (errs < 10) $display("ERR re-assert not held region %0d cyc %0d", k, cyc); end
    end
  endtask
  initial begin
    repeat (5) @(negedge ck); por_n = 1; t_por = cyc + 2;
    repeat (400) begin @(negedge ck); check; end        // host holds reset >= IGNORE + 4 after POR
    host = 1; t_rel = cyc;
    repeat (D + 200) begin @(negedge ck); check; end
    host = 0; t_ra = cyc;
    repeat (12) begin @(negedge ck); check; end
    host = 1; t_rr = cyc;
    repeat (D + HOLD + 300) begin @(negedge ck); check; end
    for (k = 0; k < NR; k = k + 1) if (loadv(k) !== 1'b1) begin errs = errs + 1; $display("ERR region %0d not released after re-release", k); end
    if (errs) begin $display("RST_REGION_FAIL errors=%0d", errs); $fatal(1); end
    $display("RST_REGION_PASS regions=%0d chains=40/150/200 local=5/60/120 calendar D+2+L exact, re-assert + HOLD", NR);
    $finish;
  end
endmodule
