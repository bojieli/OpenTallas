`timescale 1ns/1ps
// tb_hfd_ep_static_vc2 (HBM-BIND 2026-10-24): the in-band host link.  Two B2 N0 endpoints (hfd_ep_static_vc2), each
// with its host face (hfd_ep_host_vc), back to back over two REAL ot_pdie_serdes macros (KP4 FEC + rate matcher), die
// B 300 ppm slow, random pad bit errors inside the FEC's t (as tb_hfd_ep_static).  Per side and direction:
//   VC 0 (COLL): the compiler calendar -- frames only on take slots (computed two gearbox states ahead: q pin flop, then
//     the merge register), ~7/8 of slots, blocks of W with GAP beats; the receiver arms / drains blocks on fixed slots.
//   VC 1 (host): frames at random times (no calendar), spacing >= HGAP = 16 edges (the host request / response
//     rate); the receiver arms blocks of WH frames and drains them.
// Every drained frame is compared bit-exact, in order, with the peer's generator per VC; host frames must reach the far
// host face > 8 edges apart (the ot_hbm_host_cp_rxs one-frame pingpong recycle).  PASS: NBLK*W COLL frames and
// NHBLK*WH host frames each way exact, no endpoint or host-face fault, phy_up, SerDes live.
module tb_ep_vc_side #(parameter integer SIDE = 0, parameter integer MUT = 0, parameter integer NBLK = 12,
                       parameter integer W = 64, parameter integer GAP = 24, parameter integer IDLE_K = 204,
                       parameter integer NHBLK = 6, parameter integer WH = 8, parameter integer HGAP = 16) (
    input  wire clk, input wire rst_n,
    output wire [511:0] sd_tx, input wire [511:0] sd_rx, input wire [1:0] sd_st,
    output reg done_tx, output reg done_rx, output reg done_hrx, output integer got, output integer bad,
    output integer sent, output integer hgot, output integer hbad, output integer hsent, output integer hspc,
    output wire ep_fault, output wire [10:0] ep_cause, output wire ep_up, output wire h_fault, output wire [10:0] h_cause
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
    reg htx_v = 0; reg [611:0] htx_f = 0;
    reg harm_v = 0, harm_b = 0, hrel_v = 0, hrel_b = 0, hslot_v = 0, hslot_b = 0; reg [6:0] hwords = 0; reg [5:0] hslot_i = 0;
    wire hrx_v; wire [611:0] hrx_f; wire [1:0] hbready; wire h_up;
    wire vtx_v, vrx_v, vup; wire [611:0] vtx_f, vrx_f; wire [2:0] vcause;
    hfd_ep_static_vc2 #(.IDLE_K(IDLE_K), .MUT(MUT)) u_ep (.clk(clk), .rst_n(rst_n),
        .tx_v(tx_v), .tx_frame(tx_f), .rx_arm_v(arm_v), .rx_arm_bank(arm_b), .rx_block_words(words),
        .rx_release_v(rel_v), .rx_release_bank(rel_b), .rx_slot_v(slot_v), .rx_slot_bank(slot_b),
        .rx_slot_index(slot_i), .rx_pin_v(rx_v), .rx_pin_flit(rx_f), .rx_block_ready(bready),
        .phy_up(ep_up), .fault(ep_fault), .fault_cause(ep_cause),
        .h_tx_v(vtx_v), .h_tx_frame(vtx_f), .h_rx_v(vrx_v), .h_rx_frame(vrx_f), .h_up(vup), .h_cause(vcause),
        .sd_tx(sd_tx), .sd_rx(sd_rx), .sd_st(sd_st));
    hfd_ep_host_vc #(.MUT(MUT)) u_hep (.clk(clk), .rst_n(rst_n),
        .tx_v(htx_v), .tx_frame(htx_f), .rx_arm_v(harm_v), .rx_arm_bank(harm_b), .rx_block_words(hwords),
        .rx_release_v(hrel_v), .rx_release_bank(hrel_b), .rx_slot_v(hslot_v), .rx_slot_bank(hslot_b),
        .rx_slot_index(hslot_i), .rx_pin_v(hrx_v), .rx_pin_flit(hrx_f), .rx_block_ready(hbready),
        .phy_up(h_up), .fault(h_fault), .fault_cause(h_cause),
        .vc_tx_v(vtx_v), .vc_tx_frame(vtx_f), .vc_rx_v(vrx_v), .vc_rx_frame(vrx_f), .vc_up(vup), .vc_cause(vcause));
    // ---- COLL sender: at this negedge the gearbox holds s0; posedge 1 loads the q pin flop (gearbox -> s1); posedge 2
    // loads the merge register (gearbox -> s2); the gearbox consumes it on posedge 3 with the take of s2.
    integer inblk = 0, gap = 0, blk = 0, start_wait = 0;
    reg [2:0] p1, p2; reg [12:0] g1, g2; reg slot_ok;
    initial begin sent = 0; done_tx = 0; end
    always @(negedge clk) begin
        tx_v <= 0;
        if (u_ep.u_tx.gc == IDLE_K) begin p1 = u_ep.u_tx.ph; g1 = 0; end
        else begin p1 = (u_ep.u_tx.ph == 4) ? 0 : u_ep.u_tx.ph + 1; g1 = u_ep.u_tx.gc + (u_ep.u_tx.ph == 4); end
        if (g1 == IDLE_K) begin p2 = p1; g2 = 0; end
        else begin p2 = (p1 == 4) ? 0 : p1 + 1; g2 = g1 + (p1 == 4); end
        slot_ok = u_ep.rn_tx && (g2 != IDLE_K) && (p2 != 4);
        if (u_ep.rn_tx && start_wait < 600) start_wait = start_wait + 1;
        else if (u_ep.rn_tx && blk < NBLK) begin
            if (gap > 0) gap = gap - 1;
            else if (slot_ok && ($urandom % 8) != 0) begin
                tx_v <= 1; tx_f <= frame(SIDE, sent); sent = sent + 1; inblk = inblk + 1;
                if (inblk == W) begin inblk = 0; blk = blk + 1; gap = GAP; end
            end
        end else if (blk == NBLK) done_tx = 1;
    end
    // ---- host sender: no calendar, spacing >= HGAP edges
    integer hwait = 0;
    initial hsent = 0;
    always @(negedge clk) begin
        htx_v <= 0;
        if (u_ep.rn_tx && start_wait >= 600 && hsent < NHBLK * WH) begin
            if (hwait > 0) hwait = hwait - 1;
            else if (($urandom % 4) == 0) begin
                htx_v <= 1; htx_f <= frame(SIDE + 2, hsent); hsent = hsent + 1; hwait = HGAP - 1;
            end
        end
    end
    // ---- receivers (both VCs): arm / ready / arm other / release / drain on consecutive fixed slots
    integer exp_k = 0, rblk = 0, hexp_k = 0, hblk = 0;
    initial begin got = 0; bad = 0; done_rx = 0; hgot = 0; hbad = 0; done_hrx = 0; end
    task automatic step; @(negedge clk); arm_v <= 0; rel_v <= 0; slot_v <= 0; endtask
    task automatic hstep; @(negedge clk); harm_v <= 0; hrel_v <= 0; hslot_v <= 0; endtask
    integer s, hs;
    reg cur, hcur;
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
    initial begin
        hcur = 0;
        wait (u_hep.rn_bd); repeat (4) hstep;
        @(negedge clk); harm_v <= 1; harm_b <= 0; hwords <= WH; hstep;
        while (hblk < NHBLK) begin
            while (!hbready[hcur]) hstep;
            if (hblk + 1 < NHBLK) begin @(negedge clk); harm_v <= 1; harm_b <= !hcur; hwords <= WH; hstep; end
            @(negedge clk); hrel_v <= 1; hrel_b <= hcur;
            for (hs = 0; hs < WH; hs = hs + 1) begin @(negedge clk); hrel_v <= 0; hslot_v <= 1; hslot_b <= hcur; hslot_i <= hs; end
            hstep; repeat (8) hstep;
            hcur = !hcur; hblk = hblk + 1;
        end
        repeat (16) hstep;
        done_hrx = 1;
    end
    always @(posedge clk) if (rx_v) begin
        if (rx_f !== frame(1 - SIDE, exp_k)) begin bad = bad + 1; if (bad < 4) $display("SIDE%0d ERR COLL frame %0d", SIDE, exp_k); end
        exp_k = exp_k + 1; got = got + 1;
    end
    // far-end contract of ot_hbm_host_cp_rxs: host frames reach its one-frame pingpong > 8 receiver edges apart
    integer hcyc = 0, hlast = -100;
    initial hspc = 0;
    always @(posedge clk) begin
        hcyc = hcyc + 1;
        if (u_ep.h_rx_v) begin
            if (hcyc - hlast <= 8) begin hspc = hspc + 1; if (hspc < 4) $display("SIDE%0d ERR HOST spacing %0d", SIDE, hcyc - hlast); end
            hlast = hcyc;
        end
    end
    always @(posedge clk) if (hrx_v) begin
        if (hrx_f !== frame(3 - SIDE, hexp_k)) begin hbad = hbad + 1; if (hbad < 4) $display("SIDE%0d ERR HOST frame %0d", SIDE, hexp_k); end
        hexp_k = hexp_k + 1; hgot = hgot + 1;
    end
endmodule

module tb_hfd_ep_static_vc2;
    parameter integer MUT = 0, NBLK = 12, W = 64, GAP = 24, NHBLK = 6, WH = 8, TMO = 600 + NBLK * 220;
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
    wire dta, dra, dha, dtb, drb, dhb, fa, fb, upa, upb, hfa, hfb; wire [10:0] cza, czb, hza, hzb;
    integer ga, gb, xa, xb, na, nb, hga, hgb, hxa, hxb, hna, hnb, hsa, hsb;
    tb_ep_vc_side #(.SIDE(0), .MUT(MUT), .NBLK(NBLK), .W(W), .GAP(GAP), .NHBLK(NHBLK), .WH(WH)) sA (.clk(ca), .rst_n(rst),
        .sd_tx(txa), .sd_rx(rxa), .sd_st(sta), .done_tx(dta), .done_rx(dra), .done_hrx(dha), .got(ga), .bad(xa), .sent(na),
        .hgot(hga), .hbad(hxa), .hsent(hna), .hspc(hsa), .ep_fault(fa), .ep_cause(cza), .ep_up(upa), .h_fault(hfa), .h_cause(hza));
    tb_ep_vc_side #(.SIDE(1), .MUT(MUT), .NBLK(NBLK), .W(W), .GAP(GAP), .NHBLK(NHBLK), .WH(WH)) sB (.clk(cb), .rst_n(rst),
        .sd_tx(txb), .sd_rx(rxb), .sd_st(stb), .done_tx(dtb), .done_rx(drb), .done_hrx(dhb), .got(gb), .bad(xb), .sent(nb),
        .hgot(hgb), .hbad(hxb), .hsent(hnb), .hspc(hsb), .ep_fault(fb), .ep_cause(czb), .ep_up(upb), .h_fault(hfb), .h_cause(hzb));
    integer hqmax = 0;
    always @(posedge ca) if (sA.u_ep.hcnt > hqmax) hqmax = sA.u_ep.hcnt;
    always @(posedge cb) if (sB.u_ep.hcnt > hqmax) hqmax = sB.u_ep.hcnt;
    reg ok;
    initial begin
        repeat (8) @(posedge ca); rst = 1;
        fork
            begin wait (dra && drb && dha && dhb); end
            begin repeat (TMO) @(posedge ca); $display("TB_HFD_EP_STATIC_VC2 TIMEOUT (receivers incomplete)"); end
        join_any
        repeat (20) @(posedge ca);
        ok = (ga == NBLK * W) && (gb == NBLK * W) && xa == 0 && xb == 0 && hga == NHBLK * WH && hgb == NHBLK * WH &&
             hxa == 0 && hxb == 0 && hsa == 0 && hsb == 0 && !fa && !fb && !hfa && !hfb && upa && upb && sta == 2'b10 && stb == 2'b10;
        $display("TB_HFD_EP_STATIC_VC2 MUT=%0d A: coll sent=%0d got=%0d bad=%0d host sent=%0d got=%0d bad=%0d fault=%b/%b cause=%b/%b | B: coll sent=%0d got=%0d bad=%0d host sent=%0d got=%0d bad=%0d fault=%b/%b cause=%b/%b | stA=%b stB=%b hq_max=%0d spacing_viol=%0d/%0d | %s",
                 MUT, na, ga, xa, hna, hga, hxa, fa, hfa, cza, hza, nb, gb, xb, hnb, hgb, hxb, fb, hfb, czb, hzb, sta, stb, hqmax, hsa, hsb,
                 ok ? "PASS" : "FAIL");
        $finish;
    end
endmodule
