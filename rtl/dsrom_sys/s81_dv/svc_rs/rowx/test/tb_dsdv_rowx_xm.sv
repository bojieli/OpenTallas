`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-ROWX3 bench: 16-owner end-to-end model of the rank-order row transport, one die half (tiles 8..15).
//   export   every owner drives its half's RO export exactly as the RTL emits it (ROWX-2 format, CHECKED there against
//            an independent golden): 7 passes x 8 tile windows x 40 words, word i of pass p of tile t = ranks
//            2 (40 p + i), + 1, a half valid iff that rank is held by this owner; one word a cycle from GO + XOFF.
//   transport 16 dsdv_rowx_xm in a static chain (POS = a permutation of the owners), registered links with fixed
//            latency (on-die LON, die-to-die LX on every 4th link) plus random arrival jitter 0..J; the compiler
//            schedule (XOFF / BC_OFF per POS) is computed here with HOP = L + J + 4.
//   ingress  every receiver's egress (ROWS PK2 frame) is scored: header + exactly 2,048 words; every (rank, tile) of
//            the 512 x 8 slots held by ANOTHER owner lands exactly once with that owner's exact half; none of the
//            receiver's own halves; no other half.  All 16 receivers are checked.
// Negatives (verdict PASS = the fault is caught): +ovl=1 one rank exported by two owners -> f_ovl (fcode 0) at the
//   downstream owner; +short=1 link 7->8 booked 2 cycles early -> late (fcode 2); +skew=1 owner 5 exports 1 cycle late
//   -> re-pair f_mis (fcode 6).
// S81-ROWX-3b: +pk=1 packs two slots per 1,024-b link beat (0.5 beats / cycle, cfg [62]); +rate=R (per mille) caps
//   every die-to-die link (every 4th link, latency LX) at R/1000 beats / cycle from its first beat (the end-slice lep:
//   764 = 0.764, the UCIe lane pair), modelled as the lane's elastic TX FIFO: beat n leaves no earlier than
//   t0 + ceil(1000 n / R).  +rall=1 caps every link (16 dies, one owner per die: all 15 links die-to-die).  +neg_rate=1: PK = 0 at rate 764 must be caught as reduce landing late (fcode 2) at pos 4.
// Mutants: TB_MUT 1 (no self exclusion), 2 (no overlap check; run with +ovl=1), 3 (re-pair bank), 4 (padding slot kept),
//   5 (PK unpack reuses the low slot; run with +pk=1).
// ---------------------------------------------------------------------------------------------------------------------
`ifndef TB_MUT
`define TB_MUT 0
`endif
module tb_dsdv_rowx_xm;
    localparam integer N = 16, NS = 2240, NR = 512, G = 20;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer SEED = 1, J = 0, LON = 3, LX = 12, OVL = 0, SHORT = 0, SKEW = 0, PERM = 1, PK = 0, RATE = 1000, NEGR = 0, RALL = 0; string FIX;
    reg [31:0] gid [0:511];
    integer posof [0:15];            // owner {stack, die} -> chain position
    integer holder [0:511];          // rank -> chain position of its holder
    integer dup_r = -1, dup_p = -1;  // +ovl: rank also exported by position dup_p
    integer lat [0:N-1], hop [0:N-1], hopr [0:N-1], xoff [0:N-1], bcoff [0:N-1];
    integer nbr [0:N-1], nbb [0:N-1], t0r [0:N-1], t0b [0:N-1], maxlag = 0;   // per-link beat count / first beat (rate cap)

    function automatic [143:0] piece(input integer p, input integer r, input integer t);
        reg [143:0] x; reg [31:0] h;
        for (int k = 0; k < 5; k++) begin
            h = 32'(r) * 32'h9E3779B1 ^ 32'(p * 7919 + t * 104729 + k * 15485863);
            h = h ^ (h >> 15); h = h * 32'h85EBCA6B; h = h ^ (h >> 13); h = h * 32'hC2B2AE35; h = h ^ (h >> 16);
            if (k < 4) x[32*k +: 32] = h; else x[143:128] = h[15:0];
        end
        piece = x;
    endfunction
    function automatic [255:0] half(input v, input [3:0] t, input [9:0] r, input [143:0] b);
        half = v ? {88'd0, b[127:89], 9'd0, b[88:0], b[143:128], r, t, 1'b1} : 256'd0;
    endfunction
    function automatic bit holds(input integer p, input integer r);
        holds = r < NR && (holder[r] == p || (r == dup_r && p == dup_p));
    endfunction
    function automatic [512:0] xword(input integer p, input integer c);   // owner p's export word c of the half
        integer k, i, pp, t, r0; k = (c / 40) % 8; i = c % 40; pp = c / 320; t = 8 + k; r0 = 2 * (40 * pp + i);
        xword = {1'(i % 5 == 0), half(holds(p, r0 + 1), 4'(t), 10'(r0 + 1), piece(p, r0 + 1, t)),
                                 half(holds(p, r0), 4'(t), 10'(r0), piece(p, r0, t))};
    endfunction

    // ---------------------------------------------------------------- DUT chain
    reg cfg_v = 0; reg [63:0] cfg_d [0:N-1]; reg [511:0] hdr;
    reg go = 0;
    always @(posedge clk) begin cfg_v <= (cyc + 1 == 8); go <= (cyc + 1 == G); end
    reg x_v [0:N-1]; reg [512:0] x_d [0:N-1];
    reg ri_v [0:N-1]; reg [1023:0] ri_d [0:N-1]; reg bi_v [0:N-1]; reg [1023:0] bi_d [0:N-1];
    wire ro_v [0:N-1]; wire [1023:0] ro_d [0:N-1]; wire bo_v [0:N-1]; wire [1023:0] bo_d [0:N-1];
    wire e_v [0:N-1]; wire [511:0] e_d [0:N-1]; wire flt [0:N-1]; wire [7:0] fc [0:N-1];
    genvar gd;
    generate for (gd = 0; gd < N; gd++) begin : g_die
        dsdv_rowx_xm #(.MUT(`TB_MUT), .D(16)) u (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_d(cfg_d[gd]), .hdr_v(cfg_v),
            .hdr_d(hdr), .go(go), .x_v(x_v[gd]), .x_d(x_d[gd]), .ri_v(ri_v[gd]), .ri_d(ri_d[gd]), .ro_v(ro_v[gd]),
            .ro_d(ro_d[gd]), .bi_v(bi_v[gd]), .bi_d(bi_d[gd]), .bo_v(bo_v[gd]), .bo_d(bo_d[gd]), .e_v(e_v[gd]),
            .e_d(e_d[gd]), .fault(flt[gd]), .fcode(fc[gd]));
    end endgenerate

    // ---------------------------------------------------------------- links (registered, fixed latency + jitter), export drive
    typedef struct packed { logic [31:0] t; logic [1023:0] d; } lk_t;
    lk_t qr [0:N-1][$];   // reduce link p -> p + 1 (indexed by the sender)
    lk_t qb [0:N-1][$];   // broadcast link p -> p - 1 (indexed by the sender)
    integer lastr [0:N-1], lastb [0:N-1];
    reg [511:0] ew [0:N-1][$]; integer elast [0:N-1];
    always @(posedge clk) if (rst_n) begin
        for (int p = 0; p < N; p++) begin
            integer t;
            if (ro_v[p] && p < N - 1) begin t = cyc + lat[p] + (J ? $urandom % (J + 1) : 0); if (t <= lastr[p]) t = lastr[p] + 1;
                if (((p % 4) == 3 || RALL) && RATE < 1000) begin integer tc; if (nbr[p] == 0) t0r[p] = t;
                    tc = t0r[p] + (1000 * nbr[p] + RATE - 1) / RATE; if (tc > t) begin if (tc - t > maxlag) maxlag = tc - t; t = tc; end end
                nbr[p]++; lastr[p] = t; qr[p].push_back('{t: 32'(t), d: ro_d[p]}); end
            if (bo_v[p] && p > 0) begin t = cyc + lat[p - 1] + (J ? $urandom % (J + 1) : 0); if (t <= lastb[p]) t = lastb[p] + 1;
                if ((((p - 1) % 4) == 3 || RALL) && RATE < 1000) begin integer tc; if (nbb[p] == 0) t0b[p] = t;
                    tc = t0b[p] + (1000 * nbb[p] + RATE - 1) / RATE; if (tc > t) begin if (tc - t > maxlag) maxlag = tc - t; t = tc; end end
                nbb[p]++; lastb[p] = t; qb[p].push_back('{t: 32'(t), d: bo_d[p]}); end
            if (e_v[p]) begin ew[p].push_back(e_d[p]); elast[p] = cyc; end
        end
        for (int p = 0; p < N; p++) begin
            ri_v[p] <= 1'b0; bi_v[p] <= 1'b0; x_v[p] <= 1'b0;
            if (p > 0 && qr[p - 1].size() && qr[p - 1][0].t == 32'(cyc + 1)) begin ri_v[p] <= 1'b1; ri_d[p] <= qr[p - 1][0].d; void'(qr[p - 1].pop_front()); end
            if (p < N - 1 && qb[p + 1].size() && qb[p + 1][0].t == 32'(cyc + 1)) begin bi_v[p] <= 1'b1; bi_d[p] <= qb[p + 1][0].d; void'(qb[p + 1].pop_front()); end
            begin integer c; c = cyc + 1 - (G + xoff[p] + ((SKEW && p == 5) ? 1 : 0));
                if (c >= 0 && c < NS) begin x_v[p] <= 1'b1; x_d[p] <= xword(p, c); end end
        end
    end

    // ---------------------------------------------------------------- run
    integer err = 0, nfx = 0, x0 = 0, span = 0;
    reg [7:0] fexp; integer fpos;
    initial begin
        void'($value$plusargs("seed=%d", SEED)); void'($value$plusargs("j=%d", J)); void'($value$plusargs("ovl=%d", OVL));
        void'($value$plusargs("short=%d", SHORT)); void'($value$plusargs("skew=%d", SKEW)); void'($value$plusargs("perm=%d", PERM));
        void'($value$plusargs("lon=%d", LON)); void'($value$plusargs("lx=%d", LX));
        void'($value$plusargs("pk=%d", PK)); void'($value$plusargs("rate=%d", RATE)); void'($value$plusargs("neg_rate=%d", NEGR));
        void'($value$plusargs("rall=%d", RALL));   // +rall=1: every link is die-to-die (16 dies), all rate-capped
        if (NEGR) begin PK = 0; RATE = 764; end
        void'($urandom(SEED));
        for (int r = 0; r < 512; r++) gid[r] = $urandom();
        if ($value$plusargs("fix=%s", FIX)) $readmemh(FIX, gid);
        for (int o = 0; o < 16; o++) posof[o] = o;
        if (PERM) for (int o = 15; o > 0; o--) begin integer k, tmp; k = $urandom % (o + 1); tmp = posof[o]; posof[o] = posof[k]; posof[k] = tmp; end
        for (int r = 0; r < 512; r++) holder[r] = posof[{gid[r][7:6], gid[r][5:4]}];
        if (OVL) begin dup_r = 37 + $urandom % 400; dup_p = (holder[dup_r] + 1 + $urandom % 15) % 16; end
        // compiler schedule: HOP = link latency + jitter + 4 (stage flop, landing pin flop, FIFO write, 1 margin)
        for (int p = 0; p < N; p++) begin lat[p] = ((p % 4) == 3) ? LX : LON; hop[p] = lat[p] + J + 4; hopr[p] = hop[p] + PK; end
        if (SHORT) hopr[7] = hopr[7] - 2 - J - PK;
        xoff[0] = 2; for (int p = 1; p < N; p++) xoff[p] = xoff[p - 1] + hopr[p - 1];
        bcoff[N - 1] = xoff[N - 1] + 45; for (int p = N - 2; p >= 0; p--) bcoff[p] = bcoff[p + 1] + hop[p];
        for (int p = 0; p < N; p++) begin
            cfg_d[p] = '0; cfg_d[p][3:0] = 4'(p); cfg_d[p][4] = p == 0; cfg_d[p][5] = p == N - 1; cfg_d[p][6] = 1'b1;
            cfg_d[p][22:7] = 16'(xoff[p]); cfg_d[p][38:23] = 16'(bcoff[p]); cfg_d[p][50:39] = 12'(NS); cfg_d[p][61:51] = 11'(NR); cfg_d[p][62] = 1'(PK);
            lastr[p] = 0; lastb[p] = 0; elast[p] = 0; nbr[p] = 0; nbb[p] = 0;
        end
        hdr = '0; hdr[511:508] = 4'd6; hdr[503] = 1'b1; hdr[491:480] = 12'd2048; hdr[0] = 1'b1;
        repeat (4) @(posedge clk); #0.2 rst_n = 1;
        x0 = G + xoff[0];
        repeat (G + bcoff[0] + NS + 200) @(posedge clk);
        // ---------------------------------------------------------------- score every receiver
        for (int p = 0; p < N; p++) begin
            bit seen [0:511][0:7];
            for (int r = 0; r < 512; r++) for (int t = 0; t < 8; t++) seen[r][t] = 0;
            if (ew[p].size() != 2049) begin err++; $display("EGRESS_COUNT pos %0d words %0d", p, ew[p].size()); end
            if (ew[p].size() && ew[p][0] !== hdr) begin err++; $display("EGRESS_HDR pos %0d", p); end
            for (int w = 1; w < ew[p].size(); w++) for (int h = 0; h < 2; h++) begin
                reg [255:0] x; integer r, t; x = ew[p][w][256*h +: 256];
                if (x[0]) begin
                    r = x[14:5]; t = x[4:1];
                    if (t < 8) begin err++; if (err <= 10) $display("EGRESS_TILE pos %0d t %0d", p, t); end
                    else if (holder[r] == p) begin err++; if (err <= 10) $display("EGRESS_OWN pos %0d rank %0d", p, r); end
                    else if (x !== half(1, 4'(t), 10'(r), piece(holder[r], r, t))) begin err++; if (err <= 10) $display("EGRESS_DATA pos %0d rank %0d t %0d", p, r, t); end
                    else if (seen[r][t - 8]) begin err++; if (err <= 10) $display("EGRESS_DUP pos %0d rank %0d t %0d", p, r, t); end
                    else seen[r][t - 8] = 1;
                end else if (x != 0) begin err++; if (err <= 10) $display("EGRESS_JUNK pos %0d w %0d", p, w); end
            end
            for (int r = 0; r < 512; r++) for (int t = 0; t < 8; t++)
                if (holder[r] != p && !seen[r][t]) begin err++; if (err <= 10) $display("EGRESS_MISS pos %0d rank %0d t %0d", p, r, t + 8); end
            if (elast[p] - x0 + 1 > span) span = elast[p] - x0 + 1;
        end
        // ---------------------------------------------------------------- faults
        fexp = 0; fpos = -1;
        if (OVL) begin fexp = 8'h01; fpos = (dup_p > holder[dup_r]) ? dup_p : holder[dup_r]; end
        if (SHORT) begin fexp = 8'h04; fpos = 8; end
        if (SKEW) begin fexp = 8'h40; fpos = 5; end
        if (NEGR) begin fexp = 8'h04; fpos = RALL ? 1 : 4; end
        begin integer nf; nf = 0;
            for (int p = 0; p < N; p++) if (fc[p] != 0) begin nf++; if (fexp == 0 || p != fpos) $display("FAULT pos %0d fcode %02h", p, fc[p]); end
            if (fexp == 0) begin if (nf) err++; end
            else begin   // negative: the data checks are moot; PASS iff the expected fault fires where expected
                err = ((fc[fpos] & fexp) == fexp) ? 0 : 1;
                $display("NEG ovl %0d short %0d skew %0d rate %0d expect fcode %02h at pos %0d got %02h", OVL, SHORT, SKEW, NEGR, fexp, fpos, fc[fpos]);
            end
        end
        $display("TRANSPORT_TIMING first_export %0d span %0d hop_sum %0d (re-pair 42 + reduce/broadcast 2 x 15 hops + slots %0d + hdr) J %0d LON %0d LX %0d",
                 x0, span, bcoff[0] - xoff[0] - 45, NS, J, LON, LX);
        $display("LINK pk %0d rate %0d lane_lag_max %0d (cycles a beat waited for the rate cap)", PK, RATE, maxlag);
        $display("ROWXM seed %0d pk %0d rate %0d fix %0d perm %0d j %0d ovl %0d short %0d skew %0d words0 %0d err %0d mut %0d verdict=%s",
                 SEED, PK, RATE, FIX.len() > 0, PERM, J, OVL, SHORT, SKEW, ew[0].size(), err, `TB_MUT, err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
