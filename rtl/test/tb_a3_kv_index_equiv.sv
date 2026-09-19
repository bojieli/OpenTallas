`timescale 1ns/1ps
// Equivalence of the reduction-tree ot_a3_attention_kv_index against the
// serial-accumulate version it replaces.  The two modules see IDENTICAL inputs
// and every output must agree on every vector.
//
// The published function depends on the index block only through two per-lane
// facts -- is the lane padding, and is a live lane's row at or past cfg_kv_rows --
// so the vector space that matters is (mask, range) pairs, and this drives them
// directly.  At SLOTS=8 that space is 2^8 x 2^8 and is enumerated EXHAUSTIVELY;
// the 64-lane instance is then driven with the same generator over random and
// structured patterns, including every prefix-of-ones mask (the admitted family)
// and every single-gap mask (the refused family the local test has to catch).
module tb_kv_equiv #(parameter integer SLOTS = 8) ;
    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_kv_rows = 32'd512;
    reg [SLOTS*32-1:0] indices;
    wire busy_a, done_a, busy_b, done_b;
    wire [SLOTS-1:0] lv_a, lv_b;
    wire [31:0] lc_a, lc_b;
    wire [7:0] ec_a, ec_b;

    integer errors = 0, checked = 0;
    integer i, m, r, t;
    reg [SLOTS-1:0] mask, range;

    ot_a3_attention_kv_index_ref #(.SLOTS(SLOTS)) ref_i (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_kv_rows(cfg_kv_rows),
        .indices(indices), .busy(busy_a), .done(done_a),
        .lane_valid(lv_a), .live_count(lc_a), .error_code(ec_a));
    ot_a3_attention_kv_index #(.SLOTS(SLOTS)) new_i (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_kv_rows(cfg_kv_rows),
        .indices(indices), .busy(busy_b), .done(done_b),
        .lane_valid(lv_b), .live_count(lc_b), .error_code(ec_b));

    always #1 clk = ~clk;

    task drive; begin
        for (i = 0; i < SLOTS; i = i + 1) begin
            if (!mask[i])      indices[i*32 +: 32] = 32'hffff_ffff;
            else if (range[i]) indices[i*32 +: 32] = cfg_kv_rows + i;
            else               indices[i*32 +: 32] = i;
        end
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        @(negedge clk);
        checked = checked + 1;
        if (lv_a !== lv_b || lc_a !== lc_b || ec_a !== ec_b) begin
            errors = errors + 1;
            if (errors <= 8)
                $display("FAIL mask=%h range=%h  ref(lv=%h lc=%0d ec=%h) new(lv=%h lc=%0d ec=%h)",
                         mask, range, lv_a, lc_a, ec_a, lv_b, lc_b, ec_b);
        end
    end endtask

    initial begin
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;
        if (SLOTS <= 8) begin
            for (m = 0; m < (1 << SLOTS); m = m + 1)
                for (r = 0; r < (1 << SLOTS); r = r + 1) begin
                    mask = m[SLOTS-1:0]; range = r[SLOTS-1:0]; drive;
                end
        end else begin
            //: every prefix-of-ones mask, which is the whole admitted family
            for (m = 0; m <= SLOTS; m = m + 1) begin
                mask = ({{SLOTS{1'b0}}, {SLOTS{1'b1}}} >> (SLOTS - m)) & {SLOTS{1'b1}};
                if (m == 0) mask = {SLOTS{1'b0}};
                range = {SLOTS{1'b0}}; drive;
                range = {SLOTS{1'b1}}; drive;
                range = $random; drive;
            end
            //: every single-gap mask: a prefix of ones with one lane punched out,
            //: which is exactly what the local trailing-run test must refuse
            for (m = 1; m <= SLOTS; m = m + 1)
                for (i = 0; i < m; i = i + 1) begin
                    mask = {SLOTS{1'b0}};
                    for (t = 0; t < m; t = t + 1) mask[t] = 1'b1;
                    mask[i] = 1'b0;
                    range = {SLOTS{1'b0}}; drive;
                end
            for (t = 0; t < 4000; t = t + 1) begin
                mask = {$random, $random}; range = {$random, $random}; drive;
            end
        end
        if (errors == 0)
            $display("PASS kv_equiv SLOTS=%0d: %0d vectors, the reduction tree and the serial accumulate agree on every output",
                     SLOTS, checked);
        else
            $display("FAIL kv_equiv SLOTS=%0d: %0d of %0d vectors disagree", SLOTS, errors, checked);
        $finish;
    end
endmodule
