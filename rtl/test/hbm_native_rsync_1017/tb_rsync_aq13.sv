`timescale 1ns/1ps
// HBM-NATIVE 2026-10-17: lockstep f1 (raw rst_n: ot_hbm_xp_aq_tree13_fmt_f1ref) vs f2 (2-flop pin reset sync) x-load
// quantiser (FP4=0). Same random 1024-b x / v stream (random fp32 lanes incl. zero / NaN / Inf / huge exponents, v
// duty ~60%) into both, plus random-time mid-run resets with up to 13 valid beats in flight. Every output is compared
// (vo / fault always, q / e / y whenever vo) at every edge except inside the reset window [assert edge - 3, release edge + 4] (v held low there; f2 asserts and
// releases 2 edges after f1). One PASS/FAIL line.
module tb_rsync_aq13;
parameter integer RSMUT = 0, NCYC = 40000, SEED = 5;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg d_v = 0, hold = 1; reg [1023:0] x = 0;
wire v = d_v & !hold;
wire vo0, vo1, f0, f1; wire [255:0] q0, q1; wire signed [9:0] e0, e1; wire [511:0] y0, y1;
ot_hbm_xp_aq_tree13_fmt_f1ref #(.FP4(0)) u_old(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(vo0),.q(q0),.e(e0),.y(y0),.fault(f0));
ot_hbm_xp_aq_tree13_fmt #(.FP4(0),.RSMUT(RSMUT)) u_new(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(vo1),.q(q1),.e(e1),.y(y1),.fault(f1));
// q / e / y are data registers without reset: compared whenever vo is high (when vo is low they hold stale beats, which
// differ after a reset by the beats r1 cleared and r2 still advanced in the 2 edges before its synchronised assert).
wire [779:0] o0 = {vo0,f0, vo0 ? {q0,e0,y0} : 778'd0}, o1 = {vo1,f1, vo1 ? {q1,e1,y1} : 778'd0};
integer cyc = 0, seed = SEED, err = 0, cmp = 0, nvo = 0, nf = 0, nrst = 0, rlo = 0, win = 0, pre = 0, i, kk;
always @(negedge clk) begin
  cyc = cyc + 1;
  if (cyc == 6) begin rst_n = 1; win = 5; end
  else if (cyc > 6 && rst_n && win == 0 && pre == 0 && ($urandom(seed) % 1500) == 0) begin pre = 3; end
  else if (pre > 0) begin pre = pre - 1; if (pre == 0) begin hold = 1; rst_n = 0; rlo = 3 + $urandom(seed) % 6; nrst = nrst + 1; end end
  else if (cyc > 6 && !rst_n) begin rlo = rlo - 1; if (rlo <= 0) begin rst_n = 1; win = 5; end end
  else if (win > 0) begin win = win - 1; if (win == 0) hold = 0; end
  if (!hold && pre == 0) begin
    cmp = cmp + 1;
    if (o0 !== o1) begin err = err + 1; if (err <= 5) $display("MISMATCH cyc %0d vo %b/%b f %b/%b", cyc, vo0, vo1, f0, f1); end
    if (vo0) nvo = nvo + 1; if (f0) nf = nf + 1;
  end
  d_v = ($urandom(seed) % 10) < 6;
  for (i = 0; i < 32; i = i + 1) begin
    kk = $urandom(seed) % 64;
    x[i*32 +: 32] = (kk == 0) ? 32'h0 : (kk == 1) ? 32'h7fc00000 : (kk == 2) ? 32'h7f800000 :
                    (kk < 6) ? {1'($urandom(seed)), 8'($urandom(seed)), 23'($urandom(seed))} :
                    {1'($urandom(seed)), 8'(110 + $urandom(seed) % 40), 23'($urandom(seed))};
  end
  if (cyc >= NCYC) begin
    $display("RSYNC_AQ13 RSMUT=%0d cycles %0d compared %0d resets %0d vo %0d fault_cycles %0d errors %0d %s",
             RSMUT, cyc, cmp, nrst + 1, nvo, nf, err, (err == 0 && nvo >= 1000 && nrst >= 10) ? "RSYNC_LOCKSTEP PASS" : "RSYNC_LOCKSTEP FAIL");
    $finish;
  end
end
endmodule
