`timescale 1ns/1ps
// HBM-HCBANK6 10-20: ot_static_program_target FAN32 1 (bitmap written one edge later from slice copies + scan bypass,
// scan-row read copies) against FAN32 0 in lockstep on random F20 traffic (programme writes into a few small address
// windows with valid magic / identity, descriptors over those windows incl. reuse, back-to-back write -> descriptor,
// launches, illegal requests).  Every output compared on every edge.  +define+MUT=1 drives the FAN32 1 copy without
// its bypass (row_installed from the slice bitmap only): must FAIL.
`ifndef MUT
`define MUT 0
`endif
module tb_static_program_target_fan32;
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg cfg_v = 0, desc_v = 0, launch_v = 0, pa = 0;
    reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0, desc_base = 0; reg [255:0] cfg_data = 0;
    reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    wire [9:0] a0, a1, sb0, sb1; wire [255:0] d0, d1; wire [10:0] sl0, sl1; wire [15:0] lo0, lo1;
    wire we0, we1, sv0, sv1, c0, c1, f0, f1;
    ot_static_program_target #(.PCW(10), .TGT_PIN(1), .RLC(40), .FAN32(0)) r0 (.clk(clk), .rst_n(rst_n), .clk_cap(clk), .tgt(8'd108),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(pa), .program_cfg_we(we0),
        .program_cfg_addr(a0), .program_cfg_data(d0), .program_start_v(sv0), .program_start_base(sb0), .program_start_limit(sl0),
        .program_start_loops(lo0), .configured(c0), .fault(f0));
    ot_static_program_target #(.PCW(10), .TGT_PIN(1), .RLC(40), .FAN32(1), .MUT(`MUT)) r1 (.clk(clk), .rst_n(rst_n), .clk_cap(clk), .tgt(8'd108),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .program_active(pa), .program_cfg_we(we1),
        .program_cfg_addr(a1), .program_cfg_data(d1), .program_start_v(sv1), .program_start_base(sb1), .program_start_limit(sl1),
        .program_start_loops(lo1), .configured(c1), .fault(f1));
    integer cyc = 0, bad = 0, nconf = 0, nstart = 0, nfault = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            if ({we0, a0, d0, sv0, sb0, sl0, lo0, c0, f0} !== {we1, a1, d1, sv1, sb1, sl1, lo1, c1, f1}) begin
                bad <= bad + 1; if (bad < 5) $display("MISMATCH cyc=%0d c %b/%b f %b/%b sv %b/%b", cyc, c0, c1, f0, f1, sv0, sv1);
            end
            if (sv0) nstart <= nstart + 1;
        end
    end
    reg f0_q = 0; integer nfr = 0;
    always @(posedge clk) begin f0_q <= f0; if (f0 && !f0_q && nfr < 12) begin nfr <= nfr + 1;
        $display("FAULTRISE cyc=%0d cv=%b dv=%b lv=%b scan=%b armed=%b val=%b miss=%b pa=%b commit=%b addr=%0d", cyc, r0.cv, r0.dv, r0.lv,
                 r0.scanning, r0.armed, r0.validated, r0.missing, r0.program_active, r0.commit, r0.address);
        $display("   scan_row=%0d limit=%0d base=%0d inst=%b", r0.scan_row, r0.scan_limit, r0.stored_base, r0.installed[r0.stored_base +: 24]); end end
    reg c0_q = 0; always @(posedge clk) begin c0_q <= c0; if (c0 && !c0_q) nconf <= nconf + 1; end
    // every bus action occupies exactly one edge: inputs change at the falling edge (no race with the sampling edge)
    task automatic idle; begin cfg_v = 0; desc_v = 0; launch_v = 0; end endtask
    task automatic tick(input integer n); repeat (n) begin @(negedge clk); idle; end endtask
    task automatic wr(input [11:0] a);
        begin @(negedge clk); idle; cfg_v = 1; cfg_target = 8'd108; cfg_addr = a; cfg_data = {16'hc7a1, 4'h0, a, 224'($urandom)}; end
    endtask
    task automatic desc(input [11:0] b, input [12:0] l);
        begin @(negedge clk); idle; desc_v = 1; desc_base = b; desc_limit = l; desc_loops = 16'd1 + 16'($urandom % 2); end
    endtask
    integer it, n, k, gap; reg [11:0] b;
    initial begin
        tick(4); rst_n = 1; tick(8);
        for (it = 0; it < 1500; it = it + 1) begin
            b = 12'($urandom % 1000); n = 1 + $urandom % 24; if (b + n > 1024) b = 12'(1024 - n);
            gap = $urandom % 4;                                   // 0: back-to-back writes, else idle edges between
            for (k = 0; k < n; k = k + 1) begin
                if (!($urandom % 40 == 0)) wr(12'(b + k));         // rare missing row -> scan fault
                if (gap != 0) tick($urandom % gap);
            end
            if ($urandom % 3 == 0) begin                          // second generation: the first write clears the bitmap
                if ($urandom % 2) desc(b, 13'(b + n));
                tick($urandom % 3);
                for (k = 0; k < n; k = k + 1) if (!($urandom % 60 == 0)) wr(12'(b + n - 1 - k));
            end
            desc(b, 13'(b + n));                                  // immediately behind the last write (no idle edge)
            tick(n + 2 + $urandom % 4);
            if ($urandom % 4 == 0) desc(b, 13'(b + n));           // descriptor-only re-arm (reuse)
            tick(n + 4);
            @(negedge clk); idle; launch_v = ($urandom % 10 != 0);
            tick(3); pa = 1; tick(2 + $urandom % 8); pa = 0; tick(2);
            if (f0) begin nfault = nfault + 1; rst_n = 0; tick(3); rst_n = 1; tick(6); end
        end
        if (bad == 0 && nconf > 500 && nstart > 300 && nfault > 10) $display("PTGT_FAN32 PASS MUT=%0d configured=%0d starts=%0d faults=%0d", `MUT, nconf, nstart, nfault);
        else $display("PTGT_FAN32 FAIL MUT=%0d bad=%0d configured=%0d starts=%0d faults=%0d", `MUT, bad, nconf, nstart, nfault);
        $finish;
    end
endmodule
