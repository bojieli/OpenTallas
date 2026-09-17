`timescale 1ns/1ps
// ATTENTION.SPARSE end to end, against the reference's public entry point.
//
// tools/build_a3_attention_sparse_vectors.py calls
// ``sparse_attention_bf16_codes`` -- the whole operator, not a part of it -- so
// the expectations here are the reference's own output codes. Every component
// was already qualified against the reference individually, which means this
// bench exists to catch what those cannot: a composition error. A block run out
// of order, a running maximum carried across a row boundary, a rescale paired
// with the wrong block's probabilities, a probability narrowed twice or not at
// all -- each of those leaves all six component suites green.
module tb_a3_attention_sparse;
    localparam integer LANES = 64;
    localparam integer QUERY_BASE = 0;
    localparam integer INDEX_BASE = 2048;
    localparam integer SINK_BASE = 3072;
    localparam integer KV_BASE = 4096;
    localparam integer OUT_BASE = 16384;

    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_rows, cfg_heads, cfg_head_dim, cfg_slots, cfg_kv_rows;
    wire mem_rd_en, mem_we, sink_rd_en;
    wire [31:0] mem_rd_addr, mem_wr_addr, mem_wr_data, sink_rd_addr;
    reg  [31:0] mem_rd_data, sink_rd_data;
    wire busy, done, nonfinite;
    wire [7:0] error_code;
    wire [31:0] valid_row_reads, padding_lanes_seen, rows_emitted;
    wire [31:0] saturation_count;

    reg [31:0] mem [0:65535];
    reg [31:0] emem [0:16383];
    integer j, errors = 0, shown = 0;
    integer ncases, c, span, heads, head_dim, slots, kv_rows, want_sat;
    integer fh, code, outputs;
    reg [1023:0] name, path;

    ot_a3_attention_sparse #(
        .LANES(LANES), .CHANNELS_MAX(64), .HEADS_MAX(8), .KV_ROWS_MAX(4096)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_query_base(QUERY_BASE), .cfg_kv_base(KV_BASE),
        .cfg_index_base(INDEX_BASE), .cfg_sink_base(SINK_BASE),
        .cfg_out_base(OUT_BASE),
        .cfg_rows(cfg_rows), .cfg_heads(cfg_heads),
        .cfg_head_dim(cfg_head_dim), .cfg_slots(cfg_slots),
        .cfg_kv_rows(cfg_kv_rows),
        //: The shipped descriptors' own score scale, 1/sqrt(512).
        .cfg_scale_code(32'h3d35_04f3),
        .mem_rd_en(mem_rd_en), .mem_rd_addr(mem_rd_addr),
        .mem_rd_data(mem_rd_data),
        //: A second bank in the real device; the same array here, so the
        //: address assertion below still covers it.
        .sink_rd_en(sink_rd_en), .sink_rd_addr(sink_rd_addr),
        .sink_rd_data(sink_rd_data),
        .mem_we(mem_we), .mem_wr_addr(mem_wr_addr), .mem_wr_data(mem_wr_data),
        .busy(busy), .done(done), .error_code(error_code),
        .nonfinite(nonfinite),
        .valid_row_reads(valid_row_reads),
        .padding_lanes_seen(padding_lanes_seen),
        .rows_emitted(rows_emitted), .saturation_count(saturation_count)
    );

    always #1 clk = ~clk;
    //: One registered read port serves all five views, which is the whole point
    //: of the operator's port mux.
    always @(posedge clk) if (mem_rd_en)  mem_rd_data  <= mem[mem_rd_addr[15:0]];
    always @(posedge clk) if (sink_rd_en) sink_rd_data <= mem[sink_rd_addr[15:0]];

    //: EVERY READ MUST LAND INSIDE A BOUND VIEW. An operator that addresses
    //: past its own index view, or gathers at a padding lane's -1, still gets
    //: the right answer here -- the walks substitute the contract's zero element
    //: for an invalid lane, so whatever junk it read is discarded -- and would
    //: go on doing so on a device where that address belongs to another
    //: placement. No numeric check can see this; only the address can. Two
    //: mutations established that: gathering at an ungated -1, and reading the
    //: padded tail of a partial index block, both left every output bit-exact.
    integer stray_reads; initial stray_reads = 0;
    always @(posedge clk) begin
        if (rst_n && sink_rd_en) begin
            if (!(sink_rd_addr >= SINK_BASE &&
                  sink_rd_addr <  SINK_BASE + cfg_heads)) begin
                if (stray_reads < 6)
                    $display("FAIL stray sink read at %0d", sink_rd_addr);
                stray_reads = stray_reads + 1;
            end
        end
        if (rst_n && mem_rd_en) begin
            if (!((mem_rd_addr >= QUERY_BASE &&
                   mem_rd_addr <  QUERY_BASE + cfg_rows*cfg_heads*cfg_head_dim) ||
                  (mem_rd_addr >= INDEX_BASE &&
                   mem_rd_addr <  INDEX_BASE + cfg_rows*cfg_slots) ||
                  (mem_rd_addr >= SINK_BASE &&
                   mem_rd_addr <  SINK_BASE + cfg_heads) ||
                  (mem_rd_addr >= KV_BASE &&
                   mem_rd_addr <  KV_BASE + cfg_kv_rows*cfg_head_dim))) begin
                if (stray_reads < 6)
                    $display("FAIL stray read at %0d, outside every bound view",
                             mem_rd_addr);
                stray_reads = stray_reads + 1;
            end
        end
    end
    always @(posedge clk) if (mem_we)    mem[mem_wr_addr[15:0]] <= mem_wr_data;

    localparam integer WATCHDOG = 60_000_000;
    integer watchdog;
    initial watchdog = 0;
    always @(posedge clk) begin
        watchdog <= watchdog + 1;
        if (watchdog > WATCHDOG) begin
            $display("FAIL watchdog: the operator made no progress in %0d cycles",
                     WATCHDOG);
            $finish;
        end
    end

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %d %d %d %d %d\n",
                           name, span, heads, head_dim, slots, kv_rows, want_sat);
            for (j = 0; j < 65536; j = j + 1) mem[j] = 32'd0;
            for (j = 0; j < 16384; j = j + 1) emem[j] = 32'hDEAD_BEEF;
            $sformat(path, "q_%0d.hex", c);    $readmemh(path, mem, QUERY_BASE);
            $sformat(path, "kv_%0d.hex", c);   $readmemh(path, mem, KV_BASE);
            $sformat(path, "idx_%0d.hex", c);  $readmemh(path, mem, INDEX_BASE);
            $sformat(path, "sink_%0d.hex", c); $readmemh(path, mem, SINK_BASE);
            $sformat(path, "out_%0d.hex", c);  $readmemh(path, emem);

            cfg_rows = span; cfg_heads = heads; cfg_head_dim = head_dim;
            cfg_slots = slots; cfg_kv_rows = kv_rows;
            watchdog = 0;
            @(negedge clk); start = 1; @(negedge clk); start = 0;
            wait (done); @(negedge clk);

            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            if (nonfinite !== 1'b0) begin
                $display("FAIL %0s reported a nonfinite intermediate", name);
                errors = errors + 1;
            end
            outputs = span * heads * head_dim;
            for (j = 0; j < outputs; j = j + 1)
                if (mem[OUT_BASE + j][15:0] !== emem[j][15:0]) begin
                    if (shown < 20) begin
                        $display("FAIL %0s output %0d got %04h expected %04h",
                                 name, j, mem[OUT_BASE + j][15:0], emem[j][15:0]);
                        shown = shown + 1;
                    end
                    errors = errors + 1;
                end
            //: One emitted element per (row, head, channel).
            if (rows_emitted !== outputs) begin
                $display("FAIL %0s emitted %0d elements, expected %0d",
                         name, rows_emitted, outputs);
                errors = errors + 1;
            end
            if (saturation_count !== want_sat) begin
                $display("FAIL %0s counted %0d saturations, reference says %0d",
                         name, saturation_count, want_sat);
                errors = errors + 1;
            end
            //: The counters separate real KV rows from the padded tail, which is
            //: what the descriptor's counter scope asks for. Every (row, head,
            //: block) visits all 64 lanes, and a slot past the descriptor's
            //: count is padding.
            if (valid_row_reads + padding_lanes_seen
                !== span * heads * ((slots + LANES - 1) / LANES) * LANES) begin
                $display("FAIL %0s lanes accounted %0d + %0d, expected %0d",
                         name, valid_row_reads, padding_lanes_seen,
                         span * heads * ((slots + LANES - 1) / LANES) * LANES);
                errors = errors + 1;
            end
            if (valid_row_reads !== span * heads * slots) begin
                $display("FAIL %0s counted %0d valid rows, expected %0d",
                         name, valid_row_reads, span * heads * slots);
                errors = errors + 1;
            end
            $display("  %0s: span=%0d heads=%0d head_dim=%0d slots=%0d valid=%0d padding=%0d",
                     name, span, heads, head_dim, slots,
                     valid_row_reads, padding_lanes_seen);
        end
        $fclose(fh);

        cfg_head_dim = 32'd0; watchdog = 0;
        @(negedge clk); start = 1; @(negedge clk); start = 0; wait (done);
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL zero head_dim gave %0h", error_code);
            errors = errors + 1;
        end

        if (stray_reads != 0) begin
            $display("FAIL %0d reads fell outside the operator's bound views",
                     stray_reads);
            errors = errors + stray_reads;
        end
        if (errors == 0)
            $display("PASS a3_attention_sparse: %0d transactions bit-identical to sparse_attention_bf16_codes, with counters, saturation, and every read inside a bound view", ncases);
        else
            $display("FAIL a3_attention_sparse: %0d errors", errors);
        $finish;
    end
endmodule
