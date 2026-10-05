`timescale 1ns/1ps
// TENSOR.ROUTED_MATMUL against sequential_matmul_binary32, with the node-shard
// skip exercised: half the rows belong to the other node and must be left as
// exact positive zero.
module tb_a3_routed_matmul;
    reg clk = 0, rst_n = 0, start = 0;
    reg [15:0] cfg_rows, cfg_cols, cfg_depth;
    reg [31:0] cfg_topk, cfg_local_experts, cfg_global_experts;
    reg [31:0] cfg_expert_base, cfg_expert_stride;
    reg [7:0]  cfg_dtype_a, cfg_dtype_b;
    reg [31:0] cfg_a_base, cfg_b_base, cfg_id_base, cfg_out_base;
    wire id_rd_en; wire [31:0] id_rd_addr; reg [31:0] id_rd_data;
    wire a_rd_en; wire [31:0] a_rd_addr; reg [31:0] a_rd_data;
    wire b_rd_en; wire [31:0] b_rd_addr; reg [31:0] b_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] out_count, saturation_count, mac_count, rows_skipped, rejected_ids;

    reg [31:0] amem [0:255];
    reg [31:0] bmem [0:255];
    reg [31:0] imem [0:63];
    reg [31:0] emem [0:63];
    reg [31:0] omem [0:63];
    integer j, errors = 0, writes;
    integer M, N, K, EL, EG, BASE, STRIDE, SKIPPED;
    integer fh, code; reg [255:0] key;

    ot_a3_tensor_routed_matmul #(.LANES_IF(8)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_topk(cfg_topk), .cfg_local_experts(cfg_local_experts),
        .cfg_global_experts(cfg_global_experts),
        .cfg_expert_base(cfg_expert_base), .cfg_expert_stride(cfg_expert_stride),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b),
        .cfg_a_base(cfg_a_base), .cfg_b_base(cfg_b_base),
        .cfg_id_base(cfg_id_base), .cfg_out_base(cfg_out_base),
        .id_rd_en(id_rd_en), .id_rd_addr(id_rd_addr), .id_rd_data(id_rd_data),
        .a_rd_en(a_rd_en), .a_rd_addr(a_rd_addr), .a_rd_data(a_rd_data),
        .b_rd_en(b_rd_en), .b_rd_addr(b_rd_addr), .b_rd_data(b_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .saturation_count(saturation_count),
        .mac_count(mac_count), .rows_skipped(rows_skipped),
        .rejected_ids(rejected_ids)
    );

    always #1 clk = ~clk;
    always @(posedge clk) begin
        if (id_rd_en) id_rd_data <= imem[id_rd_addr[5:0]];
        if (a_rd_en)  a_rd_data  <= amem[a_rd_addr[7:0]];
        if (b_rd_en)  b_rd_data  <= bmem[b_rd_addr[7:0]];
    end
    always @(posedge clk) if (out_we) begin omem[out_addr[5:0]] <= out_data; writes = writes + 1; end

    task go; begin
        writes = 0;
        for (j = 0; j < 64; j = j + 1) omem[j] = 32'hdead_beef;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cfg.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cfg.txt"); $finish; end
        code = $fscanf(fh, "%s %d\n", key, M);
        code = $fscanf(fh, "%s %d\n", key, N);
        code = $fscanf(fh, "%s %d\n", key, K);
        code = $fscanf(fh, "%s %d\n", key, EL);
        code = $fscanf(fh, "%s %d\n", key, EG);
        code = $fscanf(fh, "%s %d\n", key, BASE);
        code = $fscanf(fh, "%s %d\n", key, STRIDE);
        code = $fscanf(fh, "%s %d\n", key, SKIPPED);
        $fclose(fh);
        $readmemh("acts.hex", amem);
        $readmemh("wts.hex",  bmem);
        $readmemh("ids.hex",  imem);
        $readmemh("exp.hex",  emem);
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        cfg_rows = M[15:0]; cfg_cols = N[15:0]; cfg_depth = K[15:0];
        cfg_topk = 1; cfg_local_experts = EL; cfg_global_experts = EG;
        cfg_expert_base = BASE; cfg_expert_stride = STRIDE;
        cfg_dtype_a = 8'h10; cfg_dtype_b = 8'h10;   // BF16
        cfg_a_base = 0; cfg_b_base = 0; cfg_id_base = 0; cfg_out_base = 0;
        go;

        if (error_code !== 8'd0) begin
            $display("FAIL error=%0d", error_code); errors = errors + 1; end
        if (rows_skipped !== SKIPPED) begin
            $display("FAIL rows_skipped=%0d expected %0d", rows_skipped, SKIPPED);
            errors = errors + 1; end
        if (out_count !== M*N) begin
            $display("FAIL out_count=%0d expected %0d", out_count, M*N);
            errors = errors + 1; end
        for (j = 0; j < M*N; j = j + 1)
            if (omem[j][15:0] !== emem[j][15:0]) begin
                $display("FAIL elem %0d (row %0d col %0d) got %04x expected %04x",
                         j, j/N, j%N, omem[j][15:0], emem[j][15:0]);
                errors = errors + 1;
            end

        // -- an ID outside the GLOBAL bound refuses, and nothing is contracted -
        imem[0] = EG;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL an ID outside the global bound was accepted"); errors=errors+1; end
        if (rejected_ids !== 1) begin
            $display("FAIL rejected_ids=%0d expected 1", rejected_ids); errors=errors+1; end
        if (writes !== 0) begin
            $display("FAIL refused operator wrote %0d elements", writes); errors=errors+1; end
        imem[0] = 3;

        // -- topk > 1 is refused rather than given a combination order --------
        cfg_topk = 2;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL topk=2 was accepted"); errors=errors+1; end
        cfg_topk = 1;

        if (errors == 0)
            $display("PASS: routed_matmul vs sequential_matmul_binary32, node-shard skip zero-filled, bound and topk refusals");
        else $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
