`timescale 1ns/1fs
// tb_s81_rate_match (ELEM-CENSUS 2026-10-16, S81-LINK leaf kit): unit bench of ot_s81_rate_match (ot_pdie_serdes.sv),
// the recovered-clock -> local-clock lane-beat crossing of the S81 die links, standalone at a plesiochronous offset
// far beyond the 300 ppm link budget (+-~1100 ppm) so the drop / insert paths are exercised many times.
//   writer (wclk): one beat a cycle after reset; data beat k = {k, pattern} with bit 1 = 0, one gearbox IDLE beat
//   (512'b10) every IDLE_EVERY beats.  FAST 1: writer clock faster than the reader (IDLE beats must be DROPPED);
//   FAST 0: writer slower (the reader must INSERT IDLE beats).
//   reader (rclk): every non-IDLE beat must arrive in order and exact; no fault; and the slip must be absorbed on IDLE
//   beats only: FAST 1 -> idle beats seen between data < idle beats sent (>= MIN_SLIP dropped), FAST 0 -> > (>= MIN_SLIP
//   inserted).
// Verdict line: TB_S81_RATE_MATCH FAST=<f> sent=.. got=.. bad=.. idle_sent=.. idle_seen=.. slip=.. fault=.. PASS|FAIL
module tb_s81_rate_match;
    parameter integer FAST = 1, NB = 24000, IDLE_EVERY = 128, MIN_SLIP = 8;
    reg wclk = 0, rclk = 0, wrst_n = 0, rrst_n = 0;
    always #0.416667 rclk = ~rclk;
    generate if (FAST) begin : g_f always #0.416200 wclk = ~wclk; end
             else      begin : g_s always #0.417130 wclk = ~wclk; end endgenerate
    reg w_v = 0; reg [511:0] w_d = 512'd2;
    wire [511:0] r_d; wire fault;
    ot_s81_rate_match u_rm (.wclk(wclk), .wrst_n(wrst_n), .w_v(w_v), .w_d(w_d), .rclk(rclk), .rrst_n(rrst_n), .r_d(r_d),
        .fault(fault));
    function automatic [511:0] beat(input integer n);
        beat = {32'(n), 32'(n * 7 + 3), 32'(n ^ 32'h5A5A), 384'h0, 30'(n), 2'b00} ^ ({64'h0, {448{n[0]}}} & ~512'h3);
    endfunction
    // ---- writer
    integer sent = 0, idle_sent = 0, wc = 0;
    always @(posedge wclk) if (wrst_n) begin
        wc = wc + 1;
        if (wc > 20 && sent < NB) begin
            w_v <= 1'b1;
            if (wc % IDLE_EVERY == 0) begin w_d <= 512'd2; idle_sent = idle_sent + 1; end
            else begin w_d <= beat(sent); sent = sent + 1; end
        end else begin w_v <= (wc > 20); w_d <= 512'd2; end
    end
    // ---- reader: idles counted only between data beats (not before the first / after the last)
    integer got = 0, bad = 0, idle_seen = 0, idle_run = 0, fault_seen = 0;
    always @(posedge rclk) if (rrst_n) begin
        if (fault) fault_seen = 1;
        if (r_d[1] && !r_d[0]) idle_run = idle_run + 1;
        else begin
            if (got > 0) idle_seen = idle_seen + idle_run;
            idle_run = 0;
            if (r_d !== beat(got)) begin bad = bad + 1; if (bad < 4) $display("ERR beat %0d", got); end
            got = got + 1;
        end
    end
    integer slip; reg ok;
    initial begin
        repeat (5) @(posedge rclk); wrst_n = 1; rrst_n = 1;
        wait (sent == NB);
        repeat (64) @(posedge rclk);
        // idle_sent counts every IDLE the writer sent between its data beats
        slip = FAST ? idle_sent - idle_seen : idle_seen - idle_sent;
        ok = got == NB && bad == 0 && !fault_seen && slip >= MIN_SLIP;
        $display("TB_S81_RATE_MATCH FAST=%0d sent=%0d got=%0d bad=%0d idle_sent=%0d idle_seen=%0d slip=%0d fault=%0d %s", FAST,
                 sent, got, bad, idle_sent, idle_seen, slip, fault_seen, ok ? "PASS" : "FAIL");
        $finish;
    end
endmodule
