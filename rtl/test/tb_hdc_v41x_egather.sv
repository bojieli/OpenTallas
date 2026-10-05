`timescale 1ns/1ps
// Bench of the per-bank Engram gather: NL x NC ot_hdc_v41x_egather_slice (one per
// column bank) with behavioural in-order ROMs, a behavioural merge network that
// carries ONE 256-bit beat per cycle to the consuming die (round-robin or random
// bank order, a pipeline of +NETLAT cycles, link stalls), and the consumer-side
// ot_hdc_v41x_egather_asm writing a behavioural vector memory.  Every word of
// every token is compared with the golden rows (tools/rtl_hdc_v41x_egather_campaign.py).
// Files (run directory):
//   eg_meta.mem  {ntok, table_rows}
//   eg_base.mem  per bank (l*NC + c) the column's first row in the layer table
//   eg_req.mem   per token, per bank: the global row id (the hash unit's output)
//   eg_exp.mem   per token, per word ((l*NC + c)*BEATS + beat): 512-bit BF16 word
//   eg_tab.mem   +TABLE=1: 264-bit rows, index l*TROWS + row (codes [255:0], scale [263:256])
// ROM content without +TABLE: splitmix64(l << 40 | row << 6 | j), the content of
// tools/hdc_v41_engram_shipped.row_bytes.
// Plusargs: LAT, JIT (ROM latency LAT + rand(JIT), in order), NETLAT, NSTALL (% link
// stalls), ARB (0 round robin, 1 random), WSTALL (% write-port stalls), SPACED (one
// token at a time), CDEL (consumer hold before release), SEED.
module tb_hdc_v41x_egather #(
    parameter integer NL = 2,
    parameter integer NC = 24,
    parameter integer BEATS = 8,
    parameter integer MAXT = 512,
    parameter integer TROWS = 1 << 18
) (input wire clk);
    localparam integer NB = NL * NC;
    localparam integer TW = 1, LW = 1, CW = 5;
    localparam integer BTW = (BEATS > 1) ? $clog2(BEATS) : 1;
    localparam integer TAGW = TW + LW + CW + BTW + 8;
    localparam integer TOT = NB * BEATS;
    localparam integer NS = 2;
    localparam integer RW = 32, AW = 24;
    localparam integer VAW = $clog2(NS * TOT);

    reg [31:0]  meta [0:1];
    reg [31:0]  basem [0:NB-1];
    reg [31:0]  reqm [0:MAXT*NB-1];
    reg [511:0] expm [0:MAXT*TOT-1];
    reg [263:0] tab  [0:NL*TROWS-1];
    integer ntok, table_mode = 0, lat = 4, jit = 0, netlat = 2, nstall = 0, arb = 0, wstall = 0, spaced = 0;
    integer cdel = 0;
    reg [31:0] seed = 32'h9abcdef1;
    initial begin
        $readmemh("eg_meta.mem", meta);
        ntok = meta[0];
        $readmemh("eg_base.mem", basem);
        $readmemh("eg_req.mem", reqm, 0, ntok * NB - 1);
        $readmemh("eg_exp.mem", expm, 0, ntok * TOT - 1);
        if (!$value$plusargs("TABLE=%d", table_mode)) table_mode = 0;
        if (table_mode != 0) $readmemh("eg_tab.mem", tab);   // sparse: @address lines
        if (!$value$plusargs("LAT=%d", lat)) lat = 4;
        if (!$value$plusargs("JIT=%d", jit)) jit = 0;
        if (!$value$plusargs("NETLAT=%d", netlat)) netlat = 2;
        if (!$value$plusargs("NSTALL=%d", nstall)) nstall = 0;
        if (!$value$plusargs("ARB=%d", arb)) arb = 0;
        if (!$value$plusargs("WSTALL=%d", wstall)) wstall = 0;
        if (!$value$plusargs("SPACED=%d", spaced)) spaced = 0;
        if (!$value$plusargs("CDEL=%d", cdel)) cdel = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h9abcdef1;
    end
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    function automatic [63:0] smix(input [63:0] x);
        reg [63:0] z;
        begin
            z = x + 64'h9E3779B97F4A7C15;
            z = (z ^ (z >> 30)) * 64'hBF58476D1CE4E5B9;
            z = (z ^ (z >> 27)) * 64'h94D049BB133111EB;
            smix = z ^ (z >> 31);
        end
    endfunction
    //: the ROM word: beat j of global row g of layer l (the side byte is the scale on beat 0 only)
    function automatic [263:0] romword(input integer l, input [31:0] g, input integer j);
        reg [263:0] d;
        reg [63:0] key, w;
        integer q;
        begin
            key = ({32'd0, l[31:0]} << 40) | ({32'd0, g} << 6);
            for (q = 0; q < 4; q = q + 1) d[64*q +: 64] = smix(key | (4 * j + q));
            w = smix(key | 64'd32);
            d[263:256] = (j != 0) ? 8'hA5 : (w[8] ? w[7:0] : (8'd107 + (w[7:0] % 8'd41)));
            romword = d;
        end
    endfunction

    reg rst_n = 1'b0;
    // -- slices ----------------------------------------------------------------------
    reg  [NB-1:0]      req_valid = 0;
    wire [NB-1:0]      req_ready;
    reg  [NB*RW-1:0]   req_row = 0;
    reg  [NB*TW-1:0]   req_tag = 0;
    wire [NB-1:0]      rom_re;
    wire [NB*(AW+BTW)-1:0] rom_addr;
    reg  [NB-1:0]      rom_rvalid = 0;
    reg  [NB*264-1:0]  rom_rdata;
    wire [NB-1:0]      sb_valid;
    reg  [NB-1:0]      sb_ready;
    wire [NB*256-1:0]  sb_data;
    wire [NB*TAGW-1:0] sb_tag;
    genvar gb;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_bank
        ot_hdc_v41x_egather_slice #(.RW(RW), .AW(AW), .BEATS(BEATS), .TW(TW), .LW(LW), .CW(CW), .DQ(4)) u_s (
            .clk(clk), .rst_n(rst_n), .cfg_base(basem[gb]), .cfg_layer(gb / NC), .cfg_col(gb % NC),
            .req_valid(req_valid[gb]), .req_ready(req_ready[gb]), .req_row(req_row[RW*gb +: RW]),
            .req_tag(req_tag[TW*gb +: TW]), .rom_re(rom_re[gb]), .rom_addr(rom_addr[(AW+BTW)*gb +: AW+BTW]),
            .rom_rvalid(rom_rvalid[gb]), .rom_rdata(rom_rdata[264*gb +: 264]), .b_valid(sb_valid[gb]),
            .b_ready(sb_ready[gb]), .b_data(sb_data[256*gb +: 256]), .b_tag(sb_tag[TAGW*gb +: TAGW]));
    end endgenerate
    // -- assembler ---------------------------------------------------------------------
    reg              tok_valid = 1'b0;
    wire             tok_ready;
    wire [TW-1:0]    tok_tag;
    reg              a_valid = 1'b0;
    wire             a_ready;
    reg  [255:0]     a_data;
    reg  [TAGW-1:0]  a_tag;
    wire             wr_valid;
    reg              wr_ready = 1'b1;
    wire [VAW-1:0]   wr_addr;
    wire [511:0]     wr_data;
    wire [NS-1:0]    rdy;
    reg              rel_valid = 1'b0;
    reg  [TW-1:0]    rel_tag = 0;
    wire             fault;
    ot_hdc_v41x_egather_asm #(.NL(NL), .NC(NC), .BEATS(BEATS), .TW(TW), .LW(LW), .CW(CW)) u_asm (
        .clk(clk), .rst_n(rst_n), .tok_valid(tok_valid), .tok_ready(tok_ready), .tok_tag(tok_tag),
        .b_valid(a_valid), .b_ready(a_ready), .b_data(a_data), .b_tag(a_tag), .wr_valid(wr_valid),
        .wr_ready(wr_ready), .wr_addr(wr_addr), .wr_data(wr_data), .rdy(rdy), .rel_valid(rel_valid),
        .rel_tag(rel_tag), .fault(fault));
    reg [511:0] vmem [0:NS*TOT-1];
    always @(posedge clk) if (wr_valid && wr_ready) vmem[wr_addr] <= wr_data;

    // -- ROMs: in order, latency LAT + rand(JIT) ----------------------------------------
    localparam integer RQ = 16;
    reg  [263:0] rq_d [0:NB-1][0:RQ-1];
    integer      rq_t [0:NB-1][0:RQ-1];
    integer      rq_w [0:NB-1];
    integer      rq_r [0:NB-1];
    integer      rq_last [0:NB-1];
    integer cyc = 0, b, j, q, r_over = 0;
    reg [31:0] g;
    integer res, bt;
    always @(posedge clk) begin
        for (b = 0; b < NB; b = b + 1) begin
            if (!rst_n) begin rq_w[b] = 0; rq_r[b] = 0; rq_last[b] = 0; end
            rom_rvalid[b] <= 1'b0;
            if (rq_r[b] != rq_w[b] && rq_t[b][rq_r[b] % RQ] <= cyc) begin
                rom_rvalid[b] <= 1'b1;
                rom_rdata[264*b +: 264] <= rq_d[b][rq_r[b] % RQ];
                rq_r[b] = rq_r[b] + 1;
            end
            if (rom_re[b]) begin
                if (rq_w[b] - rq_r[b] >= RQ) r_over = r_over + 1;
                if (BEATS > 1) begin
                    res = rom_addr[(AW+BTW)*b + BTW +: AW];
                    bt = rom_addr[(AW+BTW)*b +: BTW];
                end else begin
                    res = rom_addr[(AW+BTW)*b + 1 +: AW];
                    bt = 0;
                end
                g = basem[b] + res;
                if (table_mode != 0) rq_d[b][rq_w[b] % RQ] = tab[(b / NC) * TROWS + g];
                else rq_d[b][rq_w[b] % RQ] = romword(b / NC, g, bt);
                rq_last[b] = ((cyc + lat + ((jit > 0) ? (xs(seed ^ (b * 977) ^ cyc) % (jit + 1)) : 0)) > rq_last[b])
                             ? (cyc + lat + ((jit > 0) ? (xs(seed ^ (b * 977) ^ cyc) % (jit + 1)) : 0)) : rq_last[b];
                rq_t[b][rq_w[b] % RQ] = rq_last[b];
                rq_w[b] = rq_w[b] + 1;
            end
        end
    end

    // -- merge network: one beat per cycle to the consumer ------------------------------
    localparam integer NQ = 512;
    reg  [256+TAGW-1:0] nq [0:NQ-1];
    integer nq_w = 0, nq_r = 0, ninf = 0, rr = 0, pick, k2, nstall_now = 0, beats_moved = 0;
    integer             nq_t [0:NQ-1];
    always @(*) begin
        sb_ready = {NB{1'b0}};
        pick = -1;
        if (rst_n && !nstall_now && (nq_w - nq_r) < NQ - 2) begin
            for (k2 = 0; k2 < NB; k2 = k2 + 1)
                if (pick < 0 && sb_valid[(rr + k2) % NB]) pick = (rr + k2) % NB;
            if (pick >= 0) sb_ready[pick] = 1'b1;
        end
    end
    always @(posedge clk) begin
        // the link: a granted beat reaches the consumer NETLAT cycles later (timestamped queue)
        if (pick >= 0) begin
            beats_moved = beats_moved + 1;
            nq[nq_w % NQ] = {sb_tag[TAGW*pick +: TAGW], sb_data[256*pick +: 256]};
            nq_t[nq_w % NQ] = cyc + netlat;
            nq_w = nq_w + 1;
            rr <= (arb != 0) ? (xs(seed ^ cyc) % NB) : (pick + 1) % NB;
        end else if (arb != 0) rr <= xs(seed ^ cyc ^ 32'h55) % NB;
        nstall_now <= (nstall > 0) && ((xs(seed ^ (cyc * 31)) % 100) < nstall);
        // to the assembler (a registered valid/data pair)
        if (a_valid && a_ready) a_valid <= 1'b0;
        if ((!a_valid || a_ready) && nq_r != nq_w && nq_t[nq_r % NQ] <= cyc) begin
            {a_tag, a_data} <= nq[nq_r % NQ];
            a_valid <= 1'b1;
            nq_r = nq_r + 1;
        end
        wr_ready <= (wstall == 0) ? 1'b1 : ((xs(seed ^ (cyc * 7)) % 100) >= wstall);
    end

    // -- driver ----------------------------------------------------------------------------
    localparam integer BQ = 4;
    reg  [RW+TW-1:0] bqd [0:NB-1][0:BQ-1];
    integer bq_w [0:NB-1];
    integer bq_r [0:NB-1];
    integer alloc = 0, done = 0, errors = 0, words = 0, faults = 0, t0 = -1, tlast = 0;
    integer lat_min = 1 << 30, lat_max = 0, lat_sum = 0, gap_min = 1 << 30, gap_max = 0, prev_done = -1;
    integer t_alloc [0:MAXT-1];
    integer slot_tok [0:NS-1];
    integer rel_at [0:NS-1];
    reg     seen [0:NS-1];
    integer full, s, w, e;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        seed <= xs(seed);
        if (cyc == 4) rst_n <= 1'b1;
        if (!rst_n) for (b = 0; b < NB; b = b + 1) begin bq_w[b] = 0; bq_r[b] = 0; end
        if (!rst_n) for (s = 0; s < NS; s = s + 1) begin rel_at[s] = -1; seen[s] = 1'b0; end
        // requests to the banks
        for (b = 0; b < NB; b = b + 1) begin
            if (req_valid[b] && req_ready[b]) bq_r[b] = bq_r[b] + 1;
            req_valid[b] <= (bq_r[b] != bq_w[b]);
            {req_tag[TW*b +: TW], req_row[RW*b +: RW]} <= bqd[b][bq_r[b] % BQ];
        end
        // allocation
        if (tok_valid && tok_ready) begin
            tok_valid <= 1'b0;
            slot_tok[tok_tag] = alloc;
            t_alloc[alloc] = cyc;
            if (t0 < 0) t0 = cyc;
            for (b = 0; b < NB; b = b + 1) begin
                bqd[b][bq_w[b] % BQ] = {tok_tag, reqm[alloc * NB + b]};
                bq_w[b] = bq_w[b] + 1;
            end
            alloc = alloc + 1;
        end
        full = 0;
        for (b = 0; b < NB; b = b + 1) if (bq_w[b] - bq_r[b] >= BQ - 1) full = 1;
        if (rst_n && cyc > 8 && !tok_valid && alloc < ntok && !full && (spaced == 0 || done == alloc))
            tok_valid <= 1'b1;
        // consumer
        rel_valid <= 1'b0;
        for (s = 0; s < NS; s = s + 1) begin
            if (!rdy[s]) seen[s] = 1'b0;
            if (rst_n && rdy[s] && !seen[s]) begin
                seen[s] = 1'b1;
                w = slot_tok[s];
                e = 0;
                for (q = 0; q < TOT; q = q + 1) begin
                    if (vmem[s * TOT + q] !== expm[w * TOT + q]) begin
                        e = e + 1;
                        if (errors + e <= 10)
                            $display("MISMATCH token %0d word %0d got %0128x exp %0128x", w, q,
                                     vmem[s * TOT + q], expm[w * TOT + q]);
                    end
                end
                errors = errors + e;
                words = words + TOT;
                lat_min = (cyc - t_alloc[w] < lat_min) ? cyc - t_alloc[w] : lat_min;
                lat_max = (cyc - t_alloc[w] > lat_max) ? cyc - t_alloc[w] : lat_max;
                lat_sum = lat_sum + (cyc - t_alloc[w]);
                if (prev_done >= 0) begin
                    gap_min = (cyc - prev_done < gap_min) ? cyc - prev_done : gap_min;
                    gap_max = (cyc - prev_done > gap_max) ? cyc - prev_done : gap_max;
                end
                prev_done = cyc;
                tlast = cyc;
                done = done + 1;
                rel_at[s] = cyc + cdel;
            end
            if (rel_at[s] >= 0 && cyc >= rel_at[s] && !rel_valid) begin
                rel_valid <= 1'b1; rel_tag <= s; rel_at[s] = -1;
            end
        end
        if (fault && rst_n && cyc > 6) faults = faults + 1;
        if (done == ntok && ntok > 0) begin
            $display("EG tokens=%0d words=%0d errors=%0d faults=%0d rom_over=%0d cycles=%0d beats=%0d lat_min=%0d lat_max=%0d lat_sum=%0d gap_min=%0d gap_max=%0d",
                     done, words, errors, faults, r_over, tlast - t0, beats_moved, lat_min, lat_max, lat_sum,
                     gap_min, gap_max);
            $finish;
        end
        if (cyc > 20000000) begin
            $display("EG TIMEOUT done=%0d alloc=%0d", done, alloc);
            $finish;
        end
    end
endmodule
