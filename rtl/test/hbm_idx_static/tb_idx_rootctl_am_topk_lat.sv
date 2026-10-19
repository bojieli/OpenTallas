`timescale 1ns/1ps
`default_nettype none
// HBM-BANKLAT-IDX 2026-10-19: TOPK path of the IDX root ot_hbm_idx_rootctl_static_am at the d4g GEN2c BUDGET
// (results/arch/hbm_banklat_1019/idx_budget.json: VM_RT 65 = faces pin 1 + rq4/rr4 lanes 64, CR_RT 36 = faces pin 1 +
// cq lanes 18 + cr lanes 17; SEL_LAT 30). From tb_idx_rootctl_am_topk (same stimulus, same exact checks): REF =
// ot_hbm_idx_rootctl_static #(.PIN_IN(1)) on the faces VM model (RD 8 / ACKD 12, its as-built timing); DUT on its own
// model whose VM answer is RD = 7 + VM_RT_M edges after the vm_rq port (bank 6 + pin 1 + lanes) and whose hub echo
// reaches cr ACKD = 11 + CR_RT_M edges after cq (pin + cq/cr lanes). Every VM request, every write (payload + cq_seq)
// and every done/fault must match the REF in order at the static offsets the budget implies (d = VM_RT_M per row):
//   request 1 + r*d, write 2 + (r+1)*d, done/fault of a legal record 2 + (r+1)*d + CR_RT_M, illegal descriptor 2.
// The DUT's engine runs RT_EXTRA 66 / ACK 49 (the counter width fix CW 8 in ot_hbm_idx_topk_static is exercised).
// Mutants (DUT params != model): VM_RT_P 1 / CR_RT_P 1 (the am_pin master on the GEN2c lanes), VM_RT_P 64, CR_RT_P 35.
module tb_idx_rootctl_am_topk_lat;
`ifndef VM_RT_M
`define VM_RT_M 65
`endif
`ifndef CR_RT_M
`define CR_RT_M 36
`endif
`ifndef VM_RT_P
`define VM_RT_P `VM_RT_M
`endif
`ifndef CR_RT_P
`define CR_RT_P `CR_RT_M
`endif
`ifndef AMMUT
`define AMMUT 0
`endif
`ifndef NREC
`define NREC 240
`endif
    localparam integer RD = 8, ACKD = 12, RD1 = 7 + `VM_RT_M, ACKD1 = 11 + `CR_RT_M, DR = `VM_RT_M, PD = 128;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg go = 0, order = 0, a_mirror = 0, o_mirror = 0, has_r = 0; reg [3:0] k = 0; reg [19:0] n = 0, m = 0;
    reg [17:0] a_base = 0, a_str = 0, o_base = 0, o_str = 0, r_base = 0, r_str = 0;
    reg drop_rr = 0, drop_ack = 0;
    `define RC_TK .program_we(1'b0), .program_addr(8'd0), .program_data(256'd0), .start(1'b0), .length(12'd0), \
        .sel_op(), .sel_pass(), .sel_addr(), .link_flush(), .link_emit(), .link_group(), .link_clear(), .selected_v(4'h0), \
        .ingest_v(), .tree_ev(4'h0), .qfault(4'h0), .sf(1'b0), .lf(1'b0), .done(), .fault(), .topk_go(go), .topk_k(k), \
        .topk_order(order), .topk_n(n), .topk_m(m), .topk_a_mirror(a_mirror), .topk_a_base(a_base), .topk_a_str(a_str), \
        .topk_o_mirror(o_mirror), .topk_o_base(o_base), .topk_o_str(o_str), .topk_has_r(has_r), .topk_r_base(r_base), \
        .topk_r_str(r_str), .index_rq(136'd0), .index_rr(), .argmax_rq(136'd0)
    reg [2055:0] rr0 = 0, rr1 = 0; reg [273:0] cr0 = 0, cr1 = 0;
    wire [135:0] q0, q1; wire [337:0] cq0, cq1; wire [1:0] s0, s1; wire b0, b1, d0, d1, f0, f1, sf0, sf1;
    ot_hbm_idx_rootctl_static #(.PIN_IN(1)) rc0(.clk_program(clk), .clk_program_mem(clk), .clk_sel(clk), .clk_topk(clk), .clk_pair({4{clk}}),
        .rst_n(rst_n), `RC_TK, .argmax_rr(), .vm_rq(q0), .vm_rr(rr0), .cq(cq0), .cq_seq(s0), .cr(cr0),
        .topk_busy(b0), .topk_done(d0), .topk_fault(f0), .share_fault(sf0));
    ot_hbm_idx_rootctl_static_am #(.AMMUT(`AMMUT), .VM_RT(`VM_RT_P), .CR_RT(`CR_RT_P), .SEL_LAT(30)) rc1(.clk(clk), .rst_n(rst_n), `RC_TK, .argmax_m(), .vm_rq(q1), .vm_rr(rr1),
        .cq(cq1), .cq_seq(s1), .cr(cr1), .topk_busy(b1), .topk_done(d1), .topk_fault(f1), .share_fault(sf1));
    // ---------------- VM + client models (same function for both sides)
    function automatic [255:0] sdat(input [15:0] q, input integer l);
        integer e; reg [31:0] h; begin
            for (e = 0; e < 8; e = e + 1) begin h = {q, 3'(l), 3'(e)} * 32'h9E3779B1 ^ 32'h5bd1e995; sdat[32*e +: 32] = h & 32'hBFFF_FFFF; end
        end endfunction
    reg [16:0] p0 [0:PD-1][0:7]; reg [16:0] p1 [0:PD-1][0:7]; reg [16:0] c0 [0:PD-1]; reg [16:0] c1 [0:PD-1]; integer t, l;
    initial for (t = 0; t < PD; t = t + 1) begin c0[t] = 0; c1[t] = 0; for (l = 0; l < 8; l = l + 1) begin p0[t][l] = 0; p1[t][l] = 0; end end
    always @(posedge clk) begin
        for (t = PD-1; t > 0; t = t - 1) begin c0[t] <= c0[t-1]; c1[t] <= c1[t-1]; for (l = 0; l < 8; l = l + 1) begin p0[t][l] <= p0[t-1][l]; p1[t][l] <= p1[t-1][l]; end end
        for (l = 0; l < 8; l = l + 1) begin p0[0][l] <= {q0[17*l+16], q0[17*l +: 16]}; p1[0][l] <= {q1[17*l+16], q1[17*l +: 16]}; end
        c0[0] <= {cq0[337], cq0[15:0]}; c1[0] <= {cq1[337], cq1[15:0]};
    end
    always @(negedge clk) begin
        for (l = 0; l < 8; l = l + 1) begin
            rr0[257*l +: 256] = sdat(p0[RD-1][l][15:0], l); rr0[257*l+256] = p0[RD-1][l][16] && !drop_rr;
            rr1[257*l +: 256] = sdat(p1[RD1-1][l][15:0], l); rr1[257*l+256] = p1[RD1-1][l][16] && !drop_rr;
        end
        cr0 = 0; cr0[273] = c0[ACKD-1][16] && !drop_ack; cr0[272:257] = c0[ACKD-1][15:0]; cr0[256] = c0[ACKD-1][16];
        cr1 = 0; cr1[273] = c1[ACKD1-1][16] && !drop_ack; cr1[272:257] = c1[ACKD1-1][15:0]; cr1[256] = c1[ACKD1-1][16];
    end
    // ---------------- transaction logs (row r of the reference engine at the edge)
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [19:0] lq0 [0:131071]; reg [19:0] lq1 [0:131071]; integer tq0 [0:131071]; integer tq1 [0:131071]; integer rq0r [0:131071];
    integer nq0 = 0, nq1 = 0;
    reg [339:0] lw0 [0:16383]; reg [339:0] lw1 [0:16383]; integer tw0 [0:16383]; integer tw1 [0:16383]; integer rw0r [0:16383];
    integer nw0 = 0, nw1 = 0;
    reg [1:0] le0 [0:4095]; reg [1:0] le1 [0:4095]; integer te0 [0:4095]; integer te1 [0:4095]; integer xe0 [0:4095];
    integer ne0 = 0, ne1 = 0;
    always @(posedge clk) if (rst_n) begin
        for (l = 0; l < 8; l = l + 1) begin
            if (q0[17*l+16]) begin lq0[nq0] = {l[2:0], q0[17*l +: 17]}; tq0[nq0] = cyc; rq0r[nq0] = rc0.topk.c_row; nq0 = nq0 + 1; end
            if (q1[17*l+16]) begin lq1[nq1] = {l[2:0], q1[17*l +: 17]}; tq1[nq1] = cyc; nq1 = nq1 + 1; end
        end
        if (cq0[337]) begin lw0[nw0] = {s0, cq0}; tw0[nw0] = cyc; rw0r[nw0] = rc0.topk.c_row; nw0 = nw0 + 1; end
        if (cq1[337]) begin lw1[nw1] = {s1, cq1}; tw1[nw1] = cyc; nw1 = nw1 + 1; end
        if (d0 || f0) begin le0[ne0] = {d0, f0}; te0[ne0] = cyc; xe0[ne0] = rc0.topk.legal_q ? 2 + (rc0.topk.c_row + 1) * DR + `CR_RT_M : 2; ne0 = ne0 + 1; end
        if (d1 || f1) begin le1[ne1] = {d1, f1}; te1[ne1] = cyc; ne1 = ne1 + 1; end
    end
    integer w, errs = 0, i, ndone = 0, nflt = 0, nill = 0, maxrow = 0;
    initial begin
        repeat (6) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        for (w = 0; w < `NREC; w = w + 1) begin
            @(negedge clk);
            drop_rr = ($urandom % 16) == 0; drop_ack = !drop_rr && ($urandom % 16) == 0;
            k = 1 + $urandom % 8; n = k + $urandom % 120; m = 1 + $urandom % 4; order = $urandom; a_mirror = $urandom;
            a_base = {(($urandom % 16) == 0) ? 2'd1 : 2'd0, 16'($urandom)}; a_str = $urandom % 512;
            o_mirror = ($urandom % 24) == 0; o_base = {2'd0, 16'($urandom % 60000)}; o_str = $urandom % 64;
            has_r = $urandom; r_base = {2'd0, 16'($urandom % 60000)}; r_str = $urandom % 64;
            go = 1;
            @(negedge clk) go = 0;
            repeat (4) @(negedge clk);
            while (b0 || b1) @(negedge clk);
            repeat (3) @(negedge clk);
        end
        repeat (40 + 2 * `VM_RT_M + `CR_RT_M) @(negedge clk);
        if (nq0 != nq1 || nw0 != nw1 || ne0 != ne1) begin errs = errs + 1; $display("COUNT q %0d/%0d w %0d/%0d e %0d/%0d", nq0, nq1, nw0, nw1, ne0, ne1); end
        for (i = 0; i < nq0 && i < nq1; i = i + 1) begin
            if (lq0[i] !== lq1[i]) begin errs = errs + 1; if (errs < 6) $display("RQ %0d differs", i); end
            if (tq1[i] - tq0[i] != 1 + rq0r[i] * DR) begin errs = errs + 1; if (errs < 6) $display("RQ %0d offset %0d row %0d", i, tq1[i] - tq0[i], rq0r[i]); end
            if (rq0r[i] > maxrow) maxrow = rq0r[i];
        end
        for (i = 0; i < nw0 && i < nw1; i = i + 1) begin
            // a killed write (zero byte mask: fault path) carries an unspecified payload; compare everything else
            if ((lw0[i][47:16] == 0 && lw1[i][47:16] == 0) ? ({lw0[i][339:304], lw0[i][47:0]} !== {lw1[i][339:304], lw1[i][47:0]}) : (lw0[i] !== lw1[i])) begin
                errs = errs + 1; if (errs < 6) $display("WRITE %0d differs", i); end
            if (tw1[i] - tw0[i] != 2 + (rw0r[i] + 1) * DR) begin errs = errs + 1; if (errs < 6) $display("WRITE %0d offset %0d row %0d", i, tw1[i] - tw0[i], rw0r[i]); end
        end
        for (i = 0; i < ne0 && i < ne1; i = i + 1) begin
            if (le0[i] !== le1[i]) begin errs = errs + 1; if (errs < 6) $display("EVENT %0d differs %b/%b", i, le0[i], le1[i]); end
            if (te1[i] - te0[i] != xe0[i]) begin errs = errs + 1; if (errs < 6) $display("EVENT %0d offset %0d expected %0d", i, te1[i] - te0[i], xe0[i]); end
            if (le0[i][1]) ndone = ndone + 1; else if (xe0[i] == 2) nill = nill + 1; else nflt = nflt + 1;
        end
        $display("TOPK_LAT VM_RT_M=%0d CR_RT_M=%0d VM_RT_P=%0d CR_RT_P=%0d AMMUT=%0d requests %0d writes %0d events %0d (done %0d fault %0d illegal %0d) max_row %0d share_fault %b/%b errors %0d",
                 `VM_RT_M, `CR_RT_M, `VM_RT_P, `CR_RT_P, `AMMUT, nq0, nw0, ne0, ndone, nflt, nill, maxrow, sf0, sf1, errs);
        if (errs == 0 && ndone > `NREC / 2 && nflt > 0 && nill > 0 && maxrow >= 3 && !sf0 && !sf1) $display("IDX_AM_TOPK_LAT PASS");
        else $display("IDX_AM_TOPK_LAT FAIL");
        $finish;
    end
endmodule
`default_nettype wire
