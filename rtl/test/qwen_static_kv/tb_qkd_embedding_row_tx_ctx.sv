`timescale 1ns/1ps
// KVJ-C (b) 2026-10-17: bench of qkd_embedding_row_tx behind the REAL qkd_embedding_static_join.
//   Beats (low half, high half per code word; one packed scale sector) arrive at the join in a per-token shuffled
//   compiled order with random gaps; fill_begin (the RESULT's token) precedes them.  The d2d port-2 TX slots then
//   ask for header + 64 words, back-to-back (the program_profile calendar) or with gaps (GAPS=1 tokens).
//   Golden (independent of the RTL): code word w of token t = H(t, w) (512 b), scale = lane t[3:0] of the scale
//   sector S(t); payloads decoded with qfd_sys_face's record layout (header {token, 0, 0, epoch [47:32], scale [15:0]},
//   word {token [547:530], word [529:524], 0 [523:512], code [511:0]}), emb_tx_v exactly one edge after each slot.
//   Negative cases (each in its own reset window, fault must latch): a word after the header slot (late), a missing
//   word at first send, a duplicate word, a foreign-token word, a 66th slot, a fill_begin that drops an unsent row.
// Mutants: -DOT_KVJ_ROWTX_MUT=1 (word index field), 2 (no residency check), 3 (read one item late) must FAIL.
// KV-EMB4 10-19: _ctx variant (qkd_embedding_row_tx_ctx): also checks row_open against an independent armed model
// (high the edge after fill_begin through the 65th send slot); mutant 4 (row_open = row_ready) must FAIL.
// Prints "PASS kvjc row_tx ..." or "FAIL kvjc row_tx ...".
`ifndef OT_KVJ_ROWTX_MUT
`define OT_KVJ_ROWTX_MUT 0
`endif
module tb_qkd_embedding_row_tx_ctx;
    parameter integer NTOK = 24;
    reg ck = 0, rst_n = 0;
    always #0.4165 ck = ~ck;
    integer cyc = 0;
    always @(posedge ck) cyc = cyc + 1;
    function automatic [511:0] H(input [17:0] t, input integer w);
        reg [31:0] x; integer j;
        begin
            for (j = 0; j < 16; j = j + 1) begin
                x = {14'd0, t} * 32'h9E3779B1 + w * 32'h7F4A7C15 + j * 32'h85EBCA6B + 32'h1234567;
                x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
                H[32*j +: 32] = x;
            end
        end
    endfunction
    function automatic [255:0] S(input [17:0] t);   // scale sector of t's 16-token group: lane j = scale of t[17:4]*16+j
        integer j; reg [15:0] s;
        begin
            for (j = 0; j < 16; j = j + 1) begin s = 16'h3c00 ^ 16'({t[17:4], 4'(j)} * 16'h9e37); S[16*j +: 16] = s; end
        end
    endfunction
    // ---- DUT chain ----
    reg          b_slot = 0, b_v = 0, b_half = 0, b_scale = 0;
    reg  [255:0] b_data = 0;
    reg  [17:0]  b_tok = 0;
    reg  [5:0]   b_word = 0;
    reg  [15:0]  b_ep = 0;
    wire         w_v, w_scale, j_fault;
    wire [511:0] w_data;
    wire [17:0]  w_tok;
    wire [5:0]   w_idx;
    wire [15:0]  w_ep;
    qkd_embedding_static_join u_join (.ck(ck), .rst_n(rst_n), .beat_slot(b_slot), .beat_v(b_v), .beat_data(b_data),
        .beat_token(b_tok), .beat_word(b_word), .beat_half(b_half), .beat_scale(b_scale), .beat_epoch(b_ep),
        .word_v(w_v), .word_data(w_data), .word_token(w_tok), .word_index(w_idx), .word_scale(w_scale),
        .word_epoch(w_ep), .fault(j_fault));
    reg          fb = 0, slot = 0;
    reg  [17:0]  fb_tok = 0;
    reg  [15:0]  fb_ep = 0;
    wire         tx_v, tx_fault, rdy, ropen;
    wire [547:0] tx_p;
    qkd_embedding_row_tx_ctx #(.MUT(`OT_KVJ_ROWTX_MUT)) dut (.ck(ck), .rst_n(rst_n), .fill_begin(fb), .fill_token(fb_tok),
        .fill_epoch(fb_ep), .word_v(w_v), .word_data(w_data), .word_token(w_tok), .word_index(w_idx),
        .word_scale(w_scale), .word_epoch(w_ep), .emb_tx_slot(slot), .emb_tx_v(tx_v), .emb_tx_payload(tx_p),
        .fault(tx_fault), .row_ready(rdy), .row_open(ropen));
    // ---- checker: sys_face record layout, one edge after the slot ----
    integer errors = 0, items = 0, exp_item = 0, words_ok = 0, hdr_ok = 0;
    reg [17:0] c_tok; reg [15:0] c_ep;
    reg slot_q = 0, checking = 1;
    reg [547:0] e;
    always @(posedge ck) slot_q <= rst_n ? slot : 1'b0;
    always @(negedge ck) if (rst_n && checking) begin
        if (tx_v !== slot_q) begin errors = errors + 1; $display("FAIL cyc %0d emb_tx_v %b vs slot one edge earlier %b", cyc, tx_v, slot_q); end
        if (tx_v) begin
            if (exp_item == 0) e = {c_tok, 6'd0, 12'd0, 464'd0, c_ep, 16'd0, S(c_tok)[16*c_tok[3:0] +: 16]};
            else e = {c_tok, 6'(exp_item - 1), 12'd0, H(c_tok, exp_item - 1)};
            if (tx_p !== e) begin
                errors = errors + 1;
                if (errors < 6) $display("FAIL cyc %0d token %0d item %0d: got tok %h w %0d lo %h exp tok %h w %0d lo %h", cyc, c_tok,
                                         exp_item, tx_p[547:530], tx_p[529:524], tx_p[63:0], e[547:530], e[529:524], e[63:0]);
            end else if (exp_item == 0) hdr_ok = hdr_ok + 1; else words_ok = words_ok + 1;
            exp_item = exp_item + 1; items = items + 1;
        end
    end
    // ---- row_open checker (KV-EMB4): independent armed model, positive phase only ----
    reg eo = 0; integer ocnt = 0, open_hi = 0, open_fall = 0; reg ropen_q = 0;
    always @(posedge ck) begin
        if (!rst_n) begin eo <= 0; ocnt <= 0; end
        else if (fb) begin eo <= 1; ocnt <= 0; end
        else if (slot && eo) begin ocnt <= ocnt + 1; if (ocnt == 64) eo <= 0; end
    end
    always @(negedge ck) if (rst_n && checking) begin
        if (ropen !== eo) begin errors = errors + 1; if (errors < 6) $display("FAIL cyc %0d row_open %b vs armed model %b", cyc, ropen, eo); end
        if (ropen === 1'b1) open_hi = open_hi + 1;
        if (ropen_q && ropen === 1'b0) open_fall = open_fall + 1;
        ropen_q = ropen;
    end
    // ---- drivers ----
    integer seed = 20261017, i, w, k, t, g;
    integer order [0:63];
    task automatic beat(input [17:0] tk, input [15:0] ep_, input [5:0] wd, input hf, input sc, input [255:0] d);
        begin
            b_slot = 1; b_v = 1; b_tok = tk; b_ep = ep_; b_word = wd; b_half = hf; b_scale = sc; b_data = d;
            @(negedge ck); b_slot = 0; b_v = 0;
        end
    endtask
    // fill a row (skip = word left out, dup = word sent twice, ftok = foreign token on word 5)
    task automatic fill(input [17:0] tk, input [15:0] ep_, input integer skip, input integer dup, input integer foreign);
        reg [511:0] cw; integer sc_at;
        begin
            fb = 1; fb_tok = tk; fb_ep = ep_; @(negedge ck); fb = 0;
            repeat ($random(seed) & 3) @(negedge ck);
            for (i = 0; i < 64; i = i + 1) order[i] = i;
            for (i = 63; i > 0; i = i - 1) begin k = ($random(seed) & 32'h7fffffff) % (i + 1); w = order[i]; order[i] = order[k]; order[k] = w; end
            sc_at = ($random(seed) & 32'h7fffffff) % 65;
            for (i = 0; i < 64; i = i + 1) begin
                if (i == sc_at) beat(tk, ep_, 6'd0, 1'b0, 1'b1, S(tk));
                w = order[i];
                if (w != skip) begin
                    cw = H(tk, w);
                    beat((foreign && w == 5) ? tk ^ 18'd1 : tk, ep_, 6'(w), 1'b0, 1'b0, cw[255:0]);
                    beat((foreign && w == 5) ? tk ^ 18'd1 : tk, ep_, 6'(w), 1'b1, 1'b0, cw[511:256]);
                    if (w == dup) begin beat(tk, ep_, 6'(w), 1'b0, 1'b0, cw[255:0]); beat(tk, ep_, 6'(w), 1'b1, 1'b0, cw[511:256]); end
                end
                if (($random(seed) & 7) == 0) repeat (($random(seed) & 3)) @(negedge ck);
            end
            if (sc_at == 64) beat(tk, ep_, 6'd0, 1'b0, 1'b1, S(tk));
            repeat (2) @(negedge ck);           // the join's edge + the write
        end
    endtask
    task automatic send(input [17:0] tk, input [15:0] ep_, input integer n, input integer gaps);
        begin
            c_tok = tk; c_ep = ep_; exp_item = 0;
            for (i = 0; i < n; i = i + 1) begin
                slot = 1; @(negedge ck); slot = 0;
                if (gaps && ($random(seed) & 3) == 0) repeat (($random(seed) & 7) + 1) @(negedge ck);
            end
            repeat (2) @(negedge ck);
        end
    endtask
    task automatic window_reset;
        begin rst_n = 0; repeat (3) @(negedge ck); rst_n = 1; repeat (3) @(negedge ck); end
    endtask
    integer neg_seen = 0, neg_n = 0;
    task automatic expect_fault(input [8*24-1:0] name);
        begin
            neg_n = neg_n + 1;
            if (tx_fault) neg_seen = neg_seen + 1;
            else begin errors = errors + 1; $display("FAIL negative case '%0s' did not fault", name); end
            checking = 0; window_reset;
        end
    endtask
    reg [17:0] tk;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261017;
        window_reset;
        // ---- positive: NTOK tokens back to back (last vocabulary row and token 0 included) ----
        for (t = 0; t < NTOK; t = t + 1) begin
            tk = (t == 0) ? 18'd0 : (t == 1) ? 18'd151935 : 18'(($random(seed) & 32'h7fffffff) % 151936);
            fill(tk, 16'h0400 + 16'(t), -1, -1, 0);
            if (!rdy) begin errors = errors + 1; $display("FAIL token %0d row not resident after its fill", t); end
            send(tk, 16'h0400 + 16'(t), 65, t % 3 == 2);
            if (tx_fault || j_fault) begin errors = errors + 1; $display("FAIL fault on legal token %0d (tx %b join %b)", t, tx_fault, j_fault); t = NTOK; end
        end
        $display("POSITIVE tokens=%0d items=%0d headers_ok=%0d words_ok=%0d fault=%b", NTOK, items, hdr_ok, words_ok, tx_fault);
        if (hdr_ok != NTOK || words_ok != 64 * NTOK) begin errors = errors + 1; $display("FAIL item counts"); end
        $display("ROW_OPEN high_samples=%0d falls=%0d", open_hi, open_fall);
        if (open_fall != NTOK || open_hi < 65 * NTOK) begin errors = errors + 1; $display("FAIL row_open window count"); end
        // ---- negative cases ----
        checking = 0;
        tk = 18'd4242;
        fill(tk, 16'h77, 9, -1, 0); send(tk, 16'h77, 1, 0);                      // missing word 9 at the header slot
        expect_fault("missing word");
        fill(tk, 16'h77, 9, -1, 0); send(tk, 16'h77, 1, 0);                      // ... and its late arrival
        beat(tk, 16'h77, 6'd9, 1'b0, 1'b0, 256'd1); beat(tk, 16'h77, 6'd9, 1'b1, 1'b0, 256'd2); repeat (3) @(negedge ck);
        expect_fault("late word");
        fill(tk, 16'h77, -1, 17, 0); expect_fault("duplicate word");
        fill(tk, 16'h77, -1, -1, 1); expect_fault("foreign token");
        fill(tk, 16'h77, -1, -1, 0); send(tk, 16'h77, 66, 0); expect_fault("66th slot");
        fill(tk, 16'h77, -1, -1, 0); fb = 1; fb_tok = tk; @(negedge ck); fb = 0; @(negedge ck); expect_fault("unsent row dropped");
        checking = 1;
        $display("NEGATIVE cases=%0d faulted=%0d", neg_n, neg_seen);
        if (errors == 0)
            $display("PASS kvjc row_tx_ctx row_open=armed tokens=%0d items=%0d (header + 64 words each, sys_face layout, v = slot + 1 edge) negatives=%0d/%0d",
                     NTOK, items, neg_seen, neg_n);
        else $display("FAIL kvjc row_tx_ctx errors=%0d", errors);
        $finish;
    end
    initial begin #20000000; $display("FAIL kvjc row_tx timeout"); $finish; end
endmodule
