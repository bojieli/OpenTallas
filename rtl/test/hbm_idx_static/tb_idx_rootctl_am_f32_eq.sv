`timescale 1ns/1ps
`default_nettype none
// HBM-IDX6 2026-10-20: FAN32 equivalence of the d4g IDX root. REF = ot_hbm_idx_rootctl_static_am #(VM_RT 65, CR_RT 36,
// SEL_LAT 30, RSTL 1, FAN32 0) (the g2d elaboration), DUT = the same with FAN32 1. Both see the SAME inputs every edge;
// EVERY output port must be identical (!==, X-exact) on EVERY edge after reset release. Stimulus, three overlapping phases per record:
//   TOPK: random legal / illegal descriptors (k 1..8, n k..k+120, m 1..4, mirrors, unaligned bases, strides, has_r),
//         scores from a hash or (1 in 3 records) a tie-heavy set {+0, -0, +-1, +-2, 3} with rare NaN; VM model answers the
//         REF's vm_rq at 7 + VM_RT (dropped 1 in 16 records: fault path), hub echo at 11 + CR_RT (dropped 1 in 16);
//   ARGMAX / INDEX: sparse requests on banks the TOPK record leaves free (and, 1 in 8 records, colliding: share fault);
//   CALENDAR: programme rows written while idle, start with length 0..64 (0 / overlap: fault), random selected_v /
//         tree_ev / qfault / sf / lf.
// Also requires the FAN32 engine's simulation-only copy checker (every kept copy == the decode it replaces) to be 0.
// MUT1 = DUT AMMUT (mutants: 5 TOPK capture one edge early, 3 ARGMAX data unmasked, 6 ingest_v early) -> must FAIL.
module tb_idx_rootctl_am_f32_eq;
`ifndef MUT1
`define MUT1 0
`endif
`ifndef NREC
`define NREC 160
`endif
`ifndef SEED
`define SEED 1
`endif
    localparam integer VMRT = 65, CRRT = 36, RD1 = 7 + VMRT, ACKD1 = 11 + CRRT, PD = 160;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    // ---------------- inputs (shared)
    reg program_we = 0; reg [7:0] program_addr = 0; reg [255:0] program_data = 0; reg start = 0; reg [11:0] length = 0;
    reg [3:0] selected_v = 0, tree_ev = 0, qfault = 0; reg sf = 0, lf = 0;
    reg go = 0, order = 0, a_mirror = 0, o_mirror = 0, has_r = 0; reg [3:0] k = 0; reg [19:0] n = 0, m = 0;
    reg [17:0] a_base = 0, a_str = 0, o_base = 0, o_str = 0, r_base = 0, r_str = 0;
    reg [135:0] index_rq = 0, argmax_rq = 0; reg [2055:0] vm_rr = 0; reg [273:0] cr = 0;
    // ---------------- outputs
    wire [3:0] so0, so1; wire [1:0] sp0, sp1; wire [7:0] sa0, sa1; wire lf0, lf1, le0, le1, lc0, lc1; wire [3:0] lg0, lg1;
    wire iv0, iv1, dn0, dn1, ft0, ft1; wire [337:0] cq0, cq1; wire [1:0] cs0, cs1; wire tb0, tb1, td0, td1, tf0, tf1;
    wire [2055:0] ir0, ir1; wire [263:0] am0, am1; wire [135:0] vq0, vq1; wire sh0, sh1;
    `define RC_IN .clk(clk), .rst_n(rst_n), .program_we(program_we), .program_addr(program_addr), .program_data(program_data), \
        .start(start), .length(length), .selected_v(selected_v), .tree_ev(tree_ev), .qfault(qfault), .sf(sf), .lf(lf), \
        .topk_go(go), .topk_k(k), .topk_order(order), .topk_n(n), .topk_m(m), .topk_a_mirror(a_mirror), .topk_a_base(a_base), \
        .topk_a_str(a_str), .topk_o_mirror(o_mirror), .topk_o_base(o_base), .topk_o_str(o_str), .topk_has_r(has_r), \
        .topk_r_base(r_base), .topk_r_str(r_str), .cr(cr), .index_rq(index_rq), .argmax_rq(argmax_rq), .vm_rr(vm_rr)
    ot_hbm_idx_rootctl_static_am #(.AMMUT(0), .VM_RT(VMRT), .CR_RT(CRRT), .SEL_LAT(30), .RSTL(1), .FAN32(0)) r0(`RC_IN,
        .sel_op(so0), .sel_pass(sp0), .sel_addr(sa0), .link_flush(lf0), .link_emit(le0), .link_group(lg0), .link_clear(lc0),
        .ingest_v(iv0), .done(dn0), .fault(ft0), .cq(cq0), .cq_seq(cs0), .topk_busy(tb0), .topk_done(td0), .topk_fault(tf0),
        .index_rr(ir0), .argmax_m(am0), .vm_rq(vq0), .share_fault(sh0));
    ot_hbm_idx_rootctl_static_am #(.AMMUT(`MUT1), .VM_RT(VMRT), .CR_RT(CRRT), .SEL_LAT(30), .RSTL(1), .FAN32(1)) r1(`RC_IN,
        .sel_op(so1), .sel_pass(sp1), .sel_addr(sa1), .link_flush(lf1), .link_emit(le1), .link_group(lg1), .link_clear(lc1),
        .ingest_v(iv1), .done(dn1), .fault(ft1), .cq(cq1), .cq_seq(cs1), .topk_busy(tb1), .topk_done(td1), .topk_fault(tf1),
        .index_rr(ir1), .argmax_m(am1), .vm_rq(vq1), .share_fault(sh1));
    wire [3010:0] o0 = {so0, sp0, sa0, lf0, le0, lg0, lc0, iv0, dn0, ft0, cq0, cs0, tb0, td0, tf0, ir0, am0, vq0, sh0};
    wire [3010:0] o1 = {so1, sp1, sa1, lf1, le1, lg1, lc1, iv1, dn1, ft1, cq1, cs1, tb1, td1, tf1, ir1, am1, vq1, sh1};
    // ---------------- VM + hub models (answer the REF's requests; the DUT must have issued the same ones)
    integer tie = 0, nanr = 0;
    function automatic [31:0] sval(input [15:0] q, input integer l, input integer e);
        reg [31:0] h; begin
            h = {q, 3'(l), 3'(e)} * 32'h9E3779B1 ^ 32'h5bd1e995;
            if (tie != 0) case (h[18:16])
                3'd0: sval = 32'h0000_0000; 3'd1: sval = 32'h8000_0000; 3'd2: sval = 32'h3f80_0000; 3'd3: sval = 32'hbf80_0000;
                3'd4: sval = 32'h4000_0000; 3'd5: sval = 32'hc000_0000; 3'd6: sval = 32'h4040_0000;
                default: sval = (nanr != 0 && h[23:19] == 5'd0) ? 32'h7fc0_0001 : 32'h3f80_0000;
            endcase else sval = h & 32'hBFFF_FFFF;
        end endfunction
    reg [16:0] pq [0:PD-1][0:7]; reg [16:0] pc [0:PD-1]; integer t, l, e;
    initial for (t = 0; t < PD; t = t + 1) begin pc[t] = 0; for (l = 0; l < 8; l = l + 1) pq[t][l] = 0; end
    reg drop_rr = 0, drop_ack = 0;
    always @(posedge clk) begin
        for (t = PD-1; t > 0; t = t - 1) begin pc[t] <= pc[t-1]; for (l = 0; l < 8; l = l + 1) pq[t][l] <= pq[t-1][l]; end
        for (l = 0; l < 8; l = l + 1) pq[0][l] <= {vq0[17*l+16], vq0[17*l +: 16]};
        pc[0] <= {cq0[337], cq0[15:0]};
    end
    always @(negedge clk) begin
        for (l = 0; l < 8; l = l + 1) begin
            for (e = 0; e < 8; e = e + 1) vm_rr[257*l + 32*e +: 32] = sval(pq[RD1-1][l][15:0], l, e);
            vm_rr[257*l+256] = pq[RD1-1][l][16] && !drop_rr;
        end
        cr = 0; cr[273] = pc[ACKD1-1][16] && !drop_ack; cr[272:257] = pc[ACKD1-1][15:0]; cr[256] = pc[ACKD1-1][16];
    end
    // ---------------- compare every edge
    integer cyc = 0, errs = 0, nq = 0, nw = 0, ndone = 0, nflt = 0, nam = 0, nidx = 0, ncal = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n && o0 !== o1) begin   // from reset release (before it the as-built X/0 init differs only in sim)
            errs = errs + 1;
            if (errs < 6) $display("DIFF cyc %0d: sel %h/%h cq %b/%b busy %b/%b done %b/%b fault %b/%b am %b ir %b vq %b sh %b/%b",
                cyc, {so0, sp0, sa0}, {so1, sp1, sa1}, cq0 !== cq1, 1'b0, tb0, tb1, {td0, dn0}, {td1, dn1}, {tf0, ft0}, {tf1, ft1},
                am0 !== am1, ir0 !== ir1, vq0 !== vq1, sh0, sh1);
        end
        for (l = 0; l < 8; l = l + 1) if (vq0[17*l+16]) nq = nq + 1;
        if (cq0[337]) nw = nw + 1;
        if (td0) ndone = ndone + 1;
        if (tf0) nflt = nflt + 1;
        if (am0[263:256] != 0) nam = nam + 1;
        if (so0 != 0) ncal = ncal + 1;
    end
    // ---------------- stimulus
    integer w, rnd, busyband; integer seed = `SEED;
    task automatic side_requests;     // ARGMAX / INDEX on banks 4..7 (TOPK reads whatever sector it needs: collisions = fault)
        integer b; begin
            index_rq = 0; argmax_rq = 0;
            for (b = 0; b < 8; b = b + 1) begin
                rnd = $urandom % 64;
                if (rnd == 0) begin argmax_rq[17*b +: 17] = {1'b1, 1'b0, 15'($urandom)}; nam = nam; end
                else if (rnd == 1) begin index_rq[17*b +: 17] = {1'b1, 1'b0, 15'($urandom)}; nidx = nidx + 1; end
            end
        end endtask
    initial begin
        rnd = $urandom(seed);
        repeat (6) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        // programme 8 calendar rows
        for (w = 0; w < 8; w = w + 1) begin
            program_we = 1; program_addr = w; for (e = 0; e < 8; e = e + 1) program_data[32*e +: 32] = $urandom; @(negedge clk);
        end
        program_we = 0;
        for (w = 0; w < `NREC; w = w + 1) begin
            @(negedge clk);
            drop_rr = ($urandom % 16) == 0; drop_ack = !drop_rr && ($urandom % 16) == 0;
            tie = ($urandom % 3) == 0; nanr = ($urandom % 6) == 0;
            k = ($urandom % 24 == 0) ? 0 : 1 + $urandom % 8; n = k + $urandom % 120; m = 1 + $urandom % 4; order = $urandom;
            a_mirror = $urandom; a_base = {(($urandom % 16) == 0) ? 2'd1 : 2'd0, 16'($urandom)}; a_str = $urandom % 512;
            o_mirror = ($urandom % 24) == 0; o_base = {2'd0, 16'($urandom % 60000)}; o_str = $urandom % 64;
            has_r = $urandom; r_base = {2'd0, 16'($urandom % 60000)}; r_str = $urandom % 64;
            go = 1;
            if ((w % 5) == 2) begin start = 1; length = ($urandom % 12 == 0) ? 0 : $urandom % 64; end
            @(negedge clk) begin go = 0; start = 0; k = $urandom; n = $urandom; m = $urandom; a_base = $urandom; o_base = $urandom; end
            busyband = 0;
            while (tb0 || tb1 || busyband < 4) begin
                @(negedge clk); busyband = busyband + 1;
                selected_v = ($urandom % 8 == 0) ? 4'($urandom) : {4{iv0}};
                tree_ev = ($urandom % 32 == 0) ? 4'($urandom) : 4'hf; qfault = ($urandom % 512 == 0) ? 4'd1 : 4'd0;
                sf = ($urandom % 1024) == 0; lf = ($urandom % 1024) == 0;
                if ((w % 8) == 3) side_requests(); else begin index_rq = 0; argmax_rq = 0; end
                if ($urandom % 97 == 0) go = 1; else go = 0;    // go while busy: ignored by both
            end
            index_rq = 0; argmax_rq = 0; go = 0;
            // idle window: ARGMAX / INDEX traffic with TOPK idle
            repeat (8) begin @(negedge clk); side_requests(); end
            index_rq = 0; argmax_rq = 0;
            repeat (3) @(negedge clk);
        end
        repeat (40 + 2 * VMRT + CRRT) @(negedge clk);
        $display("F32_EQ MUT1=%0d SEED=%0d cycles %0d reads %0d writes %0d topk_done %0d topk_fault %0d argmax_words %0d index_req %0d sel_ops %0d copy_err %0d errors %0d",
                 `MUT1, `SEED, cyc, nq, nw, ndone, nflt, nam, nidx, ncal, r1.g_tk32.topk.f32_copy_err, errs);
        if (errs == 0 && r1.g_tk32.topk.f32_copy_err == 0 && ndone > `NREC / 3 && nflt > 0 && nam > 0 && nidx > 0 && ncal > 0)
            $display("IDX_F32_EQ PASS");
        else $display("IDX_F32_EQ FAIL");
        $finish;
    end
endmodule
`default_nettype wire
