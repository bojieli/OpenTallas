`timescale 1ns/1ps
// SM -> SU native result edge, composed with the real 1.2 GHz SM (ENABLE = 1) on W13's golden vectors:
// tb_hbm_accel_sm_v with the SM result face routed through ot_hbm_sm_su_result_edge (pin station, NST relay
// stations, pin station, SU result ingress).  The op's rows are RESERVED at the ingress before `start`; the
// result file is written from the ingress drain (count-gated release, random consumer back-pressure), so the
// golden comparison in tools/rtl_gpu_sm_exact.py checks the rows after the native edge.  `fault` reported is
// SM fault | ingress fault.  Original header follows.
// Bench of the 1.2 GHz SM successor (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv; ENABLE = 0 is W13's ot_gpu_sm_v):
// tb_gpu_sm_v unchanged except the DUT and its line-take probe.  Original header:
// Bench of the V4.1 SM macro top (rtl/gpu/ot_gpu_sm_v.sv) with its physical parts: the weight lines come
// from a behavioural HBM share through the SM's own bulk-copy engine (reads return after LAT + jitter, in
// any order, one line a cycle at most), the x fragments are written into the x-store macros, the row
// scales into the scale macro.  Same vectors and result format as tb_gpu_sm (tools/rtl_gpu_sm_exact.py).
module tb_hbm_sm_su_composed;
    parameter integer NST = 4, ENABLE = 1, SUB = 4, LBS = 2, LSB = 16, NC = 2, XDEPTH = 128, RMAX = 256, LEV = 4, LAT = 60, JIT = 40;
    localparam integer RW = $clog2(RMAX);
    localparam integer FRAGW = NC * (SUB * LBS * 266 + SUB * LSB * 16);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_scale; reg op_gs; reg [1:0] op_fmt;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
    reg xw_en = 0; reg [$clog2(XDEPTH)-1:0] xw_addr; reg [6:0] xw_grp; reg [8*256-1:0] xw_data; integer gg;
    wire sm_rv; wire [RW-1:0] sm_rrow; wire [NC*32-1:0] sm_rdata; wire sm_fault; wire arrive; wire released;
    wire ed_op_ack, ed_out_v, ed_op_done, ed_fault; wire [RW-1:0] ed_row; wire [NC*32-1:0] ed_data; wire [6:0] ed_done_rows, ed_free;
    reg ed_op_v = 0; reg ed_out_r = 0; wire fault = sm_fault | ed_fault; wire rv = ed_out_v && ed_out_r;
    wire [RW-1:0] rrow = ed_row; wire [NC*32-1:0] rdata = ed_data;
    ot_hbm_sm_su_result_edge #(.NST(NST), .RW(RW), .DW(NC*32)) edge_u (.clk(clk), .rst_n(rst_n), .rv(sm_rv), .rrow(sm_rrow),
        .rdata(sm_rdata), .sm_fault(sm_fault), .op_v(ed_op_v), .op_rows(op_rows[6:0]), .op_ack(ed_op_ack), .out_v(ed_out_v),
        .out_r(ed_out_r), .out_row(ed_row), .out_data(ed_data), .op_done(ed_op_done), .op_done_rows(ed_done_rows),
        .fault(ed_fault), .free_o(ed_free));
    integer ed_seed = 5; always @(negedge clk) ed_out_r = ($urandom % 5) != 0;
    integer done_seen = 0; always @(posedge clk) if (ed_op_done) done_seen = done_seen + 1;
    reg release_in = 0;
    ot_hbm_accel_sm_v #(.ENABLE(ENABLE), .SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .RMAX(RMAX), .LEV(LEV), .XD(XDEPTH), .MAX_OUT(512)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g), .op_gs(op_gs),
        .op_fmt(op_fmt), .busy(busy), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base),
        .d_lines(d_lines), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp),
        .xw_data(xw_data), .rv(sm_rv), .rrow(sm_rrow), .rdata(sm_rdata), .fault(sm_fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [1087:0] lines [0:65535];
    reg [FRAGW+2047:0] xwords [0:XDEPTH-1];
    reg [31:0] cfg [0:7];
    // behavioural HBM share: pending reads
    reg [31:0] p_addr [0:511]; reg [9:0] p_tag [0:511]; integer p_rdy [0:511]; reg p_use [0:511];
    integer t_done, nlines, i, ii, kk, fo, seed, pick, cyc, t0, t_first, t_last, nres, t_lastline, consumed;
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
        // reserve the op's rows at the SU ingress before the SM may start (credit reservation)
        @(negedge clk); d_valid = 0; ed_op_v = 1;
        while (!ed_op_ack) @(negedge clk);
        ed_op_v = 0; start = 1;
        t0 = $time;
        @(negedge clk); start = 0;
    end
    always @(posedge clk) if (rv) begin
        if (nres == 0) t_first = $time;
        t_last = $time;
        $fwrite(fo, "%0d %h\n", rrow, rdata);
        nres = nres + 1;
    end
    always @(posedge clk) release_in <= arrive;
    initial begin
        #5;
        wait (rst_n); wait (start); wait (!start); wait (busy); wait (!busy);
        repeat (4) @(posedge clk);
        for (kk = 0; kk < 20000 && (nres < op_rows || done_seen != 1); kk = kk + 1) @(posedge clk);
        t_done = $time - t0;
        // the successor's barrier outputs reach the pins PIO cycles later: wait (bounded) for `released`
        for (kk = 0; kk < 64 && !released; kk = kk + 1) @(posedge clk);
        $fwrite(fo, "# edge_stations %0d edge_done %0d edge_free %0d\n", NST, done_seen, ed_free);
        $fwrite(fo, "# cycles_start_to_done %0d first_result %0d last_result %0d lines %0d consumed %0d fault %0d released %0d drain_last_line_to_last_result %0d released_after_done %0d\n",
                t_done, t_first - t0, t_last - t0, nlines, consumed, fault, released, t_last - t_lastline, $time - t0 - t_done + 4);
        $fclose(fo);
        $finish;
    end
    initial begin #20000000; $fwrite(fo, "# TIMEOUT\n"); $fclose(fo); $finish; end
endmodule
