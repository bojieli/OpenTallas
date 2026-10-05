`timescale 1ns/1ps
// Bench of the 1.2 GHz SM successor (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv; ENABLE = 0 is W13's ot_gpu_sm_v):
// tb_gpu_sm_v unchanged except the DUT and its line-take probe.  Original header:
// Bench of the V4.1 SM macro top (rtl/gpu/ot_gpu_sm_v.sv) with its physical parts: the weight lines come
// from a behavioural HBM share through the SM's own bulk-copy engine (reads return after LAT + jitter, in
// any order, one line a cycle at most), the x fragments are written into the x-store macros, the row
// scales into the scale macro.  Same vectors and result format as tb_gpu_sm (tools/rtl_gpu_sm_exact.py).
module tb_hbm_accel_sm_v_finite;
    parameter integer ENABLE = 1, SUB = 4, LBS = 2, LSB = 16, NC = 8, XDEPTH = 128, RMAX = 4096, LEV = 4, LAT = 60, JIT = 40;
    localparam integer RW = $clog2(RMAX);
    localparam integer FRAGW = NC * (SUB * LBS * 266 + SUB * LSB * 16);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_scale; reg op_gs; reg [1:0] op_fmt;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines;
    wire req_ready;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
    reg xw_en = 0; reg [$clog2(XDEPTH)-1:0] xw_addr; reg [6:0] xw_grp; reg [8*256-1:0] xw_data; integer gg;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_hbm_accel_sm_v #(.ENABLE(ENABLE), .SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .RMAX(RMAX), .LEV(LEV), .XD(XDEPTH), .MAX_OUT(512)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .op_fmt(op_fmt), .busy(busy), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base),
        .d_lines(d_lines), .req_v(req_v), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp),
        .xw_data(xw_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [1087:0] lines [0:65535];
    reg [FRAGW+2047:0] xwords [0:XDEPTH-1];
    reg [31:0] cfg [0:7];
    // behavioural HBM share: pending reads
    reg [31:0] p_addr [0:511]; reg [9:0] p_tag [0:511]; integer p_rdy [0:511]; reg p_use [0:511];
    integer accepted_requests = 0, returned_requests = 0, stalled_requests = 0;
    integer free_slot;
    integer t_done, nlines, i, ii, kk, fo, seed, pick, cyc, t0, t_first, t_last, nres, t_lastline, consumed;
    reg [1023:0] dir;
    initial for (ii = 0; ii < 512; ii = ii + 1) p_use[ii] = 0;
    // Actual finite provider admission, sampled on the same OLD request edge.
    // No constant ready: two blocked cycles per nine plus the 512 live seats.
    always @* begin
        free_slot = -1;
        for (integer seat=0; seat<512; seat=seat+1)
            if (!p_use[seat] && free_slot<0) free_slot=seat;
    end
    assign req_ready = rst_n && free_slot>=0 && cyc%9>=2;
    always @(posedge clk) begin
        rsp_v <= 1'b0;
        if (rst_n) begin
            if (req_v && !req_ready) stalled_requests=stalled_requests+1;
            if (req_v && req_ready) begin
                accepted_requests=accepted_requests+1;
                if (req_addr>=nlines) $fatal(1,"accepted request outside real weight lines");
                for (integer seat=0;seat<512;seat=seat+1)
                    if (p_use[seat] && p_tag[seat]==req_tag) $fatal(1,"duplicate live request tag");
                pick = -1;
                for (i = 0; i < 512; i = i + 1) if (!p_use[i] && pick < 0) pick = i;
                if (pick<0) $fatal(1,"request accepted without finite seat");
                p_use[pick] = 1; p_addr[pick] = req_addr; p_tag[pick] = req_tag;
                p_rdy[pick] = cyc + LAT + ($urandom(seed) % (JIT + 1));
            end
            pick = -1;
            for (i = 0; i < 512; i = i + 1)
                if (p_use[i] && p_rdy[i] <= cyc && (pick < 0 || p_rdy[i] < p_rdy[pick])) pick = i;
            if (pick >= 0) begin
                returned_requests=returned_requests+1;
                rsp_v <= 1'b1; rsp_tag <= p_tag[pick]; rsp_data <= lines[p_addr[pick]];
                p_use[pick] = 0;
            end
        end
    end
    always @(posedge clk) cyc <= cyc + 1;
    wire take;
    generate if (ENABLE != 0) begin : g_pn
        assign take = dut.g_new.w_valid && dut.g_new.w_ready;
    end else begin : g_po
        assign take = dut.g_original.u_original.w_valid && dut.g_original.u_original.w_ready;
    end endgenerate
    always @(posedge clk) if (take) begin consumed = consumed + 1; t_lastline = $time; end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        seed = 7; cyc = 0; nres = 0; consumed = 0;
        $readmemh({dir, "/cfg.hex"}, cfg);
        op_rows = cfg[0]; op_c = cfg[1]; op_g = cfg[2]; op_fmt = cfg[3]; nlines = cfg[4]; op_gs = cfg[5];
        $readmemh({dir, "/lines.hex"}, lines);
        $readmemh({dir, "/x.hex"}, xwords);
        fo = $fopen({dir, "/out.txt"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        for (ii = 0; ii < XDEPTH; ii = ii + 1)
            for (gg = 0; gg < (FRAGW + 2047) / 2048; gg = gg + 1) begin
                @(negedge clk); xw_en = 1; xw_addr = ii; xw_grp = gg; xw_data = xwords[ii][gg * 2048 +: 2048];
            end
        @(negedge clk); xw_en = 0; d_valid = 1; d_lines = nlines;
        // Retain descriptor through its real credit-channel handshake.
        @(posedge clk);
        while (!d_ready) @(posedge clk);
        @(negedge clk); d_valid = 0; start = 1;
        t0 = $time;
        @(negedge clk); start = 0;
    end
    always @(posedge clk) if (rv) begin
        if (nres == 0) t_first = $time;
        t_last = $time;
        $fwrite(fo, "%0d %h\n", rrow, rdata);
        nres = nres + 1;
    end
    integer arrived_edges=0;
    always @(posedge clk) begin
        if (arrive) arrived_edges=arrived_edges+1;
        release_in <= arrived_edges>=6; // actual arrival-held barrier, not an idle/timer grant
    end
    initial begin
        #5;
        wait (rst_n); wait (start); wait (!start); wait (busy); wait (!busy);
        repeat (4) @(posedge clk);
        t_done = $time - t0;
        // the successor's barrier outputs reach the pins PIO cycles later: wait (bounded) for `released`
        for (kk = 0; kk < 64 && !released; kk = kk + 1) @(posedge clk);
        $fwrite(fo, "# cycles_start_to_done %0d first_result %0d last_result %0d lines %0d consumed %0d fault %0d released %0d drain_last_line_to_last_result %0d released_after_done %0d\n",
                t_done, t_first - t0, t_last - t0, nlines, consumed, fault, released, t_last - t_lastline, $time - t0 - t_done + 4);
        if (accepted_requests!=nlines || returned_requests!=nlines ||
            consumed!=nlines || !released || fault || stalled_requests==0)
            $fatal(1,"request/return/consume/barrier debt did not close");
        for (integer seat=0;seat<512;seat=seat+1)
            if(p_use[seat]) $fatal(1,"pending provider debt at terminal");
        $fwrite(fo,"# accepted_requests %0d returned_requests %0d stalled_requests %0d\n",
                accepted_requests,returned_requests,stalled_requests);
        $fclose(fo);
        $finish;
    end
endmodule
