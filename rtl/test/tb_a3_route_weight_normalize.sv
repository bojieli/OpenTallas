`timescale 1ns/1ps
// ROUTE.WEIGHT_NORMALIZE against the reference, plus every refusal it owes.
//
// Expectations come from tools/build_a3_weight_normalize_vectors.py, which calls
// runtime.sim.formats.narrow for the stored code and evaluates the reference's
// own divide-then-scale expression; only the fold is reproduced, and case
// order_matters is built so a re-associating fold gives a DIFFERENT total
// (1.0 sequential against 1.0000001 pairwise), so quiet re-association fails
// there and nowhere else.
//
// The group total is checked as well as the outputs. A wrong total scales a whole
// group by one wrong constant, which leaves every quotient self-consistent and
// is invisible to a spot check of one element.
module tb_a3_route_weight_normalize;
    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_groups, cfg_slots, cfg_scale_code, cfg_in_base, cfg_out_base;
    reg [7:0]  cfg_reduction_order;
    reg        cfg_has_scale, cfg_out_fp32;
    wire wgt_rd_en; wire [31:0] wgt_rd_addr; reg [31:0] wgt_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] out_count, saturation_count;

    reg [31:0] wmem [0:255];
    reg [31:0] emem [0:255];
    reg [31:0] tmem [0:255];
    reg [31:0] omem [0:255];
    integer j, errors = 0, writes;
    integer ncases, c, groups, slots, ofp32, order, order_seen = 0;
    integer fh, code; reg [1023:0] name, path;

    ot_a3_route_weight_normalize #(.MAX_SLOTS(8), .DIVIDERS(1), .ENABLE_SCALE(0)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_groups(cfg_groups), .cfg_slots(cfg_slots),
        .cfg_reduction_order(cfg_reduction_order),
        .cfg_has_scale(cfg_has_scale), .cfg_scale_code(cfg_scale_code),
        .cfg_in_base(cfg_in_base), .cfg_out_base(cfg_out_base),
        .cfg_out_fp32(cfg_out_fp32),
        .wgt_rd_en(wgt_rd_en), .wgt_rd_addr(wgt_rd_addr), .wgt_rd_data(wgt_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .out_count(out_count), .saturation_count(saturation_count)
    );

    always #1 clk = ~clk;
    always @(posedge clk) if (wgt_rd_en) wgt_rd_data <= wmem[wgt_rd_addr[7:0]];
    always @(posedge clk) if (out_we) begin omem[out_addr[7:0]] <= out_data; writes = writes + 1; end

    task go; begin
        writes = 0;
        for (j = 0; j < 256; j = j + 1) omem[j] = 32'hdead_0000;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %d %d %d\n", name, groups, slots, ofp32, order);
            for (j = 0; j < 256; j = j + 1) begin
                wmem[j] = 0; emem[j] = 0; tmem[j] = 0;
            end
            $sformat(path, "wgt_%0d.hex", c); $readmemh(path, wmem);
            $sformat(path, "exp_%0d.hex", c); $readmemh(path, emem);
            $sformat(path, "tot_%0d.hex", c); $readmemh(path, tmem);

            cfg_groups = groups; cfg_slots = slots;
            cfg_reduction_order = order[7:0];
            cfg_has_scale = 1'b0; cfg_scale_code = 32'h3f80_0000;
            cfg_in_base = 0; cfg_out_base = 0; cfg_out_fp32 = ofp32[0];
            go;

            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            if (writes !== groups * slots || out_count !== groups * slots) begin
                $display("FAIL %0s wrote %0d (counter %0d), expected %0d",
                         name, writes, out_count, groups * slots);
                errors = errors + 1;
            end
            for (j = 0; j < groups * slots; j = j + 1)
                if (omem[j] !== emem[j]) begin
                    $display("FAIL %0s out[%0d] got %08h expected %08h",
                             name, j, omem[j], emem[j]);
                    errors = errors + 1;
                end
            //: The last group's total is still latched, so at least that one is
            //: checked directly rather than only through its quotients.
            if (dut.total !== tmem[groups-1]) begin
                $display("FAIL %0s final total got %08h expected %08h",
                         name, dut.total, tmem[groups-1]);
                errors = errors + 1;
            end
            if (name == "order_matters") order_seen = 1;
            $display("  %0s: %0d groups x %0d slots, out_fp32=%0d -> %0d writes",
                     name, groups, slots, ofp32, writes);
        end
        $fclose(fh);

        if (!order_seen) begin
            $display("FAIL the order_matters case is absent from cases.txt");
            errors = errors + 1;
        end

        // -- Refusals ------------------------------------------------------
        cfg_groups = 2; cfg_slots = 4; cfg_out_fp32 = 1; cfg_has_scale = 1'b0;
        cfg_reduction_order = 8'd1;                //: PAIRWISE_TREE
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL pairwise order gave %0h", error_code); errors = errors + 1;
        end
        cfg_reduction_order = 8'd2;                //: BLOCKED_ASCENDING
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL blocked order gave %0h", error_code); errors = errors + 1;
        end
        cfg_reduction_order = 8'd0; cfg_slots = 9;  //: slots > MAX_SLOTS
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL slots>MAX gave %0h", error_code); errors = errors + 1;
        end
        cfg_slots = 0; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL slots=0 gave %0h", error_code); errors = errors + 1;
        end
        //: ENABLE_SCALE is 0 here, so a scaled operator must FAIL CLOSED rather
        //: than silently normalise without the scale.
        cfg_slots = 4; cfg_has_scale = 1'b1; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SCALE_RANGE) begin
            $display("FAIL scaled operator gave %0h", error_code); errors = errors + 1;
        end
        cfg_has_scale = 1'b0;

        //: A group sum that is not positive finite is the reference's trap 6.
        cfg_groups = 1; cfg_slots = 2;
        wmem[0] = 32'h3f80_0000; wmem[1] = 32'hbf80_0000;   //: 1 + (-1) = +0
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE) begin
            $display("FAIL zero sum gave %0h", error_code); errors = errors + 1;
        end
        wmem[0] = 32'hbf80_0000; wmem[1] = 32'hbf00_0000;   //: -1.5, negative
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE) begin
            $display("FAIL negative sum gave %0h", error_code); errors = errors + 1;
        end
        wmem[0] = 32'h7f80_0000; wmem[1] = 32'h3f80_0000;   //: +inf operand
        go;
        if (error_code === 8'h00) begin
            $display("FAIL nonfinite operand was accepted"); errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_route_weight_normalize: %0d cases match the reference totals and stored codes, and 8 refusals fail closed", ncases);
        else
            $display("FAIL a3_route_weight_normalize: %0d errors", errors);
        $finish;
    end
endmodule
