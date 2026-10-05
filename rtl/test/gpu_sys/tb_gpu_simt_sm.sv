`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Unit bench of ot_gpu_simt_sm: one SM against a behavioural memory that
// answers its LSU and bulk-copy MREQ ports out of order after random delays,
// a self-releasing barrier and a single-rank collective (identity).  The
// program, launch parameters and memory image come from files written by
// tools/gpu_sys/run_simt_sm.py, which runs the same program on the Python
// reference (tools/gpu_sys/machine.py) and diffs the dumped register file and
// memory.  Plusargs: +DIR=<case dir>  +SEED=<n>  +MAXLAT=<cycles>
// ---------------------------------------------------------------------------
module tb_gpu_simt_sm;
    localparam integer NL = 128, NV = 256, MEMB = 131072;
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg [7:0] mem [0:MEMB-1];
    reg [63:0] prog [0:8191];
    reg [31:0] cfg [0:7];
    string dir;
    integer seed, maxlat, nprog, i, j, fd, cyc, ii, jj;

    reg im_we; reg [12:0] im_addr; reg [63:0] im_data;
    reg launch_v;
    wire sm_done, sm_fault, res_v, busy, bar_arrive;
    wire [31:0] res_data;
    wire lreq_v, lreq_we, lrsp_rdy, treq_v, trsp_rdy;
    wire [31:0] lreq_addr, lreq_wstrb, treq_addr;
    wire [255:0] lreq_wdata;
    wire [15:0] lreq_tag, treq_tag;
    reg lreq_rdy, treq_rdy;
    reg lrsp_v, lrsp_we, trsp_v;
    reg [15:0] lrsp_tag, trsp_tag;
    reg [255:0] lrsp_data, trsp_data;
    wire coll_req_v, coll_mode, coll_rsp_rdy;
    wire [7:0] coll_count;
    wire [NL*32-1:0] coll_data;
    reg coll_req_rdy, coll_rsp_v;
    reg [NL*32-1:0] coll_rsp_data;
    wire [31:0] st_instr, st_cycles, st_stall_mem, st_tc_rows;

    ot_gpu_simt_sm #(.ENABLE(1), .NL(NL), .NV(NV), .HAS_DIV(1), .HAS_BD(1)) dut (
        .clk(clk), .rst_n(rst_n), .sm_id(8'd0), .die_id(8'd0),
        .im_we(im_we), .im_addr(im_addr), .im_data(im_data),
        .launch_v(launch_v), .launch_pc(32'd0), .launch_token(cfg[0][15:0]), .launch_pos(cfg[1][15:0]),
        .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .busy(busy),
        .bar_arrive(bar_arrive), .bar_release(bar_arrive),
        .lreq_v(lreq_v), .lreq_rdy(lreq_rdy), .lreq_we(lreq_we), .lreq_addr(lreq_addr), .lreq_wdata(lreq_wdata),
        .lreq_wstrb(lreq_wstrb), .lreq_tag(lreq_tag), .lrsp_v(lrsp_v), .lrsp_rdy(lrsp_rdy), .lrsp_tag(lrsp_tag),
        .lrsp_we(lrsp_we), .lrsp_data(lrsp_data),
        .treq_v(treq_v), .treq_rdy(treq_rdy), .treq_addr(treq_addr), .treq_tag(treq_tag), .trsp_v(trsp_v),
        .trsp_rdy(trsp_rdy), .trsp_tag(trsp_tag), .trsp_data(trsp_data),
        .coll_req_v(coll_req_v), .coll_req_rdy(coll_req_rdy), .coll_mode(coll_mode), .coll_count(coll_count),
        .coll_data(coll_data), .coll_rsp_v(coll_rsp_v), .coll_rsp_rdy(coll_rsp_rdy), .coll_rsp_data(coll_rsp_data),
        .st_instr(st_instr), .st_cycles(st_cycles), .st_stall_mem(st_stall_mem), .st_tc_rows(st_tc_rows));

    // ---------------- behavioural memory: per-port pending queues, random-latency out-of-order responses
    localparam integer QN = 64;
    reg        lq_v [0:QN-1]; reg lq_we [0:QN-1]; reg [31:0] lq_a [0:QN-1]; reg [15:0] lq_t [0:QN-1];
    integer    lq_due [0:QN-1];
    reg        tq_v [0:QN-1]; reg [31:0] tq_a [0:QN-1]; reg [15:0] tq_t [0:QN-1]; integer tq_due [0:QN-1];
    function automatic [255:0] rd_sector(input [31:0] a);
        integer k;
        for (k = 0; k < 32; k = k + 1) rd_sector[k*8 +: 8] = mem[(a & 32'hFFFFFFE0) + k];
    endfunction
    integer free_l, free_t, pick;
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < QN; i = i + 1) begin lq_v[i] <= 0; tq_v[i] <= 0; end
            lrsp_v <= 0; trsp_v <= 0; lreq_rdy <= 0; treq_rdy <= 0; coll_req_rdy <= 0; coll_rsp_v <= 0;
        end else begin
            // accept
            free_l = -1; free_t = -1;
            for (i = 0; i < QN; i = i + 1) begin
                if (!lq_v[i] && free_l < 0) free_l = i;
                if (!tq_v[i] && free_t < 0) free_t = i;
            end
            if (lreq_v && lreq_rdy) begin
                if (lreq_addr + 32 > MEMB) begin $display("FAIL lsu address %h out of range", lreq_addr); $finish; end
                lq_v[free_l] <= 1; lq_we[free_l] <= lreq_we; lq_a[free_l] <= lreq_addr; lq_t[free_l] <= lreq_tag;
                lq_due[free_l] <= cyc + 2 + ($urandom % maxlat);
                if (lreq_we) for (j = 0; j < 32; j = j + 1) if (lreq_wstrb[j]) mem[lreq_addr + j] <= lreq_wdata[j*8 +: 8];
            end
            if (treq_v && treq_rdy) begin
                tq_v[free_t] <= 1; tq_a[free_t] <= treq_addr; tq_t[free_t] <= treq_tag;
                tq_due[free_t] <= cyc + 2 + ($urandom % maxlat);
            end
            lreq_rdy <= ($urandom % 4) != 0;
            treq_rdy <= ($urandom % 4) != 0;
            // respond (one per port per cycle, a random due entry)
            if (lrsp_v && lrsp_rdy) lrsp_v <= 0;
            if (!lrsp_v || lrsp_rdy) begin
                pick = -1;
                for (i = 0; i < QN; i = i + 1) if (lq_v[i] && lq_due[i] <= cyc && (pick < 0 || ($urandom % 2))) pick = i;
                if (pick >= 0 && !(lreq_v && lreq_rdy && free_l == pick)) begin
                    lrsp_v <= 1; lrsp_tag <= lq_t[pick]; lrsp_we <= lq_we[pick]; lrsp_data <= rd_sector(lq_a[pick]);
                    lq_v[pick] <= 0;
                end
            end
            trsp_v <= 0;
            pick = -1;
            for (i = 0; i < QN; i = i + 1) if (tq_v[i] && tq_due[i] <= cyc && (pick < 0 || ($urandom % 2))) pick = i;
            if (pick >= 0 && trsp_rdy && !(treq_v && treq_rdy && free_t == pick)) begin
                trsp_v <= 1; trsp_tag <= tq_t[pick]; trsp_data <= rd_sector(tq_a[pick]); tq_v[pick] <= 0;
            end
            // single-rank collective: the result is the input's first `count` lanes
            coll_req_rdy <= coll_req_v && !coll_req_rdy && !coll_rsp_v;
            if (coll_req_v && coll_req_rdy) begin
                for (j = 0; j < NL; j = j + 1) coll_rsp_data[j*32 +: 32] <= (j < coll_count) ? coll_data[j*32 +: 32] : 32'd0;
                coll_rsp_v <= 1;
            end else if (coll_rsp_v && coll_rsp_rdy) coll_rsp_v <= 0;
        end
    end

    reg [31:0] result_q; reg result_seen;
    always @(posedge clk) if (res_v) begin result_q <= res_data; result_seen <= 1; end

    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("MAXLAT=%d", maxlat)) maxlat = 40;
        void'($urandom(seed));
        for (ii = 0; ii < MEMB; ii = ii + 1) mem[ii] = 0;
        $readmemh({dir, "/mem.hex"}, mem);
        $readmemh({dir, "/prog.hex"}, prog);
        $readmemh({dir, "/cfg.hex"}, cfg);
        nprog = cfg[2];
        im_we = 0; launch_v = 0; cyc = 0; result_seen = 0;
        repeat (5) @(posedge clk);
        rst_n = 1;
        for (ii = 0; ii < nprog; ii = ii + 1) begin
            @(negedge clk); im_we = 1; im_addr = ii; im_data = prog[ii];
        end
        @(negedge clk); im_we = 0; launch_v = 1;
        @(negedge clk); launch_v = 0;
        while (!sm_done && cyc < cfg[3]) @(posedge clk);
        if (!sm_done) $display("FAIL timeout after %0d cycles", cyc);
        repeat (2) @(posedge clk);
        fd = $fopen({dir, "/rtl_out.txt"}, "w");
        $fdisplay(fd, "# fault %0d result %0d %0d instr %0d cycles %0d stall_mem %0d tc_rows %0d", sm_fault, result_seen,
                  result_q, st_instr, st_cycles, st_stall_mem, st_tc_rows);
        for (ii = 0; ii < NV; ii = ii + 1) $fdisplay(fd, "v %0d %h", ii, dut.g_on.vr[ii]);
        for (ii = 0; ii < 16; ii = ii + 1) $fdisplay(fd, "u %0d %h", ii, dut.g_on.ur[ii]);
        for (ii = 0; ii < MEMB; ii = ii + 32) begin
            $fwrite(fd, "m %0d ", ii);
            for (jj = 31; jj >= 0; jj = jj - 1) $fwrite(fd, "%h", mem[ii + jj]);
            $fwrite(fd, "\n");
        end
        for (ii = 0; ii < 8192; ii = ii + 1) $fdisplay(fd, "s %0d %h", ii, dut.g_on.smem[ii]);
        $fclose(fd);
        $display("TB_GPU_SIMT_SM DONE fault=%0d cycles=%0d", sm_fault, cyc);
        $finish;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc % 20000 == 0 && cyc > 0)
            $display("cyc %0d pc %0d bst %0d running %0d fault %0d instr %0d pend %0d tc_active %0d", cyc, dut.g_on.pc,
                     dut.g_on.bst, dut.g_on.running, sm_fault, st_instr, $countones(dut.g_on.pend), dut.g_on.tc_active);
    end
endmodule
