`timescale 1ns/1ps
// S81/IDXNET (2026-10-25, S81 DECISION 2): bench of dsdv_idx_qfs = dsdv_idx_qf + the 2-beat qc serializer (iqf partition).
// uid 3.  (1) a tree frame (type 10, NS 2, relay count 2 in d[7:4]) + 64 query words on the LOCAL source qs at 1 word / 2
// cycles (the root's own frame); (2) the same kind of frame on the parent link ql (a shard die's: never forwarded);
// (3) a non-tree frame (type 1) on qs (never forwarded); (4) two qs tree words back-to-back (a compile error).
// Checks, every edge: qc == beat 0 {w[256:1], 0, 1} of every qs tree word w exactly 3 edges after its pin edge and beat 1
// {w[512:257], 1, 1} 4 edges after, idle (v 0) otherwise through (1)-(3); qr == qf's IDX_S rewrite (frames 1 + 2) / the
// type-1 frame unchanged; fault[4] (serializer collision) 0 until (4), 1 after; fault[0] 0.  Prints TB_QFS PASS / FAIL.
// Negative controls (must FAIL): -GMUT=1 (qf: next uid's spec), -GSMUT=1 (beat 1 carries the low half),
// +define+DSDV_IDX_QF_MUT_FWDALL (qf forwards every word, the pre-IDXNET qc0).
module tb_dsdv_idx_qfs;
    parameter integer MUT = 0, SMUT = 0;
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    reg  [512:0] qs = 0, ql = 0;
    wire [512:0] qr; wire [257:0] qc; wire fault;
    dsdv_idx_qfs #(.MUT(MUT), .SMUT(SMUT)) dut (.ck(ck), .rst(rst), .qs(qs), .ql(ql), .qr(qr), .qc(qc), .fault(fault));
    integer cyc = 0, nerr = 0, nqc = 0, phase4 = 0;
    reg [257:0] expc [int];
    reg [512:0] expr [int];
    function automatic [106:0] spec_of(input integer u);
        spec_of = {u[7:0], 99'(64'h9E3779B97F4A7C15 * (u + 7))};
    endfunction
    function automatic [511:0] hdr(input [3:0] ty, input [7:0] tag, input [11:0] len, input [9:0] user, input [3:0] ns,
                                   input [3:0] rl);
        hdr = 512'd0; hdr[511:508] = ty; hdr[502:495] = tag; hdr[491:480] = len; hdr[458:449] = user; hdr[7:4] = rl; hdr[3:0] = ns;
    endfunction
    function automatic [511:0] specw(input integer u0, input integer n);
        integer e; specw = 512'd0;
        for (e = 0; e < 4; e = e + 1) if (e < n) begin
            specw[128 * e + 127] = 1'b1; specw[128 * e + 119 +: 8] = 8'(u0 + e); specw[128 * e +: 107] = spec_of(u0 + e);
        end
    endfunction
    always @(posedge ck) begin
        #0.1;
        if (rst && !phase4) begin
            if (qc[0] !== (expc.exists(cyc) ? 1'b1 : 1'b0) || (qc[0] && qc !== expc[cyc])) begin
                nerr++; if (nerr < 8) $display("TB_QFS qc mismatch cyc %0d got v%0d b%0d %h", cyc, qc[0], qc[1], qc[257:226]);
            end
            if (qc[0]) nqc++;
            if (qr[0] !== (expr.exists(cyc) ? 1'b1 : 1'b0) || (qr[0] && qr !== expr[cyc])) begin
                nerr++; if (nerr < 8) $display("TB_QFS qr mismatch cyc %0d got v%0d %h", cyc, qr[0], qr[512:497]);
            end
        end
        cyc++;
    end
    // drive word w on port (0 ql, 1 qs) for the next edge e = cyc; fwd: expect it on qc at e+3 / e+4; to_r: qr at e+2
    task automatic drive(input integer port, input [511:0] w, input bit fwd, input bit to_r, input [511:0] rw);
        reg [512:0] x;
        @(negedge ck);
        x = {w, 1'b1};
        if (port == 0) begin ql = x; qs = 0; end else begin qs = x; ql = 0; end
        if (fwd) begin expc[cyc + 3] = {x[256:1], 1'b0, 1'b1}; expc[cyc + 4] = {x[512:257], 1'b1, 1'b1}; end
        if (to_r) expr[cyc + 2] = {rw, 1'b1};
    endtask
    task automatic idle(input integer n);
        repeat (n) begin @(negedge ck); ql = 0; qs = 0; end
    endtask
    task automatic frame(input integer port, input [7:0] tag, input bit fwd, input bit pace);
        reg [511:0] h, q, m; integer i;
        h = hdr(4'd10, tag, 12'd66, 10'd5, 4'd2, 4'd2);
        drive(port, h, fwd, 0, 0); if (pace) idle(1);
        drive(port, specw(0, 4), fwd, 0, 0); if (pace) idle(1);
        m = hdr(4'd4, tag, 12'd64, 10'd5, 4'd0, 4'd0); m[106:0] = spec_of(3);
        drive(port, specw(4, 2), fwd, 1, m); if (pace) idle(1);
        for (i = 0; i < 64; i = i + 1) begin
            q = {16{32'hC0DE_0000 + 32'(i) + {tag, 16'd0}}}; drive(port, q, fwd, 1, q); if (pace) idle(1);
        end
    endtask
    initial begin : run
        reg [511:0] h, q;
        integer i;
        repeat (5) @(posedge ck); rst = 1; repeat (5) @(posedge ck);
        h = 512'd0; h[511:508] = 4'd11; h[7:0] = 8'd3;
        drive(1, h, 0, 0, 0); idle(3); // boot uid, consumed locally
        frame(1, 8'h31, 1, 1);          // (1) root: qs, paced, forwarded 2-beat
        idle(6);
        frame(0, 8'h32, 0, 0);          // (2) shard: ql, back-to-back, never forwarded
        idle(6);
        h = hdr(4'd1, 8'h07, 12'd2, 10'd1, 4'd0, 4'd0);   // (3) non-tree frame on qs: qr only
        drive(1, h, 0, 1, h);
        for (i = 0; i < 2; i = i + 1) begin q = {16{32'hBEEF_0000 + 32'(i)}}; drive(1, q, 0, 1, q); end
        idle(8);
        if (fault !== 1'b0) begin nerr++; $display("TB_QFS early fault fault %b", fault); end
        $display("TB_QFS_STATS main nerr %0d qc beats %0d (exp %0d) fault %b", nerr, nqc, 2 * 67, fault);
        if (nqc != 2 * 67) nerr++;
        phase4 = 1;                     // (4) two qs tree words back-to-back -> serializer collision fault
        h = hdr(4'd10, 8'h33, 12'd66, 10'd5, 4'd2, 4'd0);
        drive(1, h, 0, 0, 0); drive(1, specw(0, 4), 0, 0, 0);
        idle(10);
        if (fault !== 1'b1) begin nerr++; $display("TB_QFS collision not flagged fault %b", fault); end
        $display("TB_QFS_STATS nerr %0d fault %b mut %0d smut %0d", nerr, fault, MUT, SMUT);
        if (nerr) $display("TB_QFS FAIL"); else $display("TB_QFS PASS");
        $finish;
    end
endmodule
