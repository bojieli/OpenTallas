`timescale 1ns/1ps
// tb_rxbm3_spcyc (CORES-HBM-1 rxbm3 11-12; gate: run_rxbm3_spcyc_gate.sh): lock-step trace bench of the HBM RX bm3_rest core composition
//   pma_rx <- ot_s81_kp4_enc + random symbol errors (tb_s81_kp4 channel: n = 0..15 per frame, every 8th frame 16..22)
//   ot_pdie_serdes_rx_bm3_rest (face shell, SEAM 7) + 3 x ot_pdie_serdes_rx_bm_native + ot_s81_kp4_dchn
//   (k_* -> KD-edge die seam -> dchn -> cw/apply/o_unc/o_ne/fs).
// Writes one line per cycle: cyc rx st.  Run once per define set; compare_traces.py checks the form against the base
// at a fixed cycle offset, and that the base decodes the sent beats.
module tb_rxbm3_spcyc;
    parameter integer NF = 120, KD = 3;
    reg clk = 0, rst_n = 0;
    always #0.41667 clk = ~clk;
    reg tx_v = 0; reg [511:0] tx_d = 0;
    wire p_v; wire [543:0] p_d; wire efault;
    ot_s81_kp4_enc u_e (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(p_v), .p_d(p_d), .fault(efault));
    reg [543:0] ch_d = 0;
    // ---- DUT
    wire [511:0] rx; wire [1:0] st; wire [3:0] k_v; wire [309:0] k_lo; wire [4:0] k_L; wire k_any;
    wire [543:0] cw; wire [7:0] apply; wire o_unc; wire [4:0] o_ne; wire fs; wire [31:0] n_corr, n_unc;
    wire [299:0] bm_S; wire [11:0] bm_ld, bm_done; wire bm_rs_n; wire [479:0] bm_lam; wire [449:0] bm_om;
    wire [14:0] bm_L; wire [2:0] bm_any;
    tb_rxbm3_rest_fshell_seam7 u_rest (.clk(clk), .rck_clk(clk), .rst(rst_n), .rx(rx), .st(st), .pma_rx(ch_d), .e_flt_i(1'b0),
        .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .cw_q(cw), .apply(apply), .o_unc(o_unc), .fs(fs),
        .bm_S(bm_S), .bm_ld(bm_ld), .bm_rs_n(bm_rs_n), .bm_lam(bm_lam), .bm_om(bm_om), .bm_L(bm_L), .bm_any(bm_any), .bm_done(bm_done));
    genvar ge;
    generate for (ge = 0; ge < 3; ge = ge + 1) begin : g_bm
        ot_pdie_serdes_rx_bm_native #(.BMTHC(1)) u_bm (.clk(clk), .rs_n(bm_rs_n), .ld(bm_ld[4*ge+:4]), .S(bm_S),
            .lam(bm_lam[160*ge+:160]), .om(bm_om[150*ge+:150]), .L(bm_L[5*ge+:5]), .any(bm_any[ge]), .done(bm_done[4*ge+:4]));
    end endgenerate
    // die seam on k_* (KD edges), then the Chien / Forney core
    reg [319:0] kd [0:7];
    integer s;
    always @(posedge clk) begin kd[0] <= {k_v, k_lo, k_L, k_any}; for (s = 1; s < 8; s = s + 1) kd[s] <= kd[s-1]; end
    wire [319:0] kk = (KD == 0) ? {k_v, k_lo, k_L, k_any} : kd[KD-1];
    ot_s81_kp4_dchn u_chn (.clk(clk), .rst_n(rst_n), .k_v(kk[319:316]), .k_lo(kk[315:6]), .k_L(kk[5:1]), .k_any(kk[0]),
        .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(n_corr), .n_unc(n_unc));
    // ---- stimulus (tb_s81_kp4 form, fixed seed via $urandom(seed) at start)
    integer nerr_of [0:NF+64];
    integer f, b, nb = 0, fsent;
    integer seed0;
    initial begin
        seed0 = $urandom(20261112);
        fsent = $fopen("sent.txt", "w");
        for (f = 0; f <= NF + 64; f = f + 1) nerr_of[f] = (f % 8 == 7) ? 16 + (f / 8) % 7 : f % 16;
        repeat (80) @(posedge clk); rst_n = 1;
        repeat (3) @(posedge clk);
        for (f = 0; f < NF + 8; f = f + 1)
            for (b = 0; b < 10; b = b + 1) begin
                @(negedge clk);
                tx_v = 1;
                tx_d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                        $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                $fdisplay(fsent, "%0d %0d %h", f, nerr_of[f], tx_d);
            end
        $fclose(fsent);
        forever begin @(negedge clk); tx_d = 0; end
    end
    integer cw_i = 0, wi = 0;
    reg [5439:0] emask;
    task automatic draw(input integer n);
        integer m, p, used [0:543];
        reg [9:0] ev;
        begin
            emask = 0;
            for (m = 0; m < 544; m = m + 1) used[m] = 0;
            m = 0;
            while (m < n) begin
                p = $urandom % 544;
                if (!used[p]) begin used[p] = 1; ev = 10'($urandom % 1023 + 1); emask[5439 - 10 * p -: 10] = ev; m = m + 1; end
            end
        end
    endtask
    always @(negedge clk) begin
        if (p_v) begin
            if (wi % 10 == 0) draw(nerr_of[cw_i]);
            ch_d <= p_d ^ emask[5439 - 544 * (wi % 10) -: 544];
            if (wi % 10 == 9) cw_i = cw_i + 1;
            wi = wi + 1;
        end else ch_d <= 544'd0;
    end
    integer cyc = 0, ftr;
    initial ftr = $fopen("trace.txt", "w");
    always @(posedge clk) begin
        cyc = cyc + 1;
        $fdisplay(ftr, "%0d %h %b", cyc, rx, st);
        if (cyc > (NF + 8) * 10 + 400) begin
            $display("TB_RXBM3_SPCYC done cyc=%0d n_corr=%0d n_unc=%0d efault=%0d", cyc, n_corr, n_unc, efault);
            $fclose(ftr);
            $finish;
        end
    end
endmodule
