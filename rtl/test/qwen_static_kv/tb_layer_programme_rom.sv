`timescale 1ns/1ps
// Q-KVSYS PVJOIN 2026-10-16: the compiler-constant layer programme qkd_static_kv_layer_programme_img against
//  (a) the boot-loaded qkd_static_kv_layer_programme sealed with the same compiled image (boot.hex, written through its
//      cfg port): every output equal on every edge over NTOK tokens (cycle equivalence), and
//  (b) the KV link calendar sequencer qkd_d2d_cal_seq_pin (committed compiler image): the programme start is the token
//      tok_start (one edge before the token cal_start); every layer run's cal_start (layer l >= 1) must land on stage l + 1's stage_start at the
//      fixed offset of the token run's (the stage frames ARE the link calendar's layer starts), and stage 36 ends at
//      the link program's token_cycles_through_L35.
// Prints one LAYER_ROM line; MUT (ROM variant only) 1..4 must FAIL.
module tb_layer_programme_rom #(parameter integer MUT = 0, parameter integer NTOK = 2, parameter GOLD = "lp") ();
    reg ck = 0;
    always #0.5 ck = ~ck;
    reg rst_n = 0, epoch_go = 0, we = 0;
    reg [8:0] addr = 0; reg [63:0] data = 0;
    wire c_tx_we, c_rx_we, cal_start, cal_seg, cal_ready, running, adm_done, tok_start, sq_fault;
    wire [5:0] c_addr, layer; wire [31:0] c_data;
    qkd_d2d_cal_seq_pin #(.EP_SKEW(3)) u_seq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(1'b0),
        .cfg_tx_we(c_tx_we), .cfg_rx_we(c_rx_we), .cfg_addr(c_addr), .cfg_data(c_data), .cal_start(cal_start),
        .cal_seg(cal_seg), .cal_ready(cal_ready), .running(running), .layer(layer), .adm_done(adm_done),
        .tok_start(tok_start), .fault(sq_fault));
    wire start = tok_start;                       // the die's programme start: the sequencer's token go (one edge before cal_start)
    reg [63:0] boot [0:326];
    initial $readmemh({GOLD, "/boot.hex"}, boot);
    reg [15:0] aep = 16'h0123; reg [17:0] atok = 4242, apos = 77; reg [1:0] agen = 0;
    wire [9:0] ao, bo; wire [5:0] acs, bcs, ast, bst, aly, bly; wire [17:0] atk, btk, aps, bps;
    wire [13:0] acx, bcx; wire [1:0] agn, bgn; wire [3:0] af, bf; wire [7:0] afc, bfc; wire [31:0] aag, bag, atc, btc;
    wire [15:0] aep_, bep_;
    qkd_static_kv_layer_programme ref_ (.ck(ck), .rst_n(rst_n), .cfg_we(we), .cfg_addr(addr), .cfg_data(data),
        .start(start), .authority_valid(1'b1), .programme_authorized(1'b1), .programme_epoch(boot[325][15:0]),
        .programme_digest(boot[324]), .authority_epoch(aep), .authority_token(atok), .authority_position(apos),
        .authority_generation(agen), .ctrl_go(ao[0]), .kgo(ao[1]), .vgo(ao[2]), .attention_issue(ao[3]),
        .attention_run(ao[4]), .writer_start(ao[5]), .link_start(ao[6]), .stage_start(ao[7]), .stage_done(ao[8]),
        .expected_upstream_quiet(ao[9]), .completed_stage(acs), .stage(ast), .layer(aly), .epoch(aep_), .token(atk),
        .position(aps), .ctx_t(acx), .generation(agn), .configured(af[0]), .active(af[1]), .done(af[2]), .fault(af[3]),
        .fault_code(afc), .age(aag), .token_cycles(atc));
    qkd_static_kv_layer_programme_img #(.MUT(MUT)) dut (.ck(ck), .rst_n(rst_n),
        .start(start), .token_epoch_valid(1'b1), .program_ready(1'b1), .program_epoch(boot[325][15:0]),
        .program_digest(boot[324]), .cohort_tag({aep, 6'd0, atok, apos[12:0], 6'd0}), .cohort_gen(agen), .ctrl_go(bo[0]), .kgo(bo[1]), .vgo(bo[2]), .attention_issue(bo[3]),
        .attention_run(bo[4]), .writer_start(bo[5]), .link_start(bo[6]), .stage_start(bo[7]), .stage_done(bo[8]),
        .expected_upstream_quiet(bo[9]), .completed_stage(bcs), .stage(bst), .layer(bly), .epoch(bep_), .token(btk),
        .position(bps), .ctx_t(bcx), .generation(bgn), .configured(bf[0]), .active(bf[1]), .done(bf[2]), .fault(bf[3]),
        .fault_code(bfc), .age(bag), .token_cycles(btc));
    integer cyc = 0, errs = 0, tok = -1, t_tok = 0, run_ofs = -1, runs = 0, stages = 0, dones = 0, events = 0, i;
    integer pending_l = -1, t_run = 0;
    reg booted = 0;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (booted) begin
            // (a) cycle equivalence on every output
            if ({ao, acs, ast, aly, aep_, atk, aps, acx, agn, af, afc, aag, atc} !== {bo, bcs, bst, bly, bep_, btk, bps, bcx, bgn, bf, bfc, bag, btc}) begin
                errs = errs + 1;
                if (errs < 6) $display("ERR equivalence cyc %0d tok %0d ref %b/%0d/%0d img %b/%0d/%0d", cyc, tok, ao, ast, aag, bo, bst, bag);
            end
            events = events + (bo[0] + bo[1] + bo[2] + bo[3] + bo[4] + bo[5] + bo[6]);
            if (bf[3]) begin errs = errs + 1; $display("ERR image programme fault code %h", bfc); end
            // (b) link calendar: layer runs vs stage starts
            if (cal_start && layer == 6'd0) begin tok = tok + 1; t_tok = cyc; end
            if (cal_start && layer != 6'h3f && layer != 6'd0) begin pending_l = layer; t_run = cyc; runs = runs + 1; end
            if (bo[7]) begin
                stages = stages + 1;
                if (bst == 6'd1) begin
                    if (run_ofs < 0) run_ofs = cyc - t_tok;
                    else if (cyc - t_tok != run_ofs) begin errs = errs + 1; $display("ERR stage 1 start offset %0d", cyc - t_tok); end
                end else if (pending_l + 1 != bst || cyc - t_run != run_ofs) begin
                    errs = errs + 1; $display("ERR stage %0d start: layer run %0d at offset %0d (token run offset %0d)", bst, pending_l, cyc - t_run, run_ofs);
                end
            end
            if (bf[2]) dones = dones + 1;
        end
    end
    integer k;
    initial begin
        repeat (8) @(posedge ck);
        rst_n = 1;
        repeat (4) @(posedge ck);
        for (k = 0; k < 327; k = k + 1) begin
            @(negedge ck); we = 1; addr = 9'(k); data = boot[k];
            @(negedge ck); we = 0; @(posedge ck); @(posedge ck);
        end
        if (!af[0] || af[3]) begin errs = errs + 1; $display("ERR boot-loaded reference not sealed (fault %0d code %h)", af[3], afc); end
        booted = 1;
        wait (cal_ready);
        repeat (4) @(posedge ck);
        epoch_go = 1;
        for (k = 0; k < NTOK; k = k + 1) begin
            wait (tok == k);
            @(negedge ck); atok = 18'(4242 + 1009 * (k + 1)); apos = 18'(78 + k); agen = 2'(k + 1);   // next token's context
            wait (dones == k + 1);
        end
        repeat (100) @(posedge ck);
        if (stages != 36 * NTOK) begin errs = errs + 1; $display("ERR stages %0d", stages); end
        if (runs != 35 * NTOK) begin errs = errs + 1; $display("ERR layer runs %0d", runs); end
        if (sq_fault) begin errs = errs + 1; $display("ERR sequencer fault"); end
        $display("LAYER_ROM %s tokens=%0d stages=%0d runs=%0d events=%0d run_ofs=%0d errors=%0d mut=%0d",
                 errs == 0 ? "PASS" : "FAIL", NTOK, stages, runs, events, run_ofs, errs, MUT);
        $finish;
    end
    initial begin #2000000; $display("LAYER_ROM FAIL timeout tok=%0d stages=%0d", tok, stages); $finish; end
endmodule
