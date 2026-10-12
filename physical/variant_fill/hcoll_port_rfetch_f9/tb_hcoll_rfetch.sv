`timescale 1ns/1ps
// FILL-9 2026-10-10: cycle lockstep of ot_hcoll_port RFETCH=1 (registered SRAM-FIFO fetch) against RFETCH=0, full
// shape (PWT 545, QAW 7, RXAW 8 = 2 rb banks, WSTG 14, K 8), random push / switch-credit / rx / consumer-credit traffic
// with fill, drain and stall phases.  Every output compared every edge; rb beats and tx flits also scoreboarded in order.
// Prints HCOLL_RFETCH PASS; mutant OT_HCOLL_MUT_RFETCH_LATE (fetch decided on stale counters) must print FAIL.
module tb_hcoll_rfetch;
    localparam integer PWT = 545;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg qp_push, qr_push, sw_cr_ret, ph_rx_v, rb_cr;
    reg [PWT-1:0] qp_din, qr_din, ph_rx_flit;
    wire tv0, tv1, rbv0, rbv1, st0, st1, f0, f1;
    wire [PWT-1:0] tf0, tf1, rbd0, rbd1;
    ot_hcoll_port #(.RFETCH(0)) u_ref (.clk(clk), .rst_n(rst_n), .qp_push(qp_push), .qp_din(qp_din), .qr_push(qr_push),
        .qr_din(qr_din), .sw_cr_ret(sw_cr_ret), .ph_tx_v(tv0), .ph_tx_flit(tf0), .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit),
        .rb_v(rbv0), .rb_d(rbd0), .rb_cr(rb_cr), .stall(st0), .fault(f0));
    ot_hcoll_port #(.RFETCH(1)) u_dut (.clk(clk), .rst_n(rst_n), .qp_push(qp_push), .qp_din(qp_din), .qr_push(qr_push),
        .qr_din(qr_din), .sw_cr_ret(sw_cr_ret), .ph_tx_v(tv1), .ph_tx_flit(tf1), .ph_rx_v(ph_rx_v), .ph_rx_flit(ph_rx_flit),
        .rb_v(rbv1), .rb_d(rbd1), .rb_cr(rb_cr), .stall(st1), .fault(f1));
    // idle-sweep-1010: fill a 576-bit word, then truncate.  rnd[544 +: 32] wrote 31 bits past the 545-bit return value:
    // Icarus 11 dropped them silently, Icarus 12 vvp aborts (of_RET_VEC4 assertion), which failed the bench on EPYC4.
    function automatic [PWT-1:0] rnd();
        reg [((PWT + 31) / 32) * 32 - 1:0] w;
        for (integer i = 0; i < PWT; i = i + 32) w[i +: 32] = $urandom;
        rnd = w[PWT-1:0];
    endfunction
    // scoreboards
    reg [PWT-1:0] rxq [0:65535]; integer rx_w = 0, rx_r = 0;
    integer pushed = 0, txed = 0, cred_pend = 0, cons = 0, mism = 0, sb_err = 0, cyc = 0, rb_beats = 0;
    integer phase;
    initial begin
        if (!$value$plusargs("SEED=%d", phase)) phase = 1;
        mism = $urandom(phase); mism = 0;
        {qp_push, qr_push, sw_cr_ret, ph_rx_v, rb_cr} = 0; qp_din = 0; qr_din = 0; ph_rx_flit = 0;
        repeat (5) @(posedge clk); #0.1 rst_n = 1;
        for (cyc = 0; cyc < 24000; cyc = cyc + 1) begin
            @(negedge clk);
            phase = (cyc / 3000) % 4;   // 0 mixed, 1 credit-starved fill, 2 fast drain, 3 consumer-slow
            qp_push = (pushed - txed < 120) && ($urandom % 100 < (phase == 1 ? 45 : 25));
            qr_push = (pushed - txed + qp_push < 120) && ($urandom % 100 < (phase == 1 ? 35 : 20));
            qp_din = rnd(); qr_din = rnd();
            pushed = pushed + qp_push + qr_push;
            sw_cr_ret = 0;
            if (cred_pend > 0 && ($urandom % 100 < (phase == 1 ? 5 : phase == 2 ? 95 : 60))) begin sw_cr_ret = 1; cred_pend = cred_pend - 1; end
            ph_rx_v = (rx_w - rx_r < 200) && ($urandom % 100 < (phase == 3 ? 70 : 40));
            ph_rx_flit = rnd();
            if (ph_rx_v) begin rxq[rx_w % 65536] = ph_rx_flit; rx_w = rx_w + 1; end
            rb_cr = 0;
            if (cons > 0 && ($urandom % 100 < (phase == 3 ? 10 : 70))) begin rb_cr = 1; cons = cons - 1; rx_r = rx_r + 1; end
            @(posedge clk); #0.2;
            if ({tv0, rbv0, st0, f0} !== {tv1, rbv1, st1, f1} || (tv0 && tf0 !== tf1) || (rbv0 && rbd0 !== rbd1)) begin
                mism = mism + 1;
                if (mism <= 5) $display("MISMATCH cyc %0d tv %b/%b rbv %b/%b stall %b/%b fault %b/%b", cyc, tv0, tv1, rbv0, rbv1, st0, st1, f0, f1);
            end
            if (tv0) begin txed = txed + 1; cred_pend = cred_pend + 1; end
            if (rbv1) begin
                if (rbd1 !== rxq[(rx_r + cons) % 65536]) sb_err = sb_err + 1;
                cons = cons + 1; rb_beats = rb_beats + 1;
            end
        end
        $display("HCOLL_RFETCH cycles=%0d pushed=%0d tx=%0d rb_beats=%0d mism=%0d sb_err=%0d fault=%b/%b", cyc, pushed, txed,
                 rb_beats, mism, sb_err, f0, f1);
        if (mism == 0 && sb_err == 0 && !f0 && !f1 && txed > 4000 && rb_beats > 4000) $display("HCOLL_RFETCH PASS");
        else $display("FAIL HCOLL_RFETCH");
        $finish;
    end
endmodule
