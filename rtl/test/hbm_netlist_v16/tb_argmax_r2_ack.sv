`timescale 1ns/1ps
`default_nettype none
// HBM-BIND B2 (2026-10-24): ot_hbm_argmax_static_sw_vm_r2 ACK beyond the 6-bit counter (CNTW). Two r2 engines, each
// with the real ot_hbm_idx_vm_share_static_am merge chain and its own VM / record-client model (copied from
// tb_argmax_sw_vm_r2.sv): engine 0 = default (ACK 13, CNTW 6: the closed as-built form), engine 1 = ACK 13+XA with its
// client acks XA edges later (the B2 hub echo over the two-stop ring). Same record stream, serialised (both idle before
// the next go). Every VM request and every client write (payload + cq_seq) must match IN ORDER at offset 0; every
// done/fault (+ nan_flag) event must match in order at offset XA (records that fault at E_CHK: offset 0). Garbled
// records (missing bank valid / missing ack / STREAM) must give the same outcome. CMUT 1: engine 1 forced to CNTW 6.
module tb_argmax_r2_ack;
`ifndef NREC
`define NREC 300
`endif
`ifndef XA
`define XA 98
`endif
`ifndef CMUT
`define CMUT 0
`endif
    localparam integer RD = 7, ACKD = 11;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg go = 0, mode = 0, a_mirror = 0; reg [17:0] imm_a = 0, a_base = 0, n = 0, o_base = 0; reg [15:0] o_is = 0;
    reg drop_rr = 0, drop_ack = 0;
    // ---------------- engine 0: r2 default (ACK 13)
    reg [2055:0] rr0 = 0; reg [273:0] cr0 = 0;
    wire [135:0] rq0, rqs0; wire [263:0] am0; wire [337:0] cq0; wire [1:0] s0; wire b0, d0, f0, n0, sf0;
    wire [2055:0] unused_i0, unused_t0;
    ot_hbm_idx_vm_share_static_am share0(.clk_pair({4{clk}}), .rst_n(rst_n), .index_rq(136'd0), .topk_rq(136'd0),
        .argmax_rq(rq0), .vm_rq(rqs0), .vm_rr(rr0), .index_rr(unused_i0), .topk_rr(unused_t0), .argmax_m(am0), .fault(sf0));
    ot_hbm_argmax_static_sw_vm_r2 #(.TP(192)) e0(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(go), .mode(mode), .imm_a(imm_a),
        .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq0), .vm_rr(am0),
        .cq(cq0), .cq_seq(s0), .cr(cr0), .busy(b0), .done(d0), .fault(f0), .nan_flag(n0));
    // ---------------- engine 1: r2 ACK 13+XA (CNTW auto; CMUT 1 forces 6)
    reg [2055:0] bank1 = 0; reg [273:0] cr1 = 0;
    wire [135:0] rq1, rqs; wire [263:0] am; wire [337:0] cq1; wire [1:0] s1; wire b1, d1, f1, n1, sf;
    wire [2055:0] unused_i, unused_t;
    ot_hbm_idx_vm_share_static_am share(.clk_pair({4{clk}}), .rst_n(rst_n), .index_rq(136'd0), .topk_rq(136'd0),
        .argmax_rq(rq1), .vm_rq(rqs), .vm_rr(bank1), .index_rr(unused_i), .topk_rr(unused_t), .argmax_m(am), .fault(sf));
    ot_hbm_argmax_static_sw_vm_r2 #(.TP(192), .ACK(13 + `XA), .CNTW((`CMUT == 1) ? 6 : ((13 + `XA > 62) ? 8 : 6))) e1(.clk(clk), .rst_n(rst_n), .die_id(8'd3), .go(go), .mode(mode),
        .imm_a(imm_a), .a_mirror(a_mirror), .a_base(a_base), .n(n), .o_base(o_base), .o_is(o_is), .vm_rq(rq1),
        .vm_rr(am), .cq(cq1), .cq_seq(s1), .cr(cr1), .busy(b1), .done(d1), .fault(f1), .nan_flag(n1));
    // ---------------- VM + client models (same function for both sides)
    function automatic [255:0] sdat(input [15:0] q, input integer l);
        integer k; reg [31:0] h; begin
            for (k = 0; k < 8; k = k + 1) begin h = {q, 3'(l), 3'(k)} * 32'h9E3779B1 ^ 32'h5bd1e995; sdat[32*k +: 32] = h & 32'hBFFF_FFFF; end
        end endfunction
    reg [16:0] p0 [0:31][0:7]; reg [16:0] p1 [0:31][0:7]; reg [16:0] c0 [0:255]; reg [16:0] c1 [0:255]; integer t, k;
    initial for (t = 0; t < 256; t = t + 1) begin c0[t] = 0; c1[t] = 0; if (t < 32) for (k = 0; k < 8; k = k + 1) begin p0[t][k] = 0; p1[t][k] = 0; end end
    always @(posedge clk) begin
        for (t = 255; t > 0; t = t - 1) begin c0[t] <= c0[t-1]; c1[t] <= c1[t-1]; if (t < 32) for (k = 0; k < 8; k = k + 1) begin p0[t][k] <= p0[t-1][k]; p1[t][k] <= p1[t-1][k]; end end
        for (k = 0; k < 8; k = k + 1) begin p0[0][k] <= {rqs0[17*k+16], rqs0[17*k +: 16]}; p1[0][k] <= {rqs[17*k+16], rqs[17*k +: 16]}; end
        c0[0] <= {cq0[337], cq0[15:0]}; c1[0] <= {cq1[337], cq1[15:0]};
    end
    always @(negedge clk) begin
        for (k = 0; k < 8; k = k + 1) begin
            rr0[257*k +: 256] = sdat(p0[RD-1][k][15:0], k); rr0[257*k+256] = p0[RD-1][k][16] && !drop_rr;
            bank1[257*k +: 256] = sdat(p1[RD-1][k][15:0], k); bank1[257*k+256] = p1[RD-1][k][16] && !drop_rr;
        end
        cr0 = 0; cr0[273] = c0[ACKD-1][16] && !drop_ack; cr0[272:257] = c0[ACKD-1][15:0]; cr0[256] = c0[ACKD-1][16];
        cr1 = 0; cr1[273] = c1[ACKD+`XA-1][16] && !drop_ack; cr1[272:257] = c1[ACKD+`XA-1][15:0]; cr1[256] = c1[ACKD+`XA-1][16];
    end
    // ---------------- transaction logs
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [400:0] lq0 [0:65535]; reg [400:0] lq1 [0:65535]; integer tq0 [0:65535]; integer tq1 [0:65535]; integer nq0 = 0, nq1 = 0;
    reg [400:0] lw0 [0:8191]; reg [400:0] lw1 [0:8191]; integer tw0 [0:8191]; integer tw1 [0:8191]; integer nw0 = 0, nw1 = 0;
    reg [2:0] le0 [0:4095]; reg [2:0] le1 [0:4095]; integer te0 [0:4095]; integer te1 [0:4095]; integer ne0 = 0, ne1 = 0;
    always @(posedge clk) if (rst_n) begin
        for (k = 0; k < 8; k = k + 1) begin
            if (rq0[17*k+16]) begin lq0[nq0] = {k[2:0], rq0[17*k +: 16]}; tq0[nq0] = cyc; nq0 = nq0 + 1; end
            if (rq1[17*k+16]) begin lq1[nq1] = {k[2:0], rq1[17*k +: 16]}; tq1[nq1] = cyc; nq1 = nq1 + 1; end
        end
        if (cq0[337]) begin lw0[nw0] = {s0, cq0}; tw0[nw0] = cyc; nw0 = nw0 + 1; end
        if (cq1[337]) begin lw1[nw1] = {s1, cq1}; tw1[nw1] = cyc; nw1 = nw1 + 1; end
        if (d0 || f0) begin le0[ne0] = {d0, f0, n0}; te0[ne0] = cyc; ne0 = ne0 + 1; end
        if (d1 || f1) begin le1[ne1] = {d1, f1, n1}; te1[ne1] = cyc; ne1 = ne1 + 1; end
    end
    integer w, errs = 0, oq = -999, ow = -999, oe = -999, nrec_vm = 0, ndone = 0, i;
    task automatic rec(input m);
        begin
            @(negedge clk);
            mode = m; imm_a = $urandom % 40000; a_mirror = $urandom % 2; n = 1 + $urandom % 200;
            a_base = {(($urandom % 8) == 0) ? 2'd1 : 2'd0, 16'($urandom)}; o_base = {2'd0, 16'($urandom % 60000)};
            o_is = $urandom % 64; go = 1;
            @(negedge clk) go = 0;
        end
    endtask
    initial begin
        repeat (6) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        for (w = 0; w < `NREC; w = w + 1) begin
            drop_rr = ($urandom % 12) == 0; drop_ack = !drop_rr && ($urandom % 12) == 0;
            rec(($urandom % 8) == 0);
            repeat (3) @(negedge clk);
            while (b0 || b1) @(negedge clk);
            repeat (2) @(negedge clk);
        end
        repeat (40) @(negedge clk);
        if (nq0 != nq1 || nw0 != nw1 || ne0 != ne1) begin errs = errs + 1; $display("COUNT q %0d/%0d w %0d/%0d e %0d/%0d", nq0, nq1, nw0, nw1, ne0, ne1); end
        for (i = 0; i < nq0 && i < nq1; i = i + 1) begin
            if (lq0[i] !== lq1[i]) begin errs = errs + 1; if (errs < 5) $display("RQ %0d differs", i); end
            if (oq == -999) oq = tq1[i] - tq0[i]; else if (tq1[i] - tq0[i] != oq) begin errs = errs + 1; if (errs < 5) $display("RQ offset %0d", i); end
        end
        for (i = 0; i < nw0 && i < nw1; i = i + 1) begin
            // a killed write (zero byte mask: fault path) carries an unspecified payload; compare everything else
            if ((lw0[i][47:16] == 0 && lw1[i][47:16] == 0) ? ({lw0[i][339:304], lw0[i][47:0]} !== {lw1[i][339:304], lw1[i][47:0]}) : (lw0[i] !== lw1[i])) begin
                errs = errs + 1; if (errs < 5) $display("WRITE %0d differs mask %h/%h", i, lw0[i][47:16], lw1[i][47:16]); end
            if (ow == -999) ow = tw1[i] - tw0[i]; else if (tw1[i] - tw0[i] != ow) begin errs = errs + 1; if (errs < 5) $display("WRITE offset %0d", i); end
        end
        for (i = 0; i < ne0 && i < ne1; i = i + 1) begin
            if (le0[i] !== le1[i]) begin errs = errs + 1; if (errs < 5) $display("EVENT %0d differs %b/%b", i, le0[i], le1[i]); end
            if (le0[i][2]) ndone = ndone + 1;
            // an illegal record (incl. every STREAM record) faults at E_CHK: only the go pin register (+1) applies
            if (le0[i][1] && !le0[i][2] && te1[i] - te0[i] == 0) ;
            else if (oe == -999) oe = te1[i] - te0[i]; else if (te1[i] - te0[i] != oe) begin errs = errs + 1; if (errs < 5) $display("EVENT offset %0d", i); end
        end
        if (nq0 > 0 && oq != 0) begin errs = errs + 1; $display("RQ offset %0d != 0", oq); end
        if (nw0 > 0 && ow != 0) begin errs = errs + 1; $display("WRITE offset %0d != 0", ow); end
        if (oe != -999 && oe != `XA) begin errs = errs + 1; $display("EVENT offset %0d != XA %0d", oe, `XA); end
        $display("requests %0d writes %0d events %0d (done %0d) offsets rq %0d write %0d event %0d share_fault %b%b errors %0d",
                 nq0, nw0, ne0, ndone, oq, ow, oe, sf0, sf, errs);
        if (errs == 0 && ndone > `NREC / 3 && nw0 > 0) $display("ARGMAX_R2_ACK PASS XA=%0d CMUT=%0d", `XA, `CMUT); else $display("ARGMAX_R2_ACK FAIL XA=%0d CMUT=%0d", `XA, `CMUT);
        $finish;
    end
endmodule
`default_nettype wire
