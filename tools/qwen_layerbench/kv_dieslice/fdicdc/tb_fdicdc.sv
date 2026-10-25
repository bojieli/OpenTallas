`timescale 1ns/1ps
// TOK-QK/C 10-24: unit bench of the KV host-SerDes FDI clock crossing (rtl/physical/ot_fdi_phy_cdc.sv x2 halves +
// ot_fdi_join2 + ot_fdi_tx_pace), both directions, two unrelated clocks, randomised phase / traffic / lane skew.
//   RX  phy-domain source (1043-b flits, random density, sequence-numbered) -> per-half PHY lane skew (0..3 phy cycles)
//       -> ot_fdi_phy_cdc (W 522 / E 521) -> core lanes (+LW / +LE core cycles) -> ot_fdi_join2 (core) -> checker
//   TX  core-domain adapter model (offers a flit in every paced slot with prob TXDENS) -> core lanes (+TW / +TE) ->
//       ot_fdi_phy_cdc TX -> PHY pins -> board-side ot_fdi_join2 (clk_phy) -> checker
// PASS = every flit received exactly once, in order, bit-exact, in both directions, no FIFO loss.  Latency report: RX PHY
// pin (p_rx_v phy edge) -> c_rx_v (core edge) in core cycles; TX c_tx_v -> p_tx_v in phy cycles (per half).
// Plusargs: +TC_PS (core period, 833.334) +TP_PS (phy period, 1043) +PHASE_PS (phy start offset) +SEED +N (flits/dir)
//   +RXDENS +TXDENS (percent) +LW +LE +TW +TE (core lane depths) +MUT_C1 (W lane valid +4 cycles vs its data = the C1 bug)
// Mutant (ii) = compile mut_direct.sv instead of rtl/physical/ot_fdi_phy_cdc.sv (direct wiring, the old crossing).
module tb_fdicdc;
    real tc = 0.833334, tp = 1.043, ph = 0.0;
    integer seed = 1, N = 4000, rxd = 70, txd = 90, LW = 28, LE = 34, TW = 28, TE = 34, mut_c1 = 0;
    reg clk = 0, clk_phy = 0, link_rst_n = 0;
    initial begin
        integer x;
        if ($value$plusargs("TC_PS=%d", x)) tc = x / 1000.0;
        if ($value$plusargs("TP_PS=%d", x)) tp = x / 1000.0;
        if ($value$plusargs("PHASE_PS=%d", x)) ph = x / 1000.0;
        void'($value$plusargs("SEED=%d", seed)); void'($value$plusargs("N=%d", N));
        void'($value$plusargs("RXDENS=%d", rxd)); void'($value$plusargs("TXDENS=%d", txd));
        void'($value$plusargs("LW=%d", LW)); void'($value$plusargs("LE=%d", LE));
        void'($value$plusargs("TW=%d", TW)); void'($value$plusargs("TE=%d", TE));
        if ($test$plusargs("MUT_C1")) mut_c1 = 1;
        x = $urandom(seed);
        $display("FDICDC cfg tc %0.4f ns tp %0.4f ns ratio %0.5f phase %0.3f seed %0d N %0d rxdens %0d txdens %0d lanes rx W%0d E%0d tx W%0d E%0d mut_c1 %0d",
                 tc, tp, tc / tp, ph, seed, N, rxd, txd, LW, LE, TW, TE, mut_c1);
    end
    initial begin #0.001; forever #(tc / 2) clk = ~clk; end
    initial begin #(ph + 0.001); forever #(tp / 2) clk_phy = ~clk_phy; end
    integer cyc_c = 0, cyc_p = 0;
    always @(posedge clk) cyc_c <= cyc_c + 1;
    always @(posedge clk_phy) cyc_p <= cyc_p + 1;
    initial begin #50; @(posedge clk); link_rst_n <= 1'b1; end

    // ---------------- RX: PHY -> core ----------------
    function automatic [1042:0] flit_of(input integer k, input integer dir);
        reg [1042:0] f; integer i;
        f = '0;
        for (i = 0; i < 33; i++) f[32*i +: 32] = k * 32'h9E3779B1 + i * 32'h85EBCA77 + dir * 32'hC2B2AE3D;
        f[1042:1040] = 3'(k ^ dir); f[31:0] = k;
        return f;
    endfunction
    integer rx_sent = 0, rx_got = 0, rx_err = 0, tx_sent = 0, tx_got = 0, tx_err = 0;
    reg [1042:0] rxs_d; reg rxs_v = 0;
    wire pr_n_w, pr_n_e;
    always @(posedge clk_phy) begin
        rxs_v <= 1'b0;
        if (pr_n_w && pr_n_e && rx_sent < N && cyc_p > 40 && ($urandom % 100) < rxd) begin
            rxs_v <= 1'b1; rxs_d <= flit_of(rx_sent, 0); rx_sent <= rx_sent + 1;
        end
    end
    // per-half PHY lane skew (phy cycles, fixed per run)
    integer skw = 0, ske = 0;
    initial begin skw = $urandom % 4; ske = $urandom % 4; $display("FDICDC phy lane skew W %0d E %0d", skw, ske); end
    reg [1042:0] sd [0:7]; reg sv [0:7];
    always @(posedge clk_phy) begin sd[0] <= rxs_d; sv[0] <= rxs_v; for (int i = 1; i < 8; i++) begin sd[i] <= sd[i-1]; sv[i] <= sv[i-1]; end end
    wire        prx_vw = sv[skw], prx_ve = sv[ske];
    wire [521:0] prx_dw = sd[skw][521:0];
    wire [520:0] prx_de = sd[ske][1042:522];
    // the two halves
    wire        ctx_v; wire [1042:0] ctx_d;     // core-side TX word (after the core lanes, per half below)
    wire        crx_vw, crx_ve, ptx_vw, ptx_ve, cup_w, cup_e;
    wire [521:0] crx_dw, ptx_dw; wire [520:0] crx_de, ptx_de;
    wire        ctx_vw, ctx_ve; wire [521:0] ctx_dw; wire [520:0] ctx_de;
    ot_fdi_phy_cdc #(.W(522), .DEPTH(8)) u_w (.clk(clk), .link_rst_n(link_rst_n), .c_tx_v(ctx_vw), .c_tx_d(ctx_dw),
        .c_rx_v(crx_vw), .c_rx_d(crx_dw), .c_tx_up(cup_w), .clk_phy(clk_phy), .p_rst_n(pr_n_w), .p_tx_v(ptx_vw), .p_tx_d(ptx_dw),
        .p_rx_v(prx_vw), .p_rx_d(prx_dw), .p_tx_up(1'b1));
    ot_fdi_phy_cdc #(.W(521), .DEPTH(8)) u_e (.clk(clk), .link_rst_n(link_rst_n), .c_tx_v(ctx_ve), .c_tx_d(ctx_de),
        .c_rx_v(crx_ve), .c_rx_d(crx_de), .c_tx_up(cup_e), .clk_phy(clk_phy), .p_rst_n(pr_n_e), .p_tx_v(ptx_ve), .p_tx_d(ptx_de),
        .p_rx_v(prx_ve), .p_rx_d(prx_de), .p_tx_up(1'b1));
    // core lanes (valid in the same word as its data; MUT_C1: the W valid lands 4 cycles after its data)
    reg [522:0] lw [0:63]; reg [521:0] le [0:63];
    always @(posedge clk) begin lw[0] <= {crx_vw, crx_dw}; le[0] <= {crx_ve, crx_de}; for (int i = 1; i < 64; i++) begin lw[i] <= lw[i-1]; le[i] <= le[i-1]; end end
    wire        j_vw = mut_c1 ? lw[LW + 4][522] : lw[LW][522];
    wire [521:0] j_dw = lw[LW][521:0];
    wire        j_ve = le[LE][521];
    wire [520:0] j_de = le[LE][520:0];
    wire        rx_v; wire [1042:0] rx_d;
    ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_join (.clk(clk), .rst_n(link_rst_n), .a_v(j_vw), .a_d(j_dw), .b_v(j_ve), .b_d(j_de),
        .o_v(rx_v), .o_d(rx_d));
    always @(posedge clk) if (rx_v) begin
        if (rx_d !== flit_of(rx_got, 0)) begin
            rx_err = rx_err + 1;
            if (rx_err <= 5) $display("FDICDC RX MISMATCH flit %0d got seq %0d", rx_got, rx_d[31:0]);
        end
        rx_got <= rx_got + 1;
    end
    // RX latency: PHY pin edge of half W -> c_rx_v of half W (FIFO order)
    real t_pin [$]; real lat_sum = 0, lat_min = 1e9, lat_max = 0; integer lat_n = 0;
    always @(posedge clk_phy) if (prx_vw) t_pin.push_back($realtime);
    always @(posedge clk) if (crx_vw && t_pin.size() > 0) begin
        real l; l = ($realtime - t_pin.pop_front()) / tc;
        lat_sum += l; lat_n++; if (l < lat_min) lat_min = l; if (l > lat_max) lat_max = l;
    end

    // ---------------- TX: core -> PHY ----------------
    wire slot;
    ot_fdi_tx_pace #(.NUM(19), .DEN(24)) u_pace (.clk(clk), .rst_n(link_rst_n), .slot(slot));
    reg slot_q = 0; reg [1042:0] txs_d; reg txs_v = 0;
    always @(posedge clk) begin
        slot_q <= slot & cup_w & cup_e;           // adapter: up_q captured at its pin, a flit only in a slot
        txs_v <= 1'b0;
        if (slot_q && tx_sent < N && ($urandom % 100) < txd) begin txs_v <= 1'b1; txs_d <= flit_of(tx_sent, 1); tx_sent <= tx_sent + 1; end
    end
    reg [1043:0] tl [0:63];
    always @(posedge clk) begin tl[0] <= {txs_v, txs_d}; for (int i = 1; i < 64; i++) tl[i] <= tl[i-1]; end
    assign ctx_vw = tl[TW][1043]; assign ctx_dw = tl[TW][521:0];
    assign ctx_ve = tl[TE][1043]; assign ctx_de = tl[TE][1042:522];
    wire tx_v; wire [1042:0] tx_d;
    ot_fdi_join2 #(.WA(522), .WB(521), .DEPTH(16)) u_bjoin (.clk(clk_phy), .rst_n(link_rst_n), .a_v(ptx_vw), .a_d(ptx_dw),
        .b_v(ptx_ve), .b_d(ptx_de), .o_v(tx_v), .o_d(tx_d));
    always @(posedge clk_phy) if (tx_v) begin
        if (tx_d !== flit_of(tx_got, 1)) begin
            tx_err = tx_err + 1;
            if (tx_err <= 5) $display("FDICDC TX MISMATCH flit %0d got seq %0d", tx_got, tx_d[31:0]);
        end
        tx_got <= tx_got + 1;
    end
    real tq [$]; real tl_sum = 0, tl_min = 1e9, tl_max = 0; integer tl_n = 0;
    always @(posedge clk) if (ctx_vw) tq.push_back($realtime);
    always @(posedge clk_phy) if (ptx_vw && tq.size() > 0) begin
        real l; l = ($realtime - tq.pop_front()) / tp;
        tl_sum += l; tl_n++; if (l < tl_min) tl_min = l; if (l > tl_max) tl_max = l;
    end

    // ---------------- verdict ----------------
    initial begin
        integer lost;
        wait (rx_sent == N && tx_sent == N);
        repeat (400) @(posedge clk);
        lost = u_w.n_rx_lost + u_e.n_rx_lost + u_w.n_tx_lost + u_e.n_tx_lost;
        $display("FDICDC RX sent %0d got %0d mism %0d | TX sent %0d got %0d mism %0d | fifo_lost %0d | join max skew rx %0d tx %0d",
                 rx_sent, rx_got, rx_err, tx_sent, tx_got, tx_err, lost, u_join.max_skew, u_bjoin.max_skew);
        $display("FDICDC LAT rx pin->core %0.2f avg [%0.2f..%0.2f] core cycles | tx core->pin %0.2f avg [%0.2f..%0.2f] phy cycles",
                 lat_sum / lat_n, lat_min, lat_max, tl_sum / tl_n, tl_min, tl_max);
        if (rx_got == N && tx_got == N && rx_err == 0 && tx_err == 0 && lost == 0) $display("FDICDC PASS");
        else $display("FDICDC FAIL");
        $finish;
    end
    initial begin #2000000; $display("FDICDC FAIL timeout rx %0d/%0d tx %0d/%0d", rx_got, rx_sent, tx_got, tx_sent); $finish; end
endmodule
