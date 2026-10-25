`timescale 1ns/1ps
// S81-L20DIE (10-19): self-checking bench of dsdv_idx_qf (query fan-out).  uid 3.  Sequence on the parent link ql:
// (1) a tree frame (type 10, NS 2: entries for uids 0..5) + 64 query words; (2) a non-tree frame (type 1, len 2) on the
// local source qs; (3) a tree frame whose spec table has no entry for uid 3.  Checks: qc0 never valid (S81/IDXNET 10-25:
// qc0 carries only tree frames from the local source qs, none here; qc1 is gone; dsdv_idx_qfs bench covers qc0); qr == [type-4 header with uid 3's spec, the frame's tag / user, len 64] in the
// cycle of the last spec word, then the 64 query words, END 3 edges after its pin edge; the type-1 frame unchanged on
// qr (3 edges); nothing on qr for frame (3); st fault bit 0, st no-entry bit 1.  Prints TB_QF PASS / FAIL.
module tb_dsdv_idx_qf;
    parameter integer MUT = 0;
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    reg  [512:0] qs = 0, ql = 0;
    wire [512:0] qr, qc0;
    wire [3:0] st;
    dsdv_idx_qf #(.MUT(MUT)) dut (.ck(ck), .rst(rst), .uid(8'd3), .qs(qs), .ql(ql), .qr(qr), .qc0(qc0), .st(st));
    integer cyc = 0, nerr = 0;
    reg [512:0] inw [int];               // word driven for edge e (either port)
    reg [512:0] expr [int];              // expected qr after edge e
    function automatic [106:0] spec_of(input integer u);
        spec_of = {u[7:0], 99'(64'h9E3779B97F4A7C15 * (u + 7))};
    endfunction
    function automatic [511:0] hdr(input [3:0] ty, input [7:0] tag, input [11:0] len, input [9:0] user, input [3:0] ns);
        hdr = 512'd0; hdr[511:508] = ty; hdr[502:495] = tag; hdr[491:480] = len; hdr[458:449] = user; hdr[3:0] = ns;
    endfunction
    function automatic [511:0] specw(input integer u0, input integer n, input integer skip);
        integer e; specw = 512'd0;
        for (e = 0; e < 4; e = e + 1) if (e < n && u0 + e != skip) begin
            specw[128 * e + 127] = 1'b1; specw[128 * e + 119 +: 8] = 8'(u0 + e); specw[128 * e +: 107] = spec_of(u0 + e);
        end
    endfunction
    always @(posedge ck) begin
        #0.1;
        if (rst) begin
            if (qc0[0] !== 1'b0) begin
                nerr++; if (nerr < 6) $display("TB_QF child mismatch cyc %0d got %h", cyc, qc0[16:0]);
            end
            // qr: valid bit every edge, data when valid (the chain ignores data bits of an idle word)
            if (qr[0] !== (expr.exists(cyc) ? 1'b1 : 1'b0) || (qr[0] && qr !== expr[cyc])) begin
                nerr++; if (nerr < 6) $display("TB_QF qr mismatch cyc %0d got v%0d %h exp v%0d", cyc, qr[0], qr[512:497],
                                                 expr.exists(cyc) ? expr[cyc][0] : 0);
            end
        end
        cyc++;
    end
    task automatic drive(input integer port, input [511:0] w, input bit to_r, input [511:0] rw);
        @(negedge ck);
        if (port == 0) begin ql = {w, 1'b1}; qs = 0; end else begin qs = {w, 1'b1}; ql = 0; end
        inw[cyc] = {w, 1'b1};
        if (to_r) expr[cyc + 2] = {rw, 1'b1};
    endtask
    task automatic idle(input integer n);
        repeat (n) begin @(negedge ck); ql = 0; qs = 0; end
    endtask
    initial begin : run
        reg [511:0] h, q, m;
        integer i;
        repeat (5) @(posedge ck); rst = 1; repeat (5) @(posedge ck);
        // (1) tree frame
        h = hdr(4'd10, 8'h31, 12'd66, 10'd5, 4'd2);
        drive(0, h, 0, 0);
        drive(0, specw(0, 4, -1), 0, 0);
        m = hdr(4'd4, 8'h31, 12'd64, 10'd5, 4'd0); m[106:0] = spec_of(3);
        drive(0, specw(4, 2, -1), 1, m);
        for (i = 0; i < 64; i = i + 1) begin q = {16{32'hC0DE_0000 + 32'(i)}}; drive(0, q, 1, q); end
        idle(4);
        // (2) a non-tree frame on the local source
        h = hdr(4'd1, 8'h07, 12'd2, 10'd1, 4'd0);
        drive(1, h, 1, h);
        for (i = 0; i < 2; i = i + 1) begin q = {16{32'hBEEF_0000 + 32'(i)}}; drive(1, q, 1, q); end
        idle(4);
        // (3) a tree frame without uid 3
        h = hdr(4'd10, 8'h32, 12'd66, 10'd5, 4'd2);
        drive(0, h, 0, 0);
        drive(0, specw(0, 4, 3), 0, 0);
        drive(0, specw(4, 2, -1), 0, 0);
        for (i = 0; i < 64; i = i + 1) begin q = {16{32'hF00D_0000 + 32'(i)}}; drive(0, q, 0, 0); end
        idle(10);
        if (st[0] !== 1'b0) begin nerr++; $display("TB_QF fault st %b", st); end
        if (st[3] !== 1'b1) begin nerr++; $display("TB_QF no-entry not flagged st %b", st); end
        $display("TB_QF_STATS nerr %0d st %b mut %0d", nerr, st, MUT);
        if (nerr) $display("TB_QF FAIL"); else $display("TB_QF PASS");
        $finish;
    end
endmodule
