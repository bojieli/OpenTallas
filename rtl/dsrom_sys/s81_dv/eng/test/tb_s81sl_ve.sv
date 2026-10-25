`timescale 1ns/1ps
// S81U-MIX bench for ot_s81sl_ve (one beat leaf, 4 copies x 64 elements) against tools/hdc_golden_v41 (chunk8):
// beat partials hh / kk / dd = csum over the beat (an aligned golden subtree) and out = bf16(h + gate*v), bit exact.
// Fixtures from tools/s81_dv/ve_golden.py (+dir=).  Reduce stream: one quad a cycle (GAP idle cycles between quads,
// the feeder's cadence); add stream: one 8-lane sub-beat a cycle.  Reports the fixed latencies.
module tb_s81sl_ve #(parameter integer MUT = 0, GAP = 1, LM = 5, LA = 4);
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg r_v = 0; reg [1:0] r_c = 0; reg [127:0] r_h = 0, r_k = 0, r_w = 0;
    reg a_v = 0; reg [1:0] a_c = 0; reg [255:0] a_h = 0, a_val = 0; reg [31:0] a_g = 0;
    wire [63:0] r_hp = {r_h[127:112], r_h[95:80], r_h[63:48], r_h[31:16]}; wire [127:0] a_hp = {a_h[255:240], a_h[223:208], a_h[191:176], a_h[159:144], a_h[127:112], a_h[95:80], a_h[63:48], a_h[31:16]};   // packed BF16 h for ot_s81sl_ve (OWNER DECISION 8)
    wire p_v, o_v, fault; wire [1:0] p_c, o_c; wire [31:0] p_hh, p_kk, p_dd; wire [127:0] o_yp; wire [255:0] o_y = {o_yp[127:112], 16'd0, o_yp[111:96], 16'd0, o_yp[95:80], 16'd0, o_yp[79:64], 16'd0, o_yp[63:48], 16'd0, o_yp[47:32], 16'd0, o_yp[31:16], 16'd0, o_yp[15:0], 16'd0};
    ot_s81sl_ve #(.LM(LM), .LA(LA), .MUT(MUT)) dut (clk, rst_n, r_v, r_c, r_hp, r_k, r_w, p_v, p_c, p_hh, p_kk, p_dd,
                                               a_v, a_c, a_hp, a_val, a_g, o_v, o_c, o_yp, fault);
    reg [31:0] hm [0:255], km [0:255], wm [0:255], vm [0:63], gm [0:3], pm [0:11], ym [0:255];
    string dir;
    integer i, c, e, cyc = 0, bad = 0, np = 0, no = 0, t_r0 = -1, t_p_last = -1, t_a0 = -1, t_o_last = -1;
    always @(posedge clk) cyc <= cyc + 1;
    // outputs are checked only once reset is released (every unreset register powers up random in this bench, and the
    // outputs during reset assertion are don't-care: the parent's reset covers them)
    always @(posedge clk) if (rst_n) begin
        if (p_v) begin
            if (p_c != np[1:0]) begin bad = bad + 1; $display("BAD partial copy %0d expected %0d", p_c, np); end
            if (p_hh !== pm[3*np] || p_kk !== pm[3*np+1] || p_dd !== pm[3*np+2]) begin
                bad = bad + 1;
                $display("BAD partial copy %0d: hh %h/%h kk %h/%h dd %h/%h", np, p_hh, pm[3*np], p_kk, pm[3*np+1], p_dd, pm[3*np+2]);
            end
            np = np + 1; t_p_last = cyc;
        end
        if (o_v) begin
            for (e = 0; e < 8; e = e + 1)
                if (o_y[32*e +: 32] !== ym[8*no + e]) begin
                    bad = bad + 1;
                    if (bad < 8) $display("BAD y sub-beat %0d lane %0d: %h vs %h", no, e, o_y[32*e +: 32], ym[8*no + e]);
                end
            if (o_c != no[4:3]) begin bad = bad + 1; $display("BAD y copy"); end
            no = no + 1; t_o_last = cyc;
        end
        if (fault && MUT == 0) $fatal(1, "fault at cycle %0d", cyc);
    end
    always @(posedge clk) if (cyc > 5000) $fatal(1, "timeout");
    initial begin
        if (!$value$plusargs("dir=%s", dir)) $fatal(1, "dir required");
        $readmemh({dir, "/h.mem"}, hm); $readmemh({dir, "/k.mem"}, km); $readmemh({dir, "/w.mem"}, wm);
        $readmemh({dir, "/v.mem"}, vm); $readmemh({dir, "/g.mem"}, gm); $readmemh({dir, "/p.mem"}, pm);
        $readmemh({dir, "/y.mem"}, ym);
        repeat (4) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        t_r0 = cyc;
        for (i = 0; i < 64; i = i + 1) begin
            r_v = 1; r_c = i / 16;
            for (e = 0; e < 4; e = e + 1) begin
                r_h[32*e +: 32] = hm[4*i + e]; r_k[32*e +: 32] = km[4*i + e]; r_w[32*e +: 32] = wm[4*i + e];
            end
            @(negedge clk); r_v = 0;
            repeat (GAP) @(negedge clk);
        end
        wait (np == 4); repeat (3) @(negedge clk);
        t_a0 = cyc;
        for (i = 0; i < 32; i = i + 1) begin
            a_v = 1; a_c = i / 8; a_g = gm[i / 8];
            for (e = 0; e < 8; e = e + 1) begin a_h[32*e +: 32] = hm[8*i + e]; a_val[32*e +: 32] = vm[8*(i % 8) + e]; end
            @(negedge clk);
        end
        a_v = 0;
        wait (no == 32); repeat (20) @(negedge clk);
        if (MUT != 0) begin
            if (bad == 0) $fatal(1, "MUTANT %0d NOT DETECTED", MUT);
            $display("MUTANT %0d REJECTED mismatches=%0d", MUT, bad);
        end else begin
        if (bad) $fatal(1, "FAIL %0d mismatches", bad);
        if (np != 4 || no != 32) $fatal(1, "count np=%0d no=%0d", np, no);
        $display("PASS ot_s81sl_ve beat 4 copies x 64: 12 partials + 256 outputs bit exact; reduce first-in -> last partial %0d cyc (GAP %0d), add first-in -> last out %0d cyc",
                 t_p_last - t_r0, GAP, t_o_last - t_a0);
        end
        $finish;
    end
endmodule
