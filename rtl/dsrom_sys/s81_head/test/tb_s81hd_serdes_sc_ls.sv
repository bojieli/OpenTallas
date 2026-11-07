`timescale 1ns/1ps
// DH81-SEQ 2026-11-07: warm-reset sequencer (OWNER 11-02 17:55) on the hd_serdes SC form. Compile with -DOT_S81HD_SERDES_SC.
//  dut  = ot_s81hd_serdes_link_ls LOCKSAFE=1 -> ot_s81hd_pdie_sc (hard children u_tx, u_bm0..2, u_chn)
//  refr = a separate ot_pdie_pma_reset_hold #(64) on the true lock -> ot_s81hd_pdie_q (RXQ), the released cycle reference
//  b    = peer link on a plesiochronous clock; its clock, gated by run_q, is the recovered clock of dut and refr
// Epochs: E0 cold (lock late), E1 lock loss rck running, E2 lock loss rck stopped, E3 rst_n pulse rck stopped, E4 short rst_n
// pulse rck running.  Checked: while held, core_rst_n, u_chn.rst_n, rs_r, rs_t, rm_l, u_tx.rst all low; after release, at
// recovered edge n: core_rst_n rises exactly at 66, u_chn.rst_n exactly at 68; rs_t[1], all 17 rm_l and u_tx.rst high by edge 72.
// Every ck edge: dut {st, rx} == refr {st, rx}.  In traffic: pma_tx == refr pma_tx delayed 2 ck edges (SC pin cycles).
// Non-vacuous: each epoch decodes >= MINB peer beats and goes live; the peer decodes the dut stream.
module tb_s81hd_serdes_sc_ls;
    parameter integer HOLD = 64, IGNORE_LOCK = 0, RUN = 3000, MINB = 1000;
    parameter real PH = 0.0;              // start offset of the peer clock, ns
    reg ca = 0, cb = 0, rst = 0, rstb = 0, lock = 0, run = 0, run_q = 0;
    always #0.41667 ca = ~ca;
    initial begin #(PH); forever #0.41679 cb = ~cb; end
    always @(negedge cb) run_q <= run;
    wire pck = cb & run_q;
    function automatic [511:0] pat(input [31:0] n);
        pat = {16{n << 2}};
    endfunction
    function automatic ispat(input [511:0] w);
        ispat = w == {16{w[511:480]}} && w[1:0] == 2'b00 && w[511:480] != 0;
    endfunction
    reg  [511:0] txa = 512'd2, txb = 512'd2;
    wire [513:0] d_o, b_o; wire [511:0] r_rx; wire [1:0] r_st;
    wire [543:0] d_pa, r_pa, pb; wire d_ta, r_ta, tb_;
    reg  [543:0] e_ba = 0;
    always @(posedge cb) e_ba <= ($urandom % 2) ? (544'd1 << ($urandom % 544)) : 544'd0;
    ot_s81hd_serdes_link_ls #(.LOCKSAFE(1), .HOLD_EDGES(HOLD)) dut (.ck(ca), .rst_n(rst),
        .pma_lock(IGNORE_LOCK != 0 ? 1'b1 : lock), .coll_i0(txa), .coll_o0(d_o), .pma_tx(d_pa), .pma_tck(d_ta),
        .pma_rx(pb ^ e_ba), .pma_rck(pck));
    wire r_core, r_rdy;
    ot_pdie_pma_reset_hold #(.HOLD_EDGES(64)) h_ref (.rst_n(rst), .pma_lock(lock), .pma_rck(pck), .core_rst_n(r_core), .hold_ready(r_rdy));
    ot_s81hd_pdie_q refr (.clk(ca), .rst(r_core), .tx(txa), .rx(r_rx), .st(r_st), .pma_tx(r_pa), .pma_tck(r_ta),
        .pma_rx(pb ^ e_ba), .pma_rck(pck));
    ot_s81hd_serdes_link b (.ck(cb), .rst_n(rstb), .coll_i0(txb), .coll_o0(b_o), .pma_tx(pb), .pma_tck(tb_), .pma_rx(d_pa), .pma_rck(d_ta));
    wire core = dut.core_rst_n;
    wire chn  = dut.u_link.u_dec.u_chn.rst_n;
    wire rsr  = dut.u_link.rs_r[1] | dut.u_link.rs_r[0];
    wire rstt = dut.u_link.rs_t[1];
    wire [16:0] rml = dut.u_link.rm_l;
    wire txr  = dut.u_link.u_tx.rst;
    integer n, ep = -1, mrx = 0, mtx = 0, first = -1, na = 0, nb = 0, got = 0, gotb = 0, minep = 1 << 30, checks = 0;
    reg tx_chk = 0;
    reg [543:0] r_pa1 = 0, r_pa2 = 0;
    always @(posedge ca) begin r_pa1 <= r_pa; r_pa2 <= r_pa1; end
    task automatic fail(input string s);
        begin $display("SERDES_SC_LS FAIL ep=%0d %s", ep, s); $finish; end
    endtask
    always @(negedge ca) begin
        na = na + 1;
        txa <= (ep < 0 || na % 256 == 0) ? 512'd2 : pat(32'(na));
        if (d_o[511:0] !== r_rx || d_o[513:512] !== r_st) begin mrx = mrx + 1; if (first < 0) first = na; end
        if (tx_chk && d_pa !== r_pa2) begin mtx = mtx + 1; if (first < 0) first = na; end
        if (ispat(d_o[511:0])) got = got + 1;
        checks = checks + 1;
    end
    always @(negedge cb) begin
        nb = nb + 1;
        txb <= (nb % 256 == 0 || nb < 40) ? 512'd2 : pat(32'(nb) * 3);
        if (ispat(b_o[511:0])) gotb = gotb + 1;
    end
    task automatic held(input string where);
        begin
            #0.02;
            if (core !== 1'b0) fail({where, " core_rst_n not held"});
            if (chn !== 1'b0) fail({where, " u_chn.rst_n not held"});
            if (rsr !== 1'b0) fail({where, " rs_r not held"});
            if (rstt !== 1'b0) fail({where, " rs_t not held"});
            if (rml !== 17'd0) fail({where, " rm_l not held"});
            if (txr !== 1'b0) fail({where, " u_tx.rst not held"});
        end
    endtask
    task automatic release_check;
        begin
            for (n = 1; n <= 72; n = n + 1) begin
                @(posedge pck); #0.02;
                if (n < 66 && core !== 1'b0) fail($sformatf("core_rst_n early at recovered edge %0d", n));
                if (n >= 66 && core !== 1'b1) fail($sformatf("core_rst_n late at recovered edge %0d", n));
                if (n < 68 && chn !== 1'b0) fail($sformatf("u_chn.rst_n early at recovered edge %0d", n));
                if (n >= 68 && chn !== 1'b1) fail($sformatf("u_chn.rst_n late at recovered edge %0d", n));
                if (n < 66 && (rml !== 17'd0 || txr !== 1'b0 || rstt !== 1'b0)) fail($sformatf("ck side early at recovered edge %0d", n));
            end
            if (rml !== {17{1'b1}} || rstt !== 1'b1 || txr !== 1'b1) fail("ck side not released by recovered edge 72");
            $display("SC_LS_RELEASE ep=%0d guard_rck_edge=66 chn_rck_edge=68", ep);
        end
    endtask
    task automatic traffic;
        begin
            got = 0;
            repeat (200) @(posedge ca);
            tx_chk = 1;
            repeat (RUN) @(posedge ca);
            tx_chk = 0;
            $display("SC_LS_EPOCH ep=%0d beats=%0d live=%b", ep, got, d_o[513]);
            if (got < MINB) fail($sformatf("vacuous: %0d beats", got));
            if (d_o[513] !== 1'b1) fail("link not live");
            if (got < minep) minep = got;
        end
    endtask
    initial begin
        repeat (8) @(posedge cb); rstb = 1;
        repeat (8) @(posedge ca);
        ep = 0;                                          // E0 cold: lock late, rst_n early
        held("E0 power-up"); rst = 1; repeat (8) @(posedge ca); held("E0 rst_n up, rck stopped, no lock");
        run = 1; repeat (20) @(posedge pck); held("E0 rck running, no lock");
        @(negedge pck); lock = 1; release_check(); traffic();
        ep = 1;                                          // E1 lock loss, rck running
        @(negedge pck); lock = 0; held("E1 assert"); repeat (10) @(posedge pck); held("E1 lock low");
        @(negedge pck); lock = 1; release_check(); traffic();
        ep = 2;                                          // E2 lock loss, rck stopped (restart sees lock high first)
        run = 0; repeat (8) @(posedge ca); lock = 0; held("E2 assert"); repeat (8) @(posedge ca); lock = 1;
        repeat (8) @(posedge ca); held("E2 stopped, lock up");
        run = 1; release_check(); traffic();
        ep = 3;                                          // E3 rst_n pulse, rck stopped
        run = 0; repeat (8) @(posedge ca); rst = 0; held("E3 assert"); repeat (8) @(posedge ca); rst = 1;
        repeat (8) @(posedge ca); held("E3 stopped, rst_n up");
        run = 1; release_check(); traffic();
        ep = 4;                                          // E4 short rst_n pulse, rck running
        @(negedge pck); rst = 0; held("E4 assert"); @(negedge pck); rst = 1; release_check(); traffic();
        if (mrx + mtx != 0) $display("SERDES_SC_LS FAIL lockstep rx=%0d tx=%0d first=%0d", mrx, mtx, first);
        else if (gotb < MINB) $display("SERDES_SC_LS FAIL vacuous peer decoded %0d", gotb);
        else $display("SERDES_SC_LS PASS 5 epochs guard 66 chn 68, %0d ck edges rx/st exact vs RXQ on the same sequencer, pma_tx +2, min beats/epoch %0d, peer beats %0d", checks, minep, gotb);
        $finish;
    end
endmodule
