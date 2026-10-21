`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19: lockstep bench qkd_pv16_vport_b (boot ages cfg_age = {DQ, RT}) vs the closed r6 module
// qkd_pv16_vport #(.DQ(D), .RT(R)).  Every output is compared on every edge.
//   phase A  random stimulus (requests, both rsp faces, flags, tags, data)            -> outputs identical
//   phase B  landing model: rsp side g = vq<g> delayed R edges (the RT contract), tag / data from the request;
//            the reference must stay fault-free (proves the slot / sel path is exercised, not only the fault path)
//   phase C  invalid ages (RT 0, RT > bound, DQ > bound): the first request must set the successor's fault
// Prints "KVBA_VPORT PASS D=.. R=.. mut=.. checks=N" or "KVBA_VPORT FAIL ...".
module tb_kvba_vport;
    parameter integer D = 0, R = 8, MUT = 0, NCYC = 4000, SEED = 1;
    localparam integer DB = 15, RB = 31;
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg [15:0] cfg;
    reg pr_valid; reg [13:0] pr_t;
    reg i0v, i0f, i1v, i1f; reg [13:0] i0t, i1t; reg [15:0] i0e, i1e; reg [1023:0] i0d, i1d;
    wire a_vq0v, a_vq1v, b_vq0v, b_vq1v; wire [13:0] a_vq0t, a_vq1t, b_vq0t, b_vq1t;
    wire a_ov, b_ov, a_f, b_f; wire [13:0] a_ot, b_ot; wire [15:0] a_oe, b_oe; wire [511:0] a_lo, a_hi, b_lo, b_hi;
    qkd_pv16_vport #(.MUT(0), .DQ(D), .RT(R)) u_ref (.ck(ck), .rst_n(rst_n), .pr_valid(pr_valid), .pr_t(pr_t),
        .vq0_valid(a_vq0v), .vq0_t(a_vq0t), .vq1_valid(a_vq1v), .vq1_t(a_vq1t),
        .in0_valid(i0v), .in0_vflag(i0f), .in0_t(i0t), .in0_epoch(i0e), .in0_d(i0d),
        .in1_valid(i1v), .in1_vflag(i1f), .in1_t(i1t), .in1_epoch(i1e), .in1_d(i1d),
        .out_valid(a_ov), .out_t(a_ot), .out_epoch(a_oe), .out_v_lo(a_lo), .out_v_hi(a_hi), .fault(a_f));
    qkd_pv16_vport_b #(.MUT(MUT), .DQ(DB), .RT(RB)) u_dut (.ck(ck), .rst_n(rst_n), .cfg_age(cfg), .pr_valid(pr_valid), .pr_t(pr_t),
        .vq0_valid(b_vq0v), .vq0_t(b_vq0t), .vq1_valid(b_vq1v), .vq1_t(b_vq1t),
        .in0_valid(i0v), .in0_vflag(i0f), .in0_t(i0t), .in0_epoch(i0e), .in0_d(i0d),
        .in1_valid(i1v), .in1_vflag(i1f), .in1_t(i1t), .in1_epoch(i1e), .in1_d(i1d),
        .out_valid(b_ov), .out_t(b_ot), .out_epoch(b_oe), .out_v_lo(b_lo), .out_v_hi(b_hi), .fault(b_f));
    integer checks = 0, errs = 0, cyc, k, seed, refault = 0, words = 0;
    // landing model: R-edge delay of each vq face (valid + tag)
    reg [R:0] lv0, lv1; reg [14*(R+1)-1:0] lt0, lt1;
    always @(posedge ck) begin
        if (!rst_n) begin lv0 <= 0; lv1 <= 0; end
        else begin lv0 <= {lv0[R-1:0], a_vq0v}; lv1 <= {lv1[R-1:0], a_vq1v}; end
        lt0 <= {lt0[14*R-1:0], a_vq0t}; lt1 <= {lt1[14*R-1:0], a_vq1t};
    end
    task cmp; begin
        checks = checks + 1;
        if ({a_vq0v, a_vq0t, a_vq1v, a_vq1t, a_ov, a_ot, a_oe, a_lo, a_hi, a_f} !==
            {b_vq0v, b_vq0t, b_vq1v, b_vq1t, b_ov, b_ot, b_oe, b_lo, b_hi, b_f}) begin
            errs = errs + 1;
            if (errs < 6) $display("MISMATCH t=%0t vq0 %b/%b vq1 %b/%b ov %b/%b ot %h/%h fault %b/%b", $time,
                                   a_vq0v, b_vq0v, a_vq1v, b_vq1v, a_ov, b_ov, a_ot, b_ot, a_f, b_f);
        end
    end endtask
    task do_reset; begin
        rst_n = 0; pr_valid = 0; i0v = 0; i1v = 0; i0f = 0; i1f = 0;
        repeat (6) @(negedge ck);
        rst_n = 1; repeat (2) @(negedge ck);
    end endtask
    reg [13:0] tq; integer bad_ok;
    initial begin
        seed = SEED; cfg = {8'(D), 8'(R)};
        pr_t = 0; i0t = 0; i1t = 0; i0e = 0; i1e = 0; i0d = 0; i1d = 0; lv0 = 0; lv1 = 0; lt0 = 0; lt1 = 0;
        do_reset;
        // ---- phase A: random
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            pr_valid = $random(seed); pr_t = $random(seed);
            i0v = $random(seed); i1v = $random(seed); i0f = $random(seed); i1f = $random(seed);
            i0t = $random(seed); i1t = $random(seed); i0e = $random(seed); i1e = $random(seed);
            for (k = 0; k < 32; k = k + 1) begin i0d[32*k +: 32] = $random(seed); i1d[32*k +: 32] = $random(seed); end
            @(posedge ck); #0.1 cmp; @(negedge ck);
        end
        // ---- phase B: landing model (one V get every other edge, as the pair issues; tag parity alternates)
        do_reset;
        for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
            tq = $random(seed);
            pr_valid = (cyc % 2 == 0) && (cyc < NCYC - 4 * (D + R + 8)); pr_t = {tq[13:1], cyc[1]};
            i0v = lv0[R-1]; i0f = 1'b1; i0t = lt0[14*(R-1) +: 14]; i0e = 16'h0b0b;
            i1v = lv1[R-1]; i1f = 1'b1; i1t = lt1[14*(R-1) +: 14]; i1e = 16'h0b0b;
            for (k = 0; k < 32; k = k + 1) begin i0d[32*k +: 32] = $random(seed); i1d[32*k +: 32] = $random(seed); end
            @(posedge ck); #0.1 cmp; if (a_f) refault = refault + 1; if (a_ov) words = words + 1; @(negedge ck);
        end
        // ---- phase C: invalid boot ages fault the successor on the first request
        bad_ok = 0;
        for (k = 0; k < 3; k = k + 1) begin
            cfg = (k == 0) ? {8'(D), 8'd0} : (k == 1) ? {8'(D), 8'(RB + 1)} : {8'(DB + 1), 8'(R)};
            do_reset; pr_valid = 0; i0v = 0; i1v = 0;
            repeat (4) @(negedge ck);
            if (b_f) $display("PHASE_C k=%0d fault before any request", k);
            else begin
                pr_valid = 1; pr_t = 0; @(negedge ck); pr_valid = 0; repeat (4) @(negedge ck);
                if (b_f) bad_ok = bad_ok + 1; else $display("PHASE_C k=%0d invalid ages accepted (no fault)", k);
            end
        end
        if (errs == 0 && refault == 0 && words > NCYC / 4 && bad_ok == 3)
            $display("KVBA_VPORT PASS D=%0d R=%0d mut=%0d checks=%0d words=%0d", D, R, MUT, checks, words);
        else
            $display("KVBA_VPORT FAIL D=%0d R=%0d mut=%0d checks=%0d errors=%0d ref_fault_cycles=%0d words=%0d invalid_caught=%0d/3",
                     D, R, MUT, checks, errs, refault, words, bad_ok);
        $finish;
    end
endmodule
