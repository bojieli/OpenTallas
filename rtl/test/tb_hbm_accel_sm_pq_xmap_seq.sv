`timescale 1ns/1ps
// Op-SEQUENCE bench of the pipelined-issue DS HBM SM element ot_hbm_accel_sm_pq (rtl/hbm_accel/sm/), derived from
// tb_hbm_accel_sm_v_seq (same behavioural HBM share, same warm descriptor stream, same x-write port protocol).
// What changes is the op protocol the pipelined element allows:
//   * `start` is a valid/ready channel: an op is posted as soon as its x is loaded, while earlier ops still issue or
//     drain (the element launches it when its issue is free and the retire-order hazard is clear);
//   * x loads use an x-store RING: an op that loads x gets the next free range (op_xb = base, addresses
//     (base + a) mod XD); its beats start once that range is disjoint from the range of every op not yet completed
//     (completion = its arrive toggle, which is after its last x read), so a load overlaps earlier ops without WAR;
//     an op that reuses the resident x takes the resident op's base and loads nothing;
//   * DEPENDENCY: an op flagged dep (the first op after a collective / local op in the program: its input is produced
//     from earlier results) waits until every earlier op has completed before its x load starts (serial, as the
//     sm_v bench does for every op).  With every op flagged dep this bench is the serial protocol.
// Results are attributed to ops in order (the element guarantees op order).  Every op's x differs, unused ring
// addresses keep stale data, so a stale or overwritten x read would mismatch the golden.
// Files (DIR): seq.hex (10 words per op: rows, c, groups, fmt, lines, gs, xload, xaddrs, dep, xbase), lines.hex,
// x.hex; +NOPS.  Output out.txt: "<op> <row> <data>" result lines and one "# op ..." timing line per op.
module tb_hbm_accel_sm_pq_xmap_seq;
    parameter integer SUB = 4, LBS = 2, LSB = 16, NC = 1, XDEPTH = 128, RMAX = 256, LEV = 4,
                      LAT = 60, JIT = 40, MAXOPS = 64, XB = 0, HAZ = 1, G1ASB = 0, XMAP = 0;
    localparam integer RW = $clog2(RMAX);
    localparam integer XW = $clog2(XDEPTH);
    localparam integer FRAGW = NC * (SUB * LBS * 266 + SUB * LSB * 16);
    localparam integer NBEAT = (FRAGW + 2047) / 2048;
    localparam integer XBEATS = (XB == 0 || XB > NBEAT) ? NBEAT : XB;
    localparam integer NW = 10;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0; wire start_ready;
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_gs; reg [1:0] op_fmt; reg [XW-1:0] op_xb;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines = 0;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
    reg xw_en = 0; reg [XW-1:0] xw_addr; reg [6:0] xw_grp; reg [8*256-1:0] xw_data;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    ot_hbm_accel_sm_pq #(.ENABLE(1), .PQ_ENABLE(1), .SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .RMAX(RMAX), .LEV(LEV), .XD(XDEPTH),
                         .MAX_OUT(512), .HAZ(HAZ), .G1ASB(G1ASB), .XMAP(XMAP)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .op_rows(op_rows), .op_c(op_c),
        .op_g(op_g), .op_gs(op_gs), .op_fmt(op_fmt), .op_xb(op_xb), .busy(busy), .d_valid(d_valid),
        .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr),
        .req_tag(req_tag), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr),
        .xw_grp(xw_grp), .xw_data(xw_data), .rv(rv), .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive),
        .release_in(release_in), .released(released));
    reg [1087:0] lines [0:131071];
    reg [FRAGW+2047:0] xwords [0:MAXOPS*XDEPTH-1];
    reg [31:0] seq [0:MAXOPS*NW-1];
    integer base_of [0:MAXOPS-1];
    reg [31:0] p_addr [0:511]; reg [9:0] p_tag [0:511]; integer p_rdy [0:511]; reg p_use [0:511];
    integer i, ii, gg, op, nops, fo, seed, pick, cyc, xptr, nd, acc, j, ok, ndone;
    integer t_load0 [0:MAXOPS-1]; integer t_post [0:MAXOPS-1]; integer t_done [0:MAXOPS-1];
    integer t_first [0:MAXOPS-1]; integer t_last [0:MAXOPS-1]; integer nres [0:MAXOPS-1];
    integer t_lastline [0:MAXOPS-1]; integer t_firstline [0:MAXOPS-1]; integer consumed [0:MAXOPS-1];
    integer t_dpost [0:MAXOPS-1]; integer t_ready [0:MAXOPS-1];
    integer cur, cons_total, line_op;
    integer active, negative_fp4, group_count, group_index;
    integer beat_groups [0:12];
    integer xload_beats [0:MAXOPS-1];
    integer serial_force;
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
    wire take = dut.g_pq.w_valid && dut.g_pq.w_ready;
    always @(posedge clk) if (take) begin
        while (line_op < nops - 1 && cons_total >= base_of[line_op + 1]) line_op = line_op + 1;
        if (consumed[line_op] == 0) t_firstline[line_op] = cyc;
        consumed[line_op] = consumed[line_op] + 1; t_lastline[line_op] = cyc; cons_total = cons_total + 1;
    end
    initial begin
        nd = 0;
        wait (rst_n);
        @(negedge clk);
        while (nd < nops) begin
            d_valid = 1; d_base = base_of[nd]; d_lines = seq[nd * NW + 4];
            @(posedge clk);
            if (d_ready) begin t_dpost[nd] = cyc; nd = nd + 1; end
            @(negedge clk);
            d_valid = 0;
        end
    end
    // results in op order
    always @(posedge clk) if (rv) begin
        while (cur < nops - 1 && nres[cur] >= seq[cur * NW + 0]) cur = cur + 1;
        if (nres[cur] == 0) t_first[cur] = cyc;
        t_last[cur] = cyc;
        $fwrite(fo, "%0d %0d %h\n", cur, rrow, rdata);
        nres[cur] = nres[cur] + 1;
    end
    // completions: one arrive toggle per op, in order
    reg arrive_q = 0;
    always @(posedge clk) begin
        arrive_q <= arrive;
        if (rst_n && (arrive != arrive_q)) begin t_done[ndone] = cyc; ndone = ndone + 1; end
    end
    always @(posedge clk) release_in <= arrive;
    // ring overlap of op k's x range with op m's
    function automatic integer overlap(input integer k, input integer m);
        integer a, b, fa, fb, d1, d2;
        begin
            a = seq[k * NW + 9]; fa = seq[k * NW + 7]; b = seq[m * NW + 9]; fb = seq[m * NW + 7];
            d1 = (b - a + XDEPTH) % XDEPTH; d2 = (a - b + XDEPTH) % XDEPTH;
            overlap = (d1 < fa) || (d2 < fb);
        end
    endfunction
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NOPS=%d", nops)) nops = 1;
        seed = 7; cyc = 0; cur = 0; cons_total = 0; line_op = 0; ndone = 0;
        $readmemh({dir, "/seq.hex"}, seq);
        $readmemh({dir, "/lines.hex"}, lines);
        $readmemh({dir, "/x.hex"}, xwords);
        acc = 0;
        for (op = 0; op < nops; op = op + 1) begin
            base_of[op] = acc; acc = acc + seq[op * NW + 4];
            nres[op] = 0; consumed[op] = 0; t_first[op] = -1; t_last[op] = -1; t_lastline[op] = -1;
            t_firstline[op] = -1; t_done[op] = -1;
        end
        fo = $fopen({dir, "/out.txt"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        @(posedge clk);
        xptr = 0;
        active = NC;
        if (!$value$plusargs("ACTIVE=%d", active)) active = NC;
        negative_fp4 = $test$plusargs("FP4_AS_FP8");
        serial_force = $test$plusargs("SERIAL");
        if (active<1 || active>NC) $fatal(1, "Bad active columns");
        for (op = 0; op < nops; op = op + 1) begin
            @(negedge clk);
            if (seq[op * NW + 8] != 0 || serial_force) begin                         // dependent: every earlier op completed
                while (ndone < op) @(negedge clk);
            end else if (seq[op * NW + 6] != 0) begin                // independent load: ring range free
                ok = 0;
                while (!ok) begin
                    ok = 1;
                    for (j = ndone; j < op; j = j + 1) if (overlap(op, j)) ok = 0;
                    if (!ok) @(negedge clk);
                end
            end
            t_load0[op] = cyc;
            xload_beats[op] = 0;
            group_count = 0;
            for (gg=0; gg<NBEAT; gg=gg+1) begin
                if (!XMAP) ok = gg < (active*(SUB*LBS*266+SUB*LSB*16)+2047)/2048;
                else if (seq[op*NW+3]==0) ok = gg*2048 < active*1024;
                else begin
                    ok = gg*2048 < active*1064;
                    if (seq[op*NW+3]==2 && !negative_fp4)
                        ok = ok || (gg*2048 < NC*1064+active*1064 && (gg+1)*2048 > NC*1064);
                end
                if (ok) begin beat_groups[group_count]=gg; group_count=group_count+1; end
            end
            if (seq[op * NW + 6] != 0) begin
                for (ii = 0; ii < seq[op * NW + 7]; ii = ii + 1)
                    for (group_index = 0; group_index < group_count; group_index = group_index + 1) begin
                        gg=beat_groups[group_index];
                        xw_en = 1; xw_addr = (seq[op * NW + 9] + ii) % XDEPTH; xw_grp = gg;
                        xw_data = xwords[xptr + ii][gg * 2048 +: 2048];
                        xload_beats[op] = xload_beats[op]+1;
                        @(negedge clk);
                    end
                xw_en = 0;
                xptr = xptr + seq[op * NW + 7];
                @(negedge clk);                       // the documented >= 1 cycle between the last beat and start
            end
            t_ready[op] = cyc;
            op_rows = seq[op * NW + 0]; op_c = seq[op * NW + 1]; op_g = seq[op * NW + 2]; op_fmt = seq[op * NW + 3];
            op_gs = seq[op * NW + 5]; op_xb = seq[op * NW + 9];
            start = 1;
            while (!start_ready) @(negedge clk);     // sampled at the negedge: the credit decode is stable
            @(posedge clk);                           // the channel takes the op on this edge
            t_post[op] = cyc;
            @(negedge clk); start = 0;
        end
        while (ndone < nops) @(negedge clk);
        repeat (8) @(posedge clk);
        for (op = 0; op < nops; op = op + 1)
            $fwrite(fo, "# op %0d t_load0 %0d t_ready %0d t_post %0d t_firstline %0d t_lastline %0d t_first %0d t_last %0d t_done %0d results %0d lines %0d consumed %0d fault %0d xload_beats %0d\n",
                    op, t_load0[op], t_ready[op], t_post[op], t_firstline[op], t_lastline[op], t_first[op],
                    t_last[op], t_done[op], nres[op], seq[op * NW + 4], consumed[op], fault, xload_beats[op]);
        $fwrite(fo, "# total_cycles %0d\n", cyc);
        $fclose(fo);
        $finish;
    end
    // +TRACE: issue launches / last lines, every retired row, the first fault (stdout)
    reg trace = 0, fault_q = 0;
    integer tr_from = 0, tr_to = 0;
    initial begin
        trace = $test$plusargs("TRACE");
        if (!$value$plusargs("TRACE_FROM=%d", tr_from)) tr_from = 0;
        if (!$value$plusargs("TRACE_TO=%d", tr_to)) tr_to = 0;
    end
    always @(posedge clk) if (trace && rst_n) begin
        if (dut.g_pq.u_issue.launch)
            $display("T %0d LAUNCH rows %0d g %0d bf %0d xb %0d need_q %0d since %0d d_cur %0d d_head %0d on %0d",
                     cyc, dut.g_pq.u_issue.op_rows, dut.g_pq.u_issue.op_g, dut.g_pq.u_issue.op_bf, dut.g_pq.h_xb, dut.g_pq.u_issue.need_q,
                     dut.g_pq.u_issue.since, dut.g_pq.u_issue.d_cur, dut.g_pq.u_issue.d_head, dut.g_pq.u_issue.on);
        if (dut.g_pq.u_issue.op_end) $display("T %0d OPEND", cyc);
        if (dut.g_pq.u_issue.rdone) $display("T %0d RDONE row %0d oh %0d ocnt %0d", cyc, dut.g_pq.crow[RW-1:0], dut.g_pq.u_issue.oh,
                                        dut.g_pq.u_issue.ocnt[dut.g_pq.u_issue.oh]);
        if (dut.g_pq.u_issue.head_done) $display("T %0d HEADDONE oh %0d", cyc, dut.g_pq.u_issue.oh);
        if (dut.g_pq.u_issue.adv && cyc >= tr_from && cyc <= tr_to)
            $display("T %0d ADV si %0d ti %0d row_ok %0d row %0d cr %0d first %0d last %0d glast %0d xa %0d wave_adv %0d lw %0d vm %b items %0d wb_n %0d",
                     cyc, dut.g_pq.u_issue.si, dut.g_pq.u_issue.ti, dut.g_pq.u_issue.row_ok, dut.g_pq.u_issue.row_now, dut.g_pq.u_issue.cr,
                     dut.g_pq.u_issue.iss_first, dut.g_pq.u_issue.iss_last, dut.g_pq.u_issue.iss_glast, dut.g_pq.u_issue.xa,
                     dut.g_pq.u_issue.wave_adv, dut.g_pq.u_issue.lw_q, dut.g_pq.u_issue.valid_mask, dut.g_pq.u_issue.items_q,
                     dut.g_pq.u_issue.wb_n);
        fault_q <= fault;
        if (fault && !fault_q) $display("T %0d FAULT", cyc);
    end
    // watchdog: no completion, result or line for STALL cycles -> dump the handshake state and stop (TIMEOUT)
    parameter integer STALL = 20000;
    integer last_prog = 0;
    always @(posedge clk) if (rv || take || (arrive != arrive_q) || start) last_prog = cyc;
    always @(posedge clk) if (rst_n && cyc - last_prog > STALL) begin
        $fwrite(fo, "# TIMEOUT stall at cyc %0d: op %0d ndone %0d cur %0d nres %0d start %0d start_ready %0d busy %0d | issue on %0d issuing %0d init %0d start_v %0d hv %0d since %0d need %0d launch %0d w_valid %0d\n",
                cyc, op, ndone, cur, nres[cur], start, start_ready, busy, dut.g_pq.u_issue.on, dut.g_pq.u_issue.issuing,
                dut.g_pq.u_issue.init_q, dut.g_pq.u_issue.start_v, dut.g_pq.u_issue.hv_q, dut.g_pq.u_issue.since, dut.g_pq.u_issue.need_q,
                dut.g_pq.u_issue.launch, dut.g_pq.w_valid);
        $fclose(fo); $finish;
    end
    initial begin #50000000; $fwrite(fo, "# TIMEOUT\n"); $fclose(fo); $finish; end
endmodule
