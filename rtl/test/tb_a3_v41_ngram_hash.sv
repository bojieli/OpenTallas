`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Independent scoreboard for ot_a3_dma_ngram_hash (DMA.NGRAM_HASH, sub 0x04).
//
// Every expected row id, residue and dividend in cases.hex comes from
// runtime/reference/engram.py's ngram_row_ids through
// tools/build_a3_v41_ngram_hash_vectors.py.  Nothing here recomputes the hash,
// so a shared mistake between bench and device is not possible.
//
// What this bench proves, beyond value equality:
//
//   * LATENCY equals the device's own info_pipe_stages -- the bench measures it
//     and compares against the port, so neither side mirrors a constant;
//   * INITIATION INTERVAL ONE: in an unstalled burst in_ready never drops and
//     the first and last outputs are exactly (cases-1) cycles apart;
//   * the same vectors survive a stalling consumer with no loss, duplication or
//     reordering (the tag is the case index);
//   * an operand write while beats are in flight is refused, and the in-flight
//     beats still retire against the configuration they were issued under;
//   * every configuration's error report matches what the vector set predicts,
//     including a column whose bucket range leaves the table and a pad id at the
//     vocabulary extent;
//   * the device's sticky Barrett bound status is clear at the end.
//
// Simulation cycles here are verification cost.  They are not an architectural
// latency, not a token time and not a TPOT.
// ---------------------------------------------------------------------------
module tb_a3_v41_ngram_hash;
    // Vector-file limits.  The file header carries the real counts and the bench
    // FAILS if they exceed these, so a grown vector set can never be silently
    // truncated into a smaller campaign.
    parameter integer MAX_CONFIG_WORDS = 8192;
    parameter integer MAX_CASE_WORDS   = 262144;
    parameter integer CASE_WORDS       = 16;
    parameter integer FILE_HEADER      = 8;
    parameter integer CONFIG_HEADER    = 8;
    parameter integer MAGIC            = 32'h4E474831;
    parameter integer TIMEOUT_CYCLES   = 400000;

    // Device geometry under test (the module defaults).
    parameter integer ID_W       = 32;
    parameter integer MULT_W     = 48;
    parameter integer MOD_W      = 32;
    parameter integer ROW_W      = 32;
    parameter integer DIVIDEND_W = 63;
    parameter integer ORDER_MAX  = 4;
    parameter integer ORDER_MIN  = 2;
    parameter integer NUM_HEADS  = 8;
    parameter integer TAG_W      = 16;
    parameter integer NUM_COLS   = (ORDER_MAX - ORDER_MIN + 1) * NUM_HEADS;
    parameter integer ORDER_W    = 3;
    parameter integer HEAD_W     = 3;

    reg [31:0] cfg_words  [0:MAX_CONFIG_WORDS-1];
    reg [31:0] case_words [0:MAX_CASE_WORDS-1];
    reg [1023:0] config_path;
    reg [1023:0] cases_path;

    reg clk;
    reg rst_n;
    initial clk = 1'b0;
    always #5 clk = ~clk;

    integer cycle;
    always @(posedge clk) cycle = cycle + 1;

    reg                  cfg_we;
    reg [3:0]            cfg_kind;
    reg [15:0]           cfg_index;
    reg [63:0]           cfg_data;
    reg                  cfg_start;
    wire                 cfg_busy;
    wire                 cfg_done;
    wire                 cfg_error;
    wire [3:0]           cfg_error_code;

    reg                  in_valid;
    wire                 in_ready;
    reg [ORDER_MAX*ID_W-1:0] in_ids;
    reg [ORDER_MAX-1:0]  in_blocked;
    reg [ORDER_W-1:0]    in_order;
    reg [HEAD_W-1:0]     in_head;
    reg [TAG_W-1:0]      in_tag;

    wire                 out_valid;
    reg                  out_ready;
    wire [ROW_W-1:0]     out_row;
    wire [3:0]           out_refuse;
    wire [TAG_W-1:0]     out_tag;
    wire [ORDER_W-1:0]   out_order;
    wire [HEAD_W-1:0]    out_head;
    wire [DIVIDEND_W-1:0] out_dividend;
    wire [MOD_W-1:0]     out_residue;
    wire [15:0]          info_pipe_stages;
    wire [15:0]          info_num_columns;
    wire                 status_bound_error;

    ot_a3_dma_ngram_hash #(
        .ID_W(ID_W), .MULT_W(MULT_W), .MOD_W(MOD_W), .ROW_W(ROW_W),
        .DIVIDEND_W(DIVIDEND_W), .ORDER_MAX(ORDER_MAX), .ORDER_MIN(ORDER_MIN),
        .NUM_HEADS(NUM_HEADS), .MUL_DIGIT_W(8), .TAG_W(TAG_W)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .cfg_we(cfg_we), .cfg_kind(cfg_kind), .cfg_index(cfg_index),
        .cfg_data(cfg_data), .cfg_start(cfg_start),
        .cfg_busy(cfg_busy), .cfg_done(cfg_done),
        .cfg_error(cfg_error), .cfg_error_code(cfg_error_code),
        .in_valid(in_valid), .in_ready(in_ready), .in_ids(in_ids),
        .in_blocked(in_blocked), .in_order(in_order), .in_head(in_head),
        .in_tag(in_tag),
        .out_valid(out_valid), .out_ready(out_ready), .out_row(out_row),
        .out_refuse(out_refuse), .out_tag(out_tag), .out_order(out_order),
        .out_head(out_head), .out_dividend(out_dividend),
        .out_residue(out_residue),
        .info_pipe_stages(info_pipe_stages), .info_num_columns(info_num_columns),
        .status_bound_error(status_bound_error)
    );

    integer failures;
    integer checks;
    integer cases_run;
    integer outputs_checked;
    integer refusals_seen;
    integer refusal_code_count [0:15];
    integer expected_code_count [0:15];
    integer expected_refusals;
    integer guard_cases;
    integer ready_drops;
    integer ii_violations;
    integer stall_events;
    integer configs_run;
    integer config_error_reports;
    integer recip_cycles_total;
    integer recip_cycles_max;
    integer observed_latency;
    integer guard_checks;
    integer ci;
    integer num_configs;
    integer total_cases;

    task fail;
        input [255:0] label;
        begin
            failures = failures + 1;
            if (failures < 40)
                $display("FAIL config=%0d %0s", configs_run, label);
        end
    endtask

    task expect_eq;
        input [255:0] label;
        input [63:0]  got;
        input [63:0]  wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL config=%0d case=%0d %0s got=%h wanted=%h",
                             configs_run, ci, label, got, wanted);
            end
        end
    endtask

    // ------------------------------------------------------------------
    // Vector-file navigation.  cfg_base(c) is the word index of config c's
    // header; case_base(c) is its first case's word index.
    // ------------------------------------------------------------------
    integer cfg_base_v [0:63];
    integer case_base_v [0:63];
    integer cfg_case_count [0:63];

    task scan_configs;
        integer c;
        integer word;
        integer cases_seen;
        begin
            word = FILE_HEADER;
            cases_seen = 0;
            for (c = 0; c < num_configs; c = c + 1) begin
                cfg_base_v[c] = word;
                cfg_case_count[c] = cfg_words[word];
                case_base_v[c] = cases_seen * CASE_WORDS;
                cases_seen = cases_seen + cfg_case_count[c];
                word = word + CONFIG_HEADER + 2*ORDER_MAX + 2*NUM_COLS;
            end
            if (cases_seen != total_cases) begin
                $display("FAIL vector header: %0d cases in configs, %0d declared",
                         cases_seen, total_cases);
                failures = failures + 1;
            end
        end
    endtask

    task cfg_write;
        input [3:0]  kind;
        input [15:0] index;
        input [63:0] data;
        begin
            @(negedge clk);
            cfg_we    = 1'b1;
            cfg_kind  = kind;
            cfg_index = index;
            cfg_data  = data;
            @(posedge clk);
            @(negedge clk);
            cfg_we = 1'b0;
        end
    endtask

    task load_config;
        input integer c;
        integer base;
        integer m;
        integer col;
        reg [63:0] value;
        begin
            base = cfg_base_v[c];
            cfg_write(4'd0, 16'd0, {32'd0, cfg_words[base+1]});   // table rows
            cfg_write(4'd1, 16'd0, {32'd0, cfg_words[base+2]});   // pad id
            cfg_write(4'd2, 16'd0, {32'd0, cfg_words[base+3]});   // vocabulary
            for (m = 0; m < ORDER_MAX; m = m + 1) begin
                value = {cfg_words[base+CONFIG_HEADER+2*m+1],
                         cfg_words[base+CONFIG_HEADER+2*m]};
                cfg_write(4'd3, m[15:0], value);
            end
            for (col = 0; col < NUM_COLS; col = col + 1) begin
                cfg_write(4'd4, col[15:0],
                          {32'd0, cfg_words[base+CONFIG_HEADER+2*ORDER_MAX+2*col]});
                cfg_write(4'd5, col[15:0],
                          {32'd0, cfg_words[base+CONFIG_HEADER+2*ORDER_MAX+2*col+1]});
            end
        end
    endtask

    task start_config;
        input integer c;
        integer base;
        integer guard;
        begin
            base = cfg_base_v[c];
            @(negedge clk);
            cfg_start = 1'b1;
            @(posedge clk);
            @(negedge clk);
            cfg_start = 1'b0;
            guard = 0;
            while (!cfg_done && guard < TIMEOUT_CYCLES) begin
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
            end
            if (!cfg_done) fail("configuration never completed");
            recip_cycles_total = recip_cycles_total + guard;
            if (guard > recip_cycles_max) recip_cycles_max = guard;
            ci = -1;
            expect_eq("cfg_error", {63'd0, cfg_error}, {63'd0, cfg_words[base+6][0]});
            expect_eq("cfg_error_code", {60'd0, cfg_error_code},
                      {32'd0, cfg_words[base+7]});
            if (cfg_error) config_error_reports = config_error_reports + 1;
            expect_eq("device column count", {48'd0, info_num_columns},
                      {32'd0, NUM_COLS[31:0]});
            if (cfg_busy) fail("cfg_busy still asserted after cfg_done");
        end
    endtask

    // ------------------------------------------------------------------
    // Case drive and check.
    // ------------------------------------------------------------------
    task drive_case;
        input integer index;       // absolute case index
        integer base;
        integer j;
        begin
            base = index * CASE_WORDS;
            in_order   = case_words[base][ORDER_W-1:0];
            in_head    = case_words[base+1][HEAD_W-1:0];
            in_blocked = case_words[base+2][ORDER_MAX-1:0];
            for (j = 0; j < ORDER_MAX; j = j + 1)
                in_ids[j*ID_W +: ID_W] = case_words[base+3+j];
            in_tag = index[TAG_W-1:0];
        end
    endtask

    task drive_poison;
        integer j;
        begin
            in_order   = 3'd5;
            in_head    = 3'd6;
            in_blocked = {ORDER_MAX{1'b1}};
            for (j = 0; j < ORDER_MAX; j = j + 1)
                in_ids[j*ID_W +: ID_W] = 32'hA5A5_5A5A;
            in_tag = 16'hFFFF;
        end
    endtask

    task check_output;
        input integer index;
        integer base;
        reg [DIVIDEND_W-1:0] want_dividend;
        begin
            base = index * CASE_WORDS;
            ci = index;
            want_dividend = {case_words[base+11][DIVIDEND_W-33:0], case_words[base+10]};
            expect_eq("out_tag", {48'd0, out_tag}, {48'd0, index[TAG_W-1:0]});
            expect_eq("out_order", {61'd0, out_order},
                      {61'd0, case_words[base][ORDER_W-1:0]});
            expect_eq("out_head", {61'd0, out_head},
                      {61'd0, case_words[base+1][HEAD_W-1:0]});
            expect_eq("out_refuse", {60'd0, out_refuse}, {32'd0, case_words[base+7]});
            expect_eq("out_row", {32'd0, out_row}, {32'd0, case_words[base+8]});
            expect_eq("out_residue", {32'd0, out_residue}, {32'd0, case_words[base+9]});
            expect_eq("out_dividend", {1'b0, out_dividend}, {1'b0, want_dividend});
            outputs_checked = outputs_checked + 1;
            if (case_words[base+7] != 32'd0) begin
                expected_refusals = expected_refusals + 1;
                expected_code_count[case_words[base+7][3:0]] =
                    expected_code_count[case_words[base+7][3:0]] + 1;
            end
            if (out_refuse != 4'd0) begin
                refusals_seen = refusals_seen + 1;
                refusal_code_count[out_refuse] = refusal_code_count[out_refuse] + 1;
            end
        end
    endtask

    // One isolated beat: measure the accept-to-out_valid latency and compare it
    // against the device's own published stage count, with the inputs poisoned
    // for the whole flight.
    task phase_latency;
        input integer first_case;
        integer guard;
        begin
            @(negedge clk);
            out_ready = 1'b0;
            in_valid  = 1'b1;
            drive_case(first_case);
            while (!in_ready) begin
                @(posedge clk);
                @(negedge clk);
            end
            @(posedge clk);          // beat accepted here
            @(negedge clk);
            in_valid = 1'b0;
            drive_poison;
            guard = 1;
            while (!out_valid && guard < TIMEOUT_CYCLES) begin
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
            end
            if (!out_valid) fail("isolated beat never produced a result");
            observed_latency = guard;
            ci = first_case;
            expect_eq("latency equals info_pipe_stages", {32'd0, guard[31:0]},
                      {48'd0, info_pipe_stages});
            //: The result holds while the consumer is not ready.
            repeat (3) begin
                expect_eq("held valid", {63'd0, out_valid}, 64'd1);
                @(posedge clk);
                @(negedge clk);
            end
            out_ready = 1'b1;
            check_output(first_case);
            @(posedge clk);
            @(negedge clk);
            out_ready = 1'b0;
            expect_eq("result consumed", {63'd0, out_valid}, 64'd0);
            cases_run = cases_run + 1;
        end
    endtask

    // The whole configuration, back to back.  stall_mode 0 is the full-rate
    // initiation-interval test; stall_mode 1 exercises the elastic boundary.
    task phase_burst;
        input integer first_case;
        input integer count;
        input integer stall_mode;
        integer sent;
        integer taken;
        integer first_cycle;
        integer last_cycle;
        integer guard;
        begin
            sent = 0;
            taken = 0;
            first_cycle = -1;
            last_cycle = -1;
            guard = 0;
            @(negedge clk);
            while (taken < count && guard < TIMEOUT_CYCLES) begin
                if (stall_mode == 0) out_ready = 1'b1;
                else begin
                    out_ready = ((cycle % 7) < 4);
                    if (!out_ready) stall_events = stall_events + 1;
                end
                if (sent < count) begin
                    in_valid = 1'b1;
                    drive_case(first_case + sent);
                end else begin
                    in_valid = 1'b0;
                    drive_poison;
                end
                if (out_valid && out_ready) begin
                    check_output(first_case + taken);
                    if (first_cycle < 0) first_cycle = cycle;
                    last_cycle = cycle;
                    taken = taken + 1;
                end
                if (in_valid && in_ready) sent = sent + 1;
                else if (in_valid && !in_ready && stall_mode == 0)
                    ready_drops = ready_drops + 1;
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
            end
            in_valid  = 1'b0;
            out_ready = 1'b0;
            if (taken != count) fail("burst did not retire every case");
            //: Initiation interval one: count results occupy exactly count
            //: consecutive cycles.
            if (stall_mode == 0 && count > 1 &&
                (last_cycle - first_cycle) != (count - 1)) begin
                ii_violations = ii_violations + 1;
                $display("FAIL config=%0d initiation interval: %0d results span %0d cycles",
                         configs_run, count, last_cycle - first_cycle + 1);
                failures = failures + 1;
            end
            cases_run = cases_run + count;
        end
    endtask

    // An operand write while beats are in flight must be refused, and the
    // in-flight beats must still retire against the configuration they were
    // issued under.
    task phase_write_guard;
        input integer first_case;
        input integer count;
        integer sent;
        integer taken;
        integer guard;
        begin
            sent = 0;
            taken = 0;
            guard = 0;
            @(negedge clk);
            out_ready = 1'b0;
            while (sent < count) begin
                in_valid = 1'b1;
                drive_case(first_case + sent);
                if (in_ready) sent = sent + 1;
                @(posedge clk);
                @(negedge clk);
            end
            in_valid = 1'b0;
            drive_poison;
            //: Beats are in flight: a write must be rejected and reported.
            expect_eq("guard precondition: no error yet", {63'd0, cfg_error}, 64'd0);
            cfg_write(4'd4, 16'd0, 64'd7);
            guard_checks = guard_checks + 1;
            expect_eq("write while active refused", {63'd0, cfg_error}, 64'd1);
            expect_eq("write refusal code", {60'd0, cfg_error_code}, 64'd1);
            //: The write was rejected, so the configuration is untouched and the
            //: device keeps serving: admission stays open and the in-flight
            //: beats retire against the values they were issued under.
            expect_eq("admission survives a refused write",
                      {63'd0, in_ready}, 64'd1);
            out_ready = 1'b1;
            while (taken < count && guard < TIMEOUT_CYCLES) begin
                if (out_valid && out_ready) begin
                    check_output(first_case + taken);
                    taken = taken + 1;
                end
                @(posedge clk);
                @(negedge clk);
                guard = guard + 1;
            end
            out_ready = 1'b0;
            if (taken != count) fail("in-flight beats lost after a refused write");
            cases_run = cases_run + count;
            guard_cases = count;
            //: And the configuration is still the one that was loaded: the same
            //: cases must still produce the same row ids after the refusal.
            phase_burst(first_case, count, 0);
            guard_cases = guard_cases + count;
        end
    endtask

    integer rc;
    initial begin
        failures = 0;
        checks = 0;
        cases_run = 0;
        outputs_checked = 0;
        refusals_seen = 0;
        ready_drops = 0;
        ii_violations = 0;
        stall_events = 0;
        configs_run = 0;
        config_error_reports = 0;
        recip_cycles_total = 0;
        recip_cycles_max = 0;
        observed_latency = 0;
        guard_checks = 0;
        cycle = 0;
        ci = -1;
        expected_refusals = 0;
        guard_cases = 0;
        for (rc = 0; rc < 16; rc = rc + 1) begin
            refusal_code_count[rc] = 0;
            expected_code_count[rc] = 0;
        end

        cfg_we = 1'b0;
        cfg_kind = 4'd0;
        cfg_index = 16'd0;
        cfg_data = 64'd0;
        cfg_start = 1'b0;
        in_valid = 1'b0;
        in_ids = {(ORDER_MAX*ID_W){1'b0}};
        in_blocked = {ORDER_MAX{1'b0}};
        in_order = {ORDER_W{1'b0}};
        in_head = {HEAD_W{1'b0}};
        in_tag = {TAG_W{1'b0}};
        out_ready = 1'b0;
        rst_n = 1'b0;

        if (!$value$plusargs("CONFIG=%s", config_path))
            config_path = "testdata/rtl/a3_v41_ngram_hash/config.hex";
        if (!$value$plusargs("CASES=%s", cases_path))
            cases_path = "testdata/rtl/a3_v41_ngram_hash/cases.hex";
        $readmemh(config_path, cfg_words);
        $readmemh(cases_path, case_words);

        if (cfg_words[0] !== MAGIC) begin
            $display("FAIL vector magic %h is not %h", cfg_words[0], MAGIC);
            failures = failures + 1;
        end
        num_configs = cfg_words[1];
        total_cases = cfg_words[2];
        if (cfg_words[3] !== CASE_WORDS) fail("vector case stride differs");
        if (cfg_words[4] !== ORDER_MAX) fail("vector token slot count differs");
        if (cfg_words[5] !== ORDER_MIN) fail("vector ORDER_MIN differs");
        if (cfg_words[6] !== ORDER_MAX) fail("vector ORDER_MAX differs");
        if (cfg_words[7] !== NUM_HEADS) fail("vector head count differs");
        if (total_cases * CASE_WORDS > MAX_CASE_WORDS)
            fail("vector set exceeds the bench case array");
        if (num_configs > 64) fail("vector set exceeds the bench config table");
        scan_configs;

        repeat (4) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        //: Before any configuration the device must refuse admission.
        expect_eq("no admission before configuration", {63'd0, in_ready}, 64'd0);
        expect_eq("no result before configuration", {63'd0, out_valid}, 64'd0);

        for (configs_run = 0; configs_run < num_configs; configs_run = configs_run + 1)
        begin
            load_config(configs_run);
            start_config(configs_run);
            phase_latency(case_base_v[configs_run] / CASE_WORDS);
            phase_burst(case_base_v[configs_run] / CASE_WORDS,
                        cfg_case_count[configs_run], 0);
            phase_burst(case_base_v[configs_run] / CASE_WORDS,
                        cfg_case_count[configs_run], 1);
            if (configs_run == 0)
                phase_write_guard(case_base_v[configs_run] / CASE_WORDS, 8);
        end

        expect_eq("sticky Barrett bound status", {63'd0, status_bound_error}, 64'd0);
        for (rc = 0; rc < 16; rc = rc + 1) begin
            ci = -1;
            expect_eq("refusal code census", {32'd0, refusal_code_count[rc][31:0]},
                      {32'd0, expected_code_count[rc][31:0]});
        end
        if (ready_drops != 0) begin
            $display("FAIL in_ready dropped %0d times in an unstalled burst",
                     ready_drops);
            failures = failures + 1;
        end

        $display("NGRAM_SUMMARY configs=%0d cases=%0d outputs=%0d refusals=%0d expected_refusals=%0d code1=%0d code2=%0d code3=%0d code4=%0d code5=%0d code6=%0d cfg_errors=%0d latency=%0d stalls=%0d guard_cases=%0d guard_checks=%0d recip_max=%0d recip_total=%0d",
                 num_configs, total_cases, outputs_checked, refusals_seen,
                 expected_refusals,
                 refusal_code_count[1], refusal_code_count[2],
                 refusal_code_count[3], refusal_code_count[4],
                 refusal_code_count[5], refusal_code_count[6],
                 config_error_reports, observed_latency, stall_events,
                 guard_cases, guard_checks, recip_cycles_max, recip_cycles_total);
        if (failures != 0) begin
            $display("FAIL a3_v41_ngram_hash failures=%0d checks=%0d", failures, checks);
            $fatal(1);
        end
        $display("PASS a3_v41_ngram_hash configs=%0d cases=%0d outputs=%0d refusals=%0d checks=%0d ii_violations=%0d",
                 num_configs, total_cases, outputs_checked, refusals_seen,
                 checks, ii_violations);
        $finish;
    end
endmodule
