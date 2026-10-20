`timescale 1ns/1ps
`default_nettype none
// HH-2 2026-10-19: unit bench of ot_hbm_sm_pv_merge at the production parameters (TAGW 16, LV 4, PUBLISH 1, ALAT 7),
// the smh_pvm hard tile.  Stimulus (pv_merge_golden.py gen): entry e (0..7) runs e+1 chunks of 16 FP32 lane sums; chunk j
// of entry e issues on the entry's turn (dut.bp == e) of round R0 + 5 j (compiler spacing: carry chain <= 3 turns, flush
// LV + 1).  Then one fold (0 <- 0 + 1) and the publication of slots 0, 2..7.  Every pv_v / pub_v beat is printed and
// checked bit for bit by pv_merge_golden.py check; fault must stay 0.  MUT = ot_hbm_sm_pv_merge MUT (negative controls).
// HBM-PVM-SAFE 10-19: SAFE = the dut's structural form (operand registers, ring fold tracker).  TIGHT 1 = the tight fold
// calendar from F0: (0<-0+1)@0 (2<-2+3)@2 (4<-4+5)@4 (2<-2+4)@14 (b = 4 is written back in its request cycle under SAFE),
// publication of slot 2 at the earliest legal cycle F0+25 (F0+24 with PUBEARLY: a schedule violation under SAFE -> fault),
// then slots 0, 6, 7.
// L2H-SMATT/PVMD 10-19: candidate = ot_hbm_sm_pv_merge_distributed (+1 input edge, +1 cold release edge) checked
// against the reference one-input/one-output SAFE2 wrapper delayed by exactly one edge, every output bit every edge.
// REASSERT 1 = the stream starts, rst_n is re-asserted mid-merge (adders, flush and stack writes in flight) with junk on
// every command input, then released and the full program runs (golden + age compare); REASSERT 2 = the same with the
// clock STOPPED during the assertion: every reset-tree node, input command capture and the core turn/busy state must
// clear with no clock edge (async assertion through real flop Q), checked before the clock restarts.
// Idle inputs carry junk: tag_d / sum are don't-care while ev is low, so every copy of ev / first-tag that is one edge
// off reads a junk word (exposes wrong-age copies).  XRAND 1 (with --x-initial unique / +verilator+rand+reset+2): unreset payload starts random, so payload fields are
// compared only under their valid (pv_v / pub_v); control/valid/fault bits stay compared every edge.
module tb_pv_merge_distributed;
    parameter integer MUT = 0;
    parameter integer TURNREG = 1;                    // HH-12: the smh_pvm kit form (registered turn state)
    parameter integer SAFE = 2, TIGHT = 0, PUBEARLY = 0, REASSERT = 0, XRAND = 0;
    localparam integer R0 = 4;
    reg clk = 0, rst_n = 0, clk_run = 1, junk = 0;
    always #0.5 clk = clk_run ? ~clk : 1'b0;
    reg ev = 0; reg [511:0] sum = 0; reg [15:0] tag_d = 0;
    reg pub_start = 0; reg [2:0] pub_slot = 0; reg fold_start = 0; reg [2:0] fold_a = 0, fold_b = 0;
    wire pv_v, pub_v, fault; wire [511:0] pv_y; wire [15:0] pv_tag, pub_tag; wire [31:0] pub_data; wire [3:0] pub_word;
    wire [2:0] pub_out_slot;
    ot_pvm_reference_pin_wrapper #(.MUT(0)) dut (.clk(clk), .rst_n(rst_n), .ev(ev), .sum(sum),
        .tag_d(tag_d), .pv_v(pv_v), .pv_y(pv_y), .pv_tag(pv_tag), .fault(fault), .pub_start(pub_start), .pub_slot(pub_slot),
        .pub_v(pub_v), .pub_data(pub_data), .pub_word(pub_word), .pub_out_slot(pub_out_slot), .pub_tag(pub_tag),
        .fold_start(fold_start), .fold_a(fold_a), .fold_b(fold_b));
    wire dv,dp,df;wire[511:0]dy;wire[15:0]dt,dpt;wire[31:0]dd;wire[3:0]dw;wire[2:0]ds;
    ot_hbm_sm_pv_merge_distributed #(.MUT(MUT)) candidate(.clk(clk),.rst_n(rst_n),.ev(ev),.sum(sum),.tag_d(tag_d),
      .pv_v(dv),.pv_y(dy),.pv_tag(dt),.fault(df),.pub_start(pub_start),.pub_slot(pub_slot),
      .pub_v(dp),.pub_data(dd),.pub_word(dw),.pub_out_slot(ds),.pub_tag(dpt),
      .fold_start(fold_start),.fold_a(fold_a),.fold_b(fold_b));
    reg [585:0] prior_ref; reg compare_started=0; integer cmp_n=0;
    // All output bits compared every edge, including invalid payload. No X masks.
    always @(negedge clk) begin
      if(compare_started && !XRAND && {dv,dy,dt,df,dp,dd,dw,ds,dpt} !== prior_ref)
        $fatal(1,"DISTRIBUTED_ALL_OUTPUT_AGE_MISMATCH");
      if(compare_started && XRAND && ({dv,df,dp} !== {prior_ref[585],prior_ref[56],prior_ref[55]} ||
         (prior_ref[585] && {dy,dt} !== prior_ref[584:57]) || (prior_ref[55] && {dd,dw,ds,dpt} !== prior_ref[54:0])))
        $fatal(1,"DISTRIBUTED_ALL_OUTPUT_AGE_MISMATCH (valid-qualified payload)");
      if(compare_started) cmp_n=cmp_n+1;
      prior_ref={pv_v,pv_y,pv_tag,fault,pub_v,pub_data,pub_word,pub_out_slot,pub_tag};
      compare_started<=1;
    end
    reg [511:0] chunk [0:63];                       // entry e chunk j at e*8+j
    initial $readmemh(`STIM, chunk);
    integer round = 0, cyc = 0, npv = 0, npub = 0, fault_cyc = -1;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (dut.bp == 3'd7) round <= round + 1;
        if (pv_v) begin $display("PV %04h %0128h", pv_tag, pv_y); npv = npv + 1; end
        if (pub_v) begin $display("PUB %0d %0d %04h %08h", pub_out_slot, pub_word, pub_tag, pub_data); npub = npub + 1; end
        if (fault && fault_cyc < 0) fault_cyc = cyc;
`ifdef DBG
        if (ev || cyc < 40) $display("DBG cyc %0d bp %0d round %0d ev %0d tag %04h busy %02h fault %0d", cyc, dut.bp, round, ev, tag_d, dut.e_busy, fault);
`endif
    end
    integer e, j, k;
    // chunk issue: drive at the negedge before the posedge that sees r = bp
    always @(negedge clk) begin
        ev <= 0; tag_d <= 16'($random) | 16'h4000; sum <= {16{32'($random)}};   // idle first-chunk bit 1: an early first-tag copy is wrong
        if (junk) begin ev <= 1; tag_d <= 16'hffff; sum <= {16{32'h7f80_0001}}; end
        else if (rst_n && round >= R0 && round < R0 + 40 && (round - R0) % 5 == 0) begin
            e = dut.bp; j = (round - R0) / 5;
            if (j <= e) begin
                ev <= 1; sum <= chunk[e*8+j];
                tag_d <= {1'b1, (j == 0), (j == e), 10'(e*8+j), 3'(e)};
            end
        end
    end
    task automatic tick(input integer n); for (k = 0; k < n; k = k + 1) @(negedge clk); endtask
    task automatic fold(input [2:0] a, input [2:0] b); fold_start = 1; fold_a = a; fold_b = b; @(negedge clk); fold_start = 0; endtask
    task automatic pub(input [2:0] sl); pub_start = 1; pub_slot = sl; @(negedge clk); pub_start = 0; endtask
    task automatic reassert;
        // the stream is running: entry 0 flushing (adders valid), entries 1..7 holding chunk 0 in the stack
        wait (round == R0 + 3); @(negedge clk);
        if (dut.u_core.e_busy == 8'd0 && candidate.u_core.e_busy == 8'd0) $fatal(1, "REASSERT_NOT_MID_STREAM");
        if (REASSERT == 2) begin
            #0.2 clk_run = 0; #2;                     // clock stopped low, no edge from here
            rst_n = 0; junk = 1; pub_start = 1; fold_start = 1; #3;
            if ((|candidate.reset_first_n) !== 1'b0 || (|candidate.reset_second_n) !== 1'b0 || (|candidate.reset_core_n) !== 1'b0 ||
                (|candidate.ev1) !== 1'b0 || (|candidate.ev2) !== 1'b0 || (|candidate.fold2c) !== 1'b0 || (|candidate.pub2c) !== 1'b0 || (|candidate.u_core.pd0_k) !== 1'b0 ||
                {candidate.pub1,candidate.pub2,candidate.fold1,candidate.fold2} !== 4'd0 ||
                candidate.u_core.e_busy !== 8'd0 || candidate.u_core.bp !== 3'd0 || (|candidate.u_core.fd1_k) !== 1'b0 ||
                (|candidate.u_core.pd1_k) !== 1'b0 || (|candidate.u_core.pa_k) !== 1'b0 ||
                {candidate.pv_v,candidate.pub_v,candidate.fault} !== 3'd0 || dut.u_core.e_busy !== 8'd0)
                $fatal(1, "STOPCLK_RESET_NOT_PROPAGATED first %b second %b core %h busy %h", candidate.reset_first_n,
                       candidate.reset_second_n, candidate.reset_core_n, candidate.u_core.e_busy);
            $display("PVM STOPCLK reset tree + captures + core state cleared with no clock edge");
            clk_run = 1; @(negedge clk);
        end else begin
            #0.2 rst_n = 0; junk = 1; pub_start = 1; fold_start = 1;
        end
        tick(4); junk = 0; pub_start = 0; fold_start = 0; rst_n = 1;
        round = 0; cyc = 0;
        $display("PVM REASSERT %0d released", REASSERT);
    endtask
    // XRAND power-up: async-clear flops are level-sensitive (0 while reset is low); a 2-state event simulator only
    // clears them on an edge, so the reset trees themselves are put in their asserted state at power-up.
    generate if (XRAND) begin : g_pwr
        for (genvar i = 0; i < 2; i = i + 1) initial #0.1 candidate.g_reset_first[i].u.q = 1'b0;
        for (genvar i = 0; i < 8; i = i + 1) initial #0.1 candidate.g_reset_second[i].u.q = 1'b0;
        for (genvar i = 0; i < 54; i = i + 1) initial #0.1 candidate.g_reset_core[i].u.q = 1'b0;
        initial #0.1 begin dut.r0 = 1'b0; dut.r1 = 1'b0; end
    end endgenerate
    initial begin
        tick(XRAND ? 6 : 3); rst_n = 1;
        if (REASSERT != 0) reassert;
        wait (round == R0 + 40 + 6);                  // every run flushed (flush <= LV + 1 turns after the last chunk)
        @(negedge clk);
        if (TIGHT) begin                              // request cycles F0 + n (each task call = 1 cycle)
            fold(0, 1); tick(1); fold(2, 3); tick(1); fold(4, 5); tick(9); fold(2, 4);    // @0 @2 @4 @14
            tick(PUBEARLY ? 9 : 10); pub(2); tick(23);                                     // @25 (@24)
            pub(0); tick(23); pub(6); tick(23); pub(7); tick(23);
        end else begin
            fold(0, 1);
            tick(20);
            for (e = 0; e < 8; e = e + 1) if (e != 1) begin
                pub(3'(e)); tick(23);
            end
        end
        tick(10);
        if (df !== 1'b0) $fatal(1, "DISTRIBUTED_CANDIDATE_FAULT");
        $display("PVM DONE pv=%0d pub=%0d fault=%0d fault_cyc=%0d cycles=%0d cmp_edges=%0d reassert=%0d xrand=%0d", npv, npub, fault,
                 fault_cyc, cyc, cmp_n, REASSERT, XRAND);
        $finish;
    end
endmodule
`default_nettype wire
