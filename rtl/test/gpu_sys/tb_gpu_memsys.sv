`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_gpu_memsys: random-traffic and performance bench for ot_gpu_memsys
// (clk_mem 1000 ps).  Driven by tools/gpu_sys/run_memsys.py.
//
// Golden: a die-global sector array gold[] covering [0, GS) sectors, loaded
// from +golden=<file> (the same content the runner placed in the partition
// images through tools/gpu_sys/mem_image.py, loaded by the DUT from
// +gpu_sys_mem_prefix=<prefix>).  The L2 slice is the point of coherence, so
// the bench serialises every request at the cycle its slice ACCEPTS it (an
// xbar->slice handshake observed hierarchically): writes update gold[] there
// (byte strobes), reads record gold[] there as their expected data.  A client
// response must then match exactly; each request gets exactly one response,
// with its own tag and direction.
//
// Phase 1 (random): NC clients, NTX requests in all: 50% reads, 25% full and
// 25% partial writes (random strobes, sometimes empty or single-byte), over a
// WIN-sector window, 30% of them on a 24-sector hot set (same-sector races
// across clients and slices); up to 16 tags per client, a tag reused only
// after its response; random request gaps; random response backpressure.
// Phase 2: client 0 reads the whole window back (final memory == golden).
// Phase 3: latency, isolated: read miss, read hit, full-write ack,
// partial-write ack (cold sectors).  Phase 4: sustained sequential reads of
// cold sectors, client 0 alone (64 tags) and all NC clients (64 tags each).
// Results are printed as "RESULT key value" lines.
// ---------------------------------------------------------------------------
module tb_gpu_memsys;
    parameter integer NC        = 4;
    parameter integer NS        = 2;
    parameter integer NPC       = 2;
    parameter integer MEM_WORDS = 16384;
    parameter integer USE_W2    = 0;
    parameter integer OSD       = 64;
    parameter integer NTX       = 20000;
    parameter integer WIN       = 4096;      // random-window sectors [0, WIN)
    parameter integer BWN       = 8192;      // bandwidth sectors [WIN, WIN+BWN)
    parameter integer LATN      = 64;        // latency sectors [WIN+BWN, +LATN)
    parameter integer SEED      = 1;
    localparam integer GS = WIN + BWN + LATN;
    localparam integer TP = 64;              // tags per client
    localparam integer LNC = (NC > 1) ? $clog2(NC) : 1;

    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg rst_n = 1'b0;

    reg  [NC-1:0]     req_v = '0;
    wire [NC-1:0]     req_rdy;
    reg  [NC-1:0]     req_we = '0;
    reg  [NC*32-1:0]  req_addr = '0;
    reg  [NC*256-1:0] req_wdata = '0;
    reg  [NC*32-1:0]  req_wstrb = '0;
    reg  [NC*16-1:0]  req_tag = '0;
    wire [NC-1:0]     rsp_v;
    reg  [NC-1:0]     rsp_rdy = '0;
    wire [NC*16-1:0]  rsp_tag;
    wire [NC-1:0]     rsp_we;
    wire [NC*256-1:0] rsp_data;
    wire              fault;

    ot_gpu_memsys #(.ENABLE(1), .NC(NC), .NS(NS), .NPC(NPC), .MEM_WORDS(MEM_WORDS), .OSD(OSD), .USE_W2(USE_W2)) dut (
        .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(req_rdy), .req_we(req_we), .req_addr(req_addr),
        .req_wdata(req_wdata), .req_wstrb(req_wstrb), .req_tag(req_tag), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy),
        .rsp_tag(rsp_tag), .rsp_we(rsp_we), .rsp_data(rsp_data), .fault(fault));

    // default-off instance: every output must stay 0
    wire [NC-1:0]     off_req_rdy, off_rsp_v, off_rsp_we;
    wire [NC*16-1:0]  off_rsp_tag;
    wire [NC*256-1:0] off_rsp_data;
    wire              off_fault;
    ot_gpu_memsys #(.NC(NC), .NS(NS)) dut_off (
        .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(off_req_rdy), .req_we(req_we), .req_addr(req_addr),
        .req_wdata(req_wdata), .req_wstrb(req_wstrb), .req_tag(req_tag), .rsp_v(off_rsp_v), .rsp_rdy(rsp_rdy),
        .rsp_tag(off_rsp_tag), .rsp_we(off_rsp_we), .rsp_data(off_rsp_data), .fault(off_fault));

    reg [255:0] gold [0:GS-1];
    // per (client, tag) bookkeeping
    reg         busy  [0:NC-1][0:TP-1];
    reg         acc   [0:NC-1][0:TP-1];
    reg         twe   [0:NC-1][0:TP-1];
    reg [255:0] texp  [0:NC-1][0:TP-1];
    longint     tiss  [0:NC-1][0:TP-1];
    longint     cyc = 0;

    // driver control (set by the main process)
    integer mode = 0;                 // 0 idle, 1 random, 2 sequential reads, 3 one request (client 0)
    reg     one_go = 1'b0, one_we = 1'b0;
    integer one_sect = 0;
    reg [31:0] one_st = 0;
    longint lat_last = 0;
    integer rand_left = 0;            // random requests still to issue (all clients)
    integer seq_next [0:NC-1];        // sequential: next sector
    integer seq_end  [0:NC-1];
    integer ntags = 16;
    integer bp_pct = 30;              // response backpressure probability (%)
    integer gap_pct = 30;             // probability a client idles a cycle (random mode)
    longint n_issued = 0, n_rsp = 0, n_rd = 0, n_wr_full = 0, n_wr_part = 0, n_hot = 0, n_bp = 0;
    longint last_rsp_cyc = 0, first_iss_cyc = -1;
    longint lat_sum = 0;
    integer outstanding [0:NC-1];
    integer hot [0:23];
    integer errors = 0;

    function automatic integer sect_slice(input integer sect);
        sect_slice = (NS > 1) ? ((sect >> 2) % NS) : 0;
    endfunction

    // ---------------- slice-acceptance monitor (coherence order) ----------------
    always @(posedge clk) if (rst_n) begin : mon
        integer s, c, t, sect, b;
        reg [31:0] a; reg [31:0] st; reg [255:0] wd;
        for (s = 0; s < NS; s = s + 1)
            if (dut.g_on.s_req_v[s] && dut.g_on.s_req_rdy[s]) begin
                a  = dut.g_on.s_req_addr[s*32 +: 32];
                t  = integer'(dut.g_on.s_req_tag[s*(16+LNC) +: 16]);
                c  = integer'(dut.g_on.s_req_tag[s*(16+LNC) + 16 +: LNC]);
                sect = integer'(a >> 5);
                if (((a >> 7) % NS) != s) begin $display("ERROR slice %0d got address %h", s, a); errors = errors + 1; end
                if (t >= TP || !busy[c][t] || acc[c][t]) begin
                    $display("ERROR accept of unknown/duplicate c%0d t%0d", c, t); errors = errors + 1;
                end else begin
                    acc[c][t] = 1'b1;
                    if (dut.g_on.s_req_we[s]) begin
                        st = dut.g_on.s_req_wstrb[s*32 +: 32]; wd = dut.g_on.s_req_wdata[s*256 +: 256];
                        for (b = 0; b < 32; b = b + 1) if (st[b]) gold[sect][b*8 +: 8] = wd[b*8 +: 8];
                    end else texp[c][t] = gold[sect];
                end
            end
    end

    // ---------------- driver and response checker ----------------
    always @(posedge clk) begin : drv
        integer c, t, k, sect, b, r;
        reg [31:0] st; reg [255:0] wd;
        reg fire, newreq;
        if (!rst_n) begin
            req_v <= '0; rsp_rdy <= '0;
        end else begin
            cyc = cyc + 1;
            if (fault) begin $display("ERROR dut fault at cycle %0d", cyc); errors = errors + 1; end
            if (off_req_rdy != 0 || off_rsp_v != 0 || off_rsp_we != 0 || off_rsp_tag != 0 || off_rsp_data != 0 || off_fault) begin
                $display("ERROR default-off instance drove an output"); errors = errors + 1;
            end
            for (c = 0; c < NC; c = c + 1) begin
                // response
                if (rsp_v[c] && rsp_rdy[c]) begin
                    t = integer'(rsp_tag[c*16 +: 16]);
                    if (t >= TP || !busy[c][t] || !acc[c][t]) begin
                        $display("ERROR c%0d unexpected response tag %0d", c, t); errors = errors + 1;
                    end else begin
                        if (rsp_we[c] != twe[c][t]) begin
                            $display("ERROR c%0d t%0d direction %0d expected %0d", c, t, rsp_we[c], twe[c][t]); errors = errors + 1;
                        end else if (!twe[c][t] && rsp_data[c*256 +: 256] != texp[c][t]) begin
                            $display("ERROR c%0d t%0d read data\n  got %h\n  exp %h", c, t, rsp_data[c*256 +: 256], texp[c][t]);
                            errors = errors + 1;
                        end
                        busy[c][t] = 1'b0; acc[c][t] = 1'b0;
                        lat_sum = lat_sum + (cyc - tiss[c][t]);
                        lat_last = cyc - tiss[c][t];
                        outstanding[c] = outstanding[c] - 1;
                        n_rsp = n_rsp + 1; last_rsp_cyc = cyc;
                    end
                end
                if (rsp_v[c] && !rsp_rdy[c]) n_bp = n_bp + 1;
                rsp_rdy[c] <= (($urandom % 100) >= bp_pct);
                // request
                fire = req_v[c] && req_rdy[c];
                if (fire) begin
                    n_issued = n_issued + 1;
                    if (first_iss_cyc < 0) first_iss_cyc = cyc;
                end
                newreq = 1'b0;
                if (!req_v[c] || fire) begin
                    // pick a free tag
                    t = -1;
                    if (outstanding[c] < ntags) begin
                        k = $urandom % ntags;
                        for (r = 0; r < ntags; r = r + 1) if (t < 0 && !busy[c][(k + r) % ntags]) t = (k + r) % ntags;
                    end
                    if (t >= 0 && mode == 1 && rand_left > 0 && (($urandom % 100) >= gap_pct)) begin
                        rand_left = rand_left - 1; newreq = 1'b1;
                        if (($urandom % 100) < 30) begin sect = hot[$urandom % 24]; n_hot = n_hot + 1; end
                        else sect = $urandom % WIN;
                        r = $urandom % 4;
                        wd = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                        if (r < 2) begin twe[c][t] = 1'b0; st = 32'd0; n_rd = n_rd + 1; end
                        else if (r == 2) begin twe[c][t] = 1'b1; st = 32'hffff_ffff; n_wr_full = n_wr_full + 1; end
                        else begin
                            twe[c][t] = 1'b1; n_wr_part = n_wr_part + 1;
                            case ($urandom % 4)
                                0: st = 32'd1 << ($urandom % 32);
                                1: st = 32'd0;
                                default: st = $urandom;
                            endcase
                            if (st == 32'hffff_ffff) st = 32'h7fff_ffff;
                        end
                    end else if (t >= 0 && mode == 2 && seq_next[c] < seq_end[c]) begin
                        newreq = 1'b1; sect = seq_next[c]; seq_next[c] = seq_next[c] + 1;
                        twe[c][t] = 1'b0; st = 32'd0; wd = '0; n_rd = n_rd + 1;
                    end
                    else if (t >= 0 && mode == 3 && c == 0 && one_go) begin
                        newreq = 1'b1; one_go = 1'b0; sect = one_sect; twe[c][t] = one_we; st = one_st;
                        wd = {8{32'hA5A5_0000 | 32'(one_sect)}};
                    end
                    if (newreq) begin
                        busy[c][t] = 1'b1; acc[c][t] = 1'b0; tiss[c][t] = cyc + 1;
                        outstanding[c] = outstanding[c] + 1;
                        req_v[c] <= 1'b1; req_we[c] <= twe[c][t]; req_addr[c*32 +: 32] <= 32'(sect) << 5;
                        req_wdata[c*256 +: 256] <= wd; req_wstrb[c*32 +: 32] <= st; req_tag[c*16 +: 16] <= 16'(t);
                    end else req_v[c] <= 1'b0;
                end
            end
        end
    end

    // ---------------- main ----------------
    longint t0, t1, sum;
    integer i, c, n0, n_lat;
    longint lat_rd_miss, lat_rd_hit, lat_wr_full, lat_wr_part;
    string gfile;

    task automatic wait_idle(input longint limit, input string what);
        longint start;
        integer cc, tot;
        start = cyc;
        forever begin
            @(posedge clk);
            tot = 0;
            for (cc = 0; cc < NC; cc = cc + 1) tot = tot + outstanding[cc] + (req_v[cc] ? 1 : 0);
            if (tot == 0 && (mode != 1 || rand_left == 0)) begin
                if (mode != 2) break;
                begin : chk
                    integer done; done = 1;
                    for (cc = 0; cc < NC; cc = cc + 1) if (seq_next[cc] < seq_end[cc]) done = 0;
                    if (done) break;
                end
            end
            if (cyc - start > limit) begin $display("ERROR timeout in %s", what); errors = errors + 1; break; end
        end
        repeat (4) @(posedge clk);
    endtask

    // one isolated request from client 0; its latency is cycles from request valid to the response handshake
    task automatic single(input integer sect, input reg we, input reg [31:0] st, output longint lat);
        one_sect = sect; one_we = we; one_st = st; one_go = 1'b1; mode = 3;
        @(posedge clk);
        while (one_go || outstanding[0] != 0 || req_v[0]) @(posedge clk);
        lat = lat_last;
        mode = 0;
        repeat (4) @(posedge clk);
    endtask

    initial begin
        begin : seeding
            integer sd;
            if (!$value$plusargs("seed=%d", sd)) sd = SEED;
            void'($urandom(sd));
        end
        if (!$value$plusargs("golden=%s", gfile)) begin $display("ERROR missing +golden="); $finish; end
        $readmemh(gfile, gold);
        for (c = 0; c < NC; c = c + 1) begin
            outstanding[c] = 0; seq_next[c] = 0; seq_end[c] = 0;
            for (i = 0; i < TP; i = i + 1) begin busy[c][i] = 1'b0; acc[c][i] = 1'b0; twe[c][i] = 1'b0; end
        end
        // hot set: 24 sectors, 12 per slice: two lines that alias in a 32 KiB slice (0, 2048) and one other
        for (i = 0; i < 24; i = i + 1) hot[i] = ((i % 4) + 4 * ((i / 4) % 2) + ((i / 8) == 0 ? 0 : (i / 8) == 1 ? 2048 : 1032)) % WIN;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        // phase 1: random
        ntags = 16; bp_pct = 30; gap_pct = 30; rand_left = NTX; mode = 1;
        t0 = cyc;
        wait_idle(64'd50_000_000, "random phase");
        mode = 0;
        $display("RESULT random_requests %0d", n_issued);
        $display("RESULT random_responses %0d", n_rsp);
        $display("RESULT random_reads %0d", n_rd);
        $display("RESULT random_full_writes %0d", n_wr_full);
        $display("RESULT random_partial_writes %0d", n_wr_part);
        $display("RESULT random_hot_set_requests %0d", n_hot);
        $display("RESULT random_bp_cycles %0d", n_bp);
        $display("RESULT random_cycles %0d", cyc - t0);
        $display("RESULT random_mean_latency %0f", real'(lat_sum) / real'(n_rsp));
        begin : stats
            integer s; longint rh, rm, wh, wm;
            rh = 0; rm = 0; wh = 0; wm = 0;
            rh = rh + dut.g_on.g_s[0].st_rd_hit; rm = rm + dut.g_on.g_s[0].st_rd_miss;
            wh = wh + dut.g_on.g_s[0].st_wr_hit; wm = wm + dut.g_on.g_s[0].st_wr_miss;
            if (NS > 1) begin
                rh = rh + dut.g_on.g_s[NS-1].st_rd_hit; rm = rm + dut.g_on.g_s[NS-1].st_rd_miss;
                wh = wh + dut.g_on.g_s[NS-1].st_wr_hit; wm = wm + dut.g_on.g_s[NS-1].st_wr_miss;
            end
            s = 0;
            $display("RESULT l2_rd_hit %0d", rh); $display("RESULT l2_rd_miss %0d", rm);
            $display("RESULT l2_wr_hit %0d", wh); $display("RESULT l2_wr_miss %0d", wm);
        end
        if (n_rsp != n_issued) begin $display("ERROR responses %0d != requests %0d", n_rsp, n_issued); errors = errors + 1; end

        // phase 2: read the window back
        n0 = n_rsp; bp_pct = 0; ntags = TP;
        seq_next[0] = 0; seq_end[0] = WIN; mode = 2;
        wait_idle(64'd5_000_000, "readback");
        mode = 0;
        $display("RESULT readback_sectors %0d", n_rsp - n0);

        // phase 3: isolated latencies on cold sectors
        bp_pct = 0;
        sum = 0; n_lat = 8;
        for (i = 0; i < n_lat; i = i + 1) begin single(WIN + BWN + 4 * i, 1'b0, 32'd0, t1); sum = sum + t1; end
        lat_rd_miss = sum;
        sum = 0;
        for (i = 0; i < n_lat; i = i + 1) begin single(WIN + BWN + 4 * i, 1'b0, 32'd0, t1); sum = sum + t1; end
        lat_rd_hit = sum;
        sum = 0;
        for (i = 0; i < n_lat; i = i + 1) begin single(WIN + BWN + 32 + 4 * i, 1'b1, 32'hffff_ffff, t1); sum = sum + t1; end
        lat_wr_full = sum;
        sum = 0;
        for (i = 0; i < n_lat; i = i + 1) begin single(WIN + BWN + 33 + 4 * i, 1'b1, 32'h0000_ff0f, t1); sum = sum + t1; end
        lat_wr_part = sum;
        $display("RESULT lat_read_miss_cycles %0f", real'(lat_rd_miss) / n_lat);
        $display("RESULT lat_read_hit_cycles %0f", real'(lat_rd_hit) / n_lat);
        $display("RESULT lat_write_full_miss_ack_cycles %0f", real'(lat_wr_full) / n_lat);
        $display("RESULT lat_write_partial_miss_ack_cycles %0f", real'(lat_wr_part) / n_lat);

        // phase 4a: sequential reads, client 0 alone
        bp_pct = 0; ntags = TP;
        n0 = n_rsp; first_iss_cyc = -1;
        seq_next[0] = WIN; seq_end[0] = WIN + BWN / 2; mode = 2;
        wait_idle(64'd5_000_000, "bw single");
        mode = 0;
        $display("RESULT bw1_sectors %0d", n_rsp - n0);
        $display("RESULT bw1_cycles %0d", last_rsp_cyc - first_iss_cyc + 1);
        // phase 4b: NC clients, each a contiguous quarter of the second half
        n0 = n_rsp; first_iss_cyc = -1;
        for (c = 0; c < NC; c = c + 1) begin
            seq_next[c] = WIN + BWN / 2 + c * (BWN / 2 / NC); seq_end[c] = seq_next[c] + BWN / 2 / NC;
        end
        mode = 2;
        wait_idle(64'd5_000_000, "bw all");
        mode = 0;
        $display("RESULT bwN_sectors %0d", n_rsp - n0);
        $display("RESULT bwN_cycles %0d", last_rsp_cyc - first_iss_cyc + 1);
        $display("RESULT total_requests %0d", n_issued);
        $display("RESULT total_responses %0d", n_rsp);
        $display("RESULT errors %0d", errors);
        if (errors == 0 && n_rsp == n_issued) $display("PASS tb_gpu_memsys");
        else $display("FAIL tb_gpu_memsys");
        $finish;
    end
endmodule
