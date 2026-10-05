`timescale 1ns/1ps
// Op-SEQUENCE bench of the DS HBM SM element (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv; ENABLE = 1 is the 1.2 GHz
// successor) for the matched HBM reference (results/rtl/dshbm_matched_reference_20261005).  It runs a list of
// matvec ops back to back on ONE element, the way the static TP-96 program issues them on the busiest SM, and
// measures per op the three terms the single-op bench (tb_hbm_accel_sm_v) leaves out:
//   * x (activation) loading: an op whose input is not resident writes ONLY its used x-store addresses
//     (8 x groups), XB beats each (the 2048-bit write port, one beat a cycle), then waits the element's documented
//     >= 1 cycle before `start` (ot_hbm_accel_sm_v header); the beats are timed from the cycle after the previous op
//     is done (serial: single x context, the next op's input is produced after the previous op on the dependency
//     path -- no overlap is claimed);
//   * the issue span with its unused slots (waves of 8 items, the partial last wave) and
//   * each op's own drain: the issue accepts `start` only when not busy (ot_hbm_accel_issue), so every op is
//     started after the previous one is done -- nothing is batched.
// Weights stream WARM: every descriptor is posted as soon as the element accepts it (the static schedule posts the
// next descriptors ahead; the bulk copy's ring keeps streaming through op boundaries), so the HBM share's latency
// (LAT + jitter) is hidden wherever the ring run-ahead covers it; whatever is not hidden stays in the measured cycles.
// Unused x-store addresses keep the PREVIOUS op's data (never cleared), and every op's x differs, so an op that read a
// stale or not-yet-landed x word would mismatch the golden.
// Files (DIR): seq.hex (8 words per op: rows, c, groups, fmt, lines, gs, xload, xaddrs), lines.hex (all ops'
// weight lines concatenated, op i at the running offset), x.hex (for every op with xload = 1, its xaddrs fragment
// words in address order, FRAGW bits each), nops via +NOPS.  Output out.txt: "<op> <row> <data>" result lines and
// one "# op <i> ..." timing line per op.
module tb_hbm_accel_sm_v_seq;
    parameter integer ENABLE = 1, SUB = 4, LBS = 2, LSB = 16, NC = 1, XDEPTH = 128, RMAX = 256, LEV = 4,
                      LAT = 60, JIT = 40, MAXOPS = 48, XB = 0;     // XB: beats per x address (0 = all FRAGW beats)
    localparam integer RW = $clog2(RMAX);
    localparam integer FRAGW = NC * (SUB * LBS * 266 + SUB * LSB * 16);
    localparam integer NBEAT = (FRAGW + 2047) / 2048;
    localparam integer XBEATS = (XB == 0 || XB > NBEAT) ? NBEAT : XB;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_gs; reg [1:0] op_fmt;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines = 0;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
    reg xw_en = 0; reg [$clog2(XDEPTH)-1:0] xw_addr; reg [6:0] xw_grp; reg [8*256-1:0] xw_data;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_hbm_accel_sm_v #(.ENABLE(ENABLE), .SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .RMAX(RMAX), .LEV(LEV), .XD(XDEPTH),
                        .MAX_OUT(512)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .op_fmt(op_fmt), .busy(busy), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base),
        .d_lines(d_lines), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp),
        .xw_data(xw_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [1087:0] lines [0:131071];
    reg [FRAGW+2047:0] xwords [0:MAXOPS*XDEPTH-1];
    reg [31:0] seq [0:MAXOPS*8-1];
    integer base_of [0:MAXOPS-1];
    // behavioural HBM share (as tb_hbm_accel_sm_v): reads return after LAT + jitter, any order, one a cycle
    reg [31:0] p_addr [0:511]; reg [9:0] p_tag [0:511]; integer p_rdy [0:511]; reg p_use [0:511];
    integer i, ii, gg, op, nops, fo, seed, pick, cyc, xptr, nd, acc;
    integer t_load0 [0:MAXOPS-1]; integer t_start [0:MAXOPS-1]; integer t_done [0:MAXOPS-1];
    integer t_first [0:MAXOPS-1]; integer t_last [0:MAXOPS-1]; integer nres [0:MAXOPS-1];
    integer t_lastline [0:MAXOPS-1]; integer consumed [0:MAXOPS-1]; integer t_dpost [0:MAXOPS-1];
    integer cur, cons_total, line_op;
    reg [1023:0] dir;
    initial for (ii = 0; ii < 512; ii = ii + 1) p_use[ii] = 0;
    always @(posedge clk) begin
        rsp_v <= 1'b0;
        if (rst_n) begin
            if (req_v) begin
                pick = -1;
                for (i = 0; i < 512; i = i + 1) if (!p_use[i] && pick < 0) pick = i;
                p_use[pick] = 1; p_addr[pick] = req_addr; p_tag[pick] = req_tag;
                p_rdy[pick] = cyc + LAT + ($urandom(seed) % (JIT + 1));
            end
            pick = -1;
            for (i = 0; i < 512; i = i + 1)
                if (p_use[i] && p_rdy[i] <= cyc && (pick < 0 || p_rdy[i] < p_rdy[pick])) pick = i;
            if (pick >= 0) begin
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
    // weight-line takes are attributed to ops by the running line count (the stream is in op order)
    always @(posedge clk) if (take) begin
        while (line_op < nops - 1 && cons_total >= base_of[line_op + 1]) line_op = line_op + 1;
        consumed[line_op] = consumed[line_op] + 1; t_lastline[line_op] = cyc; cons_total = cons_total + 1;
    end
    // descriptors: posted in order as soon as the element accepts them (warm stream)
    initial begin
        nd = 0;
        wait (rst_n);
        @(negedge clk);
        while (nd < nops) begin
            d_valid = 1; d_base = base_of[nd]; d_lines = seq[nd * 8 + 4];
            @(posedge clk);
            if (d_ready) begin t_dpost[nd] = cyc; nd = nd + 1; end
            @(negedge clk);
            d_valid = 0;
        end
    end
    always @(posedge clk) if (rv) begin
        if (nres[cur] == 0) t_first[cur] = cyc;
        t_last[cur] = cyc;
        $fwrite(fo, "%0d %0d %h\n", cur, rrow, rdata);
        nres[cur] = nres[cur] + 1;
    end
    always @(posedge clk) release_in <= arrive;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NOPS=%d", nops)) nops = 1;
        seed = 7; cyc = 0; cur = 0; cons_total = 0; line_op = 0;
        $readmemh({dir, "/seq.hex"}, seq);
        $readmemh({dir, "/lines.hex"}, lines);
        $readmemh({dir, "/x.hex"}, xwords);
        acc = 0;
        for (op = 0; op < nops; op = op + 1) begin
            base_of[op] = acc; acc = acc + seq[op * 8 + 4];
            nres[op] = 0; consumed[op] = 0; t_first[op] = -1; t_last[op] = -1; t_lastline[op] = -1;
        end
        fo = $fopen({dir, "/out.txt"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        xptr = 0;
        for (op = 0; op < nops; op = op + 1) begin
            @(negedge clk);
            t_load0[op] = cyc;
            if (seq[op * 8 + 6] != 0) begin
                for (ii = 0; ii < seq[op * 8 + 7]; ii = ii + 1)
                    for (gg = 0; gg < XBEATS; gg = gg + 1) begin
                        xw_en = 1; xw_addr = ii; xw_grp = gg; xw_data = xwords[xptr + ii][gg * 2048 +: 2048];
                        @(negedge clk);
                    end
                xw_en = 0;
                xptr = xptr + seq[op * 8 + 7];
                @(negedge clk);                       // the documented >= 1 cycle between the last beat and start
            end
            cur = op;
            op_rows = seq[op * 8 + 0]; op_c = seq[op * 8 + 1]; op_g = seq[op * 8 + 2]; op_fmt = seq[op * 8 + 3];
            op_gs = seq[op * 8 + 5];
            start = 1; t_start[op] = cyc;
            @(negedge clk); start = 0;
            wait (busy); wait (!busy);
            @(negedge clk);
            t_done[op] = cyc;                         // first negedge with busy low (start may follow at once)
        end
        repeat (8) @(posedge clk);
        for (op = 0; op < nops; op = op + 1)
            $fwrite(fo, "# op %0d load_cycles %0d start_to_done %0d start_to_first %0d start_to_last %0d results %0d lines %0d consumed %0d drain_last_line_to_last_result %0d descriptor_posted_before_start %0d fault %0d\n",
                    op, t_start[op] - t_load0[op], t_done[op] - t_start[op], t_first[op] - t_start[op],
                    t_last[op] - t_start[op], nres[op], seq[op * 8 + 4], consumed[op], t_last[op] - t_lastline[op],
                    t_start[op] - t_dpost[op], fault);
        $fwrite(fo, "# total_cycles %0d\n", cyc);
        $fclose(fo);
        $finish;
    end
    initial begin #50000000; $fwrite(fo, "# TIMEOUT\n"); $fclose(fo); $finish; end
endmodule
