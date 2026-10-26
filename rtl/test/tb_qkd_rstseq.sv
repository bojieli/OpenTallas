`timescale 1ns/1ps
// Qwen ROM TP8 track B 2026-10-13: qkd_rstseq (the die reset sequencer leaf beside the PLL hard macro) through its own
// pins.  (1) Cycle-exact against the benched body ot_qwen_sys_rst_seq (NL 4, ND 4) with the leaf's pin stages (inputs
// + 1, outputs + 1).  (2) Order properties checked on the leaf alone: host reset first, then link, then the four
// quadrant (HBM) resets together only after every link is up, one boot_go pulse per boot on all four copies while the
// die reset is still asserted, die resets (rso_c, rso_fwd) together only after every boot_done with boot_ok, ready
// last; a link time-out, an HBM time-out and a failed HBM check each stop in FAULT with their code and never release
// the die reset; a soft reset re-runs the sequence with the host side up.  Coverage refusal: every scenario must run.
module tb_qkd_rstseq;
    reg ck = 0, por_n = 0, soft_rst = 0;
    reg [3:0] link_up = 0, boot_done = 0, boot_ok = 0;
    always #5 ck = ~ck;
    wire rso_c, rso_fwd, rso_WS, rso_WN, rso_ES, rso_EN, rso_host, rso_link;
    wire [3:0] boot_go;
    wire [41:0] rst_st;
    qkd_rstseq dut (.ck(ck), .por_n(por_n), .soft_rst(soft_rst), .link_up(link_up), .boot_done(boot_done), .boot_ok(boot_ok),
        .rso_c(rso_c), .rso_fwd(rso_fwd), .rso_WS(rso_WS), .rso_WN(rso_WN), .rso_ES(rso_ES), .rso_EN(rso_EN),
        .rso_host(rso_host), .rso_link(rso_link), .boot_go(boot_go), .rst_st(rst_st));
    // reference: the body with the same pin stages
    wire r_host, r_link, r_hbm, r_go, r_die, r_rdy, r_flt;
    wire [3:0] r_state, r_err;  wire [31:0] r_cyc;
    reg sr; reg [3:0] lu, bd, bk;
    always @(posedge ck or negedge r_host) if (!r_host) begin sr <= 0; lu <= 0; bd <= 0; bk <= 0; end
                                           else begin sr <= soft_rst; lu <= link_up; bd <= boot_done; bk <= boot_ok; end
    ot_qwen_sys_rst_seq #(.NL(4), .ND(4)) u_ref (.clk(ck), .por_n(por_n), .soft_rst(sr), .link_up(lu), .boot_done(bd),
        .boot_ok(bk), .host_rst_n(r_host), .link_rst_n(r_link), .hbm_rst_n(r_hbm), .boot_go(r_go), .die_rst_n(r_die),
        .sys_ready(r_rdy), .boot_fault(r_flt), .boot_state(r_state), .boot_err(r_err), .boot_cycles(r_cyc));
    reg [53:0] rq;
    always @(posedge ck or negedge por_n) if (!por_n) rq <= 0;
        else rq <= {r_die, r_die, {4{r_hbm}}, r_host, r_link, {4{r_go}}, r_rdy, r_flt, r_state, r_err, r_cyc};
    wire [53:0] dq = {rso_c, rso_fwd, rso_WS, rso_WN, rso_ES, rso_EN, rso_host, rso_link, boot_go, rst_st};
    integer nmis = 0, ncmp = 0, nprop = 0, cyc = 0;
    always @(negedge ck) begin
        cyc = cyc + 1; ncmp = ncmp + 1;
        if (dq !== rq) begin if (nmis == 0) $display("MISMATCH at cycle %0d dut %h ref %h", cyc, dq, rq); nmis = nmis + 1; end
    end
    // ---- order properties on the leaf's own pins ----
    wire [3:0] rq4 = {rso_EN, rso_ES, rso_WN, rso_WS};
    wire       ready = rst_st[41], bflt = rst_st[40];
    wire [3:0] berr = rst_st[35:32];
    integer n_go = 0, lu_all_cyc = 0, bd_all_cyc = 0;
    task perr(input [255:0] what); begin if (nprop == 0) $display("PROPERTY %0s at cycle %0d", what, cyc); nprop = nprop + 1; end endtask
    always @(negedge ck) begin
        if (rq4 != 4'd0 && rq4 != 4'hF) perr("quadrant resets not together");
        if (boot_go != 4'd0 && boot_go != 4'hF) perr("boot_go copies differ");
        if (rso_c !== rso_fwd) perr("rso_c != rso_fwd");
        if (rso_link && !rso_host) perr("link before host");
        if (rq4 == 4'hF && !rso_link) perr("quadrant reset before link reset");
        if (rq4 == 4'hF && lu_all_cyc == 0) perr("quadrant reset released before every link was up");
        if (boot_go == 4'hF) begin n_go = n_go + 1; if (rq4 != 4'hF) perr("boot_go before the quadrant resets"); if (rso_c) perr("boot_go after the die reset"); end
        if (rso_c && rq4 != 4'hF) perr("die reset released before the quadrant resets");
        if (rso_c && bd_all_cyc == 0) perr("die reset released before boot_done with boot_ok");
        if (ready && !rso_c) perr("ready before the die reset");
        if (bflt && rso_c) perr("fault with the die reset released");
        if (&link_up) begin if (lu_all_cyc == 0) lu_all_cyc = cyc; end
        if (&boot_done && &boot_ok) begin if (bd_all_cyc == 0) bd_all_cyc = cyc; end
    end
    integer n_ok = 0, n_soft = 0, n_e1 = 0, n_e2 = 0, n_e3 = 0, t;
    task por; begin por_n = 0; link_up = 0; boot_done = 0; boot_ok = 0; soft_rst = 0; repeat (3) @(negedge ck); lu_all_cyc = 0; bd_all_cyc = 0; n_go = 0; por_n = 1; end endtask
    task wait_for(input integer what, input integer lim);   // 0 link reset, 1 quadrant resets, 2 boot_go, 3 ready, 4 fault
        begin
            t = 0;
            while (t < lim && !((what == 0 && rso_link) || (what == 1 && rq4 == 4'hF) || (what == 2 && boot_go == 4'hF) ||
                                (what == 3 && ready) || (what == 4 && bflt))) begin @(negedge ck); t = t + 1; end
            if (t >= lim) perr("time-out waiting for an output");
        end
    endtask
    task boot_ok_seq(input integer d1, input integer d2);
        begin
            wait_for(0, 40);
            repeat (d1) @(negedge ck); link_up = 4'b0101; repeat (7) @(negedge ck); link_up = 4'hF;
            wait_for(2, 40);
            if (n_go == 0) perr("no boot_go");
            repeat (d2) @(negedge ck); boot_ok = 4'hF; boot_done = 4'b0011; repeat (5) @(negedge ck); boot_done = 4'hF;
            wait_for(3, 40);
            repeat (20) @(negedge ck);
            if (n_go != 1) perr("boot_go not exactly one pulse");
            if (!(ready && rso_c && rso_fwd && rq4 == 4'hF && rso_host && rso_link && !bflt)) perr("not ready after a good boot");
        end
    endtask
    initial begin
        // 1: good boot
        por; boot_ok_seq(13, 31); n_ok = n_ok + 1;
        // 2: soft reset re-runs LINK..READY, the host side stays up
        @(negedge ck); soft_rst = 1; @(negedge ck); soft_rst = 0; link_up = 0; boot_done = 0; boot_ok = 0;
        repeat (4) @(negedge ck);
        if (!rso_host) perr("host reset dropped by a soft reset");
        if (rso_c || rq4 != 0 || rso_link) perr("soft reset did not re-assert the resets");
        lu_all_cyc = 0; bd_all_cyc = 0; n_go = 0;
        boot_ok_seq(3, 200); n_soft = n_soft + 1;
        // 3: a link never comes up -> FAULT 1
        por; wait_for(0, 40); link_up = 4'b1011; wait_for(4, 20100);
        if (!(bflt && berr == 4'd1 && !rso_c && rq4 == 0)) perr("link time-out not reported as fault 1"); else n_e1 = n_e1 + 1;
        // 4: the HBM check never finishes -> FAULT 2
        por; wait_for(0, 40); link_up = 4'hF; wait_for(2, 40); boot_ok = 4'hF; boot_done = 4'b1110; wait_for(4, 20100);
        if (!(bflt && berr == 4'd2 && !rso_c && rq4 == 4'hF)) perr("HBM time-out not reported as fault 2"); else n_e2 = n_e2 + 1;
        // 5: one quadrant's HBM check fails -> FAULT 3
        por; wait_for(0, 40); link_up = 4'hF; wait_for(2, 40); repeat (50) @(negedge ck); boot_ok = 4'b1101; boot_done = 4'hF;
        wait_for(4, 40);
        if (!(bflt && berr == 4'd3 && !rso_c)) perr("failed HBM check not reported as fault 3"); else n_e3 = n_e3 + 1;
        repeat (30) @(negedge ck);
        if (rso_c || ready) perr("die reset released after a failed HBM check");
        // 6: good boot after a power-on reset again
        por; boot_ok_seq(40, 5); n_ok = n_ok + 1;
        $display("COUNTS cycles=%0d compared=%0d good_boots=%0d soft_resets=%0d fault1=%0d fault2=%0d fault3=%0d mismatches=%0d property_errors=%0d",
                 cyc, ncmp, n_ok, n_soft, n_e1, n_e2, n_e3, nmis, nprop);
        if (nmis != 0) $display("FAIL kv_centre rstseq %0d cycles differ from the body", nmis);
        else if (nprop != 0) $display("FAIL kv_centre rstseq %0d order-property errors", nprop);
        else if (!(n_ok == 2 && n_soft == 1 && n_e1 == 1 && n_e2 == 1 && n_e3 == 1 && ncmp > 40000)) $display("FAIL kv_centre rstseq coverage refused");
        else $display("PASS kv_centre rstseq leaf == body on %0d cycles; 2 boots, soft reset, faults 1/2/3, order properties hold", ncmp);
        $finish;
    end
endmodule
