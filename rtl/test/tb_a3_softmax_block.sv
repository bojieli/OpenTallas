`timescale 1ns/1ps
// ATTENTION.SPARSE's online softmax block against the reference's exponential.
//
// Expectations come from tools/build_a3_softmax_block_vectors.py, which CALLS
// runtime.tensor_accelerator.sparse_attention.exp_cr32 -- the correctly-rounded
// binary32 exponential the operator itself uses -- so this compares the RTL
// against the operator's authority rather than against a model of it.
//
// The generator also asserts, for every case it emits, that each offset handed to
// the exponential is non-positive, because ot_a3_fp32_transcendental_cr_rne
// admits finite x <= 0 only. A case set that broke that would fail closed here
// and the failure would look like arithmetic.
module tb_a3_softmax_block;
    localparam integer LANES = 64;

    reg clk = 0, rst_n = 0, start = 0, cfg_first = 0;
    reg [31:0] cfg_running_max;
    reg [LANES-1:0] lane_valid;
    reg [LANES*32-1:0] scores;
    wire busy, done;
    wire [31:0] updated_max, rescale;
    wire [LANES*32-1:0] probabilities;
    wire [7:0] error_code;
    wire [31:0] exp_count;

    reg [31:0] smem [0:LANES-1];
    reg [31:0] pmem [0:LANES-1];
    integer j, errors = 0, live;
    integer ncases, c, first_i;
    integer fh, code;
    reg [1023:0] name, path;
    reg [31:0] run_exp, upd_exp, res_exp;
    reg [LANES-1:0] mask;

    ot_a3_attention_softmax_block #(.LANES(LANES)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_first(cfg_first), .cfg_running_max(cfg_running_max),
        .lane_valid(lane_valid), .scores(scores),
        .busy(busy), .done(done),
        .updated_max(updated_max), .rescale(rescale),
        .probabilities(probabilities),
        .error_code(error_code), .exp_count(exp_count)
    );

    always #1 clk = ~clk;

    task go; begin
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %h %h %h %b\n", name, first_i,
                           run_exp, upd_exp, res_exp, mask);
            for (j = 0; j < LANES; j = j + 1) begin smem[j] = 0; pmem[j] = 0; end
            $sformat(path, "scores_%0d.hex", c); $readmemh(path, smem);
            $sformat(path, "probs_%0d.hex", c);  $readmemh(path, pmem);
            for (j = 0; j < LANES; j = j + 1) scores[j*32 +: 32] = smem[j];
            lane_valid = mask;
            cfg_first = first_i[0];
            cfg_running_max = run_exp;
            go;

            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            if (updated_max !== upd_exp) begin
                $display("FAIL %0s updated_max got %08h expected %08h",
                         name, updated_max, upd_exp);
                errors = errors + 1;
            end
            if (rescale !== res_exp) begin
                $display("FAIL %0s rescale got %08h expected %08h",
                         name, rescale, res_exp);
                errors = errors + 1;
            end
            for (j = 0; j < LANES; j = j + 1)
                if (probabilities[j*32 +: 32] !== pmem[j]) begin
                    $display("FAIL %0s prob[%0d] got %08h expected %08h",
                             name, j, probabilities[j*32 +: 32], pmem[j]);
                    errors = errors + 1;
                end
            //: ONE EXPONENTIAL PER VALID LANE, PLUS ONE FOR THE RESCALE ON A
            //: LATER BLOCK. An invalid lane must not reach the unit at all --
            //: it would be handed -inf and refuse -- so the count is the check
            //: that the masking happens before the call and not after it.
            live = 0;
            for (j = 0; j < LANES; j = j + 1) if (mask[j]) live = live + 1;
            if (exp_count !== live + (first_i[0] ? 0 : 1)) begin
                $display("FAIL %0s performed %0d exponentials, expected %0d",
                         name, exp_count, live + (first_i[0] ? 0 : 1));
                errors = errors + 1;
            end
            $display("  %0s: max=%08h rescale=%08h exps=%0d",
                     name, updated_max, rescale, exp_count);
        end
        $fclose(fh);

        // -- refusals -------------------------------------------------------
        //: A first block with no valid lane is refused by the reference.
        cfg_first = 1'b1; lane_valid = {LANES{1'b0}};
        cfg_running_max = 32'd0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL empty first block gave %0h", error_code);
            errors = errors + 1;
        end
        //: A nonfinite score is refused before it can poison a maximum.
        lane_valid = {LANES{1'b1}};
        for (j = 0; j < LANES; j = j + 1) scores[j*32 +: 32] = 32'hbf80_0000;
        scores[5*32 +: 32] = 32'h7f80_0000;
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_OPERAND_NONFINITE) begin
            $display("FAIL nonfinite score gave %0h", error_code);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_softmax_block: %0d cases match exp_cr32 on max, rescale and every probability, and 2 refusals fail closed", ncases);
        else
            $display("FAIL a3_softmax_block: %0d errors", errors);
        $finish;
    end
endmodule
