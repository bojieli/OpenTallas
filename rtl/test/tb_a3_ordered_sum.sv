`timescale 1ns/1ps
// ORDERED_SUM against vectors produced by runtime.sim.engines.reduction itself.
module tb_a3_ordered_sum;
    localparam MAX_TERMS = 8;
    reg clk = 0, rst_n = 0, start = 0;
    reg [7:0]  cfg_terms, cfg_reduction_order;
    reg [31:0] cfg_count, cfg_in_base, cfg_stride, cfg_base_base, cfg_out_base;
    reg        cfg_has_base;
    wire [MAX_TERMS-1:0]    val_rd_en;
    wire [MAX_TERMS*32-1:0] val_rd_addr;
    reg  [MAX_TERMS*32-1:0] val_rd_data;
    wire base_rd_en; wire [31:0] base_rd_addr; reg [31:0] base_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] out_count, saturation_count;

    reg [31:0] vmem [0:255];
    reg [31:0] bmem [0:63];
    reg [31:0] emem [0:63];
    reg [31:0] got  [0:63];
    integer ncases, c, k, j, errors = 0, writes;
    integer terms, width, hb, fh, code;
    reg [1023:0] path;

    ot_a3_reduction_ordered_sum #(.MAX_TERMS(MAX_TERMS)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_terms(cfg_terms), .cfg_count(cfg_count), .cfg_in_base(cfg_in_base),
        .cfg_stride(cfg_stride), .cfg_has_base(cfg_has_base),
        .cfg_base_base(cfg_base_base),
        .cfg_reduction_order(cfg_reduction_order), .cfg_out_base(cfg_out_base),
        .val_rd_en(val_rd_en), .val_rd_addr(val_rd_addr), .val_rd_data(val_rd_data),
        .base_rd_en(base_rd_en), .base_rd_addr(base_rd_addr), .base_rd_data(base_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .saturation_count(saturation_count)
    );

    always #1 clk = ~clk;
    always @(posedge clk) begin
        for (k = 0; k < MAX_TERMS; k = k + 1)
            if (val_rd_en[k])
                val_rd_data[k*32 +: 32] <= vmem[val_rd_addr[k*32 +: 32][7:0]];
        if (base_rd_en) base_rd_data <= bmem[base_rd_addr[5:0]];
    end
    always @(posedge clk)
        if (out_we) begin got[out_addr[5:0]] <= out_data; writes = writes + 1; end

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%d %d %d\n", terms, width, hb);
            for (j = 0; j < 256; j = j + 1) vmem[j] = 32'hdead_beef;
            for (j = 0; j < 64; j = j + 1) begin
                bmem[j] = 0; emem[j] = 0; got[j] = 32'hdead_beef;
            end
            $sformat(path, "vals_%0d.hex", c); $readmemh(path, vmem);
            $sformat(path, "base_%0d.hex", c); $readmemh(path, bmem);
            $sformat(path, "exp_%0d.hex", c);  $readmemh(path, emem);

            cfg_terms = terms[7:0]; cfg_count = width;
            cfg_in_base = 0; cfg_stride = width;
            cfg_has_base = hb[0]; cfg_base_base = 0;
            cfg_reduction_order = 8'd0;   // SEQUENTIAL_ASCENDING
            cfg_out_base = 0; writes = 0;
            @(negedge clk); start = 1; @(negedge clk); start = 0;
            wait (done); @(negedge clk);

            if (error_code !== 8'd0) begin
                $display("FAIL case %0d error=%0d", c, error_code); errors=errors+1; end
            if (out_count !== width || writes !== width) begin
                $display("FAIL case %0d count=%0d writes=%0d exp %0d",
                         c, out_count, writes, width); errors=errors+1; end
            for (j = 0; j < width; j = j + 1)
                if (got[j][15:0] !== emem[j][15:0]) begin
                    $display("FAIL case %0d elem %0d got %04x exp %04x",
                             c, j, got[j][15:0], emem[j][15:0]); errors=errors+1; end
        end
        $fclose(fh);

        // An order this block does not implement must be refused, not reduced
        // in the wrong order.
        cfg_terms = 8'd4; cfg_count = 32'd4; cfg_stride = 32'd4;
        cfg_has_base = 0; cfg_reduction_order = 8'd1;   // PAIRWISE_TREE
        writes = 0;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
        if (error_code === 8'd0) begin
            $display("FAIL PAIRWISE_TREE was accepted by the sequential block");
            errors = errors + 1;
        end
        if (writes !== 0) begin
            $display("FAIL refused order still wrote %0d elements", writes);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: ordered_sum, %0d reference cases, II=1, order refusal", ncases);
        else $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
