`timescale 1ns/1ps
// q13b-kvend 2026-10-13: bench of the pin-registered link-buffer tiles ot_qkvd_sbufp / ot_qkvd_fbuf8p (pop registered
// inside, acts one cycle after the pin), driven as the d2d parent drives them at PQ=2: the pop pin is a registered
// decision taken from the parent shadow (ot_qkvd_*_shadow PIQ=1 ne_next).  Checks every cycle:
//   (a) the p tile equals the original tile fed the same pop one cycle later (dout while non-empty, empty),
//   (b) the shadow's empty equals the tile's empty,
//   (c) scoreboard: every word popped (at the effective pop) is the model's next word, a pop never hits an empty head,
//       and the buffer drains.
// +define+FBUF8 selects the flop tile.  Mutant +define+KVD_PIQMUT (pop not registered in the slices) must FAIL.
module tb_qkvd_buf_tile_p;
    parameter integer D = 8, N = 200000, SEED = 7;
    localparam integer W = 528;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg push, pin; reg [W-1:0] din;
    reg pop_e;                                   // the pop acting this cycle = the pin one cycle ago
    wire [W-1:0] d1, d0; wire e1, e0, she, shn;
`ifdef FBUF8
    ot_qkvd_fbuf8p u_dut (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pin), .dout(d1), .empty(e1));
    ot_qkvd_fbuf8  u_ref (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop_e), .dout(d0), .empty(e0));
    ot_qkvd_fbuf8_shadow #(.PIQ(1)) u_sh (.clk(clk), .rst_n(rst_n), .push(push), .pop(pin), .empty(she), .ne_next(shn));
`else
    ot_qkvd_sbufp u_dut (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pin), .dout(d1), .empty(e1));
    ot_qkvd_sbuf  u_ref (.clk(clk), .rst_n(rst_n), .push(push), .din(din), .pop(pop_e), .dout(d0), .empty(e0));
    ot_qkvd_sbuf_shadow #(.PIQ(1)) u_sh (.clk(clk), .rst_n(rst_n), .push(push), .pop(pin), .empty(she), .ne_next(shn));
`endif
    reg [W-1:0] q [$]; reg [W-1:0] hq, junk;
    integer cnt, cyc, bad, s, pp, qp, pops, k, live;
    task fail(input [255:0] m); begin bad = bad + 1; if (bad <= 5) $display("MISMATCH cyc %0d %0s", cyc, m); end endtask
    initial begin
        s = SEED; bad = 0; pops = 0; push = 0; pin = 0; pop_e = 0; din = 0; cnt = 0; live = 0;
        repeat (4) @(posedge clk); #0.1 rst_n = 1;
        for (cyc = 0; cyc < N + 600; cyc = cyc + 1) begin
            @(posedge clk); #0.1;
            if (cyc % 2000 == 0) begin pp = $urandom(s) % 101; qp = $urandom(s) % 101; end
            live = live + 1;
            // (a) / (b) / (c) on the settled outputs of this cycle; pop_e (the previous pin) acts at the next edge
            pop_e = pin;
            if (live > 8) begin
                if (e1 !== e0) fail("empty differs from the reference tile");
                if (!e0 && d1 !== d0) fail("dout differs from the reference tile");
                if (she !== e1) fail("shadow empty differs");
            end
            if (pop_e) begin
                if (e1 || q.size() == 0) fail("pop of an empty head");
                else begin hq = q[0]; if (d1 !== hq) fail("popped word is not the next word"); end
                if (q.size()) junk = q.pop_front();
                pops = pops + 1; cnt = cnt - 1;
            end
            pin  = (live > 8) && shn && (($urandom(s) % 100) < qp);   // registered decision = next cycle's pin
            push = (live > 8) && (cyc < N) && (cnt < D) && (($urandom(s) % 100) < pp);
            for (k = 0; k < W / 32 + 1; k = k + 1) din[32*k +: 32] = $urandom(s);
            if (cyc >= N) begin qp = 100; end
            if (push) begin q.push_back(din); cnt = cnt + 1; end
        end
        if (q.size() != 0) begin bad = bad + 1; $display("MISMATCH buffer did not drain (%0d left)", q.size()); end
        if (bad == 0) $display("PASS buf_tile_p D=%0d cycles=%0d pops=%0d", D, N, pops);
        else $display("FAIL buf_tile_p bad=%0d", bad);
        $finish;
    end
endmodule
