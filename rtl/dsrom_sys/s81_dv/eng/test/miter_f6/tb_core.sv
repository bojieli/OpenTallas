`timescale 1ns/1ps
// PATH-S81/ENG3 10-25 (from ENG2): exact cycle-by-cycle miter of core E dsdv_eng_rr_e built with -DOT_S81ENG_XQ_OHSEL -DOT_S81ENG_BF_PREDEC (
// one-hot rung selects in u_xq) against the unchanged source (claude/path-s81-eng-1025@d2d23d2ebb: ot_s81eng_rr_n32.sv
// + dsdv_eng_rr_split.sv renamed *_ref; every other file shared and unchanged).  Same random pin stimulus to both,
// incl. reset pulses mid-run and f_ks / pci / rung valid stalls; rco, vo_s, vo_n, st, hx_w compared on EVERY cycle.
module tb;
`ifdef BFP_MUT
    localparam integer XM = 4;
`else
    localparam integer XM = 0;
`endif
    reg ck = 0, rst_n = 0, cfg_en = 0, cfg_layer = 0;
    reg [1:0] cfg_rank = 0;
    reg [52:0] f_ks = 0;
    reg [263:0] pci = 0;
    reg [275:0] vi_s = 0, vi_n = 0;
    reg [1151:0] hx_res = 0;
    reg[52:0] f_ks_d=0;reg cfg_en_d=0;
    // Reference entry stage uses the receiver reset release, matching the added private entry readiness.
    always@(posedge ck or negedge dut.rl[2])if(!dut.rl[2])f_ks_d[52]<=0;else f_ks_d[52]<=f_ks[52];
    always@(posedge ck)begin f_ks_d[51:0]<=f_ks[51:0];cfg_en_d<=cfg_en;end

    wire [38:0] rco, rco_r; wire [275:0] vo_s, vo_n, vo_s_r, vo_n_r; wire [3:0] st, st_r; wire [67:0] hx_w, hx_w_r;
    dsdv_eng_rr_e #(.XQ_MUT(XM)) dut (.ck(ck), .rst_n(rst_n), .cfg_en(cfg_en), .cfg_layer(cfg_layer), .cfg_rank(cfg_rank),
        .f_ks(f_ks), .rco(rco), .pci(pci), .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .st(st), .hx_w(hx_w), .hx_res(hx_res));
    dsdv_eng_rr_e_ref ref0 (.ck(ck), .rst_n(rst_n), .cfg_en(cfg_en_d), .cfg_layer(cfg_layer), .cfg_rank(cfg_rank),
        .f_ks(f_ks_d), .rco(rco_r), .pci(pci), .vi_s(vi_s), .vo_s(vo_s_r), .vi_n(vi_n), .vo_n(vo_n_r), .st(st_r), .hx_w(hx_w_r), .hx_res(hx_res));
    reg [63:0] s;
    function automatic [63:0] xs(input [63:0] x);
        reg [63:0] t; begin t = x ^ (x << 13); t = t ^ (t >> 7); xs = t ^ (t << 17); end
    endfunction
    integer imis = 0, nxd = 0, cyc = 0, ncyc = 40000, seed = 1, mis = 0, n_tx = 0, n_txnz = 0, n_s1 = 0, n_pass = 0, n_rst = 0, k, gap = 0;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 40000;
        s = 64'h2545f4914f6cdd1d ^ {32'd0, seed[31:0]} ^ ({32'd0, seed[31:0]} << 41);
        cfg_rank = seed[1:0];
    end
    always #1 ck = ~ck;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        s = xs(s);
        // reset: released at 8, then a 3..10-edge pulse at ncyc/3 and at a random point of the last third
        if (cyc == 8) rst_n <= 1;
        if (cyc == ncyc / 3 || (cyc > 2 * ncyc / 3 && s[13:0] == 14'd77 && n_rst < 3)) begin rst_n <= 0; gap = 3 + s[16:14]; n_rst <= n_rst + 1; end
        else if (!rst_n && cyc > 8) begin if (gap == 0) rst_n <= 1; else gap = gap - 1; end
        cfg_en <= (cyc > 12) && !(s[23:16] == 8'd0);          // rare cfg_en drops
        if (s[31:24] == 8'd5) cfg_layer <= ~cfg_layer;
        // f_ks: bursts of valid keys with stalls (valid 0 runs)
        s = xs(s);
        f_ks[51:0] <= s[51:0];
        f_ks[52] <= (s[63:60] < 4'd11) && !(cyc % 512 > 400);
        s = xs(s); pci[63:0] <= s; pci[0] <= s[2:0] == 3'd0;
        s = xs(s); pci[127:64] <= s; s = xs(s); pci[191:128] <= s; s = xs(s); pci[255:192] <= s; pci[263:256] <= s[7:0];
        for (k = 0; k < 18; k = k + 1) begin s = xs(s); hx_res[64*k +: 64] <= s; end
        s = xs(s); vi_s[63:0] <= s; vi_s[0] <= (s[5:0] == 6'd0); s = xs(s); vi_s[127:64] <= s; s = xs(s); vi_s[191:128] <= s;
        s = xs(s); vi_s[255:192] <= s; vi_s[275:256] <= s[19:0];
        s = xs(s); vi_n[63:0] <= s; vi_n[0] <= (s[5:0] == 6'd1); s = xs(s); vi_n[127:64] <= s; s = xs(s); vi_n[191:128] <= s;
        s = xs(s); vi_n[255:192] <= s; vi_n[275:256] <= s[19:0];
        if (dut.u_xq.tx) begin n_tx <= n_tx + 1; if (vo_n[275:1] != 0) n_txnz <= n_txnz + 1; if (dut.u_xq.fc[1:0] == 2'd1) n_s1 <= n_s1 + 1; end
        else if (rst_n && vo_n[275:1] != 0) n_pass <= n_pass + 1;
        if ({rco, vo_s, vo_n, st, hx_w} !== {rco_r, vo_s_r, vo_n_r, st_r, hx_w_r}) begin
            if (mis < 5) $display("MISMATCH cyc=%0d rco %0d vo_s %0d vo_n %0d st %b/%b hx_w %0d", cyc, rco != rco_r, vo_s != vo_s_r,
                                  vo_n != vo_n_r, st, st_r, hx_w != hx_w_r);
            mis <= mis + 1;
        end
        // internal: the decoded grid input x (u_aq.s0_x D) and the wait-line output xd, every cycle
        if ({dut.u_xq.x, dut.u_xq.xd} !== {ref0.u_xq.x, ref0.u_xq.xd}) begin
            if (imis < 5) $display("MISMATCH_INTERNAL cyc=%0d x %0d xd %0d", cyc, dut.u_xq.x != ref0.u_xq.x, dut.u_xq.xd != ref0.u_xq.xd);
            imis <= imis + 1;
        end
        if (dut.u_xq.xd != 0) nxd <= nxd + 1;
        if (cyc == ncyc) begin
            $display("ENG3_INTERNAL x_xd_mismatches=%0d xd_nonzero_cycles=%0d", imis, nxd);
            $display("ENG3_CORE_MITER %s seed=%0d cycles=%0d mismatches=%0d resets=%0d tx_cycles=%0d tx_nonzero_vo_n=%0d frag1_cycles=%0d pass_nonzero=%0d st=%b",
                     (mis == 0 && imis == 0 && n_tx > 200 && n_txnz > 100 && n_s1 > 50 && n_pass > 100) ? "PASS" : "FAIL", seed, ncyc, mis, n_rst + 1,
                     n_tx, n_txnz, n_s1, n_pass, st);
            $finish;
        end
    end
endmodule
