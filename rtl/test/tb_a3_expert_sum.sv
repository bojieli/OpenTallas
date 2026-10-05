`timescale 1ns/1ps
// EXPERT_SUM against vectors produced by runtime.sim.engines.reduction itself.
module tb_a3_expert_sum;
    localparam EXPERTS = 8;
    reg clk = 0, rst_n = 0, start = 0;
    reg [7:0]  cfg_experts;
    reg [31:0] cfg_count, cfg_in_base, cfg_stride, cfg_weight_base;
    reg [31:0] cfg_base_base, cfg_out_base;
    reg        cfg_has_weights, cfg_has_base, cfg_base_after_terms;
    wire [EXPERTS-1:0]    val_rd_en;
    wire [EXPERTS*32-1:0] val_rd_addr;
    reg  [EXPERTS*32-1:0] val_rd_data;
    wire wgt_rd_en; wire [31:0] wgt_rd_addr; reg [31:0] wgt_rd_data;
    wire base_rd_en; wire [31:0] base_rd_addr; reg [31:0] base_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] out_count, saturation_count;

    reg [31:0] vmem [0:2047];      // [experts, width], row-major
    reg [31:0] wmem [0:63];
    reg [31:0] bmem [0:63];
    reg [31:0] emem [0:63];
    reg [31:0] got  [0:63];

    integer ncases, c, k, j, errors = 0, writes;
    //: THE WEIGHT READ AND THE VALUE WALK MUST NOT OVERLAP.  A caller with a
    //: fixed operand-port budget -- ot_a3_engine_issue_bridge has four -- can
    //: only fit an N-expert reduction in N ports by giving the weight vector
    //: the port expert 0 will use later. That is sound exactly while these two
    //: never assert on the same cycle, so it is counted rather than assumed.
    integer port_overlap = 0;
    integer experts, width, hw, hb, bat;
    integer fh, code;
    reg [1023:0] path;

    ot_a3_reduction_expert_sum #(.EXPERTS(EXPERTS)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_experts(cfg_experts), .cfg_count(cfg_count),
        .cfg_in_base(cfg_in_base), .cfg_stride(cfg_stride),
        .cfg_has_weights(cfg_has_weights), .cfg_weight_base(cfg_weight_base),
        .cfg_has_base(cfg_has_base), .cfg_base_base(cfg_base_base),
        .cfg_base_after_terms(cfg_base_after_terms), .cfg_out_base(cfg_out_base),
        .val_rd_en(val_rd_en), .val_rd_addr(val_rd_addr), .val_rd_data(val_rd_data),
        .wgt_rd_en(wgt_rd_en), .wgt_rd_addr(wgt_rd_addr), .wgt_rd_data(wgt_rd_data),
        .base_rd_en(base_rd_en), .base_rd_addr(base_rd_addr), .base_rd_data(base_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .saturation_count(saturation_count)
    );

    always #1 clk = ~clk;
    // Every port is registered: one cycle of memory latency.
    //: The lane address goes through a named reg: indexing a part-select is
    //: something Verilator accepts and Icarus 11 rejects outright, so the
    //: bench would only ever have run under one of the two simulators.
    reg [31:0] lane_addr;
    always @(posedge clk) begin
        for (k = 0; k < EXPERTS; k = k + 1)
            if (val_rd_en[k]) begin
                lane_addr = val_rd_addr[k*32 +: 32];
                val_rd_data[k*32 +: 32] <= vmem[lane_addr[10:0]];
            end
        if (wgt_rd_en)  wgt_rd_data  <= wmem[wgt_rd_addr[5:0]];
        if (rst_n && wgt_rd_en && (val_rd_en != {EXPERTS{1'b0}}))
            port_overlap = port_overlap + 1;
        if (base_rd_en) base_rd_data <= bmem[base_rd_addr[5:0]];
    end
    always @(posedge clk)
        if (out_we) begin
            got[out_addr[5:0]] <= out_data;
            writes = writes + 1;
        end

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%d %d %d %d %d\n", experts, width, hw, hb, bat);
            for (j = 0; j < 2048; j = j + 1) vmem[j] = 32'hdead_beef;
            for (j = 0; j < 64; j = j + 1) begin
                wmem[j] = 32'd0; bmem[j] = 32'd0; emem[j] = 32'd0; got[j] = 32'hdead_beef;
            end
            $sformat(path, "vals_%0d.hex", c); $readmemh(path, vmem);
            $sformat(path, "wts_%0d.hex", c);  $readmemh(path, wmem);
            $sformat(path, "base_%0d.hex", c); $readmemh(path, bmem);
            $sformat(path, "exp_%0d.hex", c);  $readmemh(path, emem);

            cfg_experts = experts[7:0];
            cfg_count = width;
            cfg_in_base = 32'd0;
            cfg_stride = width;
            cfg_has_weights = hw[0];
            cfg_weight_base = 32'd0;
            cfg_has_base = hb[0];
            cfg_base_base = 32'd0;
            cfg_base_after_terms = bat[0];
            cfg_out_base = 32'd0;
            writes = 0;
            @(negedge clk); start = 1; @(negedge clk); start = 0;
            wait (done); @(negedge clk);

            if (error_code !== 8'd0) begin
                $display("FAIL case %0d error_code=%0d", c, error_code);
                errors = errors + 1;
            end
            if (out_count !== width) begin
                $display("FAIL case %0d out_count=%0d expected %0d", c, out_count, width);
                errors = errors + 1;
            end
            if (writes !== width) begin
                $display("FAIL case %0d II: %0d writes for %0d elements", c, writes, width);
                errors = errors + 1;
            end
            for (j = 0; j < width; j = j + 1)
                if (got[j][15:0] !== emem[j][15:0]) begin
                    $display("FAIL case %0d elem %0d got %04x expected %04x",
                             c, j, got[j][15:0], emem[j][15:0]);
                    errors = errors + 1;
                end
        end
        $fclose(fh);

        // A zero stride is not a shape this operator has; it must refuse.
        cfg_experts = 8'd4; cfg_count = 32'd4; cfg_stride = 32'd0;
        cfg_has_weights = 0; cfg_has_base = 0;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
        if (error_code === 8'd0) begin
            $display("FAIL zero stride accepted"); errors = errors + 1;
        end

        if (port_overlap != 0) begin

            $display("FAIL wgt_rd_en overlapped val_rd_en on %0d cycles; a four-port caller would lose a read",

                     port_overlap);

            errors = errors + 1;

        end

        if (errors == 0)
            $display("PASS: expert_sum, %0d reference cases, II=1, refusal", ncases);
        else
            $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
