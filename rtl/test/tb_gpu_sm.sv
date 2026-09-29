`timescale 1ns/1ps
// Exactness bench of the GPU-organised SM (rtl/gpu/ot_gpu_sm.sv): one op per run, weights streamed
// from a line file in the SM's lockstep order (optionally with random stream gaps), x store and row
// scales preloaded, every result row written to +OUT.  tools/rtl_gpu_sm_exact.py makes the vectors
// from the golden and compares.
module tb_gpu_sm;
    parameter integer SUB = 4, LS = 32, NC = 2, XDEPTH = 96, RMAX = 256, LEV = 5, INT8 = 1;
    localparam integer L = SUB * LS;
    localparam integer WW = L * (INT8 ? 8 : 16);
    localparam integer RW = $clog2(RMAX);
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_scale;
    wire busy;
    reg w_valid;
    wire w_ready;
    reg [WW-1:0] lines [0:65535];
    reg [WW-1:0] w_data;
    reg xw_en = 0; reg [$clog2(XDEPTH)-1:0] xw_addr; reg [L*NC*16-1:0] xw_data;
    reg sw_en = 0; reg [RW-1:0] sw_addr; reg [15:0] sw_data;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_gpu_sm #(.SUB(SUB), .LS(LS), .NC(NC), .XDEPTH(XDEPTH), .RMAX(RMAX), .LEV(LEV), .INT8(INT8)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .op_rows(op_rows), .op_c(op_c), .op_g(op_g),
        .op_scale(op_scale), .busy(busy), .w_valid(w_valid), .w_ready(w_ready), .w_data(w_data),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_data(xw_data), .sw_en(sw_en), .sw_addr(sw_addr),
        .sw_data(sw_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [L*NC*16-1:0] xwords [0:XDEPTH-1];
    reg [15:0] scales [0:RMAX-1];
    reg [31:0] cfg [0:7];
    integer nlines, i, fo, gap_pct, seed, pos, t0, t_first, t_last, nres, stall_cycles, t_lastline;
    reg [1023:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("GAP=%d", gap_pct)) gap_pct = 0;
        seed = 7;
        $readmemh({dir, "/cfg.hex"}, cfg);
        op_rows = cfg[0]; op_c = cfg[1]; op_g = cfg[2]; op_scale = cfg[3]; nlines = cfg[4];
        $readmemh({dir, "/lines.hex"}, lines);
        $readmemh({dir, "/x.hex"}, xwords);
        $readmemh({dir, "/scale.hex"}, scales);
        fo = $fopen({dir, "/out.txt"}, "w");
        w_valid = 0; pos = 0; nres = 0; stall_cycles = 0;
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        for (i = 0; i < XDEPTH; i = i + 1) begin
            @(negedge clk); xw_en = 1; xw_addr = i; xw_data = xwords[i];
        end
        @(negedge clk); xw_en = 0;
        for (i = 0; i < op_rows; i = i + 1) begin
            @(negedge clk); sw_en = 1; sw_addr = i; sw_data = scales[i];
        end
        @(negedge clk); sw_en = 0; start = 1;
        t0 = $time;
        @(negedge clk); start = 0;
    end
    // weight stream with optional random gaps
    always @(negedge clk) begin
        if (rst_n) begin
            if (pos < nlines && ($urandom(seed) % 100) >= gap_pct) begin
                w_valid <= 1; w_data <= lines[pos];
            end else begin
                w_valid <= 0;
            end
        end
    end
    always @(posedge clk) begin
        if (w_valid && w_ready) begin pos <= pos + 1; t_lastline = $time; end
        if (w_ready && !w_valid) stall_cycles <= stall_cycles + 1;
    end
    always @(posedge clk) if (rv) begin
        if (nres == 0) t_first = $time;
        t_last = $time;
        $fwrite(fo, "%0d %h\n", rrow, rdata);
        nres = nres + 1;
    end
    // barrier stand-in: release as soon as this SM arrives (single-SM bench)
    always @(posedge clk) release_in <= arrive;
    initial begin
        #5;
        wait (rst_n);
        wait (start);
        wait (!start);
        wait (busy);
        wait (!busy);
        repeat (4) @(posedge clk);
        $fwrite(fo, "# cycles_start_to_done %0d first_result %0d last_result %0d lines %0d consumed %0d fault %0d stall_waits %0d released %0d drain_last_line_to_last_result %0d\n",
                ($time - t0), t_first - t0, t_last - t0, nlines, pos, fault, stall_cycles, released, t_last - t_lastline);
        $fclose(fo);
        $finish;
    end
    initial begin
        #20000000;
        $display("TIMEOUT");
        $fwrite(fo, "# TIMEOUT\n");
        $fclose(fo);
        $finish;
    end
endmodule
