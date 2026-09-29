`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Focused bench of the attention KV prefetch path of the adopted V4.1 die:
// ot_chip_v41x_kv_prefetch + four ot_chip_v41x_hbm_karb + four HBM3E stack
// interfaces (ot_chip_v41x_hbm3e_phy K ports, the adopted timing model), with a
// stand-in of the core's attention KV traffic and, on every stack, a stand-in of
// the pooled indexer's key traffic (reads and one-at-a-time sector writes on
// random pseudo-channels) running the whole time.
//
// The golden: a mirror of every KV word (the HBM KV region's initial pattern
// plus every runtime write) and of every key sector.  Cases:
//   gate      after each descriptor the "core" waits for kv_ok, as the core's
//             kv_gate does, and counts the cycles it was held (must be > 0:
//             the words come from HBM); every read word equals the golden;
//   raw       writes into a pending op's range before it is read (between the
//             descriptor and kv_ok, and after kv_ok): the op returns the new data;
//   max       the largest descriptors the attention adapter accepts (TROWS =
//             160 rows, D = 32: a q.k over 12 row tiles, a p.v over 160 rows);
//   slice     ops of a later user slice (base = user 1), addresses beyond the
//             first slice;
//   evict     back-to-back ops overlapping in the two slots, slots reused
//             (many more words than the two slots hold), ops re-reading words
//             written through earlier;
//   shared    both requesters active on the same pseudo-channels: every key
//             read returns the key mirror, every key write completes (wr_done
//             routed to its owner), contention counted;
//   wrap      an op's HBM responses on one stack held in flight (response
//             back-pressure) while six writes hit one of its rows -- more
//             restarts than the tag's 2-bit generation distinguishes: the
//             stale responses are dropped and the op returns the last write;
//   region    the KV region lies above the index keys and inside the stacks.
// At the end the HBM KV region is compared with the golden (write-through).
// ---------------------------------------------------------------------------
module tb_chip_v41x_kv_prefetch #(
    parameter bit KARB_LOCAL = 1'b0,   // 1: ot_chip_v41x_hbm_karb_local (opt-in local K partition)
    parameter bit KARB_FENCE = 1'b1
);
    localparam integer G = 4, W = 16, SW = 8, SUN = 16, AW = 24, HAW = 28, NPC = 32;
    localparam integer STG = 1024, SAW = 10;
    localparam integer KEY_SECTORS = 1 << 18;          // index-key region [0, KEY_SECTORS)
    localparam integer KV_SBASE = KEY_SECTORS;         // attention KV region
    localparam integer USER_WORDS = 1 << 12;           // KV words per user slice
    localparam integer KV_WORDS = 2 * USER_WORDS;      // two user slices
    localparam integer KV_SECTORS = 2 * (KV_WORDS / 4);
    localparam integer K_MEM = 1 << 19;
    localparam integer TAGW = 16;

    reg clk = 1'b0;
    always #1 clk = ~clk;
    reg rst_n = 1'b0;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // -- DUT ---------------------------------------------------------------------------------
    reg [AW-1:0] base = 0;                              // the running user's slice
    reg kvd_v = 0; reg [AW-1:0] kvd_wbase = 0, kvd_ts = 0, kvd_ks = 0; reg [15:0] kvd_tiles = 0, kvd_k = 0;
    reg [1:0] kvd_hg = 0;
    wire kv_ok;
    reg re = 0; reg [G*AW-1:0] raddr = 0; wire [G*W*32-1:0] q;
    reg [SW-1:0] we = 0; reg [SW*AW-1:0] waddr = 0; reg [SW*32-1:0] wdata = 0;
    reg [SUN-1:0] xwe = 0; reg [SUN*AW-1:0] xwaddr = 0; reg [SUN*32-1:0] xwdata = 0;
    wire [3:0] m_v, m_rdy, m_we, s_v, s_rdy, kwd, a_v;
    reg  [3:0] hold_rsp = 4'd0;                         // a stack's KV responses held in flight (wrap case)
    assign s_v = a_v & ~hold_rsp;
    wire [4*HAW-1:0] m_addr; wire [4*4-1:0] m_len, s_beat; wire [4*TAGW-1:0] m_tag, s_tag;
    wire [4*256-1:0] m_wdata, s_data; wire [4*32-1:0] m_wstrb;
    wire pf_fault; wire [4:0] pf_code;
    wire [31:0] st_ops, st_words, st_sw, st_ref, st_wqh, st_hold;
    ot_chip_v41x_kv_prefetch #(.G(G), .W(W), .SW(SW), .SUN(SUN), .AW(AW), .STG(STG), .SAW(SAW),
                                   .KV_SBASE(KV_SBASE), .KV_SECTORS(KV_SECTORS), .HAW(HAW), .TAGW(TAGW)) dut (
        .clk(clk), .rst_n(rst_n), .base(base),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(24'd0),
        .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_hg(kvd_hg), .kv_ok(kv_ok),
        .re(re), .raddr(raddr), .q(q), .we(we), .waddr(waddr), .wdata(wdata),
        .xwe(xwe), .xwaddr(xwaddr), .xwdata(xwdata),
        .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag), .m_we(m_we),
        .m_wdata(m_wdata), .m_wstrb(m_wstrb), .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag), .s_beat(s_beat),
        .s_data(s_data), .fault(pf_fault), .fault_code(pf_code), .st_ops(st_ops), .st_words(st_words),
        .st_sectors_written(st_sw), .st_refetches(st_ref), .st_wq_high(st_wqh), .st_hold_cycles(st_hold));

    // -- the pooled indexer's stand-in, arbiters and stacks --------------------------------------
    function automatic [4:0] pc_of(input [HAW-1:0] s);
        pc_of = 5'(((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31);
    endfunction
    reg [255:0] keym [0:KEY_SECTORS-1];                 // key mirror (all stacks identical)
    integer kbad = 0, kreads = 0, kwrites = 0, kwdone = 0, contended_total = 0;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        wire [NPC-1:0] b_rdy, b_wr_done, b_rsp_v;
        wire [NPC*TAGW-1:0] b_rsp_tag; wire [NPC*4-1:0] b_rsp_beat; wire [NPC*256-1:0] b_rsp_data;
        reg  [NPC-1:0] b_v = 0, b_we = 0;
        reg  [NPC*HAW-1:0] b_addr = 0; reg [NPC*4-1:0] b_len = 0; reg [NPC*TAGW-1:0] b_tag = 0;
        reg  [NPC*256-1:0] b_wdata = 0; reg [NPC*32-1:0] b_wstrb = 0;
        wire [NPC-1:0] h_v, h_rdy, h_we, h_wr_done, r_v, r_rdy;
        wire [NPC*HAW-1:0] h_addr; wire [NPC*4-1:0] h_len, r_beat; wire [NPC*(TAGW+1)-1:0] h_tag, r_tag;
        wire [NPC*256-1:0] h_wdata, r_data; wire [NPC*32-1:0] h_wstrb;
        wire [31:0] kg, bg, ct;
        if (KARB_LOCAL) begin : g_local
        ot_chip_v41x_hbm_karb_local #(.NPC(NPC), .AW(HAW), .TAGW(TAGW), .K_RD_FENCE(KARB_FENCE)) u_arb (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag), .b_we(b_we), .b_wdata(b_wdata),
            .b_wstrb(b_wstrb), .b_wr_done(b_wr_done), .b_rsp_v(b_rsp_v), .b_rsp_rdy({NPC{1'b1}}),
            .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data),
            .k_v(m_v[s]), .k_rdy(m_rdy[s]), .k_addr(m_addr[s*HAW +: HAW]), .k_len(m_len[s*4 +: 4]),
            .k_tag(m_tag[s*TAGW +: TAGW]), .k_we(m_we[s]), .k_wdata(m_wdata[s*256 +: 256]),
            .k_wstrb(m_wstrb[s*32 +: 32]), .k_wr_done(kwd[s]),
            .k_rsp_v(a_v[s]), .k_rsp_rdy(s_rdy[s] && !hold_rsp[s]), .k_rsp_tag(s_tag[s*TAGW +: TAGW]),
            .k_rsp_beat(s_beat[s*4 +: 4]), .k_rsp_data(s_data[s*256 +: 256]),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we), .h_wdata(h_wdata),
            .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat),
            .r_data(r_data), .k_grants(kg), .b_grants(bg), .contended(ct));
        end else begin : g_mono
        ot_chip_v41x_hbm_karb #(.NPC(NPC), .AW(HAW), .TAGW(TAGW)) u_arb (
            .clk(clk), .rst_n(rst_n),
            .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag), .b_we(b_we), .b_wdata(b_wdata),
            .b_wstrb(b_wstrb), .b_wr_done(b_wr_done), .b_rsp_v(b_rsp_v), .b_rsp_rdy({NPC{1'b1}}),
            .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data),
            .k_v(m_v[s]), .k_rdy(m_rdy[s]), .k_addr(m_addr[s*HAW +: HAW]), .k_len(m_len[s*4 +: 4]),
            .k_tag(m_tag[s*TAGW +: TAGW]), .k_we(m_we[s]), .k_wdata(m_wdata[s*256 +: 256]),
            .k_wstrb(m_wstrb[s*32 +: 32]), .k_wr_done(kwd[s]),
            .k_rsp_v(a_v[s]), .k_rsp_rdy(s_rdy[s] && !hold_rsp[s]), .k_rsp_tag(s_tag[s*TAGW +: TAGW]),
            .k_rsp_beat(s_beat[s*4 +: 4]), .k_rsp_data(s_data[s*256 +: 256]),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we), .h_wdata(h_wdata),
            .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .r_v(r_v), .r_rdy(r_rdy), .r_tag(r_tag), .r_beat(r_beat),
            .r_data(r_data), .k_grants(kg), .b_grants(bg), .contended(ct));
        end

        ot_chip_v41x_hbm3e_phy #(.NPC(NPC), .K_MEM(K_MEM), .W_PORT(0), .KTAGW(TAGW + 1)) u_hbm (
            .clk(clk), .rst_n(rst_n),
            .k_v(h_v), .k_rdy(h_rdy), .k_addr(h_addr), .k_len(h_len), .k_tag(h_tag), .k_we(h_we),
            .k_wdata(h_wdata), .k_wstrb(h_wstrb), .k_wr_done(h_wr_done),
            .kr_v(r_v), .kr_rdy(r_rdy), .kr_tag(r_tag), .kr_beat(r_beat), .kr_data(r_data),
            .w_v(1'b0), .w_rdy(), .w_addr(24'd0), .w_len(6'd0), .w_tag(10'd0), .w_room(), .wr_v(), .wr_rdy(8'd0),
            .wr_tag(), .wr_beat(), .wr_data(), .k_oor(), .refreshes(), .w_reads());
        // key traffic: per pseudo-channel, one read (or, rarely, one write per stack) held until accepted
        reg [HAW-1:0] exp_sec [0:NPC-1];
        reg busy_w = 1'b0; integer wpc = 0;
        integer p, r;
        reg [HAW-1:0] sec;
        always @(posedge clk) if (rst_n && !done) begin
            for (p = 0; p < NPC; p = p + 1) begin
                if (b_v[p] && b_rdy[p]) begin
                    b_v[p] <= 1'b0;
                    if (b_we[p]) kwrites = kwrites + 1;
                end
                if (b_rsp_v[p]) begin
                    kreads = kreads + 1;
                    if (b_rsp_data[p*256 +: 256] !== keym[b_rsp_tag[p*TAGW +: TAGW]]) begin
                        if (kbad < 5) $display("KEYBAD stack=%0d pc=%0d tag=%0d", s, p, b_rsp_tag[p*TAGW +: TAGW]);
                        kbad = kbad + 1;
                    end
                end
            end
            if (b_wr_done != 0) begin busy_w <= 1'b0; kwdone = kwdone + 1; end
            // new requests on idle channels (a quarter of the channels each cycle)
            for (p = 0; p < NPC; p = p + 1) if (!(b_v[p]) && ($urandom % 4 == 0)) begin
                // a read of a sector of the read half [0, 2^15) that maps to channel p
                sec = HAW'($urandom % (1 << 15));
                sec = (sec & ~HAW'(31 << 2)) | HAW'(((p ^ ((sec >> 7) & 31) ^ ((sec >> 12) & 31)) & 31) << 2);
                if (pc_of(sec) == p && !(b_we[p] && b_v[p])) begin
                    b_v[p] <= 1'b1; b_we[p] <= 1'b0; b_addr[p*HAW +: HAW] <= sec; b_len[p*4 +: 4] <= 4'd1;
                    b_tag[p*TAGW +: TAGW] <= TAGW'(sec);
                end
            end
            // an occasional key write (one outstanding per stack, as the bridge), to the write half
            if (!busy_w && ($urandom % 64 == 0)) begin
                sec = HAW'((1 << 16) + ($urandom % (1 << 15)));
                wpc = pc_of(sec);
                if (!b_v[wpc]) begin
                    b_v[wpc] <= 1'b1; b_we[wpc] <= 1'b1; b_addr[wpc*HAW +: HAW] <= sec; b_len[wpc*4 +: 4] <= 4'd1;
                    b_wdata[wpc*256 +: 256] <= {8{$urandom}}; b_wstrb[wpc*32 +: 32] <= 32'hffff_ffff;
                    busy_w <= 1'b1;
                end
            end
        end
    end endgenerate

    // -- golden KV and its HBM image ------------------------------------------------------------
    reg [511:0] gold [0:KV_WORDS-1];
    function automatic [511:0] pat(input integer u);
        integer e; reg [511:0] v;
        begin for (e = 0; e < 16; e = e + 1) v[32*e +: 32] = 32'(u * 131 + e * 7 + 32'h1000_0000); pat = v; end
    endfunction
    integer i, u;
    initial begin
        for (i = 0; i < KEY_SECTORS; i = i + 1) keym[i] = {8{32'(i * 2654435761)}};
        for (u = 0; u < KV_WORDS; u = u + 1) gold[u] = pat(u);
    end
    reg loaded = 1'b0;
    always @(posedge clk) if (!loaded) begin
        for (i = 0; i < (1 << 15); i = i + 1) begin
            g_s[0].u_hbm.u_k.mem[i] = keym[i]; g_s[1].u_hbm.u_k.mem[i] = keym[i];
            g_s[2].u_hbm.u_k.mem[i] = keym[i]; g_s[3].u_hbm.u_k.mem[i] = keym[i];
        end
        for (u = 0; u < KV_WORDS; u = u + 1) begin
            case (u % 4)
                0: begin g_s[0].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)] = gold[u][255:0]; g_s[0].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1] = gold[u][511:256]; end
                1: begin g_s[1].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)] = gold[u][255:0]; g_s[1].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1] = gold[u][511:256]; end
                2: begin g_s[2].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)] = gold[u][255:0]; g_s[2].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1] = gold[u][511:256]; end
                default: begin g_s[3].u_hbm.u_k.mem[KV_SBASE + 2*(u/4)] = gold[u][255:0]; g_s[3].u_hbm.u_k.mem[KV_SBASE + 2*(u/4) + 1] = gold[u][511:256]; end
            endcase
        end
        loaded = 1'b1;
    end

    // -- the core stand-in ---------------------------------------------------------------------------
    integer max_ops = 0, slice_ops = 0, wrap_done = 0, wrap_bad = 0, wrap_refetch_hits = 0;
    integer bad = 0, words_read = 0, ops = 0, held_min = 1 << 30, held_ops = 0, raw_checks = 0;
    reg done = 1'b0;
    // one KV element write through the stream-unit lane 0 (or a vector-unit lane 0), golden updated.
    // Whole vectors are assigned (one NBA per signal), so consecutive calls hold the enables high.
    task automatic kv_write(input integer word, input integer lane, input [31:0] val, input integer vu);
        reg [SW-1:0] e1; reg [SW*AW-1:0] a1; reg [SW*32-1:0] d1;
        reg [SUN-1:0] e2; reg [SUN*AW-1:0] a2; reg [SUN*32-1:0] d2;
        begin
            e1 = 0; a1 = 0; d1 = 0; e2 = 0; a2 = 0; d2 = 0;
            if (vu) begin e2[0] = 1'b1; a2[0 +: AW] = AW'(word * 16 + lane); d2[0 +: 32] = val; end
            else begin e1[0] = 1'b1; a1[0 +: AW] = AW'(word * 16 + lane); d1[0 +: 32] = val; end
            we <= e1; waddr <= a1; wdata <= d1; xwe <= e2; xwaddr <= a2; xwdata <= d2;
            gold[base + word][32*lane +: 32] = val;
            @(negedge clk);
        end
    endtask
    // the enables drop only here: an NBA clear followed in the same step by a set loses in Verilator's timing mode
    task automatic kv_idle;
        begin we <= 0; xwe <= 0; end
    endtask
    // a full row write of 16 lanes in one cycle through the vector unit
    task automatic kv_row(input integer word, input [31:0] seed);
        integer l;
        reg [SUN*AW-1:0] a2; reg [SUN*32-1:0] d2;
        begin
            for (l = 0; l < 16; l = l + 1) begin
                a2[l*AW +: AW] = AW'(word * 16 + l); d2[l*32 +: 32] = seed + l;
                gold[base + word][32*l +: 32] = seed + l;
            end
            we <= 0; xwe <= {SUN{1'b1}}; xwaddr <= a2; xwdata <= d2;
            @(negedge clk);
        end
    endtask
    // announce an op (descriptor), optionally write into its range before kv_ok, wait for kv_ok, read it
    task automatic att_op(input integer wb, input integer ts, input integer ks, input integer tiles,
                          input integer hg, input integer kn, input integer raw_before, input integer raw_after);
        integer n, c, p, held, t, k, a, lane;
        reg [511:0] got;
        begin
            n = tiles * (G >> hg) * kn;
            @(negedge clk);
            kvd_v <= 1'b1; kvd_wbase <= AW'(wb); kvd_ts <= AW'(ts); kvd_ks <= AW'(ks); kvd_tiles <= 16'(tiles);
            kvd_k <= 16'(kn); kvd_hg <= 2'(hg);
            @(negedge clk);
            kvd_v <= 1'b0;
            if (raw_before) begin
                // a word inside the range, before its words have landed
                a = wb + ((n / kn) / 2) * ts + (kn / 3) * ks; lane = a % 16;
                kv_write(a, lane, 32'hA5A5_0000 + a, 1);
                kv_idle();
                raw_checks = raw_checks + 1;
            end
            held = 0;
            @(negedge clk);
            while (!kv_ok) begin @(negedge clk); held = held + 1; end
            if (raw_after) begin
                // after kv_ok, before the op issues: kv_ok must drop and the words be fetched again
                a = wb + (kn - 1) * ks; kv_row(a, 32'h5A5A_0000 + 16 * a);
                kv_idle();
                if (kv_ok) begin $display("RAW: kv_ok still high after a write into the pending op"); bad = bad + 1; end
                while (!kv_ok) begin @(negedge clk); held = held + 1; end
                raw_checks = raw_checks + 1;
            end
            if (held < held_min) held_min = held;
            if (held > 0) held_ops = held_ops + 1;
            // the attention adapter's read order: G words a cycle, c = lc .. lc + G - 1
            for (c = 0; c < n; c = c + G) begin : rd
                reg [G*AW-1:0] ra;
                for (p = 0; p < G; p = p + 1) begin
                    t = (c + p) / kn; k = (c + p) % kn;
                    ra[p*AW +: AW] = AW'(wb + t * ts + k * ks);
                end
                re <= 1'b1; raddr <= ra;
                @(negedge clk);
                re <= 1'b0;
                @(negedge clk);
                for (p = 0; p < G; p = p + 1) if (c + p < n) begin
                    t = (c + p) / kn; k = (c + p) % kn; a = wb + t * ts + k * ks;
                    got = q[p*W*32 +: W*32];
                    words_read = words_read + 1;
                    if (got !== gold[base + a]) begin
                        if (bad < 5) $display("KVBAD op=%0d c=%0d word=%0d got=%h expect=%h", ops, c + p, a, got[63:0], gold[base + a][63:0]);
                        bad = bad + 1;
                    end
                end
            end
            ops = ops + 1;
        end
    endtask

    integer r, w2;
    initial begin
        repeat (8) @(posedge clk);
        rst_n <= 1'b1;
        repeat (20) @(posedge clk);
        // gate: q.k-shaped (ks = 1) and p.v-shaped (ks > 1) ops, all four stacks
        att_op(100, 40, 1, 2, 0, 32, 0, 0);
        att_op(900, 1, 16, 1, 0, 60, 0, 0);
        att_op(2000, 64, 1, 1, 1, 32, 0, 0);
        // raw: writes into a pending op, before and after kv_ok
        att_op(300, 40, 1, 2, 0, 32, 1, 0);
        att_op(1200, 1, 16, 1, 0, 48, 1, 1);
        att_op(300, 40, 1, 2, 0, 32, 0, 1);
        // wrap: an op's responses on stack 0 held in flight while six writes hit the same row of the op
        // (more restarts than the 2-bit generation counts); the stale responses must be dropped
        begin : wrap
            integer n, c, p, t, k, a, held;
            reg [G*AW-1:0] ra;
            reg [511:0] got;
            @(negedge clk);
            kvd_v <= 1'b1; kvd_wbase <= AW'(600); kvd_ts <= AW'(40); kvd_ks <= AW'(1); kvd_tiles <= 16'd1;
            kvd_k <= 16'd32; kvd_hg <= 2'd2;
            hold_rsp <= 4'b0001;
            @(negedge clk);
            kvd_v <= 1'b0;
            repeat (60) @(negedge clk);
            for (w2 = 0; w2 < 6; w2 = w2 + 1) begin
                kv_row(600 + 8, 32'hF00D_0000 + 64 * w2);    // word 608: stack 0, inside the op's range
                kv_idle();
                repeat (30) @(negedge clk);
            end
            wrap_refetch_hits = st_ref;
            repeat (3000) @(negedge clk);
            hold_rsp <= 4'd0;
            held = 0;
            @(negedge clk);
            while (!kv_ok) begin @(negedge clk); held = held + 1; end
            n = 32;
            for (c = 0; c < n; c = c + G) begin
                for (p = 0; p < G; p = p + 1) ra[p*AW +: AW] = AW'(600 + c + p);
                re <= 1'b1; raddr <= ra;
                @(negedge clk);
                re <= 1'b0;
                @(negedge clk);
                for (p = 0; p < G; p = p + 1) begin
                    a = 600 + c + p; got = q[p*W*32 +: W*32];
                    words_read = words_read + 1;
                    if (got !== gold[base + a]) begin
                        if (bad < 5) $display("WRAPBAD word=%0d got=%h expect=%h", a, got[63:0], gold[base + a][63:0]);
                        bad = bad + 1; wrap_bad = wrap_bad + 1;
                    end
                end
            end
            ops = ops + 1; held_ops = held_ops + 1; wrap_done = 1;
        end
        // write-through of words outside any op, then ops reading them back
        for (w2 = 0; w2 < 40; w2 = w2 + 1) kv_row(3000 + w2, 32'hC0DE_0000 + 256 * w2);
        for (w2 = 0; w2 < 24; w2 = w2 + 1) kv_write(2500 + 3 * w2, w2 % 16, 32'hBEEF_0000 + w2, w2 % 2);
        kv_idle();
        att_op(3000, 16, 1, 1, 2, 40, 0, 0);
        att_op(2500, 1, 3, 1, 1, 24, 0, 0);
        // the largest ops the adapter accepts (TROWS = 160 rows, D = 32): q.k over 12 row tiles, p.v over 160 rows
        att_op(40, 40, 1, 3, 0, 32, 0, 0);
        att_op(10, 1, 16, 1, 0, 160, 1, 0);
        max_ops = 2;
        // a later user slice: base = user 1's KV words
        base <= AW'(USER_WORDS);
        @(posedge clk);
        att_op(100, 40, 1, 2, 0, 32, 1, 0);
        att_op(64, 1, 16, 1, 0, 160, 0, 1);
        for (w2 = 0; w2 < 8; w2 = w2 + 1) kv_row(3500 + w2, 32'hD00D_0000 + 256 * w2);
        kv_idle();
        att_op(3500, 1, 1, 1, 2, 8, 0, 0);
        slice_ops = 3;
        base <= 0;
        @(posedge clk);
        // evict: many ops through the two slots (STG = 256 < their total), random shapes
        for (r = 0; r < 24; r = r + 1)
            att_op(($urandom % 1500), 1 + ($urandom % 50), 1 + ($urandom % 3), 1, $urandom % 3, 8 + ($urandom % 24),
                   (r % 5 == 0), (r % 7 == 0));
        // drain the write queue, then compare the HBM KV region with the golden (write-through)
        repeat (400) @(posedge clk);
        done = 1'b1;
        begin : final_check
            integer hb, uu; reg [511:0] hv;
            hb = 0;
            for (uu = 0; uu < KV_WORDS; uu = uu + 1) begin
                case (uu % 4)
                    0: hv = {g_s[0].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4) + 1], g_s[0].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4)]};
                    1: hv = {g_s[1].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4) + 1], g_s[1].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4)]};
                    2: hv = {g_s[2].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4) + 1], g_s[2].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4)]};
                    default: hv = {g_s[3].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4) + 1], g_s[3].u_hbm.u_k.mem[KV_SBASE + 2*(uu/4)]};
                endcase
                if (hv !== gold[uu]) begin
                    if (hb < 5) $display("HBMBAD word=%0d", uu);
                    hb = hb + 1;
                end
            end
            contended_total = g_s[0].ct + g_s[1].ct + g_s[2].ct + g_s[3].ct;
            $display("KVPF_CASES max_descriptor_ops=%0d max_words=%0d user_slice_ops=%0d slice_base=%0d",
                     max_ops, 640, slice_ops, USER_WORDS);
            $display("KVPF_WRAP done=%0d writes=6 hits=%0d mismatches=%0d", wrap_done, wrap_refetch_hits, wrap_bad);
            $display("KVPF ops=%0d words_read=%0d bad=%0d held_min=%0d held_ops=%0d raw_checks=%0d refetches=%0d sectors_written=%0d wq_high=%0d hbm_kv_mismatch=%0d fault=%0d code=%b",
                     ops, words_read, bad, held_min, held_ops, raw_checks, st_ref, st_sw, st_wqh, hb, pf_fault, pf_code);
            $display("KEYS reads=%0d bad=%0d writes=%0d wr_done=%0d contended=%0d kv_grants=%0d",
                     kreads, kbad, kwrites, kwdone, contended_total,
                     g_s[0].kg + g_s[1].kg + g_s[2].kg + g_s[3].kg);
            $display("REGION key=[0,%0d) kv=[%0d,%0d) mem=%0d disjoint=%0d inside=%0d", KEY_SECTORS, KV_SBASE,
                     KV_SBASE + KV_SECTORS, K_MEM, KV_SBASE >= KEY_SECTORS, KV_SBASE + KV_SECTORS <= K_MEM);
            if (wrap_done == 1 && wrap_bad == 0 && max_ops == 2 && slice_ops == 3 && bad == 0 && hb == 0 && !pf_fault && held_ops == ops && kbad == 0 && kreads > 0 && kwrites > 0 &&
                kwrites - kwdone <= 4 && contended_total > 0 && raw_checks > 0 && st_ref > 0 &&
                KV_SBASE >= KEY_SECTORS && KV_SBASE + KV_SECTORS <= K_MEM)
                $display("PASS");
            else
                $display("FAIL");
        end
        $finish;
    end
    initial begin
        #20000000;
        $display("TIMEOUT"); $display("FAIL"); $finish;
    end
endmodule
