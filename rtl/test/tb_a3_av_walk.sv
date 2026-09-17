`timescale 1ns/1ps
// ATTENTION.SPARSE's AV accumulation against the reference's own functions.
//
// tools/build_a3_av_walk_vectors.py calls ``_single_rounded_add`` from
// runtime/tensor_accelerator/sparse_attention.py for every product-add and
// numpy's binary32 multiply for the rescale, in ``_execute_tile``'s order, so
// what this compares against is the contract and not a reimplementation of it.
//
// Each case is a SEQUENCE of blocks driven through one walk instance: block 0
// clears, later blocks rescale what block 0 left behind. That is the only way to
// hand the walk a nonzero accumulator to rescale, and it is what the tile loop
// actually does -- a single-block case would leave both the rescale multiply and
// its drain state completely untested.
module tb_a3_av_walk;
    localparam integer CHANNELS_MAX = 512;
    localparam integer LANES_MAX = 64;
    localparam integer PROB_BASE = 0;
    localparam integer KV_BASE = 1024;

    reg clk = 0, rst_n = 0, start = 0, cfg_clear = 0;
    reg [31:0] cfg_channels, cfg_lanes, cfg_rescale_code;
    reg [31:0] cfg_kv_base, cfg_kv_stride;
    reg [LANES_MAX-1:0] lane_valid;
    reg [LANES_MAX*32-1:0] lane_row;
    reg [LANES_MAX*16-1:0] lane_prob;
    wire kv_rd_en;
    wire [31:0] kv_rd_addr;
    reg  [31:0] kv_rd_data;
    reg  [31:0] out_rd_addr;
    wire [31:0] out_rd_data;
    wire busy, done, nonfinite;
    wire [7:0] error_code;
    wire [31:0] mac_count;

    reg [31:0] mem [0:32767];
    reg [31:0] rmem [0:LANES_MAX-1];
    reg [31:0] pmem [0:LANES_MAX-1];
    reg [31:0] emem [0:CHANNELS_MAX-1];
    integer j, errors = 0;
    integer ncases, kv_rows, lanes, c, b, nblocks, channels, clear;
    integer fh, code;
    reg [1023:0] name, path;
    reg [31:0] rescale_i;
    reg [LANES_MAX-1:0] mask;

    ot_a3_attention_av_walk #(
        .CHANNELS_MAX(CHANNELS_MAX), .LANES_MAX(LANES_MAX)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_clear(cfg_clear), .cfg_channels(cfg_channels),
        .cfg_lanes(cfg_lanes), .cfg_rescale_code(cfg_rescale_code),
        .cfg_kv_base(cfg_kv_base), .cfg_kv_stride(cfg_kv_stride),
        .lane_valid(lane_valid), .lane_row(lane_row), .lane_prob(lane_prob),
        .kv_rd_en(kv_rd_en), .kv_rd_addr(kv_rd_addr), .kv_rd_data(kv_rd_data),
        .out_rd_addr(out_rd_addr), .out_rd_data(out_rd_data),
        .busy(busy), .done(done), .error_code(error_code),
        .nonfinite(nonfinite), .mac_count(mac_count)
    );

    always #1 clk = ~clk;
    always @(posedge clk) if (kv_rd_en)   kv_rd_data   <= mem[kv_rd_addr[14:0]];

    localparam integer WATCHDOG = 40_000_000;
    integer watchdog;
    initial watchdog = 0;
    always @(posedge clk) begin
        watchdog <= watchdog + 1;
        if (watchdog > WATCHDOG) begin
            $display("FAIL watchdog: no progress in %0d cycles", WATCHDOG);
            $finish;
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
        code = $fscanf(fh, "%d\n", ncases);
        code = $fscanf(fh, "%d\n", kv_rows);
        code = $fscanf(fh, "%d\n", lanes);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %d\n", name, channels, nblocks);
            for (j = 0; j < 32768; j = j + 1) mem[j] = 32'd0;
            $sformat(path, "kv_%0d.hex", c); $readmemh(path, mem, KV_BASE);
            cfg_channels = channels; cfg_lanes = lanes;
            cfg_kv_base = KV_BASE;
            cfg_kv_stride = channels;

            for (b = 0; b < nblocks; b = b + 1) begin
                code = $fscanf(fh, "%d %h %b\n", clear, rescale_i, mask);
                $sformat(path, "prob_%0d_%0d.hex", c, b);
                $readmemh(path, pmem);
                for (j = 0; j < LANES_MAX; j = j + 1)
                    lane_prob[j*16 +: 16] = pmem[j][15:0];
                $sformat(path, "rows_%0d_%0d.hex", c, b);
                $readmemh(path, rmem);
                for (j = 0; j < LANES_MAX; j = j + 1)
                    lane_row[j*32 +: 32] = rmem[j];
                lane_valid = mask;
                cfg_clear = clear[0];
                cfg_rescale_code = rescale_i;
                go;
                if (error_code !== 8'h00) begin
                    $display("FAIL %0s block %0d error_code=%0h",
                             name, b, error_code);
                    errors = errors + 1;
                end
                //: One fused product-add per (lane, channel), padding lanes
                //: included -- the contract multiplies a zeroed row rather than
                //: skipping the lane.
                if (mac_count !== lanes * channels) begin
                    $display("FAIL %0s block %0d did %0d product-adds, expected %0d",
                             name, b, mac_count, lanes * channels);
                    errors = errors + 1;
                end
            end

            $sformat(path, "acc_%0d.hex", c); $readmemh(path, emem);
            for (j = 0; j < channels; j = j + 1) begin
                out_rd_addr = j; #1;
                if (out_rd_data !== emem[j]) begin
                    if (errors < 24)
                        $display("FAIL %0s channel %0d got %08h expected %08h",
                                 name, j, out_rd_data, emem[j]);
                    errors = errors + 1;
                end
            end
            $display("  %0s: channels=%0d blocks=%0d", name, channels, nblocks);
        end
        $fclose(fh);

        //: The inner extent carries the accumulator hazard, so a head_dim that
        //: is not longer than the product-add pipeline must be refused, not run.
        cfg_channels = 32'd7; cfg_clear = 1'b1; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL channels=7 gave %0h", error_code);
            errors = errors + 1;
        end
        cfg_channels = 32'd0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL channels=0 gave %0h", error_code);
            errors = errors + 1;
        end
        cfg_channels = 32'd128; cfg_lanes = 32'd0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL lanes=0 gave %0h", error_code);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_av_walk: %0d block sequences match the reference's rescale and ascending-lane product-add, and three unsupportable shapes fail closed", ncases);
        else
            $display("FAIL a3_av_walk: %0d errors", errors);
        $finish;
    end
endmodule
