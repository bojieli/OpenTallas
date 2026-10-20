`timescale 1ns/1ps
// tb_s81_ing_n32_lockstep (S81-SHLK12 s10e, 2026-10-20): lockstep equivalence of the native-32 stream engine
// (ot_s81_ing_stream_n32) against the engine it replaces (ot_hdc_kv_ingest, QKV 0 / APIPE 10 / s10b+c+d defines), as
// instantiated by ot_rom_host_ingest on dsdv_sh_lk.  One host word stream (descriptors class 1, payload beats class 2,
// random bubbles) drives both; the write port's ready is random.  Every edge compares every output of the two engines
// (d_rdy, in_rdy, busy, w_v and, when valid, w_addr / w_data, done_v and, when valid, done_tag / n_sectors).
// Descriptors: RAW (a0, n0 sectors), ROWS (rows of rb bytes, pitch, NDIE / DIE / NS split, RING 0/16/32), IKEY (16-key
// groups); fence and tag random; payload beat count = needed beats + 0..1 padding beats.
// Plusargs: +seed=N +segs=N (segments).  Prints PASS LOCKSTEP ... or FAIL lines, then $finish.
module tb_s81_ing_n32_lockstep;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    integer seed, segs, cyc, nwr, ndone, mism;
    // host word queue
    localparam integer QN = 1 << 20;
    reg [513:0] q [0:QN-1];                 // {cls 2, data 512}
    integer qh, qt;
    reg d_v, in_v, w_rdy;
    reg [255:0] d_data; reg [511:0] in_data;
    wire r_d_rdy, r_in_rdy, r_w_v, r_done, r_busy, n_d_rdy, n_in_rdy, n_w_v, n_done, n_busy;
    wire [31:0] r_wa, n_wa, r_ns, n_ns, r_nb, n_nb; wire [255:0] r_wd, n_wd; wire [7:0] r_tag, n_tag;
    wire r_rv, n_rv; wire [31:0] r_ra, n_ra; wire n_drdy_b, n_inrdy_b, n_busy_b, n_wv_b;
    ot_hdc_kv_ingest #(.AW(32), .HDMAX(16), .KVHMAX(1), .QKV(0), .APIPE(10), .QPIPE(0)) u_ref (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(r_d_rdy), .d_data(d_data), .in_v(in_v), .in_rdy(r_in_rdy), .in_data(in_data),
        .w_v(r_w_v), .w_rdy(w_rdy), .w_addr(r_wa), .w_data(r_wd), .r_v(r_rv), .r_rdy(1'b0), .r_addr(r_ra), .rd_v(1'b0),
        .rd_data(256'd0), .done_v(r_done), .done_tag(r_tag), .busy(r_busy), .n_sectors(r_ns), .n_beats(r_nb));
    ot_s81_ing_stream_n32 u_n32 (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(n_d_rdy), .d_data(d_data), .in_v(in_v), .in_rdy(n_in_rdy), .in_data(in_data),
        .w_v(n_w_v), .w_rdy(w_rdy), .w_rdy_c({18{w_rdy}}), .w_addr(n_wa), .w_data(n_wd), .r_v(n_rv), .r_rdy(1'b0), .r_addr(n_ra),
        .rd_v(1'b0), .rd_data(256'd0), .done_v(n_done), .done_tag(n_tag), .busy(n_busy), .n_sectors(n_ns), .n_beats(n_nb),
        .drdy_b(n_drdy_b), .inrdy_b(n_inrdy_b), .busy_b(n_busy_b), .wv_b(n_wv_b));

    function automatic [31:0] rnd(input integer lo, input integer hi);
        rnd = lo + ($urandom % (hi - lo + 1));
    endfunction
    task automatic push_word(input [1:0] c, input [511:0] d);
        begin q[qt] = {c, d}; qt = qt + 1; end
    endtask
    task automatic gen_seg;
        reg [255:0] dsc; integer mode, nb, need, rows, rb, keys, k, ldie, lns, die, ring;
        begin
            dsc = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            mode = (s == 7) ? 0 : rnd(0, 2);
            dsc[7] = $urandom % 2; dsc[15:8] = $urandom;
            ldie = rnd(0, 2); lns = rnd(0, 2); die = (ldie == 0) ? 0 : rnd(0, (1 << ldie) - 1);
            ring = (rnd(0, 3) == 0) ? 16 : 0;
            dsc[217:216] = ldie; dsc[231:224] = die; dsc[233:232] = lns;
            if (mode == 0) begin                              // RAW
                dsc[3:0] = 4'd0; dsc[167:144] = (s == 7) ? rnd(65530, 65545) : rnd(0, 24);   // rare long RAW: st_left hi
                need = (dsc[167:144] + 1) / 2;
            end else if (mode == 1) begin                     // ROWS
                dsc[3:0] = 4'd2;
                rb = rnd(1, 300); rows = rnd(0, 10);
                dsc[183:168] = rb; dsc[199:184] = rows; dsc[167:144] = (rnd(0, 3) == 0) ? 65536 - rnd(0, 12) : (rnd(0, 7) == 0) ? rnd(0, 24'hffffff) : rnd(0, 200);
                dsc[84:80] = (rb + 31) / 32 + rnd(0, 2);
                if (dsc[84:80] == 0) dsc[84:80] = 1;
                dsc[143:112] = ring;
                need = (rows * rb + 63) / 64;
            end else begin                                    // IKEY
                dsc[3:0] = 4'd3;
                keys = 16 * rnd(0, 3);
                dsc[199:184] = keys; dsc[167:144] = (rnd(0, 3) == 0) ? 65536 - 16 * rnd(0, 2) : 16 * rnd(0, 70);
                need = (keys * 68 + 63) / 64;
            end
            nb = need + rnd(0, 1);
            dsc[255:240] = nb;
            push_word(2'd1, {256'd0, dsc});
            for (k = 0; k < nb; k = k + 1)
                push_word(2'd2, {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                                 $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom});
        end
    endtask
    integer s, bub;
    reg hv; reg [513:0] hw;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("segs=%d", segs)) segs = 400;
        void'($urandom(seed));
        qh = 0; qt = 0; cyc = 0; nwr = 0; ndone = 0; mism = 0;
        for (s = 0; s < segs; s = s + 1) gen_seg();
        d_v = 0; in_v = 0; w_rdy = 0; d_data = 0; in_data = 0; hv = 0; hw = 0; bub = 0;
        repeat (5) @(posedge clk);
        rst_n = 1;
    end
    // drive: the head word stays until accepted (it is the host FIFO head); random bubbles before a new head
    always @(negedge clk) if (rst_n) begin
        if (!hv && qh < qt && ($urandom % 8) != 0) begin hv = 1; hw = q[qh]; qh = qh + 1; end
        d_v = hv && hw[513:512] == 2'd1; d_data = hw[255:0];
        in_v = hv && hw[513:512] == 2'd2; in_data = hw[511:0];
        w_rdy = ($urandom % 10) < 7;
    end
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (r_d_rdy !== n_d_rdy || r_in_rdy !== n_in_rdy || r_busy !== n_busy || r_w_v !== n_w_v || r_done !== n_done ||
            (r_w_v && (r_wa !== n_wa || r_wd !== n_wd)) || (r_done && (r_tag !== n_tag || r_ns !== n_ns))) begin
            mism = mism + 1;
            if (mism < 6) $display("MISMATCH cyc %0d: drdy %b/%b inrdy %b/%b busy %b/%b wv %b/%b done %b/%b wa %h/%h tag %h/%h ns %0d/%0d wd_eq %b",
                cyc, r_d_rdy, n_d_rdy, r_in_rdy, n_in_rdy, r_busy, n_busy, r_w_v, n_w_v, r_done, n_done, r_wa, n_wa,
                r_tag, n_tag, r_ns, n_ns, r_wd === n_wd);
        end
        if (r_w_v && w_rdy) nwr = nwr + 1;
        if (r_done) ndone = ndone + 1;
        if (hv && ((d_v && r_d_rdy) || (in_v && r_in_rdy))) hv = 0;
        if ((qh >= qt && !hv && !r_busy && !n_busy) || cyc > 4000000) begin
            if (mism == 0 && qh >= qt && cyc <= 4000000)
                $display("PASS LOCKSTEP seed=%0d segs=%0d cycles=%0d writes=%0d dones=%0d", seed, segs, cyc, nwr, ndone);
            else $display("FAIL LOCKSTEP seed=%0d mismatches=%0d cycles=%0d consumed=%0d/%0d", seed, mism, cyc, qh, qt);
            $finish;
        end
    end
endmodule
