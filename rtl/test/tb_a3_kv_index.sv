`timescale 1ns/1ps
// ATTENTION.SPARSE's selected-row decode against the reference's own rules.
//
// Expectations come from tools/build_a3_kv_index_vectors.py, which transcribes
// runtime.sim.engines.attention._sparse_index_rows and asserts, for every case it
// emits, that its own admit/refuse verdict agrees with those rules -- so a case
// whose intent drifted from the reference fails to build rather than to run.
//
// Two cases carry the whole point:
//   interleaved     a live lane after a pad lane. Counting the live lanes is not
//                   the same check as requiring them to be the FIRST count of
//                   them, and an implementation doing only the former accepts
//                   this and silently drops a row.
//   wrapped_order   live rows DESCENDING, which a circular window really emits
//                   after the cursor wraps. It must be ADMITTED: the reference
//                   forbids sorting here, and rejecting the wrap is what once
//                   trapped every uncompressed sparse layer at decode 128.
module tb_a3_kv_index;
    localparam integer SLOTS = 64;

    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_kv_rows;
    reg [SLOTS*32-1:0] indices;
    wire busy, done;
    wire [SLOTS-1:0] lane_valid;
    wire [31:0] live_count;
    wire [7:0] error_code;

    reg [31:0] imem [0:SLOTS-1];
    integer j, errors = 0;
    integer ncases, c, kv_rows, admit_i, count_i;
    integer fh, code;
    reg [1023:0] name, path;
    reg [SLOTS-1:0] mask;

    ot_a3_attention_kv_index #(.SLOTS(SLOTS)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_kv_rows(cfg_kv_rows), .indices(indices),
        .busy(busy), .done(done),
        .lane_valid(lane_valid), .live_count(live_count),
        .error_code(error_code)
    );

    always #1 clk = ~clk;

    task go; begin
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        code = $fscanf(fh, "%d\n", kv_rows);
        cfg_kv_rows = kv_rows;
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %d %b\n", name, admit_i, count_i, mask);
            for (j = 0; j < SLOTS; j = j + 1) imem[j] = 32'hffff_ffff;
            $sformat(path, "idx_%0d.hex", c); $readmemh(path, imem);
            for (j = 0; j < SLOTS; j = j + 1) indices[j*32 +: 32] = imem[j];
            go;

            if (admit_i) begin
                if (error_code !== 8'h00) begin
                    $display("FAIL %0s admitted case gave error %0h", name, error_code);
                    errors = errors + 1;
                end
                if (live_count !== count_i) begin
                    $display("FAIL %0s live_count got %0d expected %0d",
                             name, live_count, count_i);
                    errors = errors + 1;
                end
                if (lane_valid !== mask) begin
                    $display("FAIL %0s mask got %h expected %h", name, lane_valid, mask);
                    errors = errors + 1;
                end
            end else begin
                if (error_code === 8'h00) begin
                    $display("FAIL %0s should have been refused", name);
                    errors = errors + 1;
                end
                //: A refused block must publish NOTHING, or a caller reading the
                //: mask without the code would treat it as a short block.
                if (lane_valid !== {SLOTS{1'b0}} || live_count !== 32'd0) begin
                    $display("FAIL %0s refused but published mask=%h count=%0d",
                             name, lane_valid, live_count);
                    errors = errors + 1;
                end
            end
            $display("  %0s: admit=%0d live=%0d err=%0h", name, admit_i,
                     live_count, error_code);
        end
        $fclose(fh);

        if (errors == 0)
            $display("PASS a3_kv_index: %0d cases match the reference decode, order preserved and three refusals fail closed", ncases);
        else
            $display("FAIL a3_kv_index: %0d errors", errors);
        $finish;
    end
endmodule
