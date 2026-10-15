`timescale 1ns/1ps
// tb_sel_c1 (s81-die-rtl-bind 2026-10-14, F5): the 1-stack selector master dsfd_bk_selector_c1 (SW lane only, absent
// quarters synthesised as EMPTY quarters) against the REFERENCE 4-lane dsfd_bk_selector fed with the same SW lane and
// explicit empty quarters (header + one empty last beat) on the three other lanes from the bench.  Segments: random
// qslot r, tag, k (1..64), base, 4..40 beats of 16 BF16 scores (random lane masks, some -0 / equal keys), paced one beat
// every 3 cycles; the next segment after the DONE word (the selector also sends one DONE after reset: NSEG + 1).  CHECK: the DUT's vd word stream (IDX / DONE / FAULT words) =
// the reference's, word for word; no fault word.  MUT 1 (synthesised qslots collide with SW) must FAIL.
module tb_sel_c1;
    parameter integer MUT = 0, NSEG = 40, SEED = 7;
    reg ck = 0, rst = 0; always #1 ck = ~ck;
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg [63:0] rs = 64'h5851F42D4C957F2D ^ SEED;
    function [31:0] rnd(input integer d); begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end endfunction
    reg [514:0] sw = 0, e1 = 0, e2 = 0, e3 = 0;
    wire [513:0] vd_d, vd_r; wire vf_d, vf_r; wire [8:0] cdn; wire [1:0] cst;
    dsfd_bk_selector_c1 #(.MUT(MUT)) dut (.ck(ck), .iSW(sw), .rst(rst), .vd(vd_d), .vf(vf_d), .c_cmd(85'd0), .c_done(cdn), .c_st(cst));
    // reference: the SW lane delayed one cycle (the DUT's absent-quarter tile pin flop) + bench empty quarters
    reg [514:0] sw1 = 0;
    always @(posedge ck) sw1 <= sw;
    reg [1:0] rq [0:3];
    wire [4*515-1:0] rl = {e3, e2, e1, sw1};
    dsfd_bk_selector u_ref (.ck(ck), .iNE(rl[3*515 +: 515]), .iNW(rl[2*515 +: 515]), .iSE(rl[515 +: 515]), .iSW(rl[0 +: 515]),
        .rst(rst), .vd(vd_r), .vf(vf_r));
    reg [511:0] qd [0:65535], qr [0:65535]; integer nd = 0, nr = 0, dones = 0, faults = 0;
    always @(posedge ck) begin
        if (vd_d[1]) begin qd[nd] = vd_d[513:2]; nd = nd + 1; if (vd_d[513:510] == 4'd5) faults = faults + 1; end
        if (vd_r[1]) begin qr[nr] = vd_r[513:2]; nr = nr + 1; if (vd_r[513:510] == 4'd4) dones = dones + 1; end
    end
    // driver
    integer s, b, nb, k, r, l, gap;
    reg [7:0] tag;
    task word(input [514:0] w, input integer ref_empty_hdr, input [7:0] t, input [9:0] kk, input [1:0] rr);
        integer j; reg [1:0] q;
        begin
            @(negedge ck); sw = w;
            if (ref_empty_hdr == 1) begin            // the three other quarters' empty headers (same cycle as the DUT's)
                for (j = 1; j < 4; j = j + 1) begin
                    q = rr + j;
                    if (j == 1) e1 = {1'b0, 1'b1, 4'd1, t, 468'd0, q, kk, 20'd0, 1'b1};
                    if (j == 2) e2 = {1'b0, 1'b1, 4'd1, t, 468'd0, q, kk, 20'd0, 1'b1};
                    if (j == 3) e3 = {1'b0, 1'b1, 4'd1, t, 468'd0, q, kk, 20'd0, 1'b1};
                end
            end else if (ref_empty_hdr == 2) begin    // their empty last beats
                e1 = {1'b0, 1'b1, 4'd2, t, 227'd0, 1'b1, 16'd0, 256'd0, 1'b1}; e2 = e1; e3 = e1;
            end else begin
                e1 = {1'b0, 1'b1, 512'd0, 1'b0}; e2 = e1; e3 = e1;
            end
        end
    endtask
    integer seen;
    initial begin
        sw = {1'b0, 1'b0, 512'd0, 1'b0}; e1 = sw; e2 = sw; e3 = sw;
        #9 rst = 1;
        repeat (20) @(posedge ck);
        sw = {1'b0, 1'b1, 512'd0, 1'b0}; e1 = sw; e2 = sw; e3 = sw;
        repeat (40) @(posedge ck);
        for (s = 0; s < NSEG; s = s + 1) begin
            tag = s; k = 1 + rnd(0) % 64; r = rnd(0) % 4; nb = 4 + rnd(0) % 37;
            seen = dones;
            // the reference sees the SW word one cycle later (sw1): its empty headers go out with the SW header's arrival
            word({1'b0, 1'b1, 4'd1, tag, 468'd0, 2'(r), 10'(k), 20'(rnd(0) % 1000 * 16), 1'b1}, 0, tag, k, r);
            word({1'b0, 1'b1, 512'd0, 1'b0}, 1, tag, k, r);
            word({1'b0, 1'b1, 512'd0, 1'b0}, 2, tag, k, r);
            for (b = 0; b < nb; b = b + 1) begin
                reg [255:0] sc; reg [15:0] lv;
                for (l = 0; l < 16; l = l + 1) sc[16 * l +: 16] = (rnd(0) % 5 == 0) ? 16'h3F80 : ((rnd(0) % 7 == 0) ? 16'h8000 : 16'(rnd(0) & 16'h7F7F));
                lv = (rnd(0) % 4 == 0) ? 16'(rnd(0)) : 16'hFFFF;
                word({1'b0, 1'b1, 4'd2, tag, 227'd0, (b == nb - 1) ? 1'b1 : 1'b0, lv, sc, 1'b1}, 0, tag, k, r);
                word({1'b0, 1'b1, 512'd0, 1'b0}, 0, tag, k, r);
                word({1'b0, 1'b1, 512'd0, 1'b0}, 0, tag, k, r);
            end
            gap = 0;
            while (dones == seen && gap < 20000) begin @(posedge ck); gap = gap + 1; end
            repeat (30) @(posedge ck);
        end
        repeat (200) @(posedge ck);
        begin : chk
            integer i, bad;
            bad = 0;
            if (nd != nr) bad = bad + 1;
            for (i = 0; i < nr && i < nd; i = i + 1) if (qd[i] !== qr[i]) begin bad = bad + 1; if (bad < 5) $display("ERR word %0d dut %h ref %h", i, qd[i][511:448], qr[i][511:448]); end
            $display("TB_SEL_C1 MUT=%0d segments=%0d dones=%0d words dut=%0d ref=%0d fault_words=%0d mismatches=%0d %s", MUT, NSEG, dones,
                     nd, nr, faults, bad, (bad == 0 && dones == NSEG + 1 && faults == 0) ? "PASS" : "FAIL");
        end
        $finish;
    end
endmodule
