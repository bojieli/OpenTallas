`timescale 1ns/1ps
// Performance + bit-exactness bench of ot_hdc_v41x_idx_engine (the V4.1
// lightning indexer) against tools/hdc_golden_v41.py (chunk8), driven by
// tools/rtl_hdc_v41x_idx_campaign.py.
//   idx_q.mem    per token, IH lines {w[15:0], scales[NB*8], codes[NB*128]}
//   idx_n.mem    per token, its key count (32 bits)
//   idx_k.mem    per key {keep, key[NB*136]}
//   idx_e.mem    per key {fault, score[15:0]}
// Per token: load the query (IH cycles), stream the token's keys NK per beat
// (the last beat partial), wait for its last score, next token.
// Plusargs: NTOK, NKEY, SEED, BUBBLE (1/16ths of cycles the source withholds
// a beat), ORDY (1/16ths of cycles the sink refuses).  Reports keys, checked,
// errors, expected-and-raised faults, the accepted beats' span (first to last
// accept per token, summed), source-ready stalls, and the beat latency
// (accept to score beat valid) min/max.
module tb_hdc_v41x_idx #(
    parameter integer NK = 8,
    parameter integer IH = 32,
    parameter integer NB = 4,
    parameter integer FD = 64,
    parameter integer FPL = 3,              // engine arithmetic latencies (3/3/3 = as built)
    parameter integer FML = 3,
    parameter integer QL = 3,
    parameter integer MAXT = 4096,
    parameter integer MAXK = 1 << 20
) (input wire clk);
    localparam integer KW = NB * 136;
    localparam integer QW = 16 + NB * 8 + NB * 128;
    reg [QW-1:0] qm [0:MAXT*IH-1];
    reg [31:0]   nm [0:MAXT-1];
    reg [KW:0]   km [0:MAXK-1];
    reg [16:0]   em [0:MAXK-1];
    integer ntok = 0, nkey = 0, bubble = 0, ordy = 0;
    reg [31:0] seed = 32'h2468ace1, seed2 = 32'h1f2e3d4c;
    initial begin
        if (!$value$plusargs("NTOK=%d", ntok)) ntok = 0;
        if (!$value$plusargs("NKEY=%d", nkey)) nkey = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h2468ace1;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("ORDY=%d", ordy)) ordy = 0;
        seed2 = seed ^ 32'h5a5a1234;
        $readmemh("idx_q.mem", qm, 0, ntok * IH - 1);
        $readmemh("idx_n.mem", nm, 0, ntok - 1);
        $readmemh("idx_k.mem", km, 0, nkey - 1);
        $readmemh("idx_e.mem", em, 0, nkey - 1);
    end
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg rst_n = 1'b0;
    reg              ql_v = 1'b0;
    reg [7:0]        ql_head = 0;
    reg [NB*128-1:0] ql_codes = 0;
    reg [NB*8-1:0]   ql_sc = 0;
    reg [15:0]       ql_w = 0;
    reg              k_valid = 1'b0;
    wire             k_ready;
    reg [NK-1:0]     k_kv = 0, k_keep = 0;
    reg [NK*KW-1:0]  k_key = 0;
    wire             o_valid;
    reg              o_ready = 1'b0;
    wire [NK-1:0]    o_kv, o_fault;
    wire [NK*16-1:0] o_score;
    ot_hdc_v41x_idx_engine #(.NK(NK), .IH(IH), .NB(NB), .FD(FD), .FPL(FPL), .FML(FML), .QL(QL)) dut (
        .clk(clk), .rst_n(rst_n), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
        .ql_w(ql_w), .k_valid(k_valid), .k_ready(k_ready), .k_kv(k_kv), .k_keep(k_keep), .k_key(k_key),
        .o_valid(o_valid), .o_ready(o_ready), .o_kv(o_kv), .o_score(o_score), .o_fault(o_fault),
        .cnt_keys_scored(cnt_ks), .cnt_headsums_fused(cnt_hs), .cnt_faults(cnt_f));
    wire [47:0] cnt_ks, cnt_hs, cnt_f;

    // beat accept times (a ring, indexed by beat number)
    localparam integer RB = 1024;
    integer acc_t [0:RB-1];
    integer cyc = 0, st = 0, tok = 0, qh = 0, kbase = 0, knext = 0, kend = 0, kout = 0, kout_end = 0;
    integer beats_in = 0, beats_out = 0, errors = 0, checked = 0, faults_ok = 0, span = 0, stall = 0;
    integer lat, lat_min = 1 << 30, lat_max = 0, t_first = 0, t_last = 0, i, j, nfill, busy = 0;
    reg [16:0] e;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        // ---- sink ----
        if (rst_n) begin
            seed2 = xs(seed2);
            o_ready <= !(ordy > 0 && (seed2[7:4] < ordy));
        end
        if (o_valid && o_ready) begin
            lat = cyc - acc_t[beats_out % RB];
            if (lat < lat_min) lat_min = lat;
            if (lat > lat_max) lat_max = lat;
            for (j = 0; j < NK; j = j + 1) begin
                if (o_kv[j]) begin
                    e = em[kout];
                    checked = checked + 1;
                    if (e[16]) begin
                        if (o_fault[j]) faults_ok = faults_ok + 1;
                        else begin
                            errors = errors + 1;
                            if (errors <= 10) $display("MISS-FAULT key %0d got %h", kout, o_score[16*j +: 16]);
                        end
                    end else if (o_fault[j] || o_score[16*j +: 16] != e[15:0]) begin
                        errors = errors + 1;
                        if (errors <= 10) $display("MISMATCH key %0d got %h f%0d exp %h", kout,
                                                   o_score[16*j +: 16], o_fault[j], e[15:0]);
                    end
                    kout = kout + 1;
                end
            end
            beats_out = beats_out + 1;
        end
        // ---- source ----
        if (rst_n) begin
            ql_v <= 1'b0;
            case (st)
                0: begin                                   // next token: load q
                    if (tok >= ntok) st = 9;
                    else begin
                        ql_v <= 1'b1;
                        ql_head <= qh[7:0];
                        {ql_w, ql_sc, ql_codes} <= qm[tok * IH + qh];
                        if (qh == IH - 1) begin
                            qh = 0; st = 1;
                            kend = kbase + nm[tok];
                            knext = kbase;
                            t_first = -1;
                        end else qh = qh + 1;
                    end
                end
                1: begin                                   // stream keys
                    if (k_valid && k_ready) begin
                        acc_t[beats_in % RB] = cyc;
                        beats_in = beats_in + 1;
                        if (t_first < 0) t_first = cyc;
                        t_last = cyc;
                        knext = knext + nfill;
                    end else if (k_valid && !k_ready) stall = stall + 1;
                    if (knext >= kend) begin
                        k_valid <= 1'b0;
                        st = 2;
                    end else begin
                        seed = xs(seed);
                        if (bubble > 0 && seed[7:4] < bubble) k_valid <= 1'b0;
                        else begin
                            k_valid <= 1'b1;
                            nfill = (kend - knext >= NK) ? NK : kend - knext;
                            for (j = 0; j < NK; j = j + 1) begin
                                k_kv[j] <= (j < nfill);
                                k_keep[j] <= (j < nfill) ? km[knext + j][KW] : 1'b0;
                                k_key[j*KW +: KW] <= (j < nfill) ? km[knext + j][KW-1:0] : {KW{1'b0}};
                            end
                        end
                    end
                end
                2: begin                                   // drain the token
                    if (kout >= kend) begin
                        span = span + (t_last - t_first + 1);
                        kbase = kend;
                        tok = tok + 1;
                        st = 0;
                    end
                end
                default: begin
                    $display("V41XIDXCNT keys_scored=%0d headsums_fused=%0d faults=%0d", cnt_ks, cnt_hs, cnt_f);
                    $display("V41XIDX keys=%0d checked=%0d errors=%0d faults_expected_and_raised=%0d beats=%0d span=%0d stall=%0d lat_min=%0d lat_max=%0d cycles=%0d",
                             nkey, checked, errors, faults_ok, beats_in, span, stall, lat_min, lat_max, cyc);
                    $finish;
                end
            endcase
        end
        if (cyc > 200000000) begin
            $display("V41XIDX TIMEOUT keys=%0d checked=%0d", nkey, checked);
            $finish;
        end
    end
endmodule
