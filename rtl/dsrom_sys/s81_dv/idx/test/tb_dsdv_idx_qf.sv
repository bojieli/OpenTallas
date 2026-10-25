`timescale 1ns/1ps
// S81-L20DIE (10-19): self-checking bench of dsdv_idx_qf (query fan-out).  uid 3.  Sequence on the parent link ql:
// (1) a tree frame (type 10, NS 2: entries for uids 0..5) + 64 query words; (2) a non-tree frame (type 1, len 2) on the
// local source qs; (3) a tree frame whose spec table has no entry for uid 3.  Checks: qc0 / qc1 == the input words
// delayed exactly 3 edges (every word); qr == [type-4 header with uid 3's spec, the frame's tag / user, len 64] in the
// cycle of the last spec word, then the 64 query words, END 3 edges after its pin edge; the type-1 frame unchanged on
// qr (3 edges); nothing on qr for frame (3); no fault before (3), fault after (3) (no entry).  Prints TB_QF PASS / FAIL.
// S81/PORTFIX-CFG 10-25: the uid is no longer a strap: (0) a CONFIG frame (type 11, len 0, uid 3) on qs first -- it must
// be consumed (nothing on qr / qc0 / qc1 for it); the frames (1)..(3) then behave exactly as with the old uid 3 strap.
// (4) a second CONFIG frame (uid 5) + a tree frame: the die now takes uid 5's entry.  (5) after a new reset, a tree
// frame with no CONFIG frame: fault (and the uid register is 0 again).  fault = OR of the former st conditions.
// The s_3S band-B splitter dsdv_idx_bsplit routes type 11 to the index chain (o_i), a svc frame (type 12) to o_s.
// Mutants (must FAIL): MUT 1 next uid's entry, 2 slice-15 qs mask, 3 config frame leaks to qr / qc, 4 uid nibbles swapped
// at the load, 5 no-entry dropped from the fault fold; BS_MUT 2 type 11 stays on the svc output.
module tb_dsdv_idx_qf;
    parameter integer MUT = 0;
    parameter integer BS_MUT = 0;
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    reg  [512:0] qs = 0, ql = 0;
    wire [512:0] qr, qc0, qc1;
    wire fault;
    dsdv_idx_qf #(.MUT(MUT)) dut (.ck(ck), .rst(rst), .qs(qs), .ql(ql), .qr(qr), .qc0(qc0), .qc1(qc1), .fault(fault));
    integer cyc = 0, nerr = 0;
    reg [512:0] inw [int];               // word driven for edge e (either port) that the children must see
    reg [512:0] expr [int];              // expected qr after edge e
    function automatic [106:0] spec_of(input integer u);
        spec_of = {u[7:0], 99'(64'h9E3779B97F4A7C15 * (u + 7))};
    endfunction
    function automatic [511:0] hdr(input [3:0] ty, input [7:0] tag, input [11:0] len, input [9:0] user, input [3:0] ns);
        hdr = 512'd0; hdr[511:508] = ty; hdr[502:495] = tag; hdr[491:480] = len; hdr[458:449] = user; hdr[3:0] = ns;
    endfunction
    function automatic [511:0] cfgw(input [7:0] u);
        cfgw = 512'd0; cfgw[511:508] = 4'd11; cfgw[7:0] = u;
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
            // children: valid bit every edge, data when valid (a consumed CONFIG word leaves an idle slot whose data
            // bits are not cleared: valid-qualified, like qr)
            if (qc0[0] !== inw.exists(cyc - 2) || (qc0[0] && qc0 !== inw[cyc - 2]) || qc1 !== qc0) begin
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
    // fwd = the children see the word (every word but a CONFIG frame word)
    task automatic drive_f(input integer port, input [511:0] w, input bit fwd, input bit to_r, input [511:0] rw);
        @(negedge ck);
        if (port == 0) begin ql = {w, 1'b1}; qs = 0; end else begin qs = {w, 1'b1}; ql = 0; end
        if (fwd) inw[cyc] = {w, 1'b1};
        if (to_r) expr[cyc + 2] = {rw, 1'b1};
    endtask
    task automatic drive(input integer port, input [511:0] w, input bit to_r, input [511:0] rw);
        drive_f(port, w, 1'b1, to_r, rw);
    endtask
    task automatic idle(input integer n);
        repeat (n) begin @(negedge ck); ql = 0; qs = 0; end
    endtask
    task automatic tree(input [7:0] tag, input integer me, input integer skip, input bit hit);
        reg [511:0] h, q, m; integer i;
        h = hdr(4'd10, tag, 12'd66, 10'd5, 4'd2);
        drive(0, h, 0, 0);
        drive(0, specw(0, 4, skip), 0, 0);
        m = hdr(4'd4, tag, 12'd64, 10'd5, 4'd0); m[106:0] = spec_of(me);
        drive(0, specw(4, 2, skip), hit, m);
        for (i = 0; i < 64; i = i + 1) begin q = {16{32'hC0DE_0000 + 32'(i) + 32'(tag) * 256}}; drive(0, q, hit, q); end
    endtask
    // ---- dsdv_idx_bsplit (s_3S band B -> iq / svc q): type 11 must take the index route
    reg  [512:0] bi = 0; wire [512:0] bo_s, bo_i; integer bs_i = 0, bs_s = 0, bs_err = 0;
    dsdv_idx_bsplit #(.BW(513), .MUT(BS_MUT)) u_bs (.ck(ck), .rst_n(rst), .i(bi), .o_s(bo_s), .o_i(bo_i));
    always @(posedge ck) begin
        if (bo_i[0]) begin bs_i++; if (bo_i[512:509] == 4'd12) bs_err++; end
        if (bo_s[0]) begin bs_s++; if (bo_s[512:509] == 4'd11) bs_err++; end
    end
    initial begin : run
        reg [511:0] h, q;
        integer i;
        repeat (5) @(posedge ck); rst = 1; repeat (5) @(posedge ck);
        // (0) CONFIG frame: uid 3 (consumed: no qr, no child word)
        drive_f(1, cfgw(8'd3), 1'b0, 1'b0, 0);
        idle(3);
        // (1) tree frame
        tree(8'h31, 3, -1, 1'b1);
        idle(4);
        // (2) a non-tree frame on the local source
        h = hdr(4'd1, 8'h07, 12'd2, 10'd1, 4'd0);
        drive(1, h, 1, h);
        for (i = 0; i < 2; i = i + 1) begin q = {16{32'hBEEF_0000 + 32'(i)}}; drive(1, q, 1, q); end
        idle(4);
        if (fault !== 1'b0) begin nerr++; $display("TB_QF fault before frame (3)"); end
        // (3) a tree frame without uid 3
        tree(8'h32, 3, 3, 1'b0);
        idle(10);
        if (fault !== 1'b1) begin nerr++; $display("TB_QF no-entry not flagged"); end
        // (4) re-config to uid 5, tree frame: uid 5's entry
        drive_f(1, cfgw(8'd5), 1'b0, 1'b0, 0);
        idle(3);
        tree(8'h33, 5, -1, 1'b1);
        idle(10);
        // (5) reset, tree frame without a CONFIG frame: fault; uid register back to 0 (die uid 0 takes entry 0)
        @(negedge ck); rst = 0; repeat (3) @(negedge ck); rst = 1; repeat (5) @(negedge ck);
        if (fault !== 1'b0) begin nerr++; $display("TB_QF fault not cleared by reset"); end
        tree(8'h34, 0, -1, 1'b1);
        idle(10);
        if (fault !== 1'b1) begin nerr++; $display("TB_QF tree frame before config not flagged"); end
        // bsplit: a CONFIG frame and a svc frame (type 12, len 1)
        @(negedge ck); bi = {cfgw(8'd9), 1'b1};
        @(negedge ck); bi = {hdr(4'd12, 8'h01, 12'd1, 10'd0, 4'd0), 1'b1};
        @(negedge ck); bi = {512'h1234, 1'b1};
        @(negedge ck); bi = 0; idle(4);
        if (bs_i != 1 || bs_s != 2 || bs_err != 0) begin nerr++; $display("TB_QF bsplit route i %0d s %0d err %0d", bs_i, bs_s, bs_err); end
        $display("TB_QF_STATS nerr %0d fault %b mut %0d bs_mut %0d", nerr, fault, MUT, BS_MUT);
        if (nerr) $display("TB_QF FAIL"); else $display("TB_QF PASS");
        $finish;
    end
endmodule
