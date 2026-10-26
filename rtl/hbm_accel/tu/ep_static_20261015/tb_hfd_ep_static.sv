`timescale 1ns/1ps
// tb_hfd_ep_static (H-LKEP 2026-10-15): two v15 link endpoints back to back over two REAL ot_pdie_serdes link macros
// (KP4 FEC RS(544,514) encoder/decoder + rate matcher over the behavioural PMA), die B's clock 300 ppm slow, one random
// pad bit error in about every second PMA word each way (inside the FEC's t = 15).  Both directions carry traffic.
// Each side's sender is the compiler calendar: frames only on TX slots (beat phase 0..3, never the IDLE beat), blocks of
// W frames separated by GAP beats; each receiver arms a block, waits for block_ready, arms the other bank, releases and
// drains the block on fixed consecutive slots.  Every drained frame is compared bit-exact, in order, with the peer's
// generator (612 b).  PASS: NBLK*W frames each way exact, no endpoint fault, phy_up, SerDes live.
module tb_ep_side #(parameter integer SIDE = 0, parameter integer MUT = 0, parameter integer NBLK = 12,
                    parameter integer W = 64, parameter integer GAP = 24, parameter integer IDLE_K = 204) (
    input  wire clk, input wire rst_n,
    output wire [511:0] sd_tx, input wire [511:0] sd_rx, input wire [1:0] sd_st,
    output reg done_tx, output reg done_rx, output integer got, output integer bad, output integer sent,
    output wire ep_fault, output wire [10:0] ep_cause, output wire ep_up
);
    function automatic [611:0] frame(input integer side, input integer k);
        reg [31:0] x; integer i; reg [639:0] acc;
        begin
            x = 32'h9E3779B9 ^ (side * 32'h85EBCA6B) ^ (k * 32'hC2B2AE35);
            for (i = 0; i < 20; i = i + 1) begin
                x = x ^ (x << 13); x = x ^ (x >> 17); x = x ^ (x << 5); x = x + 32'(i * 7919 + k);
                acc[i*32 +: 32] = x;
            end
            frame = acc[611:0];
        end
    endfunction
    reg tx_v = 0; reg [611:0] tx_f = 0;
    reg arm_v = 0, arm_b = 0, rel_v = 0, rel_b = 0, slot_v = 0, slot_b = 0; reg [6:0] words = 0; reg [5:0] slot_i = 0;
    wire rx_v; wire [611:0] rx_f; wire [1:0] bready;
    hfd_ep_static #(.IDLE_K(IDLE_K), .MUT(MUT)) u_ep (.clk(clk), .rst_n(rst_n),
        .tx_v(tx_v), .tx_frame(tx_f), .rx_arm_v(arm_v), .rx_arm_bank(arm_b), .rx_block_words(words),
        .rx_release_v(rel_v), .rx_release_bank(rel_b), .rx_slot_v(slot_v), .rx_slot_bank(slot_b),
        .rx_slot_index(slot_i), .rx_pin_v(rx_v), .rx_pin_flit(rx_f), .rx_block_ready(bready),
        .phy_up(ep_up), .fault(ep_fault), .fault_cause(ep_cause), .sd_tx(sd_tx), .sd_rx(sd_rx), .sd_st(sd_st));
    // ---- sender: the static calendar.  At this negedge the tx gearbox holds state s0; the posedge ahead loads the pin
    // register and advances the gearbox to s1; the gearbox consumes the pin register on the following posedge in s1.
    integer inblk = 0, gap = 0, blk = 0, start_wait = 0;
    reg [2:0] p1; reg [12:0] g1; reg idle0, slot_ok;
    initial begin sent = 0; done_tx = 0; end
    always @(negedge clk) begin
        tx_v <= 0;
        idle0 = (u_ep.u_tx.gc == IDLE_K);
        if (idle0) begin p1 = u_ep.u_tx.ph; g1 = 0; end
        else begin p1 = (u_ep.u_tx.ph == 4) ? 0 : u_ep.u_tx.ph + 1; g1 = u_ep.u_tx.gc + (u_ep.u_tx.ph == 4); end
        slot_ok = u_ep.rn_tx && (g1 != IDLE_K) && (p1 != 4);
        if (u_ep.rn_tx && start_wait < 600) start_wait = start_wait + 1;      // FEC lock + receiver arming
        else if (u_ep.rn_tx && blk < NBLK) begin
            if (gap > 0) gap = gap - 1;
            else if (slot_ok && ($urandom % 8) != 0) begin
                tx_v <= 1; tx_f <= frame(SIDE, sent); sent = sent + 1; inblk = inblk + 1;
                if (inblk == W) begin inblk = 0; blk = blk + 1; gap = GAP; end
            end
        end else if (blk == NBLK) done_tx = 1;
    end
    // ---- receiver: arm / ready / arm other / release / drain on consecutive fixed slots
    integer exp_k = 0, rblk = 0;
    initial begin got = 0; bad = 0; done_rx = 0; end
    task automatic step; @(negedge clk); arm_v <= 0; rel_v <= 0; slot_v <= 0; endtask
    integer s;
    reg cur;
    initial begin
        cur = 0;
        wait (u_ep.rn_bd); repeat (4) step;
        @(negedge clk); arm_v <= 1; arm_b <= 0; words <= W; step;
        while (rblk < NBLK) begin
            while (!bready[cur]) step;
            if (rblk + 1 < NBLK) begin @(negedge clk); arm_v <= 1; arm_b <= !cur; words <= W; step; end
            @(negedge clk); rel_v <= 1; rel_b <= cur;
            for (s = 0; s < W; s = s + 1) begin @(negedge clk); rel_v <= 0; slot_v <= 1; slot_b <= cur; slot_i <= s; end
            step; repeat (8) step;
            cur = !cur; rblk = rblk + 1;
        end
        repeat (16) step;
        done_rx = 1;
    end
    always @(posedge clk) if (rx_v) begin
        if (rx_f !== frame(1 - SIDE, exp_k)) begin bad = bad + 1; if (bad < 4) $display("SIDE%0d ERR frame %0d", SIDE, exp_k); end
        exp_k = exp_k + 1; got = got + 1;
    end
endmodule

module tb_hfd_ep_static;
    parameter integer MUT = 0, NBLK = 12, W = 64, GAP = 24, TMO = 600 + NBLK * 220;
    reg ca = 0, cb = 0, rst = 0;
    always #0.41667 ca = ~ca;
    always #0.41679 cb = ~cb;
    wire [511:0] txa, txb, rxa, rxb; wire [1:0] sta, stb; wire [543:0] pa, pb; wire tca, tcb; reg [543:0] pa_e, pb_e;
    ot_pdie_serdes u_sa (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb_e), .pma_rck(tcb));
    ot_pdie_serdes u_sb (.clk(cb), .rst(rst), .tx(txb), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa_e), .pma_rck(tca));
    reg ea = 0, eb = 0; integer ba = 0, bb = 0;
    always @(posedge tca) begin ea <= ($urandom % 2) == 0; ba <= $urandom % 544; end
    always @(posedge tcb) begin eb <= ($urandom % 2) == 0; bb <= $urandom % 544; end
    always @* begin pa_e = pa; if (ea) pa_e[ba] = ~pa[ba]; pb_e = pb; if (eb) pb_e[bb] = ~pb[bb]; end
    wire dta, dra, dtb, drb, fa, fb, upa, upb; wire [10:0] cza, czb; integer ga, gb, xa, xb, na, nb;
    tb_ep_side #(.SIDE(0), .MUT(MUT), .NBLK(NBLK), .W(W), .GAP(GAP)) sA (.clk(ca), .rst_n(rst), .sd_tx(txa), .sd_rx(rxa),
        .sd_st(sta), .done_tx(dta), .done_rx(dra), .got(ga), .bad(xa), .sent(na), .ep_fault(fa), .ep_cause(cza), .ep_up(upa));
    tb_ep_side #(.SIDE(1), .MUT(MUT), .NBLK(NBLK), .W(W), .GAP(GAP)) sB (.clk(cb), .rst_n(rst), .sd_tx(txb), .sd_rx(rxb),
        .sd_st(stb), .done_tx(dtb), .done_rx(drb), .got(gb), .bad(xb), .sent(nb), .ep_fault(fb), .ep_cause(czb), .ep_up(upb));
    integer cyc = 0, tx_first = -1, tx_last = 0;
    always @(posedge cb) begin cyc = cyc + 1; if (sB.u_ep.u_rxb.pin_v) ; end
    // measured A->B lane rate: frames delivered to B's RX gearbox per B beat between first and last
    integer fb_first = -1, fb_last = 0, fb_n = 0;
    always @(posedge cb) if (sB.u_ep.u_rx.f_v) begin if (fb_first < 0) fb_first = cyc; fb_last = cyc; fb_n = fb_n + 1; end
    reg ok;
    initial begin
        repeat (8) @(posedge ca); rst = 1;
        fork
            begin wait (dra && drb); end
            begin repeat (TMO) @(posedge ca); $display("TB_HFD_EP_STATIC TIMEOUT (receivers incomplete)"); end
        join_any
        repeat (20) @(posedge ca);
        ok = (ga == NBLK * W) && (gb == NBLK * W) && xa == 0 && xb == 0 && !fa && !fb && upa && upb && sta == 2'b10 && stb == 2'b10;
        $display("TB_HFD_EP_STATIC MUT=%0d A: sent=%0d got=%0d bad=%0d fault=%b cause=%b up=%b | B: sent=%0d got=%0d bad=%0d fault=%b cause=%b up=%b | stA=%b stB=%b | lane A->B %0d frames in %0d beats | %s",
                 MUT, na, ga, xa, fa, cza, upa, nb, gb, xb, fb, czb, upb, sta, stb, fb_n, fb_last - fb_first + 1, ok ? "PASS" : "FAIL");
        $finish;
    end
endmodule
