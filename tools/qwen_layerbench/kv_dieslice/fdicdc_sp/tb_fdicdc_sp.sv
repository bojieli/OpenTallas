`timescale 1ns/1ps
// KV-FDICDC-1 lock-step bench: ot_fdi_phy_cdc (new source) SEL_PIPE 0 / 1 against the 57b15ccf22 source (renamed *_old).
//   N0 (SEL_PIPE 0) : every output equal to OLD at every edge of both clocks (cycle exact).
//   N1 (SEL_PIPE 1) : p_rst_n and c_tx_up cycle exact; TX stream (p side) and RX stream (c side) equal to OLD's and to
//                     the scoreboard (every offered word, in order, none lost); latency delta reported.
module tb_fdicdc_sp;
    parameter integer W = 522;
    parameter integer NWORDS = 3000;
    real TC = 0.833, TP = 1.043;
    integer PTX = 60, PRX = 90;            // percent valid per cycle (writer pacing)
    reg clk = 0, clk_phy = 0;
    reg link_rst_n = 0;
    reg c_tx_v = 0, p_rx_v = 0, p_tx_up = 0;
    reg [W-1:0] c_tx_d = 0, p_rx_d = 0;
    initial begin
        if ($value$plusargs("tc=%f", TC)) ; if ($value$plusargs("tp=%f", TP)) ;
        if ($value$plusargs("ptx=%d", PTX)) ; if ($value$plusargs("prx=%d", PRX)) ;
    end
    initial begin #0.11; forever #(TC/2) clk = ~clk; end
    initial begin #0.37; forever #(TP/2) clk_phy = ~clk_phy; end

    wire o_crv, n0_crv, n1_crv, o_up, n0_up, n1_up, o_prst, n0_prst, n1_prst, o_ptv, n0_ptv, n1_ptv;
    wire [W-1:0] o_crd, n0_crd, n1_crd, o_ptd, n0_ptd, n1_ptd;
    ot_fdi_phy_cdc_old #(.W(W), .DEPTH(8)) u_old (.clk(clk), .link_rst_n(link_rst_n), .c_tx_v(c_tx_v), .c_tx_d(c_tx_d),
        .c_rx_v(o_crv), .c_rx_d(o_crd), .c_tx_up(o_up), .clk_phy(clk_phy), .p_rst_n(o_prst), .p_tx_v(o_ptv),
        .p_tx_d(o_ptd), .p_rx_v(p_rx_v), .p_rx_d(p_rx_d), .p_tx_up(p_tx_up));
    ot_fdi_phy_cdc #(.W(W), .DEPTH(8), .SEL_PIPE(0)) u_n0 (.clk(clk), .link_rst_n(link_rst_n), .c_tx_v(c_tx_v),
        .c_tx_d(c_tx_d), .c_rx_v(n0_crv), .c_rx_d(n0_crd), .c_tx_up(n0_up), .clk_phy(clk_phy), .p_rst_n(n0_prst),
        .p_tx_v(n0_ptv), .p_tx_d(n0_ptd), .p_rx_v(p_rx_v), .p_rx_d(p_rx_d), .p_tx_up(p_tx_up));
    ot_fdi_phy_cdc #(.W(W), .DEPTH(8), .SEL_PIPE(1)) u_n1 (.clk(clk), .link_rst_n(link_rst_n), .c_tx_v(c_tx_v),
        .c_tx_d(c_tx_d), .c_rx_v(n1_crv), .c_rx_d(n1_crd), .c_tx_up(n1_up), .clk_phy(clk_phy), .p_rst_n(n1_prst),
        .p_tx_v(n1_ptv), .p_tx_d(n1_ptd), .p_rx_v(p_rx_v), .p_rx_d(p_rx_d), .p_tx_up(p_tx_up));

    integer err0 = 0, err1 = 0, errsb = 0;
    // ---- N0: cycle exact ----
    always @(posedge clk) #0.01 if ({o_crv, o_crd, o_up} !== {n0_crv, n0_crd, n0_up}) err0 = err0 + 1;
    always @(posedge clk_phy) #0.01 if ({o_prst, o_ptv, o_ptd} !== {n0_prst, n0_ptv, n0_ptd}) err0 = err0 + 1;
    // ---- N1: reset / level paths cycle exact ----
    always @(posedge clk) #0.01 if (o_up !== n1_up) err1 = err1 + 1;
    always @(posedge clk_phy) #0.01 if (o_prst !== n1_prst) err1 = err1 + 1;
    // ---- streams ----
    localparam integer QN = 65536;
    reg [W-1:0] sb_tx [0:QN-1]; reg [W-1:0] sb_rx [0:QN-1];
    reg [W-1:0] o_tx [0:QN-1];  reg [W-1:0] n_tx [0:QN-1];
    reg [W-1:0] o_rx [0:QN-1];  reg [W-1:0] n_rx [0:QN-1];
    real ot_tx [0:QN-1]; real nt_tx [0:QN-1]; real ot_rx [0:QN-1]; real nt_rx [0:QN-1];
    integer nsb_tx = 0, nsb_rx = 0, no_tx = 0, nn_tx = 0, no_rx = 0, nn_rx = 0;
    always @(posedge clk_phy) #0.01 begin
        if (o_ptv === 1'b1) begin o_tx[no_tx] = o_ptd; ot_tx[no_tx] = $realtime; no_tx = no_tx + 1; end
        if (n1_ptv === 1'b1) begin n_tx[nn_tx] = n1_ptd; nt_tx[nn_tx] = $realtime; nn_tx = nn_tx + 1; end
        if (nsb_tx - no_tx > occ_o) occ_o = nsb_tx - no_tx;
        if (nsb_tx - nn_tx > occ_n) occ_n = nsb_tx - nn_tx;
    end
    integer occ_o = 0, occ_n = 0;
    always @(posedge clk) #0.01 begin
        if (o_crv === 1'b1) begin o_rx[no_rx] = o_crd; ot_rx[no_rx] = $realtime; no_rx = no_rx + 1; end
        if (n1_crv === 1'b1) begin n_rx[nn_rx] = n1_crd; nt_rx[nn_rx] = $realtime; nn_rx = nn_rx + 1; end
    end

    reg [W+31:0] rt; integer rk;
    function [W-1:0] rnd; input integer dummy; begin
        for (rk = 0; rk < W; rk = rk + 32) rt[rk +: 32] = $random; rnd = rt[W-1:0]; end endfunction
    reg run_tx = 0, run_rx = 0;
    // PTX < 0: the real adapter pacing, ot_fdi_tx_pace 19/24 (Bresenham), a word in EVERY slot (worst case)
    integer pacc = 0; reg pslot;
    always @(posedge clk) begin
        pslot = 1'b0;
        if (PTX < 0) begin pacc = pacc + 19; if (pacc >= 24) begin pacc = pacc - 24; pslot = 1'b1; end end
        if (run_tx && (PTX < 0 ? pslot : (($urandom % 100) < PTX))) begin
            c_tx_v <= 1'b1; c_tx_d <= rnd(0); #0.001 sb_tx[nsb_tx] = c_tx_d; nsb_tx = nsb_tx + 1;
        end else begin c_tx_v <= 1'b0; c_tx_d <= rnd(0); end      // data toggles while idle (must be ignored)
    end
    always @(posedge clk_phy) begin
        if (run_rx && ($urandom % 100) < PRX) begin
            p_rx_v <= 1'b1; p_rx_d <= rnd(0); #0.001 sb_rx[nsb_rx] = p_rx_d; nsb_rx = nsb_rx + 1;
        end else begin p_rx_v <= 1'b0; p_rx_d <= rnd(0); end
        if (($urandom % 37) == 0) p_tx_up <= ~p_tx_up;
    end

    integer seg, i, k;
    real dmax_tx, dmax_rx, d;
    initial begin
        for (seg = 0; seg < 3; seg = seg + 1) begin
            link_rst_n <= 1'b0; repeat (7) @(posedge clk); link_rst_n <= 1'b1;
            repeat (60) @(posedge clk);               // online rendezvous
            run_tx = 1; run_rx = 1;
            wait ((PTX == 0 || nsb_tx >= (seg + 1) * NWORDS) && (PRX == 0 || nsb_rx >= (seg + 1) * NWORDS));
            @(posedge clk); run_tx = 0; @(posedge clk_phy); run_rx = 0;
            repeat (80) @(posedge clk); repeat (80) @(posedge clk_phy);   // drain before the flush
        end
        #5;
        if (no_tx != nsb_tx || nn_tx != nsb_tx || no_rx != nsb_rx || nn_rx != nsb_rx) errsb = errsb + 1;
        dmax_tx = 0; dmax_rx = 0;
        for (i = 0; i < nsb_tx; i = i + 1) begin
            if (o_tx[i] !== sb_tx[i]) errsb = errsb + 1;
            if (n_tx[i] !== sb_tx[i]) err1 = err1 + 1;
            d = nt_tx[i] - ot_tx[i]; if (d > dmax_tx) dmax_tx = d;
        end
        for (i = 0; i < nsb_rx; i = i + 1) begin
            if (o_rx[i] !== sb_rx[i]) errsb = errsb + 1;
            if (n_rx[i] !== sb_rx[i]) err1 = err1 + 1;
            d = nt_rx[i] - ot_rx[i]; if (d > dmax_rx) dmax_rx = d;
        end
        if (u_old.n_tx_lost || u_old.n_rx_lost || u_n1.n_tx_lost || u_n1.n_rx_lost) errsb = errsb + 1;
        $display("FDICDC_SP W %0d tc %.3f tp %.3f words tx %0d/%0d/%0d rx %0d/%0d/%0d lost old %0d/%0d new %0d/%0d",
                 W, TC, TP, nsb_tx, no_tx, nn_tx, nsb_rx, no_rx, nn_rx, u_old.n_tx_lost, u_old.n_rx_lost,
                 u_n1.n_tx_lost, u_n1.n_rx_lost);
        $display("FDICDC_SP latency delta max tx %.3f ns rx %.3f ns; TX words in flight max old %0d new %0d (DEPTH 8)",
                 dmax_tx, dmax_rx, occ_o, occ_n);
        $display("FDICDC_SP err N0_cycle_exact %0d N1 %0d scoreboard %0d -> %s", err0, err1, errsb,
                 (err0 == 0 && err1 == 0 && errsb == 0) ? "PASS" : "FAIL");
        $finish;
    end
    initial begin #(400000); $display("FDICDC_SP TIMEOUT -> FAIL"); $finish; end
endmodule
