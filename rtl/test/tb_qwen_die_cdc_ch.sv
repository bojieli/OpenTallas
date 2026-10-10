// ot_qwen_die_cdc_ch scoreboard bench: unrelated clocks (wclk 2.0 ns, rclk 2.7 ns), a credit-respecting sender with
// random gaps (credit return travels through 3 extra pipeline cycles) and a downstream receiver returning credits
// after random delays.  Every word must arrive once, in order, bit-exact; no fault.  NEG = 1: the sender ignores
// credits (bursts) -> the bench must FAIL (fault / loss).
`timescale 1ns/1ps
module tb_qwen_die_cdc_ch;
    parameter integer N = 4000, NEG = 0, W = 72, PIPE = 0, AFW = 0;
    parameter real HW = 1.0, HR = 1.35;   // half periods (swap for a faster reader)
    reg wclk = 0, rclk = 0, rst_n = 0;
    always #HW wclk = ~wclk;
    always #HR rclk = ~rclk;
    reg i_v = 0; reg [W-1:0] i_d = 0; wire i_cr, w_fault, o_v, r_fault; wire [W-1:0] o_d; reg o_cr = 0;
    ot_qwen_die_cdc_ch #(.W(W), .PIPE(PIPE), .AFW(AFW)) u (.wclk(wclk), .wrst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_cr(i_cr), .w_fault(w_fault),
        .rclk(rclk), .rrst_n(rst_n), .o_v(o_v), .o_d(o_d), .o_cr(o_cr), .r_fault(r_fault));
    reg [W-1:0] sent [0:N-1];
    integer ns = 0, nr = 0, bad = 0, credits = 4, seed = 3, k;
    reg [3:0] crpipe = 0;
    // sender (wclk)
    reg go = 0;
    // safe-qwen 2026-10-08: the sent-word count is taken in the SAME process, before the send decision (a separate
    // always block raced with it: one word past N was sent, sent[N] out of range -> a false mismatch at N = 4000, 5000).
    always @(posedge wclk) if (go) begin
        if (i_v) begin sent[ns] = i_d; ns = ns + 1; end
        crpipe <= {crpipe[2:0], i_cr};
        credits = credits + crpipe[2];
        if (ns < N && (NEG || credits > 0) && ($random(seed) % 3 != 0)) begin
            i_v <= 1'b1;
            for (k = 0; k < W; k = k + 32) i_d[k +: 32] <= $random(seed);
            credits = credits - 1;
        end else i_v <= 1'b0;
    end
    // receiver (rclk): scoreboard + delayed credit return
    reg [15:0] owe = 0;
    always @(posedge rclk) if (rst_n) begin
        if (o_v) begin
            if (nr >= ns || o_d !== sent[nr]) bad = bad + 1;
            nr = nr + 1; owe = owe + 1;
        end
        o_cr <= 1'b0;
        if (owe > 0 && ($random(seed) & 1)) begin o_cr <= 1'b1; owe = owe - 1; end
    end
    initial begin
        repeat (5) @(posedge rclk); rst_n = 1; repeat (10) @(posedge wclk); go = 1;
        wait (ns == N); repeat (400) @(posedge rclk);
        if (bad == 0 && nr == N && !w_fault && !r_fault) $display("PASS cdc_ch words=%0d", nr);
        else $display("FAIL cdc_ch NEG=%0d: sent %0d received %0d mismatches %0d w_fault %0d r_fault %0d", NEG, ns, nr, bad, w_fault, r_fault);
        $finish;
    end
endmodule
