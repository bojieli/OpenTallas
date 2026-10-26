`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// tb_s81_draft_head (s81-functional-token r3, 2026-10-14): one DSpark DRAFT row's head on RTL (+D=<row>):
//   lm_head roots of the row (golden field partials, tools/s81_ftok/draft_head.py) -> ot_s81_native_head_tp4
//   (OPT_NATIVE_HEAD 1; its per-row RTL join root4096 + ((root1024 + 0) + 0) gives the head logit stream of each rank)
//   -> per rank NI production Markov row engines ot_dsrom_markov_row (row v on engine v mod NI; the dot of the
//   released markov_head row v with the embedding of d_i, K 256 BF16, joined to the head logit by the separate add)
//   -> per rank ot_rom_argmax_reduce over the joined logits in row order, ranks chained 0 -> 3 (lowest id on ties)
//   -> d_{i+1}.  The native terminal's own (head-only) argmax runs and is not used.
// CHECKS: every head logit (tp4 logit stream) = the golden draft head logit is implied by the joined check; every
// joined logit = the golden final logit of its row; final record = the golden d_{i+1} and its bits; no fault anywhere.
// MUT 1: ot_dsrom_markov_row MUTANT_FOLD 1 (its designed negative control) -> FAIL.
// Plusargs: +DIR=<work dir> +D=<draft row>.
// ---------------------------------------------------------------------------------------------------------------------
import ot_rom_coll_pkg::*;
module tb_s81_draft_head;
    parameter integer MUT = 0, ROWS = 32320, NI = 32, VOCAB = 4 * ROWS;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    // ---------------- head terminal of the four ranks
    reg [3:0] start = 0;
    wire [3:0] ready, in_ready, logit_valid, logit_poison, rank_fault;
    reg  [3:0] in_valid = 0; reg [4*17-1:0] in_row = 0; reg [4*32-1:0] r4096 = 0, r1024 = 0;
    wire [4*17-1:0] logit_row; wire [4*32-1:0] logit_bits; wire [4*47-1:0] logit_owner;
    wire [3:0] logit_ready;
    wire res_v, hfault; wire [31:0] hid, hbits; wire [46:0] hown; wire [63:0] hseq;
    localparam [46:0] OWN = 47'h0123456789ab;
    localparam [63:0] SEQ = 64'd1048576;
    ot_s81_native_head_tp4 #(.OPT_NATIVE_HEAD(1), .ROWS(ROWS)) u_head (
        .clk(clk), .rst_n(rst_n), .start(start), .cancel(4'd0), .start_owner({4{OWN}}), .start_sequence({4{SEQ}}),
        .ready(ready), .in_valid(in_valid), .in_ready(in_ready), .in_owner({4{OWN}}), .in_sequence({4{SEQ}}),
        .in_row(in_row), .root4096(r4096), .root1024(r1024),
        .logit_valid(logit_valid), .logit_ready(logit_ready), .logit_owner(logit_owner), .logit_row(logit_row),
        .logit_bits(logit_bits), .logit_poison(logit_poison),
        .result_valid(res_v), .result_ready(1'b1), .result_global_id(hid), .result_bits(hbits),
        .result_owner(hown), .result_sequence(hseq), .rank_fault(rank_fault), .fault(hfault));
    // ---------------- data
    reg [63:0]  roots [0:3][0:ROWS-1];
    reg [31:0]  gl    [0:3][0:ROWS-1];
    reg [255:0] mw [0:VOCAB*16-1];
    reg [255:0] mx [0:15];
    reg [31:0]  ex [0:1];
    reg [63:0]  tr [0:ROWS-1]; reg [31:0] tl [0:ROWS-1];
    string dir; integer D, r, k;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        if (!$value$plusargs("D=%d", D)) $fatal(1, "+D");
        for (r = 0; r < 4; r = r + 1) begin
            $readmemh($sformatf("%s/roots_d%0d_r%0d.mem", dir, D, r), tr);
            $readmemh($sformatf("%s/logits_d%0d_r%0d.mem", dir, D, r), tl);
            for (k = 0; k < ROWS; k = k + 1) begin roots[r][k] = tr[k]; gl[r][k] = tl[k]; end
        end
        $readmemh({dir, "/mk_w.hex"}, mw);
        $readmemh($sformatf("%s/mk_x_d%0d.hex", dir, D), mx);
        $readmemh($sformatf("%s/expect_d%0d.mem", dir, D), ex);
    end
    // root feeders (one row a cycle per rank while in_ready)
    integer sent [0:3];
    initial for (k = 0; k < 4; k = k + 1) sent[k] = 0;
    always @(posedge clk) if (rst_n) for (k = 0; k < 4; k = k + 1) begin
        if (in_valid[k] && in_ready[k]) sent[k] = sent[k] + 1;
        if (sent[k] < ROWS) begin
            in_valid[k] <= 1'b1; in_row[17 * k +: 17] <= 17'(k * ROWS + sent[k]);
            r4096[32 * k +: 32] <= roots[k][sent[k]][63:32]; r1024[32 * k +: 32] <= roots[k][sent[k]][31:0];
        end else in_valid[k] <= 1'b0;
    end
    // ---------------- Markov row engines, NI a rank; row v (rank-local) on engine v mod NI
    reg  [31:0] jl [0:3][0:ROWS-1];
    reg         jv [0:3][0:ROWS-1];
    integer bad = 0, poison = 0, mk_fault = 0;
    genvar gr, gi;
    generate for (gr = 0; gr < 4; gr = gr + 1) begin : g_r
        wire [16:0] lrow = logit_row[17 * gr +: 17] - 17'(gr * ROWS);
        wire [NI-1:0] idle;
        assign logit_ready[gr] = idle[lrow % NI];
        for (gi = 0; gi < NI; gi = gi + 1) begin : g_i
            reg st_go = 0, iv = 0, ordy = 0; reg [31:0] head = 0; reg [255:0] w = 0, x = 0;
            reg [1:0] ph = 0; reg [4:0] beat = 0; reg [16:0] row = 0;
            wire sr, ir, ov, fl; wire [31:0] ob;
            ot_dsrom_markov_row #(.MUTANT_FOLD(MUT == 1 ? 1 : 0)) u_mk (.clk(clk), .rst_n(rst_n), .start(st_go),
                .start_ready(sr), .head_logit(head), .in_valid(iv), .in_ready(ir), .weight_bf16(w), .embed_bf16(x),
                .out_valid(ov), .out_ready(ordy), .out_bits(ob), .fault(fl));
            assign idle[gi] = (ph == 0);
            always @(posedge clk) begin
                ordy <= 1'b0;
                case (ph)
                    0: if (logit_valid[gr] && logit_ready[gr] && (lrow % NI) == gi) begin
                           head <= logit_bits[32 * gr +: 32]; row <= lrow; ph <= 1; st_go <= 1'b1;
                           if (logit_poison[gr]) poison = poison + 1;
                       end
                    1: if (st_go && sr) begin st_go <= 1'b0; ph <= 2; beat <= 0;
                           iv <= 1'b1; w <= mw[(gr * ROWS + row) * 16]; x <= mx[0]; end
                    2: if (iv && ir) begin
                           if (beat == 15) begin iv <= 1'b0; ph <= 3; end
                           else begin beat <= beat + 1; w <= mw[(gr * ROWS + row) * 16 + beat + 1]; x <= mx[beat + 1]; end
                       end
                    3: if (ov && !ordy) begin
                           jl[gr][row] = ob; jv[gr][row] = 1'b1; ordy <= 1'b1; ph <= 0;
                           if (ob !== gl[gr][row]) begin bad = bad + 1; if (bad < 6) $display("ERR rank %0d row %0d joined %h golden %h", gr, row, ob, gl[gr][row]); end
                       end
                endcase
                if (fl) mk_fault = mk_fault + 1;
            end
        end
    end endgenerate
    // ---------------- per-rank argmax over the joined logits in row order, ranks chained
    wire [3:0] lg_ready, up_ready, dn_valid, dn_last, am_fault;
    wire [4*512-1:0] dn_data;
    wire [4*32-1:0] tok_out;
    reg  [3:0] lg_valid = 0; reg [4*32-1:0] lg_bits = 0; reg [4*32-1:0] lg_base = 0; reg [3:0] lg_last = 0;
    wire [3:0] dn_ready;
    integer nxt [0:3];
    initial for (k = 0; k < 4; k = k + 1) nxt[k] = 0;
    generate for (gr = 0; gr < 4; gr = gr + 1) begin : g_am
        ot_rom_argmax_reduce #(.LANES(16), .DEPTH(8), .FIRST(gr == 0), .SELF(gr), .NEXT(gr + 1)) u_am (
            .clk(clk), .rst_n(rst_n), .lg_valid(lg_valid[gr]), .lg_ready(lg_ready[gr]),
            .lg_data({480'd0, lg_bits[32 * gr +: 32]}), .lg_mask(16'd1), .lg_base(lg_base[32 * gr +: 32]), .lg_tag(8'd0),
            .lg_last(lg_last[gr]),
            .up_valid(gr == 0 ? 1'b0 : dn_valid[gr == 0 ? 0 : gr - 1]), .up_ready(up_ready[gr]),
            .up_data(gr == 0 ? 512'd0 : dn_data[(gr == 0 ? 0 : gr - 1) * 512 +: 512]),
            .up_last(gr == 0 ? 1'b0 : dn_last[gr == 0 ? 0 : gr - 1]),
            .dn_valid(dn_valid[gr]), .dn_ready(dn_ready[gr]), .dn_data(dn_data[512 * gr +: 512]), .dn_last(dn_last[gr]),
            .tokens_out(tok_out[32 * gr +: 32]), .fault(am_fault[gr]));
        if (gr < 3) begin : g_c
            assign dn_ready[gr] = up_ready[gr + 1];
        end
        always @(posedge clk) if (rst_n) begin
            if (lg_valid[gr] && lg_ready[gr]) nxt[gr] = nxt[gr] + 1;
            if (nxt[gr] < ROWS && jv[gr][nxt[gr]]) begin
                lg_valid[gr] <= 1'b1; lg_bits[32 * gr +: 32] <= jl[gr][nxt[gr]];
                lg_base[32 * gr +: 32] <= 32'(gr * ROWS + nxt[gr]); lg_last[gr] <= (nxt[gr] == ROWS - 1);
            end else lg_valid[gr] <= 1'b0;
        end
    end endgenerate
    // final record
    reg got = 0; reg [31:0] tok = 32'hFFFFFFFF, tbits = 0; reg tok_ok = 0; integer done_cyc = -1;
    wire [511:0] fr = dn_data[3 * 512 +: 512];
    assign dn_ready[3] = 1'b1;
    always @(posedge clk) if (dn_valid[3] && !got) begin
        got <= 1'b1; tok <= fr[H_ARG_ID +: 32]; tbits <= fr[H_ARG_VAL +: 32]; done_cyc <= cyc;
        tok_ok <= dn_last[3] && fr[H_KIND +: 4] == K_ARGMAX && fr[H_ARG_OK];
    end
    initial begin
        for (r = 0; r < 4; r = r + 1) for (k = 0; k < ROWS; k = k + 1) jv[r][k] = 1'b0;
        repeat (5) @(negedge clk); rst_n = 1;
        repeat (3) @(negedge clk);
        while (ready != 4'hF) @(negedge clk);
        start = 4'hF; @(negedge clk); start = 0;
        while (!got && cyc < 400000 && !(|am_fault) && !hfault) @(negedge clk);
        repeat (20) @(negedge clk);
        $display("S81_DRAFT_HEAD_STATS row=%0d joined_bad=%0d poisoned=%0d markov_fault=%0d argmax_fault=%b head_fault=%b fed=%0d/%0d/%0d/%0d token=%0d bits=%h record_ok=%b expect=%0d/%h cycles=%0d MUT=%0d NI=%0d",
                 D, bad, poison, mk_fault, am_fault, hfault, nxt[0], nxt[1], nxt[2], nxt[3], tok, tbits, tok_ok, ex[0], ex[1], done_cyc, MUT, NI);
        if (got && tok_ok && tok == ex[0] && tbits == ex[1] && bad == 0 && poison == 0 && mk_fault == 0 && !(|am_fault) && !hfault &&
            nxt[0] == ROWS && nxt[1] == ROWS && nxt[2] == ROWS && nxt[3] == ROWS)
            $display("S81_DRAFT_HEAD PASS row=%0d token=%0d", D, tok);
        else $display("S81_DRAFT_HEAD FAIL row=%0d token=%0d", D, tok);
        $finish;
    end
endmodule
