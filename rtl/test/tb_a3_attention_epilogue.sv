`timescale 1ns/1ps
// ATTENTION.SPARSE's closing stage against the reference's own helpers.
//
// Expectations come from tools/build_a3_attention_epilogue_vectors.py, which
// evaluates the reference's four closing lines with ITS exp_cr32 and ITS _narrow,
// so the sink term, the normalise and the narrowing are all compared against the
// operator's own authorities.
//
// The last two checks are the refusals, and they exist because the RTL is
// NARROWER THAN THE REFERENCE in two places that are recorded in the module
// header: a sink logit above the row maximum needs exp of a positive argument,
// which no correctly-rounded unit in this tree provides, and a non-positive
// denominator is a row the reference REPAIRS through an exact oracle that has no
// RTL. Both fail closed here, and the bench pins that they do rather than
// leaving the narrowing implicit.
module tb_a3_attention_epilogue;
    localparam integer WIDTH = 32;
    localparam integer ACC_BASE = 0;
    localparam integer OUT_BASE = 256;

    reg clk = 0, rst_n = 0, start = 0;
    reg [31:0] cfg_width, cfg_acc_base, cfg_out_base;
    reg [31:0] cfg_final_max, cfg_final_sums, cfg_sink_code;
    wire acc_rd_en; wire [31:0] acc_rd_addr; reg [31:0] acc_rd_data;
    wire out_we; wire [31:0] out_addr, out_data;
    wire busy, done; wire [7:0] error_code;
    wire [31:0] sink_exp, final_denominator, out_count, saturation_count;

    reg [31:0] mem [0:511];
    reg [31:0] exp_codes [0:WIDTH-1];
    integer j, errors = 0, writes;
    integer ncases, c, width_i, sat_i;
    integer fh, code;
    reg [1023:0] name, path;
    reg [31:0] max_i, sums_i, sink_i, se_i, den_i;

    ot_a3_attention_epilogue dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_width(cfg_width), .cfg_acc_base(cfg_acc_base),
        .cfg_out_base(cfg_out_base),
        .cfg_final_max(cfg_final_max), .cfg_final_sums(cfg_final_sums),
        .cfg_sink_code(cfg_sink_code),
        .acc_rd_en(acc_rd_en), .acc_rd_addr(acc_rd_addr), .acc_rd_data(acc_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .error_code(error_code),
        .sink_exp(sink_exp), .final_denominator(final_denominator),
        .out_count(out_count), .saturation_count(saturation_count)
    );

    always #1 clk = ~clk;

    //: A WATCHDOG, BECAUSE THE FAILURE MODE HERE IS A HANG. The epilogue waits
    //: on an exponential's out_valid, and a unit that is never given the
    //: argument its domain admits never raises it -- so mis-selecting between
    //: the nonpositive and positive units stalls instead of computing a wrong
    //: number. Without this the mutant that always picks the nonpositive unit
    //: reads as a slow test rather than a broken one.
    localparam integer WATCHDOG_CYCLES = 4_000_000;
    integer watchdog;
    initial watchdog = 0;
    always @(posedge clk) begin
        watchdog <= watchdog + 1;
        if (watchdog > WATCHDOG_CYCLES) begin
            $display("FAIL watchdog: no progress in %0d cycles -- the epilogue is stalled, most likely waiting on an exponential that was never issued its argument", WATCHDOG_CYCLES);
            $finish;
        end
    end
    always @(posedge clk) if (acc_rd_en) acc_rd_data <= mem[acc_rd_addr[8:0]];
    always @(posedge clk) if (out_we) begin
        mem[out_addr[8:0]] <= out_data; writes = writes + 1;
    end

    task go; begin
        watchdog = 0;
        writes = 0;
        for (j = OUT_BASE; j < OUT_BASE + WIDTH; j = j + 1) mem[j] = 32'hdead_0000;
        @(negedge clk); start = 1; @(negedge clk); start = 0;
        wait (done); @(negedge clk);
    end endtask

    initial begin
        fh = $fopen("cases.txt", "r");
        if (fh == 0) begin $display("FAIL cannot open cases.txt"); $finish; end
        code = $fscanf(fh, "%d\n", ncases);
        rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1;

        for (c = 0; c < ncases; c = c + 1) begin
            code = $fscanf(fh, "%s %d %h %h %h %h %h %d\n", name, width_i,
                           max_i, sums_i, sink_i, se_i, den_i, sat_i);
            for (j = 0; j < 512; j = j + 1) mem[j] = 32'd0;
            for (j = 0; j < WIDTH; j = j + 1) exp_codes[j] = 32'd0;
            $sformat(path, "acc_%0d.hex", c);   $readmemh(path, mem, ACC_BASE);
            $sformat(path, "codes_%0d.hex", c); $readmemh(path, exp_codes);

            cfg_width = width_i; cfg_acc_base = ACC_BASE; cfg_out_base = OUT_BASE;
            cfg_final_max = max_i; cfg_final_sums = sums_i; cfg_sink_code = sink_i;
            go;

            if (error_code !== 8'h00) begin
                $display("FAIL %0s error_code=%0h", name, error_code);
                errors = errors + 1;
            end
            if (sink_exp !== se_i) begin
                $display("FAIL %0s sink_exp got %08h expected %08h",
                         name, sink_exp, se_i);
                errors = errors + 1;
            end
            if (final_denominator !== den_i) begin
                $display("FAIL %0s denominator got %08h expected %08h",
                         name, final_denominator, den_i);
                errors = errors + 1;
            end
            if (writes !== width_i || out_count !== width_i) begin
                $display("FAIL %0s wrote %0d (counter %0d), expected %0d",
                         name, writes, out_count, width_i);
                errors = errors + 1;
            end
            for (j = 0; j < width_i; j = j + 1)
                if (mem[OUT_BASE + j] !== exp_codes[j]) begin
                    $display("FAIL %0s channel %0d got %08h expected %08h",
                             name, j, mem[OUT_BASE + j], exp_codes[j]);
                    errors = errors + 1;
                end
            //: The saturating clamp is _narrow's, so its count is checked too --
            //: a clamp that never fired would leave case ``saturating`` passing
            //: on a branch nothing reached.
            if (saturation_count !== sat_i) begin
                $display("FAIL %0s saturated %0d channels, expected %0d",
                         name, saturation_count, sat_i);
                errors = errors + 1;
            end
            $display("  %0s: sink_exp=%08h denom=%08h writes=%0d saturated=%0d",
                     name, sink_exp, final_denominator, writes, saturation_count);
        end
        $fclose(fh);

        // -- the one place the RTL is still narrower than the reference ------
        //: A sink above the maximum is NO LONGER a refusal -- the cases above
        //: cover both signs -- so what remains is the denominator.
        cfg_width = WIDTH;
        //: A denominator that is not positive. The reference flags the row and
        //: repairs it through an exact oracle; there is none here.
        cfg_final_max = 32'h00000000; cfg_sink_code = 32'hc2c80000;  //: -100
        cfg_final_sums = 32'h80000000;                              //: -0
        go;
        if (error_code !== ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE) begin
            $display("FAIL nonpositive denominator gave %0h", error_code);
            errors = errors + 1;
        end
        //: And a zero width is a shape refusal.
        cfg_width = 32'd0; cfg_final_sums = 32'h41000000; go;
        if (error_code !== ot_a3_engine_pkg::ERR_SHAPE) begin
            $display("FAIL zero width gave %0h", error_code);
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS a3_attention_epilogue: %0d cases match exp_cr32 and _narrow on the sink term, the denominator and every channel, at BOTH offset signs, and 2 refusals fail closed", ncases);
        else
            $display("FAIL a3_attention_epilogue: %0d errors", errors);
        $finish;
    end
endmodule
