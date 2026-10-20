`timescale 1ns/1ps
// KV-EMB4 2026-10-19 (tree K.STA.EMB): wiring lockstep of the OT_KV_EMB_CTX kvs_emb body (qkd_kvs_emb_ctx, the kit top
// of qkd_kvs_emb_x1*) against
//   (a) the generated, die-bound RESULT-started qkd_kvs_emb (qkd_kvs_tiles_hroot_ff_k.sv) whose d2d__svc start / token /
//       epoch fields are driven from the CTX tile's own px_st / px_tok / px_tep (so the join4_cal + row_tx bodies must
//       behave identically once the start source is the same), and
//   (b) a standalone reference qkd_embedding_ctx_start fed the same i_ctx fields and the reference tile's row_tx armed
//       state (so px_st / px_tok / px_tep, the overlap veto and the fault must match).
// Checked every edge after reset: rowtx__emb_tx_v / payload == (a); {px_st, px_tok, px_tep} == (b);
// emb_fault == (b).fault | (a) join fault | (a) row_tx fault.  Stimulus: kind-12 CONTEXT records with fresh owners every
// 70..400 edges (repeats in between, overlap starts while the row is still open), random emb_tx_slot, random return
// trains and boot words; phase 2 (after a reset) adds malformed records (sticky ctx fault).
// Also every input port of both hard children (u_join, u_rowtx) equal to the reference tile's, and row_open == armed.
// Coverage floor: >= 8 admitted starts, >= 2 overlap refusals, >= 1 malformed fault, >= 1 edge where emb_fault is the
// row_tx fault alone; else FAIL.
// One line "KVS_EMB_CTX PASS|FAIL ...".  Mutants (applied to a copy of qkd_kvs_emb_ctx.sv by kvs_emb_ctx_bench.sh) FAIL.
module tb_qkd_kvs_emb_ctx_lockstep;
    reg ck = 0, rst_n = 0;
    always #0.4165 ck = ~ck;
    integer cyc = 0, seed = 20261019, errors = 0;
    reg  [98:0]  i_ctx = 0;
    reg  [0:0]   slot = 0;
    reg  [72:0]  i_ctl = 0;
    reg  [298:0] ws = 0, wn = 0, es = 0, en = 0;
    wire [0:0]   n_v, n_st, n_f;
    wire [547:0] n_p;
    wire [17:0]  n_tok;
    wire [15:0]  n_tep;
    qkd_kvs_emb_ctx u_new (.ck(ck), .rst_n(rst_n), .i_ctx(i_ctx), .d2d__emb_tx_slot(slot), .rowtx__emb_tx_v(n_v),
        .rowtx__emb_tx_payload(n_p), .px_st(n_st), .px_tok(n_tok), .px_tep(n_tep), .emb_fault(n_f), .i_ctl(i_ctl),
        .i_hroot_WS(ws), .i_hroot_WN(wn), .i_hroot_ES(es), .i_hroot_EN(en));
    wire [173:0] svc = {64'd0, n_tok, 2'd0, n_tep, 49'd0, n_st, 24'd0};   // [109:92] tok, [89:74] epoch, [24] start
    wire [0:0]   o_v;
    wire [547:0] o_p;
    wire [17:0]  o_tok;
    wire [15:0]  o_tep;
    qkd_kvs_emb u_old (.ck(ck), .rst_n(rst_n), .d2d__svc(svc), .d2d__emb_tx_slot(slot), .rowtx__emb_tx_v(o_v),
        .rowtx__emb_tx_payload(o_p), .px_tok(o_tok), .px_tep(o_tep), .i_ctl(i_ctl), .i_hroot_WS(ws), .i_hroot_WN(wn),
        .i_hroot_ES(es), .i_hroot_EN(en));
    wire        r_st, r_f;
    wire [17:0] r_tok;
    wire [15:0] r_tep;
    qkd_embedding_ctx_start u_ref (.ck(ck), .rst_n(rst_n), .row_open(u_old.u_rowtx.armed), .ctx_v(i_ctx[98]),
        .ctx_observed_v(i_ctx[97]), .ctx_hdr(i_ctx[96:61]), .ctx_owner(i_ctx[60:0]), .start(r_st), .token(r_tok),
        .epoch(r_tep), .owner(), .fault(r_f));
    reg rf_q = 0;
    always @(negedge ck) begin if (rst_n && r_f && !rf_q) $display("INFO cyc %0d ref ctx fault rises (take %b hdr_ok %b own_ok %b fresh %b gap %0d open %b)", cyc, u_ref.take, u_ref.hdr_ok, u_ref.own_ok, u_ref.fresh, u_ref.gap, u_old.u_rowtx.armed); rf_q = r_f; end
    wire exp_f = r_f | u_old.w_join__fault[0] | u_old.w_rowtx__fault[0];
    integer starts = 0, overlaps = 0, malformed = 0, checks = 0, fault_rowtx_only = 0;
    reg chk = 0;
    always @(negedge ck) if (rst_n && chk) begin
        checks = checks + 1;
        if (n_v !== o_v || n_p !== o_p) begin errors = errors + 1; if (errors < 6) $display("MISMATCH cyc %0d rowtx v %b/%b payload %h/%h", cyc, n_v, o_v, n_p[547:500], o_p[547:500]); end
        if (n_st !== r_st || (r_st && (n_tok !== r_tok || n_tep !== r_tep))) begin errors = errors + 1; if (errors < 6) $display("MISMATCH cyc %0d px_st %b/%b tok %h/%h tep %h/%h", cyc, n_st, r_st, n_tok, r_tok, n_tep, r_tep); end
        if (n_f !== exp_f) begin errors = errors + 1; if (errors < 6) $display("MISMATCH cyc %0d emb_fault %b exp %b", cyc, n_f, exp_f); end
        // every input port of both hard children equal to the reference tile's (wiring checked directly)
        if (u_new.u_join.start !== u_old.u_join.start || u_new.u_join.cfg_we !== u_old.u_join.cfg_we || u_new.u_join.cfg_addr !== u_old.u_join.cfg_addr
            || u_new.u_join.cfg_data !== u_old.u_join.cfg_data || u_new.u_join.up0 !== u_old.u_join.up0 || u_new.u_join.up1 !== u_old.u_join.up1
            || u_new.u_join.up2 !== u_old.u_join.up2 || u_new.u_join.up3 !== u_old.u_join.up3) begin
            errors = errors + 1; if (errors < 6) $display("MISMATCH cyc %0d join child inputs (start %b/%b)", cyc, u_new.u_join.start, u_old.u_join.start); end
        if (u_new.u_rowtx.fill_begin !== u_old.u_rowtx.fill_begin || u_new.u_rowtx.fill_token !== u_old.u_rowtx.fill_token
            || u_new.u_rowtx.fill_epoch !== u_old.u_rowtx.fill_epoch || u_new.u_rowtx.word_v !== u_old.u_rowtx.word_v
            || u_new.u_rowtx.word_data !== u_old.u_rowtx.word_data || u_new.u_rowtx.word_token !== u_old.u_rowtx.word_token
            || u_new.u_rowtx.word_index !== u_old.u_rowtx.word_index || u_new.u_rowtx.word_scale !== u_old.u_rowtx.word_scale
            || u_new.u_rowtx.word_epoch !== u_old.u_rowtx.word_epoch || u_new.u_rowtx.emb_tx_slot !== u_old.u_rowtx.emb_tx_slot) begin
            errors = errors + 1; if (errors < 6) $display("MISMATCH cyc %0d row_tx child inputs", cyc); end
        if (u_new.u_rowtx.row_open !== u_old.u_rowtx.armed) begin errors = errors + 1; if (errors < 6) $display("MISMATCH cyc %0d row_open", cyc); end
        if (n_f && !(r_f | u_old.w_join__fault[0])) fault_rowtx_only = fault_rowtx_only + 1;
        if (r_st) starts = starts + 1;
    end
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (rst_n && u_ref.take && u_ref.hdr_ok && u_ref.own_ok && u_ref.fresh && u_ref.gap == 0 && u_old.u_rowtx.armed && !u_ref.fault) overlaps = overlaps + 1;
        if (rst_n && u_ref.take && !(u_ref.hdr_ok && u_ref.own_ok) && !u_ref.fault) malformed = malformed + 1;
    end
    // record builder: hdr {res5, kind4, layer6, epoch16, beat5}, owner {gen2, epoch16, stage6, token18, pos13, seg6}
    function automatic [98:0] rec(input [1:0] g, input [15:0] ep, input [17:0] tk, input [12:0] pos, input integer bad);
        reg [35:0] h; reg [60:0] o;
        begin
            h = {5'd0, 4'd12, 6'd63, ep, 5'd0}; o = {g, ep, 6'd0, tk, pos, 6'd0};
            if (bad == 1) h[26:21] = 6'd5;            // layer != 63
            if (bad == 2) h[20:5] = ep ^ 16'h1;       // header epoch != TAG epoch
            if (bad == 3) o[42:37] = 6'd1;            // stage != 0
            if (bad == 4) o[36:19] = 18'd151936;      // token out of vocabulary
            rec = {1'b1, 1'b1, h, o};
        end
    endfunction
    integer t, k, wait_e, closed_e, done_end;
    reg [15:0] ep; reg [17:0] tk; reg [12:0] pos; reg [1:0] g;
    // endkind 1: a fresh owner while the row is still open (overlap veto, sticky fault); 2: a malformed record
    task automatic run(input integer edges, input integer endkind);
        begin
            ep = 16'h0100 + 16'(endkind * 16'h1000); tk = 18'd7; pos = 0; g = 2'(endkind); wait_e = 0; closed_e = 0; done_end = 0;
            for (t = 0; t < edges; t = t + 1) begin
                @(negedge ck);
                slot = (($random(seed) & 3) == 0);
                if (endkind == 1) begin ws = 0; wn = 0; es = 0; en = 0; i_ctl = 0; end else begin
                ws = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
                wn = {ws[150:0], ws[298:151]}; es = ~ws; en = ws ^ {10{$random(seed)}};
                i_ctl = (($random(seed) & 63) == 0) ? {1'b1, $random(seed), $random(seed), 8'($random(seed))} : {1'b0, i_ctl[71:0]};
                end   // phases 1 / 3: idle return trains + no boot words (join fault-free: emb_fault observes ctx / row_tx alone)
                closed_e = u_old.u_rowtx.armed ? 0 : closed_e + 1;
                if (t < edges - 600) begin
                    // legal schedule: the next fresh owner only after the row drained (+2 edges) and the gap expired
                    if (wait_e > 0) wait_e = wait_e - 1;
                    else if (closed_e >= 3 && u_ref.gap == 0 && u_ref.have && u_ref.last == rec(g, ep, tk, pos, 0)[60:0]) begin   // current owner started + drained
                        ep = ep + 16'd1; pos = pos + 13'd1; tk = 18'(($random(seed) & 32'h7fffffff) % 151936);
                        wait_e = 4 + (($random(seed) & 32'h7fffffff) % 60);
                    end
                end else if (!done_end && endkind == 1 && u_old.u_rowtx.armed && u_ref.gap == 0 && u_ref.last == rec(g, ep, tk, pos, 0)[60:0]) begin
                    ep = ep + 16'd1; pos = pos + 13'd1; tk = tk ^ 18'd1; done_end = 1;          // overlap: row still open
                end
                k = $random(seed) & 7;
                if (k == 0) i_ctx = 99'd0;                                     // no record this edge
                else if (k == 1) i_ctx = {1'b1, 1'b0, rec(g, ep, tk, pos, 0)};  // tx_v without observed_v (dropped)
                else if (k == 2) begin i_ctx = rec(g, ep, tk, pos, 0); i_ctx[91:88] = 4'd13; end   // kind-13 AUTH record
                else if (endkind == 2 && t > edges - 300 && k == 3) i_ctx = rec(g, ep, tk, pos, 1 + (($random(seed) & 32'h7fffffff) % 4));
                else i_ctx = rec(g, ep, tk, pos, 0);                           // the held CONTEXT (repeat or fresh)
            end
        end
    endtask
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261019;
        repeat (6) @(negedge ck); rst_n = 1; chk = 1;
        run(6000, 1);
        chk = 0; i_ctx = 99'd0; slot = 0; rst_n = 0; repeat (6) @(negedge ck); rst_n = 1; chk = 1;
        run(4000, 2);
        chk = 0; i_ctx = 99'd0; slot = 0; rst_n = 0; repeat (6) @(negedge ck); rst_n = 1; chk = 1;
        run(4000, 1);
        $display("COVER checks=%0d starts=%0d overlaps=%0d malformed=%0d rowtx_only_fault_edges=%0d", checks, starts, overlaps, malformed, fault_rowtx_only);
        if (starts < 8 || overlaps < 2 || malformed < 1 || fault_rowtx_only < 1) begin errors = errors + 1; $display("FAIL coverage floor"); end
        if (errors == 0) $display("KVS_EMB_CTX PASS checks=%0d starts=%0d overlaps=%0d malformed=%0d errors=0", checks, starts, overlaps, malformed);
        else $display("KVS_EMB_CTX FAIL errors=%0d checks=%0d starts=%0d", errors, checks, starts);
        $finish;
    end
endmodule
