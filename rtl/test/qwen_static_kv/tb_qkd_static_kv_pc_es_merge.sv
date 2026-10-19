`timescale 1ns/1ps
// KVJ-C (c) 2026-10-17: the per-PC es merge child qkd_static_kv_pc_es_merge against the existing models.
//   Four strapped identities (stack, pc) = (0,0) (1,7) (2,19) (3,31).  Each runs the merge child (strap endpoint) beside
//   the EXISTING qkd_embedding_static_pc #(STACK, PC) on the same issue / return / er inputs (reset one flop later =
//   the child's rsi pin capture).  A random compiled stream mixes static-writer words with embedding reads (code
//   halves and scale sectors homed on this PC, one outstanding, return slot with er valid 9..20 edges later).
//   Checks every edge: es(t+1) = wes(t) if the writer word is valid, else the reference endpoint's es(t); the beat /
//   corrected / outstanding / fault outputs equal the reference's; no fault on the legal stream; writer words and
//   embedding reads all reach es exactly once.
//   Negative windows (fault must latch, and the writer word must still win the register): writer + embedding on one
//   edge; a read homed on another PC (the reference faults too: lock-step).
// Mutants: -DOT_KVJ_ESM_MUT=1 (no conflict fault), 2 (strap check ignored), 3 (embedding wins a conflict) must FAIL.
// Prints "PASS kvjc es_merge ..." or "FAIL kvjc es_merge ...".
`ifndef OT_KVJ_ESM_MUT
`define OT_KVJ_ESM_MUT 0
`endif
module tb_esm_lane #(parameter integer ST = 0, parameter integer PCN = 0, parameter integer SEED = 1) (
    input  wire ck, input wire rst_n, input wire neg_conflict, input wire neg_home,
    output integer errors, output integer writes, output integer reads, output reg fault_seen, output reg done
);
    reg rst_q = 0;
    always @(posedge ck) rst_q <= rst_n;          // the child's rsi capture flop
    reg  [287:0] wes = 0;
    reg          iv = 0, hf = 0, sc = 0, rs = 0;
    reg  [17:0]  tk = 0;
    reg  [5:0]   wi = 0;
    reg  [15:0]  ep = 0;
    reg  [260:0] er = 0;
    wire [287:0] es, res;
    wire bv, rbv, bh, rbh, bs, rbs, co, rco, ou, rou, f, rf;
    wire [255:0] bd, rbd; wire [17:0] bt, rbt; wire [5:0] bw, rbw; wire [15:0] be, rbe;
    qkd_static_kv_pc_es_merge #(.MUT(`OT_KVJ_ESM_MUT)) dut (.ck(ck), .rst_n(rst_n), .pc(5'(PCN)), .cfg_stack(2'(ST)),
        .wes(wes), .emb_boot_ready(1'b1), .emb_issue_v(iv), .emb_token(tk), .emb_word_index(wi), .emb_half(hf),
        .emb_scale(sc), .emb_epoch(ep), .emb_return_slot(rs), .es(es), .er(er), .beat_v(bv), .beat_data(bd),
        .beat_token(bt), .beat_word(bw), .beat_half(bh), .beat_scale(bs), .beat_epoch(be), .corrected(co),
        .emb_outstanding(ou), .fault(f));
    qkd_embedding_static_pc #(.STACK(ST), .PC(PCN)) ref_ (.ck(ck), .rst_n(rst_q), .boot_ready(1'b1), .issue_v(iv),
        .token(tk), .word_index(wi), .half(hf), .scale(sc), .epoch(ep), .return_slot(rs), .es(res), .er(er),
        .beat_v(rbv), .beat_data(rbd), .beat_token(rbt), .beat_word(rbw), .beat_half(rbh), .beat_scale(rbs),
        .beat_epoch(rbe), .corrected(rco), .fault(rf), .outstanding(rou));
    // expected es one edge later
    reg [287:0] exp_es = 0; reg exp_ok = 0;
    integer seed = SEED, es_w = 0, es_r = 0, cyc = 0, k;
    initial begin errors = 0; writes = 0; reads = 0; fault_seen = 0; done = 0; end
    always @(posedge ck) begin
        if (rst_q && exp_ok) begin
            if (es[0] !== exp_es[0] || (exp_es[0] && es !== exp_es)) begin
                errors = errors + 1;
                if (errors < 4) $display("FAIL lane %0d/%0d cyc %0d es v %b/%b we %b/%b lo %h/%h", ST, PCN, cyc, es[0], exp_es[0],
                                         es[287], exp_es[287], es[64:1], exp_es[64:1]);
            end
            if (es[0] && es[287]) es_w = es_w + 1;
            if (es[0] && !es[287]) es_r = es_r + 1;
            if ({bv, bd, bt, bw, bh, bs, be, co, ou} !== {rbv, rbd, rbt, rbw, rbh, rbs, rbe, rco, rou} && rbv) begin
                errors = errors + 1; if (errors < 4) $display("FAIL lane %0d/%0d cyc %0d beat differs from qkd_embedding_static_pc", ST, PCN, cyc);
            end
            if ((f & ~dut.m_fault) !== rf) begin
                errors = errors + 1; if (errors < 4) $display("FAIL lane %0d/%0d cyc %0d endpoint fault %b vs reference %b", ST, PCN, cyc, f, rf);
            end
        end
        exp_es <= wes[0] ? wes : res; exp_ok <= rst_q;
        if (f) fault_seen <= 1'b1;
        cyc = cyc + 1;
    end
    // the read for this home: code (word {ST, PCN[4:1]}, half PCN[0}) or the scale sector s = {.., ST, PCN}
    task automatic home_read(input integer foreign);
        reg [13:0] s;
        begin
            sc = ($random(seed) & 3) == 0;
            if (sc) begin
                s = {7'(($random(seed) & 32'h7fffffff) % 74), 2'(ST), 5'(PCN)};           // s[13:7] < 74 keeps t < 151936
                tk = {s, 4'($random(seed))}; wi = 0; hf = 0;
            end else begin
                tk = 18'(($random(seed) & 32'h7fffffff) % 151936); wi = {2'(ST), 4'(PCN >> 1)}; hf = PCN[0];
            end
            if (foreign) wi = wi ^ 6'h10;
            if (foreign) sc = 0;
        end
    endtask
    integer n, gap, ret, i;
    task automatic one_read(input integer foreign, input integer with_write);
        begin
            @(negedge ck);
            home_read(foreign); ep = 16'($random(seed)); iv = 1;
            @(negedge ck); iv = 0; wes[0] = 0; reads = reads + 1;
            // conflict case: a writer word on the edge the endpoint's es word reaches the select
            if (with_write) begin wes = {2'b11, 29'($random(seed)), {8{$random(seed)}}, 1'b1}; writes = writes + 1; end
            ret = 9 + (($random(seed) & 32'h7fffffff) % 12);
            for (i = 0; i < ret; i = i + 1) begin
                @(negedge ck);
                // writer words in the idle edges between the issue and the return (disjoint compiled slots)
                if (($random(seed) & 1) == 0) begin wes = {2'b11, 29'($random(seed)), {8{$random(seed)}}, 1'b1}; writes = writes + 1; end
                else wes[0] = 0;
                if (i == ret - 1) begin rs = 1; er = {1'b0, 1'b0, 1'b0, (($random(seed) & 7) == 0), {8{$random(seed)}}, 1'b1}; end
            end
            @(negedge ck); wes[0] = 0; rs = 0; er[0] = 0;
        end
    endtask
    initial begin
        @(posedge rst_n); repeat (4) @(negedge ck);
        for (n = 0; n < 300; n = n + 1) begin
            one_read(0, 0);
            gap = $random(seed) & 3; repeat (gap) @(negedge ck);
        end
        repeat (4) @(negedge ck);
        if (fault_seen) begin errors = errors + 1; $display("FAIL lane %0d/%0d fault on the legal stream", ST, PCN); end
        if (es_w != writes || es_r != reads) begin errors = errors + 1; $display("FAIL lane %0d/%0d es counts w %0d/%0d r %0d/%0d", ST, PCN, es_w, writes, es_r, reads); end
        if (neg_conflict) one_read(0, 1);
        if (neg_home) one_read(1, 0);
        repeat (4) @(negedge ck);
        done = 1;
    end
endmodule

module tb_qkd_static_kv_pc_es_merge;
    reg ck = 0, rst_n = 0;
    always #0.4165 ck = ~ck;
    integer e [0:5], w [0:5], r [0:5];
    wire [5:0] fs, dn;
    // lanes 0..3: legal streams; lane 4: + conflict; lane 5: + foreign home
    tb_esm_lane #(0, 0, 11)  l0 (ck, rst_n, 1'b0, 1'b0, e[0], w[0], r[0], fs[0], dn[0]);
    tb_esm_lane #(1, 7, 12)  l1 (ck, rst_n, 1'b0, 1'b0, e[1], w[1], r[1], fs[1], dn[1]);
    tb_esm_lane #(2, 19, 13) l2 (ck, rst_n, 1'b0, 1'b0, e[2], w[2], r[2], fs[2], dn[2]);
    tb_esm_lane #(3, 31, 14) l3 (ck, rst_n, 1'b0, 1'b0, e[3], w[3], r[3], fs[3], dn[3]);
    tb_esm_lane #(1, 22, 15) l4 (ck, rst_n, 1'b1, 1'b0, e[4], w[4], r[4], fs[4], dn[4]);
    tb_esm_lane #(2, 5, 16)  l5 (ck, rst_n, 1'b0, 1'b1, e[5], w[5], r[5], fs[5], dn[5]);
    integer errors, i, tw, tr;
    initial begin
        repeat (5) @(negedge ck); rst_n = 1;
        wait (&dn);
        errors = 0; tw = 0; tr = 0;
        for (i = 0; i < 6; i = i + 1) begin errors = errors + e[i]; tw = tw + w[i]; tr = tr + r[i]; end
        if (|fs[3:0]) begin errors = errors + 1; $display("FAIL fault on a legal lane %b", fs[3:0]); end
        if (!fs[4]) begin errors = errors + 1; $display("FAIL conflict (writer + embedding on one edge) did not fault"); end
        if (!fs[5]) begin errors = errors + 1; $display("FAIL foreign-home read did not fault"); end
        if (errors == 0)
            $display("PASS kvjc es_merge lanes=6 writer_words=%0d emb_reads=%0d (es = registered slot select, endpoint lock-step = qkd_embedding_static_pc) negatives=2/2",
                     tw, tr);
        else $display("FAIL kvjc es_merge errors=%0d", errors);
        $finish;
    end
    initial begin #2000000; $display("FAIL kvjc es_merge timeout"); $finish; end
endmodule
