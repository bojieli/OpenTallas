`timescale 1ns/1ps
module tb;
    reg ck = 0, rst_n = 0;
    always #5 ck = ~ck;
    reg [31:0] v = 0;
    reg [17:0] expected = 0;
    reg [89:0] slot = 0;
    reg [15:0] extra = 0;
    wire fault, old_bad;
    dsfd_vm_native_valid_diag dut(ck, rst_n, v, expected, slot, extra, fault);
    // Existing production RTL is the independent oracle; its data output is
    // deliberately unused because only its live READ4 diagnostic cone changes.
    dsfd_vm_static_suhc_return_map #(.DW(1)) original(
        .i_v(v), .i_data(32'd0), .expected_v(expected), .release_slot(slot),
        .o_v(), .o_data(), .fault(old_bad));
    reg old_bad_q = 0, expected_fault = 0;
    integer checked = 0, bad = 0, seed = 5127;
    always @(posedge ck) begin
        old_bad_q <= old_bad | (|extra);
        if (!rst_n) expected_fault <= 0;
        else expected_fault <= expected_fault | old_bad_q;
        #1;
        if (checked > 2 && fault !== expected_fault) begin
            bad = bad + 1;
            if (bad < 8) $display("DIAG mismatch edge=%0d got=%b expected=%b", checked, fault, expected_fault);
        end
        checked = checked + 1;
    end
    task clear_fault;
        begin
            @(negedge ck); rst_n = 0; expected = 0; v = 0; slot = 0; extra = 0;
            repeat(3) @(negedge ck);
            rst_n = 1;
        end
    endtask
    integer p, s, k, t;
    initial begin
        clear_fault();
        // Exhaust all 18 logical ports, all32 selectors and the selected bit's
        // present/absent states. Invalid slots are tested with every bit valid.
        for (p = 0; p < 18; p = p + 1) begin
            for (s = 0; s < 32; s = s + 1) begin
                for (t = 0; t < 2; t = t + 1) begin
                    clear_fault();
                    expected = 18'd1 << p;
                    slot[5*p+:5] = s;
                    v = t ? 32'hffffffff : 0;
                    repeat(3) @(negedge ck);
                    expected = 0;
                    repeat(2) @(negedge ck);
                end
            end
        end
        for (k = 0; k < 16; k = k + 1) begin
            clear_fault(); extra = 16'd1 << k;
            repeat(3) @(negedge ck);
        end
        // Parallel-port traffic and reset/restart after a sticky error.
        for (k = 0; k < 500; k = k + 1) begin
            if (k % 13 == 0) clear_fault();
            extra = $random(seed); v = $random(seed); expected = $random(seed);
            for (p = 0; p < 18; p = p + 1) slot[5*p+:5] = $random(seed);
            @(negedge ck);
        end
        expected = 0;
        repeat(4) @(negedge ck);
        $display("NATIVE_DIAG %s checked=%0d exhaustive_cases=1152 randomized_edges=500", bad ? "FAIL" : "PASS", checked);
        if (bad) $fatal(1);
        $finish;
    end
endmodule
