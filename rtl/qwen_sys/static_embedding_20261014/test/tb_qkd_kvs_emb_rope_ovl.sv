`timescale 1ns/1ps
// SQ-KATTN2 2026-10-21 (K.STA.EMB, kit qkd_kvs_emb_rope73_ovl): behavioural bench of the generated RoPE/OVL kvs_emb tile
// top qkd_kvs_emb_rope_ovl (qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_rope_ovl.sv) against an independent scoreboard:
//   - an admitted kind-12 CONTEXT (ovl_adm=1, matching head user) starts the embedding sweep: px_st with the record's
//     token / epoch, u_join.rope_sweep low;
//   - exactly ROPE_DELAY (1024) edges after that start the RoPE sweep starts: px_st again, px_tok = 151936 + owner[18:9]
//     (= 151936 + pos[12:3]), px_tep = the record epoch, u_join.rope_sweep high;
//   - o_ctx_svc == {svc[173:110], px_tok, svc[91:90], px_tep, svc[73:25], px_st, svc[23:0]} on every edge;
//   - no start while ovl_adm=0; emb_fault rises on a wrong head user, on a wrong EMB TX slot user, and on i_kvn_fault.
// One line "KVS_EMB_ROPE_OVL PASS|FAIL ...". Mutants (kvs_emb_rope_ovl_bench.sh, applied to a copy of qkd_kvs_emb_ctx.sv)
// must FAIL.
module tb_qkd_kvs_emb_rope_ovl;
    reg ck = 0, rst_n = 0;
    always #0.4165 ck = ~ck;
    integer cyc = 0, errors = 0, seed = 20261021;
    reg  [173:0] svc = 0;
    reg  [0:0]   slot = 0;
    reg  [72:0]  i_ctl = 0;
    reg  [298:0] ws = 0, wn = 0, es = 0, en = 0;
    reg  [551:0] hr = 0;
    reg  [3:0]   users = 0;
    reg          kvn_f = 0, adm = 0;
    wire         tx_v, emb_f;
    wire [547:0] tx_p;
    wire [17:0]  p_tok;
    wire [15:0]  p_tep;
    wire [173:0] o_svc;
    qkd_kvs_emb_rope_ovl dut (.ck(ck), .rst_n(rst_n), .d2d__svc(svc), .d2d__emb_tx_slot(slot), .rowtx__emb_tx_v(tx_v),
        .rowtx__emb_tx_payload(tx_p), .px_tok(p_tok), .px_tep(p_tep), .i_ctl(i_ctl), .i_hroot_WS(ws), .i_hroot_WN(wn),
        .i_hroot_ES(es), .i_hroot_EN(en), .i_head_record(hr), .i_ovl_users(users), .i_kvn_fault(kvn_f), .i_ovl_adm(adm),
        .o_ctx_svc(o_svc), .emb_fault(emb_f));
    wire p_st = o_svc[24];
    wire rope_sw = dut.u_context.u_join.rope_sweep;
    // head record builder: hdr {res5, kind4, layer6, epoch16, beat5} at [551:516]; owner {gen2, epoch16, stage6, token18,
    // pos13, seg6} at [64:4]; valid at [3]
    function automatic [551:0] rec(input [15:0] ep, input [17:0] tk, input [12:0] pos);
        reg [551:0] r;
        begin
            r = 0; r[551:516] = {5'd0, 4'd12, 6'd63, ep, 5'd0}; r[64:4] = {2'd0, ep, 6'd0, tk, pos, 6'd0}; r[3] = 1'b1;
            rec = r;
        end
    endfunction
    // scoreboard
    integer st_count = 0, rope_count = 0, last_st = -1, checks = 0;
    reg [17:0] exp_tok; reg [15:0] exp_ep; reg [12:0] exp_pos; reg expect_on = 0;
    always @(negedge ck) if (rst_n) begin
        checks = checks + 1;
        if (o_svc !== {svc[173:110], p_tok, svc[91:90], p_tep, svc[73:25], p_st, svc[23:0]}) begin
            errors = errors + 1; if (errors < 8) $display("MISMATCH cyc %0d o_ctx_svc composition", cyc); end
        if (p_st) begin
            if (!expect_on) begin errors = errors + 1; if (errors < 8) $display("MISMATCH cyc %0d unexpected px_st", cyc); end
            else if (last_st < 0 || cyc - last_st != 1024) begin       // embedding sweep start
                st_count = st_count + 1;
                if (p_tok !== exp_tok || p_tep !== exp_ep || rope_sw !== 1'b0) begin errors = errors + 1;
                    if (errors < 8) $display("MISMATCH cyc %0d emb start tok %h/%h ep %h/%h rope_sweep %b", cyc, p_tok, exp_tok, p_tep, exp_ep, rope_sw); end
                last_st = cyc;
            end else begin                                               // RoPE sweep start, exactly 1024 edges later
                rope_count = rope_count + 1;
                if (p_tok !== 18'd151936 + {8'd0, exp_pos[12:3]} || p_tep !== exp_ep || rope_sw !== 1'b1) begin errors = errors + 1;
                    if (errors < 8) $display("MISMATCH cyc %0d rope start tok %h/%h ep %h/%h rope_sweep %b", cyc, p_tok, 18'd151936 + {8'd0, exp_pos[12:3]}, p_tep, exp_ep, rope_sw); end
                last_st = -1;
            end
        end
    end
    always @(posedge ck) cyc <= cyc + 1;
    task automatic idle(input integer n); integer i; begin for (i = 0; i < n; i = i + 1) begin
        @(negedge ck);
        svc = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
    end end endtask
    task automatic phase_reset; begin
        rst_n = 0; adm = 0; expect_on = 0; last_st = -1; hr = 0; slot = 0; users = 0; repeat (8) @(negedge ck); rst_n = 1; idle(12);
    end endtask
    // one CONTEXT per reset phase (no return trains / slots: the row stays armed, so the one admitted start is checked
    // without the row-transport schedule; the embedding row path is the closed die qkd_embedding row_tx contract)
    task automatic token(input [15:0] ep, input [17:0] tk, input [12:0] pos, input integer with_adm, input [1:0] head_user);
        begin
            exp_tok = tk; exp_ep = ep; exp_pos = pos; expect_on = with_adm;
            @(negedge ck); adm = with_adm; users = {head_user, ep[1:0]}; hr = rec(ep, tk, pos);
            @(negedge ck); hr = 0;
            idle(1100);
            $display("INFO token ep %h st %0d rope %0d fault %b", ep, st_count, rope_count, emb_f);
        end
    endtask
    integer fa, fb, fc, f1, f2, f3;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261021;
        repeat (8) @(negedge ck); rst_n = 1; idle(20);
        token(16'h0101, 18'd1234, 13'd17, 0, 2'd1);           // phase-unqualified record (no adm_done): no start
        phase_reset; token(16'h0105, 18'd4321, 13'd18, 1, 2'd1); fa = emb_f;
        phase_reset; token(16'h0109, 18'd99, 13'd1023, 1, 2'd1); fb = emb_f;
        phase_reset; token(16'h010e, 18'd151935, 13'd8191, 1, 2'd2); fc = emb_f;
        // fault 1: admitted kind-12 record whose head user differs from the RX calendar user (the start still goes:
        // static schedule, no wait; the health fault is sticky)
        phase_reset; token(16'h0111, 18'd5, 13'd20, 1, 2'd3); f1 = emb_f;
        // fault 2: an EMB TX slot whose calendar TX user differs from the admitted epoch's user
        phase_reset; token(16'h0201, 18'd77, 13'd40, 1, 2'd1);
        @(negedge ck); users = {2'd1, 2'd2}; slot = 1; @(negedge ck); slot = 0; idle(4); f2 = emb_f;
        // fault 3: KVN bank fault
        phase_reset; @(negedge ck); kvn_f = 1; idle(3); f3 = emb_f; kvn_f = 0;
        $display("COVER checks=%0d starts=%0d rope=%0d ok_faults=%0d%0d%0d wrong_head=%0d wrong_tx=%0d kvn=%0d", checks, st_count, rope_count, fa, fb, fc, f1, f2, f3);
        if (st_count != 5 || rope_count != 5) begin errors = errors + 1; $display("FAIL starts %0d rope %0d (want 5/5)", st_count, rope_count); end
        if (fa !== 0 || fb !== 0 || fc !== 0 || f1 !== 1 || f2 !== 1 || f3 !== 1) begin errors = errors + 1; $display("FAIL fault vector %0d%0d%0d %0d%0d%0d (want 000 111)", fa, fb, fc, f1, f2, f3); end
        if (errors == 0) $display("KVS_EMB_ROPE_OVL PASS checks=%0d starts=%0d rope=%0d errors=0", checks, st_count, rope_count);
        else $display("KVS_EMB_ROPE_OVL FAIL errors=%0d checks=%0d", errors, checks);
        $finish;
    end
endmodule
