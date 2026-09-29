`timescale 1ns/1ps
// Bench of the Qwen SM macro top (rtl/gpu/ot_gpu_sm_q.sv) with its physical parts: the weight lines come
// from a behavioural HBM share through the SM's own bulk-copy engine (reads return after LAT + jitter, in
// any order, one line a cycle at most), the x fragments are written into the x-store macros, the row
// scales into the scale macro.  Same vectors and result format as tb_gpu_sm (tools/rtl_gpu_sm_exact.py).
module tb_gpu_sm_q;
    parameter integer SUB = 4, LS = 32, NC = 2, XDEPTH = 96, RMAX = 256, LEV = 5, NXM = 16, LAT = 60, JIT = 40;
    localparam integer L = SUB * LS;
    localparam integer RW = $clog2(RMAX);
    localparam integer FRAGW = L * NC * 16;
    localparam integer SUBS = FRAGW / (NXM * 256);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_scale;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v = 0; reg [9:0] rsp_tag; reg [L*8-1:0] rsp_data;
    reg xw_en = 0; reg [9:0] xw_addr; reg [7:0] xw_grp; reg [8*256-1:0] xw_data; integer gg;
    reg sw_en = 0; reg [RW-1:0] sw_addr; reg [15:0] sw_data;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_gpu_sm_q #(.SUB(SUB), .LS(LS), .NC(NC), .RMAX(RMAX), .LEV(LEV), .NXM(NXM), .MAX_OUT(512)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g),
        .op_scale(op_scale), .busy(busy), .d_valid(d_valid), .d_ready(d_ready), .d_base(d_base),
        .d_lines(d_lines), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp),
        .xw_data(xw_data), .sw_en(sw_en), .sw_addr(sw_addr), .sw_data(sw_data), .rv(rv), .rrow(rrow),
        .rdata(rdata), .fault(fault), .arrive(arrive), .release_in(release_in), .released(released));
    reg [L*8-1:0] lines [0:65535];
    reg [FRAGW+2047:0] xwords [0:XDEPTH-1];   // padded so the last beat's slice stays in range
    reg [15:0] scales [0:RMAX-1];
    reg [31:0] cfg [0:7];
    // behavioural HBM share: pending reads
    reg [31:0] p_addr [0:511]; reg [9:0] p_tag [0:511]; integer p_rdy [0:511]; reg p_use [0:511];
    integer nlines, i, ii, kk, fo, seed, pick, cyc, t0, t_first, t_last, nres, t_lastline, consumed;
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
    always @(posedge clk) if (dut.w_valid && dut.w_ready) begin consumed = consumed + 1; t_lastline = $time; end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        seed = 7; cyc = 0; nres = 0; consumed = 0;
        $readmemh({dir, "/cfg.hex"}, cfg);
        op_rows = cfg[0]; op_c = cfg[1]; op_g = cfg[2]; op_scale = cfg[3]; nlines = cfg[4];
        $readmemh({dir, "/lines.hex"}, lines);
        $readmemh({dir, "/x.hex"}, xwords);
        $readmemh({dir, "/scale.hex"}, scales);
        fo = $fopen({dir, "/out.txt"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        for (ii = 0; ii < XDEPTH; ii = ii + 1)
            for (kk = 0; kk < SUBS; kk = kk + 1)
                for (gg = 0; gg < (NXM + 7) / 8; gg = gg + 1) begin
                    @(negedge clk); xw_en = 1; xw_addr = ii * SUBS + kk; xw_grp = gg;
                    xw_data = xwords[ii][(kk * NXM + gg * 8) * 256 +: 8 * 256];
                end
        @(negedge clk); xw_en = 0;
        for (ii = 0; ii < op_rows; ii = ii + 1) begin
            @(negedge clk); sw_en = 1; sw_addr = ii; sw_data = scales[ii];
        end
        @(negedge clk); sw_en = 0; d_valid = 1; d_lines = nlines;
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
    always @(posedge clk) release_in <= arrive;
    initial begin
        #5;
        wait (rst_n); wait (start); wait (!start); wait (busy); wait (!busy);
        repeat (4) @(posedge clk);
        $fwrite(fo, "# cycles_start_to_done %0d first_result %0d last_result %0d lines %0d consumed %0d fault %0d released %0d drain_last_line_to_last_result %0d\n",
                ($time - t0), t_first - t0, t_last - t0, nlines, consumed, fault, released, t_last - t_lastline);
        $fclose(fo);
        $finish;
    end
    initial begin #20000000; $fwrite(fo, "# TIMEOUT\n"); $fclose(fo); $finish; end
endmodule
