`timescale 1ns/1ps
// ROUTE.INDEX_TOPK against the reference's own selection.
//
// tools/build_a3_index_topk_vectors.py calls ``index_topk_indices`` from
// runtime/reference/selection.py, which applies the causal compressed-position
// mask, selects by ``TIE_POLICY =
// score_descending_then_logical_index_ascending``, adds the view offset and
// turns a masked selection into -1. The expectations are that function's own
// output rows, in its own order.
module tb_a3_index_topk;
    localparam integer TOPK_MAX = 64;

    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_candidates, cfg_top_k, cfg_valid_count;
    reg [31:0] cfg_offset, cfg_score_base, cfg_out_base;
    wire score_rd_en, out_we;
    wire [31:0] score_rd_addr, out_addr, out_data;
    reg  [31:0] score_rd_data;
    wire busy, done;
    wire [7:0] error_code;
    wire [31:0] selected_count, candidates_read;

    localparam integer SCORE_BASE = 0;
    localparam integer OUT_BASE = 4096;
    reg [31:0] mem [0:8191];
    reg [31:0] emem [0:1023];
    integer j, n, c, errors = 0, shown = 0, fh, code;
    integer candidates, top_k, valid, offset, expect_count;
    reg [1023:0] name, path;

    ot_a3_route_index_topk #(.TOPK_MAX(TOPK_MAX), .INDEX_BITS(16)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_candidates(cfg_candidates), .cfg_top_k(cfg_top_k),
        .cfg_valid_count(cfg_valid_count), .cfg_offset(cfg_offset),
        .cfg_score_base(cfg_score_base), .cfg_out_base(cfg_out_base),
        .score_rd_en(score_rd_en), .score_rd_addr(score_rd_addr),
        .score_rd_data(score_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .selected_count(selected_count), .candidates_read(candidates_read)
    );

    always #1 clk = ~clk;
    always @(posedge clk) if (score_rd_en) score_rd_data <= mem[score_rd_addr[12:0]];
    always @(posedge clk) if (out_we) mem[out_addr[12:0]] <= out_data;

    localparam integer WATCHDOG = 4_000_000;
    integer watchdog;
    initial watchdog = 0;
    always @(posedge clk) begin
        watchdog <= watchdog + 1;
        if (watchdog > WATCHDOG) begin
            $display("FAIL watchdog"); $finish;
        end
    end

    task go; begin
        watchdog = 0;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", n);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < n; c = c + 1) begin
            code = $fscanf(fh, "%s %d %d %d %d %d\n",
                           name, candidates, top_k, valid, offset, expect_count);
            for (j = 0; j < 8192; j = j + 1) mem[j] = 32'd0;
            for (j = 0; j < 1024; j = j + 1) emem[j] = 32'hDEAD_BEEF;
            $sformat(path, "tk_score_%0d.hex", c); $readmemh(path, mem, SCORE_BASE);
            $sformat(path, "tk_out_%0d.hex", c);   $readmemh(path, emem);
            cfg_candidates = candidates; cfg_top_k = top_k;
            cfg_valid_count = valid; cfg_offset = offset;
            cfg_score_base = SCORE_BASE; cfg_out_base = OUT_BASE;
            go;
            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            if (selected_count !== expect_count) begin
                $display("FAIL %0s selected %0d, reference selected %0d",
                         name, selected_count, expect_count);
                errors = errors + 1;
            end
            //: Every candidate is read exactly once, masked ones included: the
            //: mask changes a score's ORDER, not whether the row was visited.
            if (candidates_read !== candidates) begin
                $display("FAIL %0s read %0d candidates, expected %0d",
                         name, candidates_read, candidates);
                errors = errors + 1;
            end
            for (j = 0; j < expect_count; j = j + 1)
                if (mem[OUT_BASE + j] !== emem[j]) begin
                    if (shown < 16) begin
                        $display("FAIL %0s slot %0d got %08h expected %08h",
                                 name, j, mem[OUT_BASE + j], emem[j]);
                        shown = shown + 1;
                    end
                    errors = errors + 1;
                end
            $display("  %0s: candidates=%0d k=%0d valid=%0d selected=%0d",
                     name, candidates, top_k, valid, selected_count);
        end
        $fclose(fh);

        //: A nonfinite score is a refusal, because ``index_topk_indices``
        //: validates its scores with finite=True. The only negative infinity in
        //: this operator is the one the mask introduces.
        for (j = 0; j < 16; j = j + 1) mem[SCORE_BASE + j] = 32'h0000_3f00;
        mem[SCORE_BASE + 5] = 32'h0000_ff80;
        cfg_candidates = 16; cfg_top_k = 8; cfg_valid_count = 16; cfg_offset = 0;
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SELECT_NONFINITE) begin
            $display("FAIL a -inf score gave %0h", error_code);
            errors = errors + 1;
        end
        mem[SCORE_BASE + 5] = 32'h0000_7fc1;
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SELECT_NONFINITE) begin
            $display("FAIL a NaN score gave %0h", error_code);
            errors = errors + 1;
        end
        mem[SCORE_BASE + 5] = 32'h0000_3f00;
        cfg_top_k = TOPK_MAX + 1; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL k past the array gave %0h", error_code);
            errors = errors + 1;
        end
        cfg_top_k = 8; cfg_valid_count = 32'd17; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL a valid count past the candidates gave %0h", error_code);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_index_topk: %0d rows match index_topk_indices exactly, and a nonfinite score or an unsupportable shape fails closed", n);
        else
            $display("FAIL a3_index_topk: %0d errors", errors);
        $finish;
    end
endmodule
