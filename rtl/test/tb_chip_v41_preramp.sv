// tb_chip_v41_preramp -- self-checking bench of the schedule-driven current pre-ramp (W18).
// A static schedule of field-wide ops (random lengths and gaps, some shorter than two ramps) drives
// start_in / op_active.  Checked every cycle: the enabled-group count never moves by more than one group per
// cycle and never faster than one group per cfg_ramp/NG cycles (a bounded dI/dt), every group is on at every op
// start (no step when the real work begins), no group runs dummy work during an op, and the field returns
// to zero enables after the last op.  The dummy group-cycles are reported (the ramp's energy).
`timescale 1ns/1ps
module tb_chip_v41_preramp;
    localparam int NG = 64;
    logic clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    logic [15:0] cfg_ramp = 16'd256, cfg_gap = 16'd400, start_in = 0;
    logic holding;
    logic op_active = 0;
    logic [NG-1:0] grp_en, grp_dummy;
    ot_chip_v41_preramp #(.NG(NG)) dut (.*);
    int errors = 0, cyc = 0, prev = 0, last_change = -1000, dummy_gc = 0, starts = 0, held_gaps = 0, ramped_gaps = 0;
    int step;
    assign step = cfg_ramp / NG;
    int lvl;
    always @(posedge clk) if (rst_n) begin
        lvl = $countones(grp_en);
        cyc <= cyc + 1;
        if (lvl - prev > 1 || prev - lvl > 1) begin
            // an op start raises every group at once; that is only legal if all groups were already on
            errors++; $display("ERR level jump %0d -> %0d @%0d", prev, lvl, cyc);
        end
        if (lvl != prev && !op_active) begin
            if (cyc - last_change < step - 1) begin errors++; $display("ERR ramp too fast @%0d", cyc); end
            last_change = cyc;
        end
        if (op_active && (grp_dummy != 0)) begin errors++; $display("ERR dummy during op"); end
        dummy_gc += $countones(grp_dummy);
        prev = lvl;
    end

    task automatic op(input int gap, input int len);
        // the schedule announces the start 'gap' cycles ahead (start_in counts down); a gap no longer than
        // cfg_gap after an op must be held at full enables, a longer one ramps
        int minlvl;
        minlvl = NG;
        for (int t = gap; t > 0; t--) begin
            @(negedge clk); start_in = 16'(t); op_active = 0;
            if ($countones(grp_en) < minlvl) minlvl = $countones(grp_en);
        end
        if (starts > 0 && gap <= cfg_gap) begin
            held_gaps++;
            if (minlvl != NG) begin errors++; $display("ERR short gap %0d not held (min %0d)", gap, minlvl); end
        end
        if (starts > 0 && gap > cfg_ramp + cfg_ramp && minlvl == NG) begin
            errors++; $display("ERR long gap %0d never ramped down", gap); end
        if (starts > 0 && gap > cfg_gap) ramped_gaps++;
        @(negedge clk); start_in = 0; op_active = 1; starts++;
        @(posedge clk);
        if ($countones(grp_en) != NG) begin errors++; $display("ERR op start with %0d groups", $countones(grp_en)); end
        for (int t = 1; t < len; t++) @(negedge clk);
        @(negedge clk); op_active = 0;
    endtask

    initial begin
        repeat (4) @(posedge clk); rst_n = 1;
        for (int k = 0; k < 60; k++) op(($urandom_range(2) == 0) ? 1 + $urandom_range(399) : 401 + $urandom_range(600),
                                         20 + $urandom_range(300));
        repeat (400) @(negedge clk);
        if ($countones(grp_en) != 0) begin errors++; $display("ERR field not released"); end
        $display("W18_PRERAMP_RESULT ops=%0d ramp=%0d gap=%0d groups=%0d held_gaps=%0d ramped_gaps=%0d dummy_group_cycles=%0d errors=%0d",
                 starts, cfg_ramp, cfg_gap, NG, held_gaps, ramped_gaps, dummy_gc, errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
