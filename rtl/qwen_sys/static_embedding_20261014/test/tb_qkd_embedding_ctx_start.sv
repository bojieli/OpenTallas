`timescale 1ns/1ps
// KV-EMB2 2026-10-19: bench of qkd_embedding_ctx_start feeding the real qkd_embedding_row_tx (real SRAM model).
// The bench plays the HOST record face (kind-12 CONTEXT records exactly as qkd_host_native_context_tx forms them, kind-13
// AUTH records, observed-0 slots), then the join word face for the started row and the 65 port-2 slots, and checks the
// row header {token, epoch} against the context record the compute die retains (qfd_host_native_context_rx host_tag).
// Prompt [7, 11, 11] with one owner per step; RESULT never appears (it cannot start a fill in this design).
// Negative DUT (second instance): malformed header epoch, stage != 0, token range, two owners closer than MIN_GAP.
// Prints PASS or FAIL lines; the mutant witnesses expect a FAIL line.
module tb_qkd_embedding_ctx_start;
`ifndef MUT
`define MUT 0
`endif
    reg ck = 0, rst_n = 0;
    always #1 ck = ~ck;
    reg ctx_v = 0, ctx_o = 0; reg [35:0] ctx_h = 0; reg [60:0] ctx_d = 0;
    wire st; wire [17:0] tok; wire [15:0] tep; wire [60:0] own; wire cf;
    qkd_embedding_ctx_start #(.MUT(`MUT)) dut (.ck(ck), .rst_n(rst_n), .ctx_v(ctx_v), .ctx_observed_v(ctx_o), .ctx_hdr(ctx_h),
        .ctx_owner(ctx_d), .start(st), .token(tok), .epoch(tep), .owner(own), .fault(cf));
    reg w_v = 0, w_sc = 0; reg [511:0] w_d = 0; reg [17:0] w_t = 0; reg [5:0] w_i = 0; reg [15:0] w_e = 0; reg slot = 0;
    wire tx_v; wire [547:0] tx_p; wire rf, rr;
    qkd_embedding_row_tx u_rowtx (.ck(ck), .rst_n(rst_n), .fill_begin(st), .fill_token(tok), .fill_epoch(tep),
        .word_v(w_v), .word_data(w_d), .word_token(w_t), .word_index(w_i), .word_scale(w_sc), .word_epoch(w_e),
        .emb_tx_slot(slot), .emb_tx_v(tx_v), .emb_tx_payload(tx_p), .fault(rf), .row_ready(rr));
    // negative instance
    reg n_rst = 0, n_v = 0, n_o = 0; reg [35:0] n_h = 0; reg [60:0] n_d = 0;
    wire n_st, n_f;
    qkd_embedding_ctx_start #(.MUT(`MUT)) dneg (.ck(ck), .rst_n(n_rst), .ctx_v(n_v), .ctx_observed_v(n_o), .ctx_hdr(n_h),
        .ctx_owner(n_d), .start(n_st), .token(), .epoch(), .owner(), .fault(n_f));

    integer errors = 0, starts = 0, n_starts = 0;
    always @(posedge ck) begin if (st) starts <= starts + 1; if (n_st) n_starts <= n_starts + 1; end

    function [58:0] mktag(input [15:0] ep, input [5:0] stg, input [17:0] t, input [12:0] pos, input [5:0] seg);
        mktag = {ep, stg, t, pos, seg};
    endfunction
    function [35:0] mkhdr(input [3:0] kind, input [15:0] ep);
        mkhdr = {5'd0, kind, 6'd63, ep, 5'd0};
    endfunction
    task rec(input integer which, input v, input o, input [35:0] h, input [60:0] d);
        begin
            @(negedge ck);
            if (which == 0) begin ctx_v = v; ctx_o = o; ctx_h = h; ctx_d = d; end
            else begin n_v = v; n_o = o; n_h = h; n_d = d; end
            @(negedge ck);
            if (which == 0) begin ctx_v = 0; ctx_o = 0; end else begin n_v = 0; n_o = 0; end
        end
    endtask
    function [511:0] word(input [17:0] t, input [5:0] i);
        word = {16{t[13:0], i, 12'hA5C}};
    endfunction
    // the join word face for row (t, e): 64 code words then the scale, as join4_cal delivers them
    task fill(input [17:0] t, input [15:0] e);
        integer i;
        begin
            for (i = 0; i < 65; i = i + 1) begin
                @(negedge ck);
                w_v = 1; w_t = t; w_e = e; w_sc = (i == 64); w_i = (i == 64) ? 6'd0 : i[5:0];
                w_d = (i == 64) ? {496'd0, t[7:0], e[7:0]} : word(t, i[5:0]);
            end
            @(negedge ck); w_v = 0; w_sc = 0;
        end
    endtask
    task send(input [17:0] t, input [15:0] e);
        integer i;
        begin
            for (i = 0; i < 65; i = i + 1) begin
                @(negedge ck); slot = 1;
                @(negedge ck); slot = 0;
                @(posedge ck); #0.1;
                if (i == 0) begin
                    if (tx_p[547:530] !== t || tx_p[47:32] !== e || tx_p[15:0] !== {t[7:0], e[7:0]}) begin
                        $display("FAIL: header token %0d epoch %0d scale %h, expected the context owner token %0d epoch %0d",
                                 tx_p[547:530], tx_p[47:32], tx_p[15:0], t, e); errors = errors + 1; end
                end else if (tx_p[547:530] !== t || tx_p[529:524] !== (i - 1) || tx_p[511:0] !== word(t, i - 1)) begin
                    $display("FAIL: record %0d token %0d word %0d", i, tx_p[547:530], tx_p[529:524]); errors = errors + 1; end
            end
        end
    endtask
    task wait_edges(input integer n); integer k; begin for (k = 0; k < n; k = k + 1) @(negedge ck); end endtask
    task expect_starts(input integer n, input [127:0] what);
        begin @(negedge ck); if (starts != n) begin $display("FAIL: %0s: %0d fill starts, expected %0d", what, starts, n); errors = errors + 1; end end
    endtask
    // one step: the HOST context of the allocated step (owner O61), then the row, then its 65 records
    task step(input [15:0] e, input [17:0] t, input [12:0] pos, input [1:0] g, input integer n_expected);
        begin
            rec(0, 1, 1, mkhdr(4'd12, e), {g, mktag(e, 6'd0, t, pos, 6'd0)});
            wait_edges(2);
            expect_starts(n_expected, "context step");
            if (tok !== t || tep !== e) begin $display("FAIL: started token %0d epoch %0d, expected %0d / %0d", tok, tep, t, e); errors = errors + 1; end
            fill(t, e);
            wait_edges(2);
            send(t, e);
            wait_edges(4);
        end
    endtask

    initial begin
        wait_edges(3); rst_n = 1; n_rst = 1; wait_edges(4);
        // step 0: prompt token 7 at position 0 (first token: no RESULT exists), epoch 4 user 0, generation 1
        step(16'd4, 18'd7, 13'd0, 2'd1, 1);
        // the context port re-sends its held request every token run: same owner -> no second fill
        rec(0, 1, 1, mkhdr(4'd12, 16'd4), {2'd1, mktag(16'd4, 6'd0, 18'd7, 13'd0, 6'd0)});
        wait_edges(3); expect_starts(1, "repeated owner");
        // a kind-13 AUTH record on the same face (its DATA shaped like a valid owner) and an observed-0 kind-12 slot
        rec(0, 1, 1, mkhdr(4'd13, 16'd9), {2'd0, mktag(16'd9, 6'd0, 18'd99, 13'd5, 6'd0)});
        rec(0, 1, 0, mkhdr(4'd12, 16'd9), {2'd0, mktag(16'd9, 6'd0, 18'd99, 13'd5, 6'd0)});
        wait_edges(3); expect_starts(1, "AUTH / observed-0 record");
        // step 1: prompt token 11 at position 1, epoch 5 (a RESULT next token 13 would be wrong here; it is not an input)
        step(16'd5, 18'd11, 13'd1, 2'd1, 2);
        // step 2: prompt token 11 again at position 2, epoch 6: same token, new owner -> a new fill
        step(16'd6, 18'd11, 13'd2, 2'd1, 3);
        // step 3: user 1 (epoch[1:0] = 1), generated token 4242 at position 3
        step(16'd25, 18'd4242, 13'd3, 2'd2, 4);
        if (cf || rf) begin $display("FAIL: sticky fault ctx %0d row_tx %0d on legal traffic", cf, rf); errors = errors + 1; end
        // negatives (second instance, reset between cases)
        rec(1, 1, 1, mkhdr(4'd12, 16'd8), {2'd0, mktag(16'd7, 6'd0, 18'd5, 13'd0, 6'd0)});        // header epoch != TAG epoch
        wait_edges(3); if (!n_f) begin $display("FAIL: header epoch mismatch not faulted"); errors = errors + 1; end
        if (n_starts != 0) begin $display("FAIL: malformed record started a fill"); errors = errors + 1; end
        n_rst = 0; wait_edges(2); n_rst = 1; wait_edges(2);
        rec(1, 1, 1, mkhdr(4'd12, 16'd7), {2'd0, mktag(16'd7, 6'd3, 18'd5, 13'd0, 6'd0)});        // stage != 0
        wait_edges(3); if (!n_f) begin $display("FAIL: stage != 0 not faulted"); errors = errors + 1; end
        n_rst = 0; wait_edges(2); n_rst = 1; wait_edges(2);
        rec(1, 1, 1, mkhdr(4'd12, 16'd7), {2'd0, mktag(16'd7, 6'd0, 18'd151936, 13'd0, 6'd0)});   // token out of range
        wait_edges(3); if (!n_f) begin $display("FAIL: token range not faulted"); errors = errors + 1; end
        n_rst = 0; wait_edges(2); n_rst = 1; wait_edges(2);
        rec(1, 1, 1, mkhdr(4'd12, 16'd7), {2'd0, mktag(16'd7, 6'd0, 18'd5, 13'd0, 6'd0)});
        wait_edges(10);
        rec(1, 1, 1, mkhdr(4'd12, 16'd8), {2'd0, mktag(16'd8, 6'd0, 18'd6, 13'd1, 6'd0)});        // closer than MIN_GAP
        wait_edges(3); if (!n_f) begin $display("FAIL: two owners inside one row window not faulted"); errors = errors + 1; end
        if (errors == 0) $display("PASS tb_qkd_embedding_ctx_start: 4 steps, %0d fills, header owner = context owner, 4 negatives faulted", starts);
        else $display("FAIL tb_qkd_embedding_ctx_start: %0d errors", errors);
        $finish;
    end
    initial begin #200000; $display("FAIL: timeout"); $finish; end
endmodule
