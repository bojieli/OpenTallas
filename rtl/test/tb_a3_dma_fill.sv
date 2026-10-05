`timescale 1ns/1ps
// DMA.FILL: both code sources, the width bound, and the refusals.
module tb_a3_dma_fill;
    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_count, cfg_out_base, cfg_source_addr, cfg_immediate;
    reg        cfg_has_source, cfg_has_immediate;
    reg [7:0]  cfg_element_bits;
    wire src_rd_en; wire [31:0] src_rd_addr; reg [31:0] src_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code; wire [31:0] out_count;

    reg [31:0] smem [0:15];
    reg [31:0] omem [0:63];
    integer j, errors = 0, writes;

    ot_a3_dma_fill dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_count(cfg_count), .cfg_out_base(cfg_out_base),
        .cfg_has_source(cfg_has_source), .cfg_source_addr(cfg_source_addr),
        .cfg_has_immediate(cfg_has_immediate), .cfg_immediate(cfg_immediate),
        .cfg_element_bits(cfg_element_bits),
        .src_rd_en(src_rd_en), .src_rd_addr(src_rd_addr), .src_rd_data(src_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code), .out_count(out_count)
    );

    always #1 clk = ~clk;
    always @(posedge clk) if (src_rd_en) src_rd_data <= smem[src_rd_addr[3:0]];
    always @(posedge clk) if (out_we) begin omem[out_addr[5:0]] <= out_data; writes = writes + 1; end

    task go; begin
        writes = 0;
        for (j = 0; j < 64; j = j + 1) omem[j] = 32'hdead_beef;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        smem[3] = 32'h1234_5678;
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        // -- code from a one-element view --------------------------------
        cfg_count = 32'd12; cfg_out_base = 32'd0;
        cfg_has_source = 1; cfg_source_addr = 32'd3;
        cfg_has_immediate = 0; cfg_immediate = 32'd0; cfg_element_bits = 8'd32;
        go;
        if (error_code !== 8'd0) begin $display("FAIL view error=%0d", error_code); errors=errors+1; end
        if (out_count !== 32'd12 || writes !== 12) begin
            $display("FAIL view count=%0d writes=%0d", out_count, writes); errors=errors+1; end
        for (j = 0; j < 12; j = j + 1)
            if (omem[j] !== 32'h1234_5678) begin
                $display("FAIL view omem[%0d]=%08x", j, omem[j]); errors=errors+1; end

        // -- immediate ---------------------------------------------------
        cfg_has_source = 0; cfg_has_immediate = 1;
        cfg_immediate = 32'h0000_beef; cfg_element_bits = 8'd16; cfg_count = 32'd5;
        go;
        if (error_code !== 8'd0) begin $display("FAIL imm error=%0d", error_code); errors=errors+1; end
        for (j = 0; j < 5; j = j + 1)
            if (omem[j] !== 32'h0000_beef) begin
                $display("FAIL imm omem[%0d]=%08x", j, omem[j]); errors=errors+1; end
        if (writes !== 5) begin $display("FAIL imm II writes=%0d", writes); errors=errors+1; end

        // -- an immediate wider than the element must refuse, not truncate -
        cfg_immediate = 32'h0001_0000; cfg_element_bits = 8'd16; cfg_count = 32'd4;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL a 17-bit immediate was accepted into a 16-bit element");
            errors=errors+1;
        end
        if (writes !== 0) begin
            $display("FAIL refused fill still wrote %0d elements", writes); errors=errors+1; end

        // -- a 32-bit element admits any pattern -------------------------
        cfg_immediate = 32'hffff_ffff; cfg_element_bits = 8'd32; cfg_count = 32'd3;
        go;
        if (error_code !== 8'd0) begin
            $display("FAIL 32-bit element refused a full pattern"); errors=errors+1; end
        if (omem[0] !== 32'hffff_ffff) begin $display("FAIL 32-bit fill"); errors=errors+1; end

        // -- neither source nor immediate must refuse, not fill with zero -
        cfg_has_source = 0; cfg_has_immediate = 0; cfg_count = 32'd4;
        go;
        if (error_code === 8'd0) begin
            $display("FAIL a fill with no code was accepted"); errors=errors+1; end
        if (writes !== 0) begin $display("FAIL codeless fill wrote %0d", writes); errors=errors+1; end

        if (errors == 0)
            $display("PASS: dma_fill, both code sources, width bound, two refusals, II=1");
        else $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
