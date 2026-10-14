// qfd_xf_ch (slot leaf of qfd_io_xfifo) against the flat channel ot_qwen_die_cdc_ch #(W 1024, PIPE 2): both get the
// same clocks, reset, words and credits; every output bit of the cell is compared with the flat module on every edge
// of its own clock, and a scoreboard checks that every word arrives once, in order, bit-exact, with no fault.
// Unrelated clocks (HW / HR half periods); credit-respecting sender with random gaps, receiver returning credits after
// random delays.  NEG = 1: the sender ignores credits -> must FAIL (fault / loss).  OT_XF_MUT: must FAIL (data).
`timescale 1ns/1ps
module tb_qfd_xf_ch;
    parameter integer N = 3000, NEG = 0, W = 1024;
    parameter real HW = 1.0, HR = 1.35;
    reg wclk = 0, rclk = 0, rst_n = 0;
    always #HW wclk = ~wclk;
    always #HR rclk = ~rclk;
    reg i_v = 0; reg [W-1:0] i_d = 0; reg o_cr = 0;
    wire i_cr, w_fault, o_v, r_fault; wire [W-1:0] o_d;
    wire f_cr, f_wf, f_v, f_rf; wire [W-1:0] f_d;
    qfd_xf_ch #(.W(W)) u (.wck(wclk), .rck(rclk), .rst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_cr(i_cr), .w_fault(w_fault),
        .o_v(o_v), .o_d(o_d), .o_cr(o_cr), .r_fault(r_fault));
    ot_qwen_die_cdc_ch #(.W(W), .PIPE(2)) f (.wclk(wclk), .wrst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_cr(f_cr), .w_fault(f_wf),
        .rclk(rclk), .rrst_n(rst_n), .o_v(f_v), .o_d(f_d), .o_cr(o_cr), .r_fault(f_rf));
    reg [W-1:0] sent [0:N];
    integer ns = 0, nr = 0, bad = 0, dw = 0, dr = 0, cw = 0, cr = 0, credits = 4, seed = 3, k;
    reg [W-1:0] seen1 = 0, seen0 = 0;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 3; end
    reg [3:0] crpipe = 0;
    reg go = 0;
    always @(posedge wclk) if (go) begin
        if (i_v) begin sent[ns] = i_d; ns = ns + 1; end
        crpipe <= {crpipe[2:0], i_cr};
        credits = credits + crpipe[2];
        if (ns < N && (NEG != 0 || credits > 0) && ($random(seed) % 3 != 0)) begin
            i_v <= 1'b1;
            for (k = 0; k < W; k = k + 1) i_d[k] <= $random(seed);
            credits = credits - 1;
        end else i_v <= 1'b0;
    end
    always @(negedge wclk) if (go) begin cw = cw + 1; if (i_cr !== f_cr || w_fault !== f_wf) dw = dw + 1; end
    reg [15:0] owe = 0;
    always @(posedge rclk) if (rst_n) begin
        if (o_v) begin
            if (nr >= ns || o_d !== sent[nr]) bad = bad + 1;
            seen1 = seen1 | o_d; seen0 = seen0 | ~o_d;
            nr = nr + 1; owe = owe + 1;
        end
        o_cr <= 1'b0;
        if (owe != 0 && ($random(seed) % 4 == 0)) begin o_cr <= 1'b1; owe = owe - 1; end
    end
    always @(negedge rclk) if (go) begin
        cr = cr + 1;
        if (o_v !== f_v || r_fault !== f_rf || (f_v && o_d !== f_d)) dr = dr + 1;
    end
    initial begin
        repeat (8) @(posedge wclk); rst_n = 1; repeat (24) @(posedge wclk); go = 1;
        repeat (N * 16 + 2000) @(posedge wclk);
        if (bad == 0 && nr == N && dw == 0 && dr == 0 && !w_fault && !r_fault && (&seen1) && (&seen0))
            $display("PASS qfd_xf_ch words=%0d wck_edges=%0d rck_edges=%0d cell==flat on every edge, every data bit seen 0 and 1", nr, cw, cr);
        else
            $display("FAIL qfd_xf_ch NEG=%0d: sent %0d received %0d mismatches %0d cell!=flat wck %0d rck %0d w_fault %0d r_fault %0d toggle %0d",
                     NEG, ns, nr, bad, dw, dr, w_fault, r_fault, (&seen1) && (&seen0));
        $finish;
    end
endmodule
