`timescale 1ns/1ps
// Equivalence of the parameterised dependence table against the pre-change one.
//
// Three instances driven by one stimulus stream: the reference (as committed),
// the new module at CHECK_STAGES = 1, and the new module at CHECK_STAGES = 2.
// The first two must agree on EVERY cycle -- that is the claim that the default
// is the netlist it always was.  The third must agree with the reference one
// cycle later, which is the claim that the deeper pipeline answers the same
// question about the same instant and only later.
module tb_a3_dependence_table_depth;
    reg clk = 0, rst_n = 0, clear = 0;
    reg        insert_valid = 0;
    reg [4:0]  insert_slot = 0;
    reg [15:0] insert_object = 0;
    reg [39:0] insert_lo = 0, insert_hi = 0;
    reg        insert_write = 0;
    reg        check0_valid = 0, check1_valid = 0;
    reg [15:0] check0_object = 0, check1_object = 0;
    reg [39:0] check0_lo = 0, check0_hi = 0, check1_lo = 0, check1_hi = 0;
    reg        check0_write = 0, check1_write = 0;
    reg        release_valid = 0;
    reg [4:0]  release_slot = 0;

    wire r_c0, r_c1, a_c0, a_c1, b_c0, b_c1;
    wire [7:0] r_used, a_used, b_used;

    ot_a3_dependence_table_ref ref_dut (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .insert_valid(insert_valid), .insert_slot(insert_slot),
        .insert_object(insert_object), .insert_lo(insert_lo),
        .insert_hi(insert_hi), .insert_write(insert_write),
        .check0_valid(check0_valid), .check0_object(check0_object),
        .check0_lo(check0_lo), .check0_hi(check0_hi),
        .check0_write(check0_write), .check0_conflict(r_c0),
        .check1_valid(check1_valid), .check1_object(check1_object),
        .check1_lo(check1_lo), .check1_hi(check1_hi),
        .check1_write(check1_write), .check1_conflict(r_c1),
        .release_valid(release_valid), .release_slot(release_slot),
        .dbg_ranges_used(r_used));

    ot_a3_dependence_table #(.CHECK_STAGES(1)) one_dut (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .insert_valid(insert_valid), .insert_slot(insert_slot),
        .insert_object(insert_object), .insert_lo(insert_lo),
        .insert_hi(insert_hi), .insert_write(insert_write),
        .check0_valid(check0_valid), .check0_object(check0_object),
        .check0_lo(check0_lo), .check0_hi(check0_hi),
        .check0_write(check0_write), .check0_conflict(a_c0),
        .check1_valid(check1_valid), .check1_object(check1_object),
        .check1_lo(check1_lo), .check1_hi(check1_hi),
        .check1_write(check1_write), .check1_conflict(a_c1),
        .release_valid(release_valid), .release_slot(release_slot),
        .dbg_ranges_used(a_used));

    ot_a3_dependence_table #(.CHECK_STAGES(2)) two_dut (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .insert_valid(insert_valid), .insert_slot(insert_slot),
        .insert_object(insert_object), .insert_lo(insert_lo),
        .insert_hi(insert_hi), .insert_write(insert_write),
        .check0_valid(check0_valid), .check0_object(check0_object),
        .check0_lo(check0_lo), .check0_hi(check0_hi),
        .check0_write(check0_write), .check0_conflict(b_c0),
        .check1_valid(check1_valid), .check1_object(check1_object),
        .check1_lo(check1_lo), .check1_hi(check1_hi),
        .check1_write(check1_write), .check1_conflict(b_c1),
        .release_valid(release_valid), .release_slot(release_slot),
        .dbg_ranges_used(b_used));

    always #1 clk = ~clk;

    integer cycle, errors, seed, checks, deep_checks;
    reg r_c0_d, r_c1_d, r_valid_d;
    initial begin
        errors = 0; checks = 0; deep_checks = 0; seed = 32'h5eed_0001;
        r_c0_d = 0; r_c1_d = 0; r_valid_d = 0;
        repeat (4) @(negedge clk); rst_n = 1;
        for (cycle = 0; cycle < 20000; cycle = cycle + 1) begin
            @(negedge clk);
            // Random traffic over a small object space so conflicts actually occur.
            insert_valid  = ($random(seed) % 3) == 0;
            insert_slot   = $random(seed) % 32;
            insert_object = $random(seed) % 6;
            insert_lo     = $random(seed) % 64;
            insert_hi     = insert_lo + 1 + ($random(seed) % 32);
            insert_write  = ($random(seed) % 2) == 0;
            check0_valid  = ($random(seed) % 2) == 0;
            check0_object = $random(seed) % 6;
            check0_lo     = $random(seed) % 64;
            check0_hi     = check0_lo + 1 + ($random(seed) % 32);
            check0_write  = ($random(seed) % 2) == 0;
            check1_valid  = ($random(seed) % 2) == 0;
            check1_object = $random(seed) % 6;
            check1_lo     = $random(seed) % 64;
            check1_hi     = check1_lo + 1 + ($random(seed) % 32);
            check1_write  = ($random(seed) % 2) == 0;
            release_valid = ($random(seed) % 7) == 0;
            release_slot  = $random(seed) % 32;
            clear         = ($random(seed) % 997) == 0;
            @(posedge clk);
            #0;
            checks = checks + 1;
            if (r_c0 !== a_c0 || r_c1 !== a_c1 || r_used !== a_used) begin
                errors = errors + 1;
                if (errors < 8)
                    $display("STAGE1 MISMATCH cycle %0d ref=%b%b/%0d new=%b%b/%0d",
                             cycle, r_c0, r_c1, r_used, a_c0, a_c1, a_used);
            end
            // The deep form must equal the reference delayed by one cycle.
            if (cycle > 2) begin
                deep_checks = deep_checks + 1;
                if (b_c0 !== r_c0_d || b_c1 !== r_c1_d) begin
                    errors = errors + 1;
                    if (errors < 16)
                        $display("STAGE2 MISMATCH cycle %0d refd=%b%b deep=%b%b",
                                 cycle, r_c0_d, r_c1_d, b_c0, b_c1);
                end
            end
            r_c0_d = r_c0; r_c1_d = r_c1;
        end
        $display("cycles=%0d stage1_checks=%0d stage2_checks=%0d errors=%0d",
                 cycle, checks, deep_checks, errors);
        if (errors == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
