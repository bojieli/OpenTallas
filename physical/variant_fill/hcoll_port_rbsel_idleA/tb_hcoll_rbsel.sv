`timescale 1ns/1ps
// idleA-hcoll 2026-10-10: ot_hcoll_port RBSEL=1 (registered rb bank select, +1 edge, K = 9) against the RFETCH line
// (RFETCH=1, RBSEL=0, K = 8), full shape (PWT 545, QAW 7, RXAW 8 = 2 rb banks, WSTG 14).  Each port drives a model of the
// core side of ot_hbm_accel_tu_endpoint_psg: rb_v/rb_d -> lv_q/ld_q flop -> land FIFO (ot_ha2_fifo, 16 deep) -> pop ->
// rbcr_q flop -> rb_cr, so the credit loop is the real one.  Checks:
//   TX side cycle lockstep (ph_tx_v / ph_tx_flit / stall) -- RBSEL touches only the RX buffer;
//   RX side every popped word in order against the ph_rx scoreboard, per port; land occupancy never above K (credit
//   safety), no fault / ovf;
//   throughput: a saturating phase (rx every cycle, consumer pops every cycle): RBSEL K=9 >= 99% of a beat a cycle and
//   >= the reference; RBSEL at K=8 is printed as the reason K = 9 (the 9-edge loop).
// Prints HCOLL_RBSEL PASS; mutant OT_HCOLL_MUT_RBSEL (select one edge late) must print FAIL HCOLL_RBSEL.
module tb_hcoll_rbsel;
    localparam integer PWT = 545;
    localparam integer NI = 3;                        // 0 ref (RBSEL 0, K 8), 1 dut (RBSEL 1, K 9), 2 info (RBSEL 1, K 8)
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg qp_push, qr_push, sw_cr_ret, ph_rx_v;
    reg [PWT-1:0] qp_din, qr_din, ph_rx_flit;
    wire [NI-1:0] tv, rbv, st, fl, lempty, lovf;
    wire [PWT-1:0] tf [0:NI-1];
    wire [PWT-1:0] rbd [0:NI-1];
    wire [PWT-1:0] lhead [0:NI-1];
    wire [4:0] lcnt [0:NI-1];
    reg  [NI-1:0] lv_q, rbcr_q, pop;
    reg  [PWT-1:0] ld_q [0:NI-1];
    reg  want;
    for (genvar g = 0; g < NI; g = g + 1) begin : g_i
        localparam integer KK = (g == 1) ? 9 : 8;
        localparam integer RB = (g == 0) ? 0 : 1;
        ot_hcoll_port #(.RFETCH(1), .RBSEL(RB), .K(KK)) u_p (.clk(clk), .rst_n(rst_n), .qp_push(qp_push), .qp_din(qp_din),
            .qr_push(qr_push), .qr_din(qr_din), .sw_cr_ret(sw_cr_ret), .ph_tx_v(tv[g]), .ph_tx_flit(tf[g]),
            .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit), .rb_v(rbv[g]), .rb_d(rbd[g]), .rb_cr(rbcr_q[g]), .stall(st[g]),
            .fault(fl[g]));
        ot_ha2_fifo #(.W(PWT), .AW(4)) u_land (.clk(clk), .rst_n(rst_n), .push(lv_q[g]), .din(ld_q[g]), .pop(pop[g]),
            .empty(lempty[g]), .dout(lhead[g]), .ovf(lovf[g]), .count(lcnt[g]));
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin lv_q[g] <= 1'b0; rbcr_q[g] <= 1'b0; end
            else begin lv_q[g] <= rbv[g]; rbcr_q[g] <= pop[g] & ~lempty[g]; end
        always @(posedge clk) ld_q[g] <= rbd[g];
        always @* pop[g] = want & ~lempty[g];
    end
    function automatic [PWT-1:0] rnd();
        reg [((PWT + 31) / 32) * 32 - 1:0] w;
        for (integer i = 0; i < PWT; i = i + 32) w[i +: 32] = $urandom;
        rnd = w[PWT-1:0];
    endfunction
    reg [PWT-1:0] rxq [0:65535]; integer rx_w = 0;
    integer rx_r [0:NI-1];
    integer sat_beats [0:NI-1];
    integer sb_err [0:NI-1];
    integer occ_err [0:NI-1];
    integer pops [0:NI-1];
    integer pushed = 0, txed = 0, cred_pend = 0, mism = 0, cyc = 0, phase, seed, inflight;
    localparam integer NCYC = 30000;
    localparam integer SAT0 = 24000, SAT1 = 28000;    // saturating window (measured after a 500-cycle ramp)
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        mism = $urandom(seed); mism = 0;
        for (integer g = 0; g < NI; g = g + 1) begin rx_r[g] = 0; sat_beats[g] = 0; sb_err[g] = 0; occ_err[g] = 0; pops[g] = 0; end
        {qp_push, qr_push, sw_cr_ret, ph_rx_v, want} = 0; qp_din = 0; qr_din = 0; ph_rx_flit = 0;
        repeat (5) @(posedge clk); #0.1 rst_n = 1;
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            @(negedge clk);
            phase = (cyc >= SAT0 && cyc < SAT1) ? 4 : (cyc / 3000) % 4;   // 0 mixed, 1 fill, 2 fast drain, 3 slow consumer
            qp_push = (pushed - txed < 120) && ($urandom % 100 < (phase == 1 ? 45 : 25));
            qr_push = (pushed - txed + qp_push < 120) && ($urandom % 100 < (phase == 1 ? 35 : 20));
            qp_din = rnd(); qr_din = rnd();
            pushed = pushed + qp_push + qr_push;
            sw_cr_ret = 0;
            if (cred_pend > 0 && ($urandom % 100 < (phase == 1 ? 5 : phase == 2 ? 95 : 60))) begin sw_cr_ret = 1; cred_pend = cred_pend - 1; end
            // keep the rx stream below what ref / dut can absorb (rb 256 + land 16); inst 2 (K 8 at the 9-edge loop) is
            // information only: it drains at 8/9 and may overflow in the saturating phase (its fault is not checked)
            inflight = rx_w - rx_r[0]; if (rx_w - rx_r[1] > inflight) inflight = rx_w - rx_r[1];
            ph_rx_v = (inflight < 200) && (phase == 4 ? 1'b1 : ($urandom % 100 < (phase == 3 ? 70 : 40)));
            ph_rx_flit = rnd();
            if (ph_rx_v) begin rxq[rx_w % 65536] = ph_rx_flit; rx_w = rx_w + 1; end
            want = (phase == 4 || phase == 2) ? 1'b1 : ($urandom % 100 < (phase == 3 ? 10 : 70));
            #0.1;
            for (integer g = 0; g < NI; g = g + 1)
                if (pop[g]) begin
                    if (lhead[g] !== rxq[rx_r[g] % 65536]) begin
                        sb_err[g] = sb_err[g] + 1;
                        if (sb_err[g] <= 3) $display("SB_ERR inst %0d cyc %0d word %0d", g, cyc, rx_r[g]);
                    end
                    rx_r[g] = rx_r[g] + 1; pops[g] = pops[g] + 1;
                    if (phase == 4 && cyc >= SAT0 + 500) sat_beats[g] = sat_beats[g] + 1;
                end
            @(posedge clk); #0.2;
            if (tv[0] !== tv[1] || st[0] !== st[1] || (tv[0] && tf[0] !== tf[1])) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH TX cyc %0d tv %b/%b stall %b/%b", cyc, tv[0], tv[1], st[0], st[1]);
            end
            if (tv[0]) begin txed = txed + 1; cred_pend = cred_pend + 1; end
            for (integer g = 0; g < 2; g = g + 1) if (lcnt[g] > ((g == 1) ? 9 : 8)) occ_err[g] = occ_err[g] + 1;
        end
        $display("HCOLL_RBSEL cycles=%0d pushed=%0d tx=%0d mism=%0d", cyc, pushed, txed, mism);
        for (integer g = 0; g < NI; g = g + 1)
            $display("HCOLL_RBSEL inst=%0d rb_pops=%0d sb_err=%0d occ_err=%0d fault=%b land_ovf=%b sat_rate=%0d/%0d", g, pops[g],
                     sb_err[g], occ_err[g], fl[g], lovf[g], sat_beats[g], SAT1 - SAT0 - 500);
        if (mism == 0 && sb_err[0] == 0 && sb_err[1] == 0 && occ_err[0] == 0 && occ_err[1] == 0 && !fl[0] && !fl[1] &&
            !lovf[0] && !lovf[1] && txed > 4000 && pops[1] > 8000 && pops[1] >= pops[0] - 16 &&
            sat_beats[1] * 100 >= (SAT1 - SAT0 - 500) * 99 && sat_beats[1] >= sat_beats[0] - 2)
            $display("HCOLL_RBSEL PASS");
        else $display("FAIL HCOLL_RBSEL");
        $finish;
    end
endmodule
