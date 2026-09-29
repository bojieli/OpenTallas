`timescale 1ns/1ps
module tb_chip_v41x_window_refill_schedule;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, start_v=0, prefetch_ready=1, prefetch_ok=0;
    reg prefetch_fault=0, issue_ready=1, issue_done=0, issue_fault=0;
    reg [9:0] start_user=0;
    reg [20:0] start_first=0;
    reg [7:0] start_count=0;
    wire start_ready, prefetch_v, issue_v, busy, done, fault;
    wire [9:0] prefetch_user, issue_user;
    wire [20:0] prefetch_row, issue_first;
    wire [7:0] issue_count, rows_refilled;
    wire [31:0] refill_cycles;
    integer sent=0, seen=0, age=0, jobs=0;
    reg pending=0;
    reg [9:0] expected_user;
    reg [20:0] expected_first;
    reg [7:0] expected_count;
    ot_chip_v41x_window_refill_schedule dut (.*);
    always @(posedge clk) if (rst_n) begin
        prefetch_ok <= 0;
        if (prefetch_v) begin
            if (pending || prefetch_user !== expected_user ||
                prefetch_row !== expected_first + 21'(sent))
                $fatal(1,"refill request tag/order mismatch");
            sent <= sent+1; pending <= 1; age <= 0;
        end else if (pending) begin
            age <= age+1;
            if (age == 2) begin
                prefetch_ok <= 1; pending <= 0;
            end
        end
        if (issue_v) begin
            if (sent != expected_count || rows_refilled != expected_count ||
                issue_user !== expected_user || issue_first !== expected_first ||
                issue_count !== expected_count)
                $fatal(1,"issue before all tagged rows refilled");
            seen <= seen+1;
            issue_done <= 1;
        end else issue_done <= 0;
        if (done) jobs <= jobs+1;
    end
    task automatic run_job(input integer u, input integer p, input integer n);
        begin
            wait (start_ready);
            @(negedge clk);
            expected_user = 10'(u); expected_first = 21'(p);
            expected_count = 8'(n); sent=0;
            start_v=1; start_user=10'(u); start_first=21'(p); start_count=8'(n);
            @(negedge clk); start_v=0;
            wait (done); @(negedge clk);
            if (fault || sent != n || seen != jobs+1)
                $fatal(1,"job completion mismatch");
        end
    endtask
    initial begin
        repeat(4) @(negedge clk); rst_n=1;
        run_job(0,126,4); // includes 127/128/129 bank rotation
        run_job(1,254,1); // same ring slot, different user/tag
        run_job(1,1048575,1);
        $display("WINDOW_REFILL_SCHEDULE_PASS jobs=3 rows=6 users=2 wrap=1");
        $finish;
    end
    initial begin #100000; $fatal(1,"refill scheduler timeout"); end
endmodule
