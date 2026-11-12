`timescale 1ns/1ps
// HBM-HUB-RTL-1 11-11 rd1 bind-side +1 BENCH: an SU LG tap (ot_hbm_vm_lg_static_bank, the leaf of
// ot_hbm_vm_lg_pair_tap) wired pin-to-pin (0 die stages, N = 0) to one faces bank body: a read round trip through the
// bank and the tap's fixed-latency calendar.  Law: READ_RETURN = 11 + N + X (X = core pin cycles: 0 main, 1 rd1),
// WRITE_RETURN = 8 + N.  Sticky tap fault (read_due && !rr_v | write_due && !done_d | ...) must stay 0 with the law
// value, and +0 / +2 of the rd1 term must trip it.  Data check: every read returns the written data on local_rr.
module tb;
    parameter integer RR = 11, WR = 8, RG = 5, WG = 2;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg  [16:0]  local_rq = 0;
    reg  [280:0] local_wq = 0;
    reg          local_read = 0, local_write = 0;
    wire [16:0]  near_rq;
    wire [280:0] near_wq;
    wire [256:0] near_rr, local_rr, far_rr;
    wire         near_w_done, local_w_done, far_w_done, fault;
    ot_hbm_vm_lg_static_bank #(.READ_RETURN(RR), .WRITE_RETURN(WR)) u_tap(
        .clk(clk), .rst_n(rst_n), .rret(5'd0), .wret(5'd0),
        .local_rq(local_rq), .far_rq(17'd0), .local_wq(local_wq), .far_wq(281'd0),
        .local_read(local_read), .local_write(local_write),
        .near_rq(near_rq), .near_wq(near_wq), .near_rr(near_rr), .near_w_done(near_w_done),
        .local_rr(local_rr), .far_rr(far_rr), .local_w_done(local_w_done), .far_w_done(far_w_done), .fault(fault));
    // the die master hfd_vms_bank_native_q0_faces (ot_pin_regs input pin flops -> ot_vms_bank_q0_faces_core -> body)
    wire [256:0] rr0, rr1, rr2, rr3, rr4;
    wire wq_done0, wq_done1;
    wire [275:0] eg;
    wire [265:0] pr;
    wire [17:0] status;
    wire dq_done, kq_done, xq_done, xq2_done;
    wire [256:0] rr = rr0;
    hfd_vms_bank_native_q0_faces u_bank(
        .clk(clk), .rst_n(rst_n), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk),
        .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .bid(3'd0), .sid(2'd0),
        .rslot_v(near_rq[16]), .rslot(3'd0), .wslot_v(near_wq[280]), .wslot(3'd0),
        .rq0(near_rq), .rq1(17'd0), .rq2(17'd0), .rq3(17'd0), .rq4(17'd0),
        .rr0(rr0), .rr1(rr1), .rr2(rr2), .rr3(rr3), .rr4(rr4),
        .wq0(near_wq), .wq1(281'd0), .wq_done0(wq_done0), .wq_done1(wq_done1),
        .dq(281'd0), .dq_done(dq_done), .kq(281'd0), .kq_done(kq_done), .xq(276'd0), .xq_done(xq_done),
        .xq2(276'd0), .xq2_done(xq2_done), .eg(eg), .pq(285'd0), .pr(pr), .status(status));
    assign near_rr = rr0;
    assign near_w_done = wq_done0;
    function automatic [255:0] pat(input integer i);
        reg [31:0] w; reg [7:0] k;
        begin
            w = 32'h5A00_0000 ^ (32'h0101_0101 * (i + 1)); k = i;
            pat = {8{w}} ^ {k, 248'd0};
        end
    endfunction
    function automatic [15:0] sec(input integer row);
        sec = {1'b0, 2'd0, row[9:0], 3'd0};
    endfunction
    integer q[0:63]; integer qh = 0, qt = 0, nrd = 0, ngot = 0, nbad = 0, nwd = 0, i, r;
    always @(posedge clk) if (rst_n) begin
        if (local_rr[256]) begin
            ngot = ngot + 1;
            if (qh == qt || local_rr[255:0] !== pat(q[qh])) begin
                nbad = nbad + 1;
                if (nbad < 4) $display("BAD read @%0t got %h exp row %0d", $time, local_rr[63:0], q[qh]);
            end
            if (qh != qt) qh = qh + 1;
        end
        if (local_w_done) nwd = nwd + 1;
    end
    task automatic wr(input integer row);
        begin
            @(negedge clk); local_wq = {1'b1, sec(row), pat(row), 8'hFF}; local_write = 1;
            @(negedge clk); local_wq = 0; local_write = 0;
        end
    endtask
    task automatic rd(input integer row);
        begin
            @(negedge clk); local_rq = {1'b1, sec(row)}; local_read = 1; q[qt] = row; qt = qt + 1; nrd = nrd + 1;
            @(negedge clk); local_rq = 0; local_read = 0;
        end
    endtask
    integer first_fault = -1;
`ifdef TRACE
    always @(posedge clk) if (rst_n && (local_write || local_read || near_wq[280] || near_rq[16] || wq_done0 || rr0[256] || u_tap.read_due || u_tap.write_due))
        $display("T%0d lw=%b lr=%b nwq=%b nrq=%b done=%b rr=%b rdue=%b wdue=%b f=%b", $time, local_write, local_read, near_wq[280], near_rq[16],
                 wq_done0, rr0[256], u_tap.read_due, u_tap.write_due, fault);
`endif
    always @(posedge clk) if (fault && first_fault < 0) first_fault = $time;
    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1;
        repeat (8) @(negedge clk);
        for (i = 0; i < 8; i = i + 1) begin wr(i); repeat (4) @(negedge clk); end
        repeat (20) @(negedge clk);
        for (i = 0; i < 8; i = i + 1) begin rd(7 - i); repeat (3) @(negedge clk); end   // isolated round trips
        repeat (20) @(negedge clk);
        for (r = 0; r < 4; r = r + 1) begin                                              // back-to-back reads
            @(negedge clk); local_rq = {1'b1, sec(r)}; local_read = 1; q[qt] = r; qt = qt + 1; nrd = nrd + 1;
        end
        @(negedge clk); local_rq = 0; local_read = 0;
        repeat (30) @(negedge clk);
        $display("RESULT RR=%0d WR=%0d fault=%0d first_fault_t=%0d reads=%0d returned=%0d bad=%0d wdone=%0d bank_status=%h",
                 RR, WR, fault, first_fault, nrd, ngot, nbad, nwd, status);
        if (!fault && ngot == nrd && nbad == 0 && nwd == 8) $display("VERDICT PASS"); else $display("VERDICT FAULT");
        $finish;
    end
endmodule
