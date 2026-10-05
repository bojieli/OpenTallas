`timescale 1ns/1ps
// GROUPED_CONCAT against hand-computed expectations, both axes.
module tb_a3_grouped_concat;
    localparam INPUTS = 4;
    reg clk = 0, rst_n = 0, start = 0;
    reg [2:0]  cfg_inputs;
    reg [31:0] cfg_rows, cfg_out_base;
    reg [INPUTS*32-1:0] cfg_width, cfg_in_base;
    wire [INPUTS-1:0]    in_rd_en;
    wire [INPUTS*32-1:0] in_rd_addr;
    reg  [INPUTS*32-1:0] in_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code; wire [31:0] out_count;

    // Four operand memories: operand k holds 1000*k + index.
    reg [31:0] mem [0:INPUTS-1][0:255];
    reg [31:0] result [0:511];
    integer k, j, errors = 0, writes = 0;

    ot_a3_reduction_grouped_concat #(.INPUTS(INPUTS)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_inputs(cfg_inputs), .cfg_rows(cfg_rows),
        .cfg_width(cfg_width), .cfg_in_base(cfg_in_base),
        .cfg_out_base(cfg_out_base),
        .in_rd_en(in_rd_en), .in_rd_addr(in_rd_addr), .in_rd_data(in_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code), .out_count(out_count)
    );

    always #1 clk = ~clk;
    // Registered read: each memory answers the cycle after the address.
    always @(posedge clk) begin
        for (k = 0; k < INPUTS; k = k + 1)
            if (in_rd_en[k])
                in_rd_data[k*32 +: 32] <= mem[k][in_rd_addr[k*32 +: 32][7:0]];
    end
    always @(posedge clk) begin
        if (out_we) begin
            result[out_addr[8:0]] <= out_data;
            writes = writes + 1;
        end
    end

    task run(input [2:0] n, input [31:0] rows,
             input [31:0] w0, input [31:0] w1, input [31:0] w2, input [31:0] w3);
        begin
            cfg_inputs = n; cfg_rows = rows;
            cfg_width = {w3, w2, w1, w0};
            cfg_in_base = {32'd0, 32'd0, 32'd0, 32'd0};
            cfg_out_base = 32'd0;
            writes = 0;
            @(negedge clk); start = 1; @(negedge clk); start = 0;
            wait (done); @(negedge clk);
        end
    endtask

    initial begin
        for (k = 0; k < INPUTS; k = k + 1)
            for (j = 0; j < 256; j = j + 1) mem[k][j] = 1000*k + j;
        repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);

        // -- axis 0: three operands end to end, 3 + 2 + 4 elements ---------
        run(3'd3, 32'd1, 32'd3, 32'd2, 32'd4, 32'd0);
        if (out_count !== 32'd9) begin
            $display("FAIL axis0 out_count=%0d expected 9", out_count); errors=errors+1;
        end
        for (j = 0; j < 3; j = j + 1)
            if (result[j] !== 32'd0 + j) begin $display("FAIL a0[%0d]=%0d", j, result[j]); errors=errors+1; end
        for (j = 0; j < 2; j = j + 1)
            if (result[3+j] !== 32'd1000 + j) begin $display("FAIL a0[%0d]=%0d", 3+j, result[3+j]); errors=errors+1; end
        for (j = 0; j < 4; j = j + 1)
            if (result[5+j] !== 32'd2000 + j) begin $display("FAIL a0[%0d]=%0d", 5+j, result[5+j]); errors=errors+1; end

        // -- axis 1: two rank-2 operands, 3 rows, widths 2 and 3 ------------
        // row r of the output is op0[r*2 .. r*2+1] then op1[r*3 .. r*3+2]
        run(3'd2, 32'd3, 32'd2, 32'd3, 32'd0, 32'd0);
        if (out_count !== 32'd15) begin
            $display("FAIL axis1 out_count=%0d expected 15", out_count); errors=errors+1;
        end
        for (j = 0; j < 3; j = j + 1) begin
            if (result[j*5+0] !== 32'd0 + j*2)   begin $display("FAIL a1 r%0d c0=%0d exp %0d", j, result[j*5+0], j*2); errors=errors+1; end
            if (result[j*5+1] !== 32'd0 + j*2+1) begin $display("FAIL a1 r%0d c1=%0d exp %0d", j, result[j*5+1], j*2+1); errors=errors+1; end
            if (result[j*5+2] !== 32'd1000+j*3)   begin $display("FAIL a1 r%0d c2=%0d exp %0d", j, result[j*5+2], 1000+j*3); errors=errors+1; end
            if (result[j*5+3] !== 32'd1000+j*3+1) begin $display("FAIL a1 r%0d c3=%0d", j, result[j*5+3]); errors=errors+1; end
            if (result[j*5+4] !== 32'd1000+j*3+2) begin $display("FAIL a1 r%0d c4=%0d", j, result[j*5+4]); errors=errors+1; end
        end

        // -- four operands, one row each, checks the INPUTS bound -----------
        run(3'd4, 32'd2, 32'd1, 32'd1, 32'd1, 32'd1);
        if (out_count !== 32'd8) begin $display("FAIL four out_count=%0d exp 8", out_count); errors=errors+1; end
        for (k = 0; k < 4; k = k + 1) begin
            if (result[k]   !== 32'd1000*k + 0) begin $display("FAIL 4op r0 k%0d=%0d", k, result[k]); errors=errors+1; end
            if (result[4+k] !== 32'd1000*k + 1) begin $display("FAIL 4op r1 k%0d=%0d", k, result[4+k]); errors=errors+1; end
        end

        // -- a zero join extent must refuse, not hang ----------------------
        run(3'd2, 32'd2, 32'd2, 32'd0, 32'd0, 32'd0);
        if (error_code === 8'd0) begin $display("FAIL zero width was accepted"); errors=errors+1; end

        // -- initiation interval: 15 elements must retire in 15 writes ------
        run(3'd2, 32'd3, 32'd2, 32'd3, 32'd0, 32'd0);
        if (writes !== 15) begin $display("FAIL II: %0d writes for 15 elements", writes); errors=errors+1; end

        if (errors == 0) $display("PASS: grouped_concat, both axes, 4 operands, refusal, II=1");
        else $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
