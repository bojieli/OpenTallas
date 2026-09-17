`timescale 1ns/1ps
// ATTENTION.SPARSE's QK reduction against the contract's own add.
//
// tools/build_a3_qk_walk_vectors.py computes each score as the reference's
// repair path defines it -- ``_single_rounded_add(acc, q, k)``, one rounding of
// ``acc + q*k``, stepped in ascending reduction order with exact rational
// arithmetic doing the product -- so this compares against the CONTRACT rather
// than against numpy's two-ufunc schedule for it. The scale is one further
// rounding afterwards and is applied as such.
//
// THE REDUCTION ORDER IS THE PART A REIMPLEMENTATION CHANGES, so the generator
// records per case whether a DESCENDING fold gives a different score and refuses
// to build if none does. Three of the six cases differ, which is what makes this
// a test of the association and not just of multiplication.
module tb_a3_qk_walk;
    localparam integer LANES = 64;
    localparam integer Q_BASE = 0;
    localparam integer KV_BASE = 1024;

    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_head_dim, cfg_q_base, cfg_kv_stride, cfg_kv_base;
    reg [31:0] cfg_scale_code;
    reg [LANES-1:0] lane_valid;
    reg [LANES*32-1:0] lane_row;
    wire q_rd_en, kv_rd_en;
    wire [31:0] q_rd_addr, kv_rd_addr;
    reg [31:0] q_rd_data, kv_rd_data;
    wire busy, done;
    wire [LANES*32-1:0] scores;
    wire [7:0] error_code;
    wire [31:0] mac_count;

    reg [31:0] mem [0:65535];
    reg [31:0] rmem [0:LANES-1];
    reg [31:0] emem [0:LANES-1];
    integer j, errors = 0, live;
    integer ncases, c, kv_rows, head_dim;
    integer fh, code;
    reg [1023:0] name, path;
    reg [31:0] scale_i;
    reg [LANES-1:0] mask;

    ot_a3_attention_qk_walk #(.LANES(LANES)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_head_dim(cfg_head_dim), .cfg_q_base(cfg_q_base),
        .cfg_kv_stride(cfg_kv_stride), .cfg_kv_base(cfg_kv_base),
        .cfg_scale_code(cfg_scale_code),
        .lane_valid(lane_valid), .lane_row(lane_row),
        .q_rd_en(q_rd_en), .q_rd_addr(q_rd_addr), .q_rd_data(q_rd_data),
        .kv_rd_en(kv_rd_en), .kv_rd_addr(kv_rd_addr), .kv_rd_data(kv_rd_data),
        .busy(busy), .done(done), .scores(scores),
        .error_code(error_code), .mac_count(mac_count)
    );

    always #1 clk = ~clk;
    //: Registered reads, which is the latency the walk's operand pipeline
    //: assumes and what the array's banks present.
    always @(posedge clk) if (q_rd_en)  q_rd_data  <= mem[q_rd_addr[15:0]];
    always @(posedge clk) if (kv_rd_en) kv_rd_data <= mem[kv_rd_addr[15:0]];

    //: The walk stalls if an accumulator is read before its product retires, so
    //: a hang here is a hazard rather than a slow test.
    localparam integer WATCHDOG = 8_000_000;
    integer watchdog;
    initial watchdog = 0;
    always @(posedge clk) begin
        watchdog <= watchdog + 1;
        if (watchdog > WATCHDOG) begin
            $display("FAIL watchdog: the walk made no progress in %0d cycles", WATCHDOG);
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
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %h %b\n", name, head_dim, scale_i, mask);
            for (j = 0; j < 65536; j = j + 1) mem[j] = 32'd0;
            for (j = 0; j < LANES; j = j + 1) begin rmem[j] = 0; emem[j] = 0; end
            $sformat(path, "q_%0d.hex", c);      $readmemh(path, mem, Q_BASE);
            $sformat(path, "kv_%0d.hex", c);     $readmemh(path, mem, KV_BASE);
            $sformat(path, "rows_%0d.hex", c);   $readmemh(path, rmem);
            $sformat(path, "scores_%0d.hex", c); $readmemh(path, emem);
            for (j = 0; j < LANES; j = j + 1) lane_row[j*32 +: 32] = rmem[j];
            lane_valid = mask;
            cfg_head_dim = head_dim; cfg_q_base = Q_BASE;
            cfg_kv_stride = head_dim; cfg_kv_base = KV_BASE;
            cfg_scale_code = scale_i;
            go;

            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            for (j = 0; j < LANES; j = j + 1)
                if (scores[j*32 +: 32] !== emem[j]) begin
                    $display("FAIL %0s lane %0d got %08h expected %08h",
                             name, j, scores[j*32 +: 32], emem[j]);
                    errors = errors + 1;
                end
            //: One fused product-add per (lane, reduction step), padding lanes
            //: included -- the reference multiplies a zeroed row rather than
            //: skipping the lane, so the count is LANES * head_dim exactly.
            if (mac_count !== LANES * head_dim) begin
                $display("FAIL %0s performed %0d products, expected %0d",
                         name, mac_count, LANES * head_dim);
                errors = errors + 1;
            end
            $display("  %0s: head_dim=%0d products=%0d", name, head_dim, mac_count);
        end
        $fclose(fh);

        cfg_head_dim = 32'd0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL zero head_dim gave %0h", error_code);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_qk_walk: %0d cases match the fused product-add in ascending order, and a zero depth fails closed", ncases);
        else
            $display("FAIL a3_qk_walk: %0d errors", errors);
        $finish;
    end
endmodule
