`timescale 1ns/1ps
// tb_hbm_b2_xcommit: the x-store commit / drain tracker (ot_hbm_b2_xcommit) gated with the REAL native SM element
// (ot_hbm_accel_smh, no parameter overrides = the selected production configuration NC 8 / RMAX 4096 / REQCR 1 /
// TAGW 16, DEF = 1 hardened-master hierarchy) behind the REAL PIPE1 sink (ot_hbm_b2_vm8_sm_sink).
// Stimulus, HBM share model, descriptor stream, result log and golden are those of rtl/test/tb_hbm_accel_sm_pq_seq.sv
// (serial protocol: an op's x load starts after every earlier op completed); what differs:
//   * every x beat enters through the sink's tap {v1, addr7, grp7, data2048} at II 1 (13 beats per address);
//   * start reaches the SM only through the tracker's registered start gate (start_in is raised at cmd_begin, BEFORE
//     the first beat: the join alone decides the dispatch edge);
//   * every x-store macro of the SM (8 columns x 2 tiles x 2 leaves x 4 macros = 256) is probed: write edges, read
//     edges, array contents against a shadow of the beats the SM pins sampled.
// The x-store arrays start with a non-zero pattern (OT_MEM_NO_INIT + the fill below), so a read before commit differs.
// Five trackers run in parallel (MUT 0..4); +SEL picks the one whose start_out drives the SM (one build, five runs).
// All monitors sample a quarter cycle BEFORE the rising clock edge (ck_s): the values the edge will sample; `e` is the
// index of that upcoming edge.  Files (+DIR): seq.hex, lines.hex, x.hex (as the pq bench), xc.hex (5 words per op:
// burst length (0 = one burst), gap between bursts, release delay, idle gap before the load, claim committed).
module tb_hbm_b2_xcommit;
    parameter integer D = 27, SMI = 5, MAXOPS = 32, LAT = 60, JIT = 40, STALL = 20000;
    localparam integer SUB = 4, LBS = 2, LSB = 16, NC = 8, XDEPTH = 128, RMAX = 4096;
    localparam integer RW = 12, XW = 7, XC = 3152, FRAGW = NC * XC, NBEAT = 13, NW = 10, NX = 5, NS = 256;
    reg clk = 0, rst_n = 0, ck_s = 1;
    always #0.5 clk = ~clk;                       // rises at 0.5 + k
    initial begin #0.25; forever #0.5 ck_s = ~ck_s; end   // falls at 0.25 + k: a quarter cycle before the rising edge
    // ---------------- the real PIPE1 sink ----------------
    reg tap_v = 0; wire tap_ready; reg [2062:0] tap_data = 0; reg [15:0] tap_ticket = 0;
    wire tap_ACK_v; wire [191:0] tap_ACK_owner; wire [15:0] tap_ACK_ticket;
    wire [7:0] xw_en; wire [55:0] xw_addr, xw_grp; wire [16383:0] xw_data; wire sink_fault, sink_drained;
    localparam [191:0] OWNER = 192'h1013_0b2c_0ffe_e5a5_7ac4_e12d_0000_abcd_ef01_2345_6789_abcd;
    ot_hbm_b2_vm8_sm_sink #(.PIPE(1)) u_sink (.clk(clk), .rst_n(rst_n), .permit(1'b1), .expected_owner(OWNER),
        .sm_mask(8'hff), .tap_v(tap_v), .tap_ready(tap_ready), .tap_data(tap_data), .tap_owner(OWNER),
        .tap_ticket(tap_ticket), .tap_ACK_v(tap_ACK_v), .tap_ACK_owner(tap_ACK_owner), .tap_ACK_ticket(tap_ACK_ticket),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .fault(sink_fault), .drained(sink_drained));
    // ---------------- the trackers (MUT 0..4) ----------------
    integer sel;
    reg cmd_begin = 0, release_final = 0, start_in = 0, start_committed = 0;
    wire start_ready;
    wire [4:0] t_inflight, t_drained, t_ok, t_start, t_taken, t_fault;
    genvar gm;
    generate for (gm = 0; gm < 5; gm = gm + 1) begin : g_trk
        ot_hbm_b2_xcommit #(.D(D), .MUT(gm)) u (.clk(clk), .rst_n(rst_n), .xw_en(xw_en), .sink_drained(sink_drained),
            .cmd_begin(cmd_begin), .release_final(release_final), .start_in(start_in),
            .start_committed(start_committed), .start_ready(start_ready && sel == gm), .x_inflight(t_inflight[gm]),
            .x_drained(t_drained[gm]), .dispatch_ok(t_ok[gm]), .start_out(t_start[gm]), .start_taken(t_taken[gm]),
            .fault(t_fault[gm]));
    end endgenerate
    wire start = t_start[sel[2:0]];
    wire trk_fault = t_fault[sel[2:0]];
    // ---------------- the real native SM ----------------
    reg [RW:0] op_rows; reg [15:0] op_c; reg [7:0] op_g; reg op_gs; reg [1:0] op_fmt; reg [XW-1:0] op_xb;
    wire busy;
    reg d_valid = 0; wire d_ready; reg [31:0] d_base = 0; reg [23:0] d_lines = 0;
    wire req_v; wire [31:0] req_addr; wire [9:0] req_tag;
    reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
    wire rv; wire [RW-1:0] rrow; wire [NC*32-1:0] rdata; wire fault; wire arrive; wire released;
    reg release_in = 0;
    reg cg_wake = 1;
    ot_hbm_accel_smh dut (
        .clk(clk), .rst_n(rst_n), .start(start), .start_ready(start_ready), .op_rows(op_rows), .op_c(op_c),
        .op_g(op_g), .op_gs(op_gs), .op_fmt(op_fmt), .op_xb(op_xb), .busy(busy), .d_valid(d_valid),
        .d_ready(d_ready), .d_base(d_base), .d_lines(d_lines), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr),
        .req_tag(req_tag), .rsp_v(rsp_v), .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en[SMI]),
        .xw_addr(xw_addr[SMI*7 +: 7]), .xw_grp(xw_grp[SMI*7 +: 7]), .xw_data(xw_data[SMI*2048 +: 2048]), .rv(rv),
        .rrow(rrow), .rdata(rdata), .fault(fault), .arrive(arrive), .release_in(release_in), .released(released),
        .cg_en(cg_wake));
    initial if (dut.DEF != 1 || dut.NBEAT != NBEAT || dut.BBW != 2069 || dut.TAGW != 16 || dut.REQCR != 1 || dut.RMAX != 4096)
        $fatal(1, "tb_hbm_b2_xcommit: the SM is not the selected native configuration");
    // ---------------- bench state ----------------
    reg [1087:0] lines [0:131071];
    reg [FRAGW+2047:0] xwords [0:MAXOPS*XDEPTH-1];
    reg [31:0] seq [0:MAXOPS*NW-1];
    reg [31:0] xcw [0:MAXOPS*NX-1];
    integer base_of [0:MAXOPS-1];
    reg [31:0] p_addr [0:511]; reg [9:0] p_tag [0:511]; integer p_rdy [0:511]; reg p_use [0:511];
    integer i, ii, gg, op, nops, fo, seed, pick, cyc, xptr, nd, acc, ndone, n_started, nb, bl, k;
    integer t_post [0:MAXOPS-1]; integer t_done [0:MAXOPS-1]; integer nres [0:MAXOPS-1]; integer consumed [0:MAXOPS-1];
    integer cur, cons_total, line_op, ticket;
    reg taken_seen = 0;
    reg [1023:0] dir;
    initial for (ii = 0; ii < 512; ii = ii + 1) p_use[ii] = 0;
    // REQCR 1: the bench receiver takes every request beat (req_ready constant 1)
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
    wire take = dut.g_fd.u_fc.u_is.w_valid && dut.g_fd.u_fc.u_is.w_ready;
    always @(posedge clk) if (take) begin
        while (line_op < nops - 1 && cons_total >= base_of[line_op + 1]) line_op = line_op + 1;
        consumed[line_op] = consumed[line_op] + 1; cons_total = cons_total + 1;
    end
    initial begin
        nd = 0;
        wait (rst_n);
        @(negedge clk);
        while (nd < nops) begin
            d_valid = 1; d_base = base_of[nd]; d_lines = seq[nd * NW + 4];
            @(posedge clk);
            if (d_ready) nd = nd + 1;
            @(negedge clk);
            d_valid = 0;
        end
    end
    always @(posedge clk) if (rv) begin
        while (cur < nops - 1 && nres[cur] >= seq[cur * NW + 0]) cur = cur + 1;
        $fwrite(fo, "%0d %0d %h\n", cur, rrow, rdata);
        nres[cur] = nres[cur] + 1;
    end
    reg arrive_q = 0, fin_tog = 0;
    always @(posedge clk) begin
        arrive_q <= arrive;
        if (rst_n && (arrive != arrive_q)) begin t_done[ndone] = cyc; ndone = ndone + 1; fin_tog = ~fin_tog; end
    end
    always @(posedge clk) release_in <= arrive;
    always @(posedge clk) if (start && start_ready) begin n_started <= n_started + 1; taken_seen = 1; end
    // the SM adapter's clock-gating contract (tb_hbm_accel_sm_pq_seq OT_SMH_CG_LOCKSTEP): awake while an x beat, a
    // start or an op is in flight; the tiles' HOLD (64 edges) covers the beats still in the x-write pipeline (D = 27)
    always @(negedge clk) cg_wake <= !rst_n || xw_en[SMI] || start || (n_started > ndone) || d_valid;
    // ---------------- shadow of the beats the SM pins sampled; monitors (quarter cycle before the edge) ----------------
    reg [NBEAT*2048-1:0] fragx [0:XDEPTH-1];
    reg [NBEAT-1:0]      shv [0:XDEPTH-1];
    integer e, e0_last, e0_first, e_rel, t_start_e, n_beats, cal;
    integer lastw [0:NS-1]; integer firstr [0:NS-1]; reg rd_seen [0:NS-1];
    integer lat_min [0:NS-1]; integer lat_max [0:NS-1]; integer rmin [0:NS-1]; integer smin [0:NS-1];
    integer rb_bad [0:NS-1]; integer stale [0:NS-1]; integer w_after_drained [0:NS-1]; integer w_gated [0:NS-1];
    integer nwr [0:NS-1];
    integer cur_xb, cur_xn;                    // the x range of the op being dispatched (readback at the start edge)
    reg fin_now = 0, fin_seen = 0, rel_mark = 0;
    wire rb_fire = start && start_ready;       // the SM takes the op on the upcoming edge
    integer op_e0 [0:MAXOPS-1]; integer op_ts [0:MAXOPS-1]; integer op_erel [0:MAXOPS-1]; integer op_ack [0:MAXOPS-1];
    integer op_rb [0:MAXOPS-1]; integer op_wl [0:MAXOPS-1]; integer op_rf [0:MAXOPS-1]; integer op_sm [0:MAXOPS-1];
    integer op_d [0:MAXOPS-1]; integer op_nb [0:MAXOPS-1]; integer op_t0 [0:MAXOPS-1]; integer e_tap0;
    integer s, sum, mx, mn, fop, e_ack, drained_low_err, sink_ack;
    initial begin
        for (s = 0; s < XDEPTH; s = s + 1) begin fragx[s] = 0; shv[s] = 0; end
        for (s = 0; s < NS; s = s + 1) begin
            lastw[s] = -1; firstr[s] = -1; rd_seen[s] = 0; lat_min[s] = 1 << 30; lat_max[s] = -1; rmin[s] = 1 << 30;
            smin[s] = 1 << 30; rb_bad[s] = 0; stale[s] = 0; w_after_drained[s] = 0; w_gated[s] = 0; nwr[s] = 0;
        end
        e = 1; e0_last = -1; e0_first = -1; e_rel = -1; t_start_e = -1; n_beats = 0; cal = 0; cur_xb = 0; cur_xn = 0; fop = 0;
        e_ack = -1; drained_low_err = 0; sink_ack = 0; e_tap0 = -1;
    end
    always @(negedge ck_s) begin
        if (rst_n) begin
            if (xw_en[SMI]) begin
                e0_last = e; if (e0_first < 0) e0_first = e; n_beats = n_beats + 1;
                fragx[xw_addr[SMI*7 +: 7]][xw_grp[SMI*7 +: 7]*2048 +: 2048] = xw_data[SMI*2048 +: 2048];
                shv[xw_addr[SMI*7 +: 7]][xw_grp[SMI*7 +: 7]] = 1'b1;
                if (t_drained[0]) drained_low_err = drained_low_err + 1;   // a beat at the pins while x_drained
            end
            if (tap_ACK_v) begin e_ack = e; sink_ack = sink_ack + 1; end
            if (cmd_begin) e_tap0 = -1;                         // per command: the edge that accepts its first tap beat
            if (tap_v && tap_ready && e_tap0 < 0) e_tap0 = e;
            if (release_final && !rel_mark) begin e_rel = e; rel_mark = 1; end
            if (!release_final) rel_mark = 0;
            if (rb_fire) begin
                t_start_e = e; op_ts[fop] = e; op_e0[fop] = e0_last; op_erel[fop] = e_rel; op_ack[fop] = e_ack;
                op_nb[fop] = n_beats; op_t0[fop] = e_tap0;
            end
            fin_now <= (fin_tog != fin_seen); fin_seen <= fin_tog;
        end
        e = e + 1;
    end
    // per x-store macro: c column, p tile row, j leaf, m macro; R = p * 2 + j the SM row of the leaf
    genvar gc, gp, gj, gx;
    generate for (gc = 0; gc < NC; gc = gc + 1) begin : m_c
        for (gp = 0; gp < 2; gp = gp + 1) begin : m_p
            wire en_l;
            if (gc < NC / 2) begin : g_w
                assign en_l = dut.g_c[gc].g_p[gp].g_tw.u_t.u.u_cgt.u_cg.en_l;
            end else begin : g_e
                assign en_l = dut.g_c[gc].g_p[gp].g_te.u_t.u.u_cgt.u_cg.en_l;
            end
            for (gj = 0; gj < 2; gj = gj + 1) begin : m_j
                for (gx = 0; gx < 4; gx = gx + 1) begin : m_x
                    localparam integer IDX = ((gc * 2 + gp) * 2 + gj) * 4 + gx;
                    localparam integer R   = gp * 2 + gj;
                    localparam integer BK  = gc * XC + R * 532;
                    localparam integer BF  = gc * XC + 2128 + R * 256;
                    localparam integer NV  = (gx == 3) ? 20 : 256;
                    integer a;
                    // hierarchical access to the macro model (the west / east tile masters differ in one scope name)
                    `define XCM(BR) dut.g_c[gc].g_p[gp].BR.u_t.u.u.g_lf[gj].u_lh.u_xs.u_leaf.g_xm[gx].u_x
                    if (gc < NC / 2) begin : g_s
                        integer q;
                        wire wce = `XCM(g_tw).w_ce_in, rce = `XCM(g_tw).r_ce_in;
                        wire [6:0] ra = `XCM(g_tw).r_addr_in;
                        initial for (q = 0; q < 130; q = q + 1)
                            `XCM(g_tw).arr[q] = {8{32'h5a5a_0000 ^ (IDX * 32'h0001_0193) ^ (q * 32'h0100_01b3)}} | 258'd1;
                        function automatic [255:0] rdw(input integer ad); rdw = `XCM(g_tw).arr[ad][255:0]; endfunction
                    end else begin : g_s
                        integer q;
                        wire wce = `XCM(g_te).w_ce_in, rce = `XCM(g_te).r_ce_in;
                        wire [6:0] ra = `XCM(g_te).r_addr_in;
                        initial for (q = 0; q < 130; q = q + 1)
                            `XCM(g_te).arr[q] = {8{32'h5a5a_0000 ^ (IDX * 32'h0001_0193) ^ (q * 32'h0100_01b3)}} | 258'd1;
                        function automatic [255:0] rdw(input integer ad); rdw = `XCM(g_te).arr[ad][255:0]; endfunction
                    end
                    `undef XCM
                    wire wce = g_s.wce, rce = g_s.rce;
                    wire [6:0] ra = g_s.ra;
                    function automatic [255:0] expw(input integer ad);
                        reg [1023:0] w;
                        begin
                            w = 1024'd0;
                            w[531:0] = fragx[ad][BK +: 532];
                            w[787:532] = fragx[ad][BF +: 256];
                            expw = w[gx*256 +: 256];
                        end
                    endfunction
                    function automatic bad(input integer ad);
                        reg [255:0] g, x;
                        begin
                            g = g_s.rdw(ad);
                            x = expw(ad);
                            bad = (&shv[ad]) ? (g[NV-1:0] !== x[NV-1:0]) : 1'b1;
                        end
                    endfunction
                    always @(negedge ck_s) if (rst_n) begin
                        // the SM takes an op on the upcoming edge: the store must already hold the op's x
                        if (rb_fire) begin
                            for (a = 0; a < cur_xn; a = a + 1)
                                if (bad((cur_xb + a) % XDEPTH)) rb_bad[IDX] = rb_bad[IDX] + 1;
                            rd_seen[IDX] = 0;
                        end
                        if (wce && m_p[gp].en_l) begin
                            lastw[IDX] = e; nwr[IDX] = nwr[IDX] + 1;
                            if (cal != 0) begin
                                if (e - e0_last < lat_min[IDX]) lat_min[IDX] = e - e0_last;
                                if (e - e0_last > lat_max[IDX]) lat_max[IDX] = e - e0_last;
                            end
                            if (t_drained[0]) w_after_drained[IDX] = w_after_drained[IDX] + 1;
                        end
                        if (wce && !m_p[gp].en_l) w_gated[IDX] = w_gated[IDX] + 1;
                        if (rce && m_p[gp].en_l) begin
                            if (!rd_seen[IDX]) begin firstr[IDX] = e; rd_seen[IDX] = 1; end
                            if (bad(ra)) stale[IDX] = stale[IDX] + 1;
                        end
                        if (fin_now && rd_seen[IDX]) begin
                            if (firstr[IDX] - t_start_e < rmin[IDX]) rmin[IDX] = firstr[IDX] - t_start_e;
                            if (firstr[IDX] - lastw[IDX] < smin[IDX]) smin[IDX] = firstr[IDX] - lastw[IDX];
                        end
                    end
                end
            end
        end
    end endgenerate
    // per op, when it completes: readback mismatches at its start edge, last write edge, first read edge, min slack
    always @(negedge ck_s) if (rst_n && fin_now) begin
        sum = 0; mx = -1; mn = 1 << 30;
        for (s = 0; s < NS; s = s + 1) begin
            if (lastw[s] > mx) mx = lastw[s];
            if (rd_seen[s] && firstr[s] < mn) mn = firstr[s];
        end
        op_wl[fop] = mx; op_rf[fop] = mn;
        mn = 1 << 30;
        for (s = 0; s < NS; s = s + 1) if (rd_seen[s] && firstr[s] - lastw[s] < mn) mn = firstr[s] - lastw[s];
        op_sm[fop] = mn;
        fop = fop + 1;
    end
    // readback mismatches are summed at the start edge (the per-macro blocks above ran in the same sampling step or
    // will: read the totals one sampling step later)
    reg rb_q = 0; integer rb_prev = 0, rb_fop = 0;
    always @(negedge ck_s) if (rst_n) begin
        if (rb_q) begin
            sum = 0; for (s = 0; s < NS; s = s + 1) sum = sum + rb_bad[s];
            op_rb[rb_fop] = sum - rb_prev; rb_prev = sum;
        end
        rb_q <= rb_fire; if (rb_fire) rb_fop = fop;
    end
    // ---------------- stimulus ----------------
    task automatic beat(input [6:0] ad, input integer g, input [2047:0] dat);
        begin
            tap_v = 1; tap_data = {1'b1, ad, g[6:0], dat}; tap_ticket = ticket[15:0]; ticket = ticket + 1;
            if (!tap_ready || sink_fault) begin $fwrite(fo, "# SINK_NOT_READY e %0d\n", e); end
            @(negedge clk);
        end
    endtask
    integer cal_gated, wl_max, total_stale, total_rb, total_wad, total_wg, lat_bad;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NOPS=%d", nops)) nops = 1;
        if (!$value$plusargs("SEL=%d", sel)) sel = 0;
        seed = 7; cyc = 0; cur = 0; cons_total = 0; line_op = 0; ndone = 0; n_started = 0; ticket = 0;
        $readmemh({dir, "/seq.hex"}, seq);
        $readmemh({dir, "/lines.hex"}, lines);
        $readmemh({dir, "/x.hex"}, xwords);
        $readmemh({dir, "/xc.hex"}, xcw);
        acc = 0;
        for (op = 0; op < nops; op = op + 1) begin
            base_of[op] = acc; acc = acc + seq[op * NW + 4];
            nres[op] = 0; consumed[op] = 0; t_done[op] = -1; t_post[op] = -1;
            op_e0[op] = -1; op_ts[op] = -1; op_erel[op] = -1; op_rb[op] = -1; op_wl[op] = -1; op_rf[op] = -1; op_sm[op] = -1;
            op_ack[op] = -1; op_nb[op] = -1; op_t0[op] = -1;
        end
        fo = $fopen({dir, "/out.txt"}, "w");
        repeat (4) @(posedge clk);
        rst_n = 1;
        // ---- calibration: 13 isolated beats (one per group) at address 127 after the tiles' gates closed ----
        repeat (150) @(negedge clk);
        cal_gated = !m_c[0].m_p[0].en_l + !m_c[7].m_p[1].en_l;
        cal = 1;
        for (gg = 0; gg < NBEAT; gg = gg + 1) begin
            beat(7'd127, gg, (gg == 12) ? {1408'd0, {20{32'hc0de_0000 + gg}}} : {64{32'hc0de_0000 + gg}});
            tap_v = 0;
            repeat (40) @(negedge clk);
        end
        cal = 0;
        xptr = 0;
        for (op = 0; op < nops; op = op + 1) begin
            @(negedge clk);
            while (ndone < op) @(negedge clk);                       // serial: every earlier op completed
            repeat (6) @(negedge clk);                               // the monitors close the finished op first
            repeat (xcw[op * NX + 3]) @(negedge clk);                // idle gap (tiles gate off after HOLD)
            op_rows = seq[op * NW + 0]; op_c = seq[op * NW + 1]; op_g = seq[op * NW + 2]; op_fmt = seq[op * NW + 3];
            op_gs = seq[op * NW + 5]; op_xb = seq[op * NW + 9];
            cur_xb = seq[op * NW + 9]; cur_xn = seq[op * NW + 7];
            taken_seen = 0;
            if (seq[op * NW + 6] != 0) begin
                release_final = 0; cmd_begin = 1;
                @(negedge clk);
                cmd_begin = 0;
                start_in = 1; start_committed = 0;                   // requested before the first beat: the join decides
                @(negedge clk);
                nb = 0; bl = xcw[op * NX + 0];
                for (ii = 0; ii < seq[op * NW + 7]; ii = ii + 1)
                    for (gg = 0; gg < NBEAT; gg = gg + 1) begin
                        if (bl != 0 && nb != 0 && (nb % bl) == 0) begin
                            tap_v = 0; repeat (xcw[op * NX + 1]) @(negedge clk);
                        end
                        beat((seq[op * NW + 9] + ii) % XDEPTH, gg, xwords[xptr + ii][gg * 2048 +: 2048]);
                        nb = nb + 1;
                    end
                tap_v = 0;
                xptr = xptr + seq[op * NW + 7];
                repeat (xcw[op * NX + 2]) @(negedge clk);            // the root's final release (0: with the last accept)
                release_final = 1;
            end else begin
                start_in = 1; start_committed = xcw[op * NX + 4];   // resident x: committed and released already
            end
            while (!taken_seen) @(negedge clk);
            t_post[op] = cyc;
            start_in = 0; start_committed = 0;
        end
        while (ndone < nops) @(negedge clk);
        repeat (8) @(posedge clk);
        @(negedge ck_s); @(negedge ck_s);
        for (op = 0; op < nops; op = op + 1)
            $fwrite(fo, "# op %0d t_post %0d t_done %0d results %0d lines %0d consumed %0d fault %0d\n",
                    op, t_post[op], t_done[op], nres[op], seq[op * NW + 4], consumed[op], fault);
        for (op = 0; op < nops; op = op + 1)
            $fwrite(fo, "# xc op %0d load %0d e0_last %0d e_ack %0d e_rel %0d t_start %0d rb_bad %0d wr_last %0d rd_first %0d slack_min %0d beats %0d e_tap0 %0d\n",
                    op, seq[op * NW + 6], op_e0[op], op_ack[op], op_erel[op], op_ts[op], op_rb[op], op_wl[op], op_rf[op],
                    op_sm[op], op_nb[op], op_t0[op]);
        total_stale = 0; total_rb = 0; total_wad = 0; total_wg = 0; lat_bad = 0; wl_max = -1;
        for (s = 0; s < NS; s = s + 1) begin
            $fwrite(fo, "# sram %0d c %0d p %0d j %0d m %0d lat_min %0d lat_max %0d nwr %0d rmin %0d smin %0d rb_bad %0d stale %0d\n",
                    s, s / 32, (s / 16) % 2, (s / 8) % 2, s % 4, lat_min[s], lat_max[s], nwr[s], rmin[s], smin[s], rb_bad[s], stale[s]);
            total_stale = total_stale + stale[s]; total_rb = total_rb + rb_bad[s]; total_wad = total_wad + w_after_drained[s];
            total_wg = total_wg + w_gated[s];
            if (lat_min[s] != lat_max[s]) lat_bad = lat_bad + 1;
            if (lat_max[s] > wl_max) wl_max = lat_max[s];
        end
        $fwrite(fo, "# xcsum sel %0d D %0d cal_lat_max %0d cal_nonuniform %0d cal_gated %0d rb_bad %0d stale %0d write_while_drained %0d write_gated %0d beat_while_drained %0d trk_fault %0d sink_fault %0d sink_acks %0d beats %0d sm_fault %0d\n",
                sel, D, wl_max, lat_bad, cal_gated, total_rb, total_stale, total_wad, total_wg, drained_low_err, trk_fault,
                sink_fault, sink_ack, n_beats, fault);
        $fwrite(fo, "# total_cycles %0d\n", cyc);
        $fclose(fo);
        $finish;
    end
    integer last_prog = 0;
    always @(posedge clk) if (rv || take || (arrive != arrive_q) || start || tap_v) last_prog = cyc;
    always @(posedge clk) if (rst_n && cyc - last_prog > STALL) begin
        $fwrite(fo, "# TIMEOUT stall at cyc %0d: op %0d ndone %0d start %0d start_ready %0d busy %0d trk_fault %0d sink_fault %0d\n",
                cyc, op, ndone, start, start_ready, busy, trk_fault, sink_fault);
        $fclose(fo); $finish;
    end
    initial begin #50000000; $fwrite(fo, "# TIMEOUT\n"); $fclose(fo); $finish; end
endmodule
