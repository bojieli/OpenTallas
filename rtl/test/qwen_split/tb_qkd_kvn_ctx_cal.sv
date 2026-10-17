`timescale 1ns/1ps
// Q-KVSYS PVJOIN 2026-10-16: qkd_kvn_ctx_cal on the KV die's real link calendar sequencer (qkd_d2d_cal_seq_pin, the
// committed compiler image) feeding the real KVN receive check of the static D2D end (ot_qwen_d2d_kvn_rx, behind the
// end's one pin flop), with the compute side's real KVN encoder (ot_qwen_d2d_kvn_tx) sending each layer's 4 KVN words at
// the compiled receive edges (tools/qwen_kv_die/kvn_ctx_golden.py: KVN_L0_OUT / KVN_LN_OUT from the link compiler's
// program calendar).  The compute word identity is qfd_native59_command_context's begin_tag {epoch, stage, token, pos, 0}.
// Checks: every run start of the sequencer at the golden START / FIRST / PERIOD; every KVN word accepted (no kvn_rx fault)
// with word_identity / generation == expect.memh (golden) and the data intact; NTOK x 36 x 4 words.
module tb_qkd_kvn_ctx_cal #(parameter integer MUT = 0, parameter integer CH_OVR = -1, parameter GOLD = "gold") ();
`include "kvn_ctx_gold.svh"
    localparam integer CH = (CH_OVR >= 0) ? CH_OVR : GOLD_CH;
    reg ck = 0;
    always #0.5 ck = ~ck;
    reg rst_n = 0, epoch_go = 0;
    wire c_tx_we, c_rx_we, cal_start, cal_seg, cal_ready, running, adm_done, tok_start, sq_fault;
    wire [5:0] c_addr, layer; wire [31:0] c_data;
    qkd_d2d_cal_seq_pin #(.EP_SKEW(3)) u_seq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(1'b0),
        .cfg_tx_we(c_tx_we), .cfg_rx_we(c_rx_we), .cfg_addr(c_addr), .cfg_data(c_data), .cal_start(cal_start),
        .cal_seg(cal_seg), .cal_ready(cal_ready), .running(running), .layer(layer), .adm_done(adm_done),
        .tok_start(tok_start), .fault(sq_fault));
    reg [58:0] host_tag = 0; reg [1:0] host_gen = 0;
    wire [58:0] ci; wire [1:0] cg;
    qkd_kvn_ctx_cal #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst_n), .cal_start(cal_start), .layer(layer),
        .cohort_tag(host_tag), .cohort_gen(host_gen), .compiled_identity(ci), .compiled_generation(cg));
    // qkd_d2d_static pin-register wrapper (PR = 1): kvn_compiled_* captured one edge at the end's pin
    reg [58:0] ci_p; reg [1:0] cg_p;
    always @(posedge ck) begin ci_p <= ci; cg_p <= cg; end
    // compute die KVN encoder and KV die KVN receive check (real RTL)
    reg [523:0] x3 = 0; reg [58:0] x3_id = 0; reg [1:0] x3_gen = 0;
    wire tv, txf; wire [547:0] tp;
    ot_qwen_d2d_kvn_tx u_tx (.ck(ck), .rst_n(rst_n), .x3(x3), .x3_identity(x3_id), .x3_generation(x3_gen),
        .tx_valid(tv), .tx_payload(tp), .fault(txf));
    reg slot = 0; reg [4:0] beat = 0;
    wire wv, wslot, rxf; wire [10:0] wtag; wire [511:0] wdata; wire [58:0] wid; wire [1:0] wgen, widx;
    ot_qwen_d2d_kvn_rx u_rx (.ck(ck), .rst_n(rst_n), .rx_event(tv), .rx_slot(slot), .rx_beat(beat), .rx_payload(tp),
        .compiled_identity(ci_p), .compiled_generation(cg_p), .word_valid(wv), .word_tag(wtag), .word_data(wdata),
        .word_identity(wid), .word_generation(wgen), .word_slot(wslot), .word_index(widx), .fault(rxf));
    reg [63:0] hostm [0:GOLD_NTOK-1];
    reg [63:0] expm [0:36*GOLD_NTOK-1];
    initial begin $readmemh({GOLD, "/host.memh"}, hostm); $readmemh({GOLD, "/expect.memh"}, expm); end
    function automatic [511:0] word(input integer t, input integer l, input integer b);
        word = {16{t[7:0], l[7:0], b[7:0], 8'h5a}};
    endfunction
    integer cyc = 0, tok = -1, lrun = -1, t_tok = 0, t_cs = 0, errs = 0, words = 0, runs = 0, b;
    integer exp_tok = -1, exp_l = -1, exp_b = 0;
    reg seen_tok = 0;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        // ---- sequencer runs vs the golden program calendar
        if (cal_start && layer != 6'h3f) begin
            if (layer == 0) begin
                if (tok >= 0 && cyc - t_tok != GOLD_PERIOD) begin errs = errs + 1; $display("ERR token period %0d", cyc - t_tok); end
                tok = tok + 1; t_tok = cyc;
            end else if (layer != lrun + 1 || cyc - t_tok != GOLD_START[20*layer +: 20]) begin
                errs = errs + 1; $display("ERR run layer %0d at token edge %0d (golden %0d)", layer, cyc - t_tok, GOLD_START[20*layer +: 20]);
            end
            lrun = layer; t_cs = cyc; runs = runs + 1;
        end
        // ---- HOST cohort for token tok, CH edges after its token cal_start (CH < 0 never used)
        if (tok >= 0 && tok < GOLD_NTOK && cyc == t_tok + CH) begin
            host_tag <= hostm[tok][58:0]; host_gen <= hostm[tok][60:59];
        end
        // ---- compute KVN sends: the word's receive edge at the end = t_cs + END_START + rx_out (x3 two edges earlier)
        x3 <= 0; slot <= 0;
        if (tok >= 0 && tok < GOLD_NTOK && lrun >= 0)
            for (b = 0; b < 4; b = b + 1)
                if (cyc + 2 == t_cs + END_START + (lrun == 0 ? KVN_L0_OUT[16*b +: 16] : KVN_LN_OUT[16*b +: 16])) begin
                    x3 <= {1'b1, 3'd2, 8'(b), word(tok, lrun, b)};
                    x3_id <= {hostm[tok][58:43], 6'(lrun + 1), hostm[tok][36:6], 6'd0};
                    x3_gen <= hostm[tok][60:59];
                end
        slot <= x3[523]; beat <= 5'(x3[519:512]);
        if (wv) begin
            if (wid !== expm[36*tok + lrun][58:0] || wgen !== expm[36*tok + lrun][60:59] || wdata !== word(tok, lrun, widx) ||
                wtag[10:8] !== 3'd2) begin
                errs = errs + 1; $display("ERR KVN word tok %0d layer %0d idx %0d id %h exp %h", tok, lrun, widx, wid, expm[36*tok + lrun][58:0]);
            end
            words = words + 1;
        end
    end
    initial begin
        repeat (8) @(posedge ck);
        rst_n = 1;
        wait (cal_ready);
        repeat (4) @(posedge ck);
        epoch_go = 1;
        wait (tok == GOLD_NTOK - 1 && lrun == 35);
        repeat (2000) @(posedge ck);
        if (rxf || txf || sq_fault) begin errs = errs + 1; $display("ERR fault kvn_rx %0d kvn_tx %0d seq %0d", rxf, txf, sq_fault); end
        if (words != 36 * 4 * GOLD_NTOK) begin errs = errs + 1; $display("ERR words %0d != %0d", words, 36 * 4 * GOLD_NTOK); end
        if (runs != 36 * GOLD_NTOK) begin errs = errs + 1; $display("ERR runs %0d", runs); end
        $display("KVN_CTX %s tokens=%0d runs=%0d words=%0d errors=%0d mut=%0d ch=%0d kvn_rx_fault=%0d",
                 errs == 0 ? "PASS" : "FAIL", GOLD_NTOK, runs, words, errs, MUT, CH, rxf);
        $finish;
    end
    initial begin #2000000; $display("KVN_CTX FAIL timeout tok=%0d lrun=%0d", tok, lrun); $finish; end
endmodule
