`timescale 1ns/1ps
// Bench of dsfd_sp_hc (stream s81-suhc-1011): the S81 HC die master driven at its controller-side adapter pins
// exactly as dsfd_sp_ctrl's stage sequencer drives an engine port (one-cycle c_cmd_v pulses, QD 8 credits returned
// only by c_done_v, no ready), a behavioural VM (fixed read latency LVM on every read slot, writes in issue order) and
// a collective y source on the direct y bus (valid / ready).  Files (tools/s81_suhc/hc_gate.py prep): vm.mem (initial
// VM image), prog.mem (84-bit commands in program order), y.mem (y beats in POST order), expa.mem / expd.mem
// (expected VM rows), n.mem (counts).  Prints per job its engine start / done (slab cycles) and
// HCG jobs= done= err= rows= fault= code= cyc= bad_tag=  then HCG PASS / HCG FAIL.
module tb_s81_hc_master;
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, LVM = 10, MUT = 0, AMUT = 0, HIER = 0, NCOL = 3, GS = 8, HALF = 0, CSPLIT = 0, TAIL_SPLIT = 0, HEAD_ROWS = 10, CNL_PIN = 0, CHAIN_STEP = 4, LANE_SPECIALIZE = 0, PIPE = 0, PIPE_PD = 40, NTREE = 0, NT_K = 67, NT_DBG = 0, RETCOL = 0;
    parameter integer MAXJ = 64, MAXE = 4096, MAXY = 2048, TMAX = 400000;
    reg cck = 0, sk = 0, crs = 0, srs = 0;
    always #0.4165 cck = ~cck;              // controller 1.2 GHz
    always #0.4255 sk = ~sk;                // slab clock (stream domain, independent source: exercises the CDC)
    reg          c_cmd_v = 0;
    reg  [83:0]  c_cmd_d = 0;
    wire         c_done_v;
    wire [7:0]   c_done_tag;
    reg          inp = 1;                   // operands of every program job are in the VM image before reset release
    reg          y_v = 0;
    wire         y_rdy;
    reg  [NG*32-1:0] y_d = 0;
    wire [S_RD-1:0] rq_v;
    wire [S_RD*14-1:0] rq_row;
    reg  [S_RD-1:0] rs_v = 0;
    reg  [S_RD*512-1:0] rs_d = 0;
    wire [S_WR-1:0] wq_v;
    wire [S_WR*14-1:0] wq_row;
    wire [S_WR*16-1:0] wq_mask;
    wire [S_WR*512-1:0] wq_d;
    wire flt, online;
    wire [3:0] fcode;
    dsfd_sp_hc #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .LVM(LVM), .MUT(MUT), .AMUT(AMUT), .HIER(HIER), .NCOL(NCOL), .GS(GS), .HALF(HALF), .CSPLIT(CSPLIT), .TAIL_SPLIT(TAIL_SPLIT),.HEAD_ROWS(HEAD_ROWS),.CNL_PIN(CNL_PIN),.CHAIN_STEP(CHAIN_STEP),.LANE_SPECIALIZE(LANE_SPECIALIZE),.PIPE(PIPE),.PIPE_PD(PIPE_PD),.NTREE(NTREE),.NT_K(NT_K),.RETCOL(RETCOL)) dut (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .y_v(y_v), .y_rdy(y_rdy), .y_d(y_d), .rq_v(rq_v), .rq_row(rq_row),
        .rs_v(rs_v), .rs_d(rs_d), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt),
        .online(online), .fcode(fcode));

    reg [511:0]     vm [0:16383];
    reg [83:0]      prog [0:MAXJ-1];
    reg [NG*32-1:0] ym [0:MAXY-1];
    reg [13:0]      ea [0:MAXE-1];
    reg [511:0]     ed [0:MAXE-1];
    reg [31:0]      nm [0:2];
    integer fd;
    integer nj, ne, ny, i, s, errs, credits, ip, ndone, yb, bad_tag, scyc, t;
    reg [MAXJ-1:0] pend;
    integer jstart [0:MAXJ-1];
    integer jdone  [0:MAXJ-1];
    initial begin
        for (i = 0; i < 16384; i = i + 1) vm[i] = 512'd0;
        $readmemh("vm.mem", vm);
        $readmemh("prog.mem", prog);
        $readmemh("y.mem", ym);
        $readmemh("expa.mem", ea);
        $readmemh("expd.mem", ed);
        $readmemh("n.mem", nm);
        nj = nm[0]; ne = nm[1]; ny = nm[2];
        for (i = 0; i < MAXJ; i = i + 1) begin jstart[i] = -1; jdone[i] = -1; end
        credits = 8; ip = 0; ndone = 0; yb = 0; bad_tag = 0; pend = 0; scyc = 0;
        repeat (4) @(posedge cck);
        crs = 1; srs = 1;
    end

    // ---- controller side: decoupled issue under QD 8 credits, completions return credits
    always @(posedge cck) if (crs) begin
        c_cmd_v <= 1'b0;
        if (c_done_v) begin
            if (!pend[c_done_tag[6:0]] || prog[c_done_tag[6:0]][83] != c_done_tag[7]) bad_tag = bad_tag + 1;
            else begin pend[c_done_tag[6:0]] = 1'b0; jdone[c_done_tag[6:0]] = scyc; end
            ndone = ndone + 1;
            credits = credits + 1;
        end
        if (online && ip < nj && credits > 0) begin
            c_cmd_v <= 1'b1; c_cmd_d <= prog[ip]; pend[ip] = 1'b1; credits = credits - 1; ip = ip + 1;
        end
    end

    // ---- slab side: VM, y source, job start stamps
    reg [S_RD-1:0]     dl_v [0:63];
    reg [S_RD*14-1:0]  dl_a [0:63];
    always @(posedge sk) if (srs) begin
        scyc = scyc + 1;
        if (dut.e_v && dut.e_r) jstart[dut.e_d[6:0]] = scyc;
        // writes take effect at issue (before reads of the same cycle: the core never mixes them in one job)
        for (s = 0; s < S_WR; s = s + 1)
            if (wq_v[s]) vm[wq_row[14 * s +: 14]] = wq_d[512 * s +: 512];
        // reads: fixed latency LVM
        for (i = 63; i > 0; i = i - 1) begin dl_v[i] = dl_v[i - 1]; dl_a[i] = dl_a[i - 1]; end
        dl_v[0] = rq_v; dl_a[0] = rq_row;
        rs_v <= dl_v[LVM - 1];
        for (s = 0; s < S_RD; s = s + 1) rs_d[512 * s +: 512] <= vm[dl_a[LVM - 1][14 * s +: 14]];
        // y: offered back to back in POST order
        if (y_v && y_rdy) yb = yb + 1;
        y_v <= (yb < ny);
        y_d <= ym[yb];
    end
    initial for (i = 0; i < 64; i = i + 1) begin dl_v[i] = 0; dl_a[i] = 0; end

    initial begin
        t = 0;
        wait (srs);
        while (t < TMAX && !(ndone >= nj && nj > 0) && !flt) begin @(posedge sk); t = t + 1; end
        repeat (200) @(posedge sk);
        errs = 0;
        fd = $fopen("got.mem", "w");
        for (i = 0; i < ne; i = i + 1) $fdisplay(fd, "%h", vm[ea[i]]);
        $fclose(fd);
        for (i = 0; i < ne; i = i + 1)
            if (vm[ea[i]] !== ed[i]) begin
                if (errs < 5) $display("mismatch row %0d got %h want %h", ea[i], vm[ea[i]][63:0], ed[i][63:0]);
                errs = errs + 1;
            end
        for (i = 0; i < nj; i = i + 1)
            $display("HCJ op=%0d kind=%0d start=%0d done=%0d", i, prog[i][30:27], jstart[i], jdone[i]);
        $display("HCG jobs=%0d done=%0d err=%0d rows=%0d fault=%0d code=%0d cyc=%0d bad_tag=%0d", nj, ndone, errs, ne,
                 flt, fcode, scyc, bad_tag);
        if (errs == 0 && ndone == nj && !flt && bad_tag == 0 && pend == 0) $display("HCG PASS"); else $display("HCG FAIL");
        $finish;
    end
// NORM tree variant: the norm's sum / rsqrt events are the bottom region's (ot_s81_hc_cnbot); NT_DBG prints every
    // lane leaf and vector beat at the collectors (the NT_K calibration of tools/s81_suhc/hc_gate.py --ntree).
    wire nt_ssv, nt_rrv;
    generate if (HIER && NTREE && TAIL_SPLIT == 2) begin : g_ntp2
        assign nt_ssv = dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.ss_v;
        assign nt_rrv = dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.u_rsq.rr_v;
        if (NT_DBG) begin : g_dbg
            always @(posedge sk) if (srs) begin : d
                integer q;
                if (dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[0].u_a.u_c.nv_v)
                    $display("NTDBG c=0 nv=%0d cyc=%0d", dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[0].u_a.u_c.nvq, scyc);
                for (q = 0; q < 2; q = q + 1) begin
                    if (dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[0].u_a.u_c.dlq[73 * q]) $display("NTDBG c=0 leaf q=%0d cyc=%0d", q, scyc);
                    if (dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[1].u_a.u_c.dlq[73 * q]) $display("NTDBG c=1 leaf q=%0d cyc=%0d", q, scyc);
                    if (dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[2].u_a.u_c.dlq[73 * q]) $display("NTDBG c=2 leaf q=%0d cyc=%0d", q, scyc);
                end
                if (dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[0].u_a.u_c.v_q) $display("NTDBG fire cyc=%0d", scyc);
                if (dut.g_hier.g_split.g_composed.u_tail.g_nt.u_bot.g_c[0].u_a.u_c.e_miss) $display("NTDBG MISS cyc=%0d", scyc);
            end
        end
    end else if (HIER && NTREE) begin : g_ntp0
        assign nt_ssv = dut.g_hier.g_unsplit.g_ntb.u_bot.ss_v;
        assign nt_rrv = dut.g_hier.g_unsplit.g_ntb.u_bot.u_rsq.rr_v;
    end else begin : g_ntpn
        assign nt_ssv = 1'b0; assign nt_rrv = 1'b0;
    end endgenerate
// Diagnostic event stamps only; no RTL datapath or timing parameter changes.
    generate if (HIER) begin : g_norm_trace
        integer trace_tag;
        always @(posedge sk) if (srs) begin
            if (dut.g_hier.u_cb.u_seq.take && dut.g_hier.u_cb.u_seq.c_arg[22:20] == 4) begin
                trace_tag = dut.g_hier.u_cb.u_seq.e_d[6:0];
                $display("NTRACE op=%0d event=accept cyc=%0d", trace_tag, scyc);
            end
            if (dut.g_hier.u_cb.u_seq.run && dut.g_hier.u_cb.u_seq.kind == 4) begin
                if (!NTREE && dut.g_hier.u_cb.u_seq.t_ssv) $display("NTRACE op=%0d event=sum_return cyc=%0d", trace_tag, scyc);
                if (!NTREE && dut.g_hier.u_cb.u_seq.rr_v) $display("NTRACE op=%0d event=rsqrt_ready cyc=%0d", trace_tag, scyc);
                if (NTREE && nt_ssv) $display("NTRACE op=%0d event=sum_return cyc=%0d", trace_tag, scyc);
                if (NTREE && nt_rrv) $display("NTRACE op=%0d event=rsqrt_ready cyc=%0d", trace_tag, scyc);
                if (dut.g_hier.u_cb.u_rx.rv[0]) $display("NTRACE op=%0d event=return_row cyc=%0d", trace_tag, scyc);
                if (dut.g_hier.u_cb.u_seq.wd_q) $display("NTRACE op=%0d event=writer_done cyc=%0d", trace_tag, scyc);
            end
        end
    end endgenerate
endmodule
