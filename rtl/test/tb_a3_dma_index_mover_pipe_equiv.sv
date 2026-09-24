`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The pipelined ot_a3_dma_index_mover against the three-cycles-per-word form it
// replaced (rtl/test/a3_dma_index_mover_ref.sv, the file at the commit before).
//
// Three instances run every case on their own copy of one memory image:
//
//   ref    the original walk
//   pipe   the new walk with ELIDE_IDENTITY_PRIOR = 0: its write stream must
//          equal ref's beat for beat -- address, data and order -- and so must
//          error_code, moved_elements and indices_checked
//   elide  the new walk with ELIDE_IDENTITY_PRIOR = 1: its final memory must
//          equal ref's word for word, and so must the three counters
//
// Each operand image is one memory (index words live in their own), so an
// in-place scatter (prior == out) really does read the words it writes, as it
// does behind the issue bridge.  Cases: gathers and scatters, in place and not,
// repeated indices, an out-of-range index at every position, empty index
// vectors and zero shapes.  Prints CYCLES per instance so the speedup is
// measured by the same bench that proves the equivalence.
// ---------------------------------------------------------------------------
module tb_a3_dma_index_mover_pipe_equiv;
    localparam integer MEM_WORDS = 8192;
    localparam integer IDX_WORDS = 64;
    localparam integer CASES = 400;
    localparam integer MAX_BEATS = 16384;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #1 clk = ~clk;

    reg        start;
    reg        cfg_scatter;
    reg [31:0] cfg_slots, cfg_trailing, cfg_rows;
    reg [31:0] cfg_index_base, cfg_source_base, cfg_prior_base, cfg_out_base;

    // -- three memories, identical at the start of every case ----------------
    reg [31:0] idx_mem [0:IDX_WORDS-1];
    reg [31:0] mem_r [0:MEM_WORDS-1];
    reg [31:0] mem_p [0:MEM_WORDS-1];
    reg [31:0] mem_e [0:MEM_WORDS-1];

    `define MOVER_PORTS(P) \
        wire P``_idx_en, P``_src_en, P``_we, P``_busy, P``_done; \
        wire [31:0] P``_idx_addr, P``_src_addr, P``_addr, P``_data; \
        wire [31:0] P``_moved, P``_checked; \
        wire [7:0] P``_error; \
        reg  [31:0] P``_idx_q, P``_src_q;

    `MOVER_PORTS(r)
    `MOVER_PORTS(p)
    `MOVER_PORTS(e)

    ot_a3_dma_index_mover_ref ref_mover (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_scatter(cfg_scatter),
        .cfg_slots(cfg_slots), .cfg_trailing(cfg_trailing), .cfg_rows(cfg_rows),
        .cfg_index_base(cfg_index_base), .cfg_source_base(cfg_source_base),
        .cfg_prior_base(cfg_prior_base), .cfg_out_base(cfg_out_base),
        .idx_rd_en(r_idx_en), .idx_rd_addr(r_idx_addr), .idx_rd_data(r_idx_q),
        .src_rd_en(r_src_en), .src_rd_addr(r_src_addr), .src_rd_data(r_src_q),
        .out_we(r_we), .out_addr(r_addr), .out_data(r_data),
        .busy(r_busy), .done(r_done), .error_code(r_error),
        .moved_elements(r_moved), .indices_checked(r_checked));

    ot_a3_dma_index_mover #(.ELIDE_IDENTITY_PRIOR(0)) pipe_mover (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_scatter(cfg_scatter),
        .cfg_slots(cfg_slots), .cfg_trailing(cfg_trailing), .cfg_rows(cfg_rows),
        .cfg_index_base(cfg_index_base), .cfg_source_base(cfg_source_base),
        .cfg_prior_base(cfg_prior_base), .cfg_out_base(cfg_out_base),
        .idx_rd_en(p_idx_en), .idx_rd_addr(p_idx_addr), .idx_rd_data(p_idx_q),
        .src_rd_en(p_src_en), .src_rd_addr(p_src_addr), .src_rd_data(p_src_q),
        .out_we(p_we), .out_addr(p_addr), .out_data(p_data),
        .busy(p_busy), .done(p_done), .error_code(p_error),
        .moved_elements(p_moved), .indices_checked(p_checked));

    ot_a3_dma_index_mover #(.ELIDE_IDENTITY_PRIOR(1)) elide_mover (
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_scatter(cfg_scatter),
        .cfg_slots(cfg_slots), .cfg_trailing(cfg_trailing), .cfg_rows(cfg_rows),
        .cfg_index_base(cfg_index_base), .cfg_source_base(cfg_source_base),
        .cfg_prior_base(cfg_prior_base), .cfg_out_base(cfg_out_base),
        .idx_rd_en(e_idx_en), .idx_rd_addr(e_idx_addr), .idx_rd_data(e_idx_q),
        .src_rd_en(e_src_en), .src_rd_addr(e_src_addr), .src_rd_data(e_src_q),
        .out_we(e_we), .out_addr(e_addr), .out_data(e_data),
        .busy(e_busy), .done(e_done), .error_code(e_error),
        .moved_elements(e_moved), .indices_checked(e_checked));

    // Synchronous one-cycle read ports, as the vehicle's banks are.
    always @(posedge clk) begin
        if (r_idx_en) r_idx_q <= idx_mem[r_idx_addr % IDX_WORDS];
        if (p_idx_en) p_idx_q <= idx_mem[p_idx_addr % IDX_WORDS];
        if (e_idx_en) e_idx_q <= idx_mem[e_idx_addr % IDX_WORDS];
        if (r_src_en) r_src_q <= mem_r[r_src_addr % MEM_WORDS];
        if (p_src_en) p_src_q <= mem_p[p_src_addr % MEM_WORDS];
        if (e_src_en) e_src_q <= mem_e[e_src_addr % MEM_WORDS];
        if (r_we) mem_r[r_addr % MEM_WORDS] <= r_data;
        if (p_we) mem_p[p_addr % MEM_WORDS] <= p_data;
        if (e_we) mem_e[e_addr % MEM_WORDS] <= e_data;
    end

    // -- write-stream capture for ref and pipe --------------------------------
    reg [63:0] r_beats [0:MAX_BEATS-1];
    reg [63:0] p_beats [0:MAX_BEATS-1];
    integer r_n, p_n, e_n;
    always @(posedge clk) begin
        if (r_we) begin r_beats[r_n % MAX_BEATS] <= {r_addr, r_data}; r_n <= r_n + 1; end
        if (p_we) begin p_beats[p_n % MAX_BEATS] <= {p_addr, p_data}; p_n <= p_n + 1; end
        if (e_we) e_n <= e_n + 1;
    end

    integer failures = 0;
    integer c, i, w;
    integer r_cycles, p_cycles, e_cycles;
    longint unsigned r_total = 0, p_total = 0, e_total = 0;
    reg r_fin, p_fin, e_fin;
    integer seed = 32'h5eed_1234;
    integer bad_at;
    reg [31:0] v;

    task automatic fail(input [8*64-1:0] what);
        begin
            failures = failures + 1;
            if (failures <= 20)
                $display("FAIL case=%0d %0s scatter=%0d slots=%0d trailing=%0d rows=%0d inplace=%0d",
                         c, what, cfg_scatter, cfg_slots, cfg_trailing, cfg_rows,
                         cfg_prior_base == cfg_out_base);
        end
    endtask

    initial begin
        start = 1'b0;
        v = $urandom(seed);
        r_n = 0; p_n = 0; e_n = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);
        for (c = 0; c < CASES; c = c + 1) begin
            // -- configuration ---------------------------------------------------
            cfg_scatter = $urandom % 2;
            cfg_trailing = 1 + ($urandom % 24);
            cfg_rows = 1 + ($urandom % 40);
            cfg_slots = $urandom % 9;
            if (c % 50 == 7) cfg_trailing = 0;                 // shape fault
            if (c % 50 == 13) cfg_rows = 0;                    // shape fault
            cfg_index_base = $urandom % (IDX_WORDS - 16);
            cfg_source_base = 32'd0;
            cfg_out_base = 32'd2048 + ($urandom % 64);
            cfg_prior_base = ($urandom % 2) ? cfg_out_base : 32'd4096 + ($urandom % 64);
            bad_at = (c % 5 == 0 && cfg_slots != 0) ? ($urandom % cfg_slots) : -1;
            for (i = 0; i < IDX_WORDS; i = i + 1) begin
                v = (cfg_rows == 0) ? 0 : ($urandom % cfg_rows);
                if (c % 3 == 0 && cfg_rows > 2) v = $urandom % 3;   // repeats
                idx_mem[i] = v;
            end
            if (bad_at >= 0) idx_mem[cfg_index_base + bad_at] = cfg_rows + ($urandom % 3);
            for (i = 0; i < MEM_WORDS; i = i + 1) begin
                v = $urandom;
                mem_r[i] = v; mem_p[i] = v; mem_e[i] = v;
            end
            r_n = 0; p_n = 0; e_n = 0;

            // -- run all three to completion -------------------------------------
            @(negedge clk); start = 1'b1;
            @(negedge clk); start = 1'b0;
            r_cycles = 1; p_cycles = 1; e_cycles = 1;
            r_fin = 0; p_fin = 0; e_fin = 0;
            while (!(r_fin && p_fin && e_fin)) begin
                @(posedge clk); #0.1;
                if (!r_fin) begin r_cycles = r_cycles + 1; if (r_done) r_fin = 1; end
                if (!p_fin) begin p_cycles = p_cycles + 1; if (p_done) p_fin = 1; end
                if (!e_fin) begin e_cycles = e_cycles + 1; if (e_done) e_fin = 1; end
                if (r_cycles > 200000) begin fail("timeout"); r_fin = 1; p_fin = 1; e_fin = 1; end
            end
            repeat (3) @(posedge clk);
            r_total = r_total + r_cycles;
            p_total = p_total + p_cycles;
            e_total = e_total + e_cycles;

            // -- verdicts ------------------------------------------------------
            if (p_error !== r_error || e_error !== r_error) fail("error_code");
            if (p_moved !== r_moved || e_moved !== r_moved) fail("moved_elements");
            if (p_checked !== r_checked || e_checked !== r_checked) fail("indices_checked");
            if (p_n != r_n) fail("pipe write-beat count");
            else for (w = 0; w < r_n && w < MAX_BEATS; w = w + 1)
                if (p_beats[w] !== r_beats[w]) begin fail("pipe write stream"); w = r_n; end
            for (i = 0; i < MEM_WORDS; i = i + 1) begin
                if (mem_p[i] !== mem_r[i]) begin fail("pipe final memory"); i = MEM_WORDS; end
            end
            for (i = 0; i < MEM_WORDS; i = i + 1) begin
                if (mem_e[i] !== mem_r[i]) begin fail("elide final memory"); i = MEM_WORDS; end
            end
        end
        $display("CYCLES ref=%0d pipe=%0d elide=%0d", r_total, p_total, e_total);
        if (failures == 0)
            $display("PASS tb_a3_dma_index_mover_pipe_equiv: %0d cases", CASES);
        else
            $display("FAIL tb_a3_dma_index_mover_pipe_equiv: %0d failures", failures);
        $finish;
    end
endmodule
