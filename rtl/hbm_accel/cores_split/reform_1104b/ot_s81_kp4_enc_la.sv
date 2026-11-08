`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_enc (s81-die-rtl-bind 2026-10-14, die item F10; STREAMING rewrite S81-KP4 2026-10-17): the transmit FEC of
// one S81 die link -- RS(544,514) "KP4" (GF(2^10), p = x^10 + x^3 + 1, g(x) = prod_{j=0..29} (x - alpha^j)), owner
// decision 2026-10-06: full KP4 FEC on every off-package link.  Reference model and frame: tools/s81_link/rs544.py.
//   in : one 512-b lane beat a cycle (the collective gearbox beat; the stream never stalls), tx_v = beat present
//   out: one 544-b PMA word a cycle: an FEC frame = 10 words = one codeword {header 20 = {AM 12'hA5C, seq 8},
//        10 beats, parity 30 symbols}; word w = codeword bits [5439 - 544 w -: 544]
// STRUCTURE (S81-KP4 10-17; replaces the A -> E -> O frame copies of 8cd04168b, whose 5,200-bit barrel window
// {60'b0, e_m} << 520 ph and 10:1 output select gave ph a fanout of 6,446, an 18-level setup path and 17,084 sinks):
//   * the parity LFSR runs ON THE ARRIVING STREAM: chunk k (52 symbols = 520 bits, 6 leading zero symbols in chunk 0)
//     lies inside {beat k-1, beat k} at a FIXED offset per k (8 k bits apart), so the window is a 10:1 one-hot select
//     over two registered beats (local wires, replicated select registers), never a barrel shifter;
//   * next rem = A rem ^ P0 ch[259:0] ^ P1 ch[519:260] (ot_s81_kp4_enc_mat.svh, tools/s81_link/gen_kp4_linear.py):
//     the two window parts are computed a cycle ahead and registered (wb), only A rem (<= 173 inputs) is in the loop;
//   * the beats wait in a 6-deep register delay line d0..d5; PMA word w is a 10:1 one-hot select over {d5, d4} at a
//     fixed offset per w (32 w bits apart; word 0 starts with the header, word 9 ends with the parity).
//   Schedule (fixed cycles, t_k = the cycle beat k sits in d0): chunk window ch at t_k + 1, wb at t_k + 3, rem after
//   chunk k at t_k + 4, parity par from t_9 + 5, PMA word w in p_d at t_k + 6.  RTL latency port -> p_d 7 cycles
//   (8cd04168b: 21).  Registers: ~6.4k (8cd04168b: 17.1k).  The tile adds one pin register per port (recipe 3/4).
// The PMA side runs continuously from the first full frame on (p_v); before it the PMA carries zero words (no AM:
// the receiver stays in hunt).  Every output leaves a flop.  Reset: regional synchronous tree, control only.
// MUT 1: parity symbol 7 inverted (the receive side must see a nonzero syndrome) -- bench mutant.
// ot_s81_kp4_enc_la (HBM-GAPS-3 2026-11-05): a copy of rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv (unchanged, S81/HEAD
// keep it) with parameter LA.  LA = 1 is that module cycle for cycle (bench: tb_kp4_enc_la.sv).  LA = 2 (default) advances the parity two chunks per
// state update, R_j = A^2 R_(j-1) ^ (A w_2j ^ w_(2j+1)) (ot_s81_kp4_enc_la2_mat.svh, gen_kp4_linear.py, self-checked vs
// rs544.py).  The state loop then has two cycles (registered partial sums of A^2 R, then one XOR level with v) instead
// of one cycle for A rem (the S81 enc tile closed TT +0.7 ps; HBM serdes_tx routed TT -180.76 on rem_q -> rem_q);
// v = A w_k ^ w_(k+1) is feed-forward.  Parity is ready one cycle later, so the PMA side reads one more beat stage
// (d6): port -> p_d latency 8 cycles (LA = 1: 7); the output stream is the LA = 1 stream delayed by exactly one cycle.
// ---------------------------------------------------------------------------------------------------------------
// FOLD (DIE-HEAD-85/TXF 2026-11-07, opt-in, LA = 2 + FF only; default 0 = the form above): A moves into the FF matrix.
// The 8 registered 65-bit window slices (fp) compute (A P) ch on an even chunk and P ch on an odd chunk
// (ot_s81_kp4_enc_ffa_mat.svh, gen_kp4_linear.py: fp = fb ^ (ev ? fa : fo), three disjoint masks), so wb = A w_2j then
// w_(2j+1) and v = wb_d ^ wb.  The l2_w cone (A on wb) and wp0..3 are gone; v holds the same value on every rem_q load,
// so p_v / p_d / fault are cycle-identical to FOLD = 0 (bench tb_kp4_enc_fold.sv).  Mutants: MUT 4 = one ev copy stuck
// at odd, MUT 5 = v without wb_d, MUT 6 = one even-only (fa) term inverted.  MUT 2 (constant flip of fq[0][0]) is an
// EQUIVALENT mutant under FOLD: a constant offset on wb cancels in v = wb_d ^ wb.
module ot_s81_kp4_enc_la #(parameter integer MUT = 0, parameter integer LA = 2, parameter integer FF = 0,
    // Opt-in local chunk capture: +1 output data/valid/fault cycle, unchanged II=1.
    parameter integer CH_STAGE = 0, parameter integer CH_MUT = 0, parameter integer FOLD = 0,
    parameter integer CH_REGION4 = 0, parameter integer CH_RELAY1 = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire [511:0]  tx_d,
    output wire          p_v,
    output reg  [543:0]  p_d,
    output wire          fault          // a cycle without a beat once the stream has started (sticky)
);
`include "ot_s81_gf1024.svh"
    // FF=1: four 65-input registered partials per half-matrix, then combine.
    // Supported on LA2; port -> p_d is 9 edges, exactly LA2 +1. Default unchanged.
    localparam integer FFS = (LA == 2 && FF != 0) ? 1 : 0;
    localparam integer CHS = (LA == 2 && FF != 0 && CH_STAGE != 0) ? 1 : 0;
    localparam integer FLD = (FFS != 0 && FOLD != 0) ? 1 : 0;
    // Optional conservative +1 PIN CYCLE. The chunk data relay is accompanied
    // by the same edge on all parity/word/header/valid/fault controls below.
    // The canonical default remains unchanged; II stays one beat per cycle.
    localparam integer REL = (CHS != 0 && CH_REGION4 != 0 && CH_RELAY1 != 0) ? 1 : 0;
    localparam integer NP = 30;
    localparam integer NRC = 4;          // chunk-select copies (130 window bits each)
    localparam integer NRO = 17;         // word-select copies (32 PMA bits each)
    wire [3:0] rs_n;
    ot_s81_kp4_rst #(.NL(4)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    // ---------------- input side: beat phase, header, beat delay line
    reg        run, flt;
    reg  [3:0] ph;                       // index of the beat arriving at the port
    reg  [7:0] seq;
    // h0 = {12'hA5C, seq of the frame in flight}: only the seq part is a register (HBM-GAPS-3 11-05: the constant
    // part as no-reset flops read X before the first frame; synthesis folded them, kit LEC could not prove them).
    reg  [7:0]  h0s;                     // seq of the frame whose beats are in flight (loaded with beat 0)
    wire [19:0] h0 = {12'hA5C, h0s};
    reg  [511:0] d0, d1, d2, d3, d4, d5, d6, d7, d8; // unused stages fold away
    reg  [511:0] d_bridge;             // optional midpoint of the input-to-data-bank flight
    wire       st = tx_v || run;         // a beat enters d0 this cycle
    (* keep *) reg [9:0] sk [0:NRC-1];   // one-hot beat index of d0 (zero = no beat), NRC copies
    always @(posedge clk) begin
        d0 <= tx_d; d_bridge <= d0;
        d1 <= REL ? d_bridge : d0;
        d2 <= d1; d3 <= d2; d4 <= d3; d5 <= d4; d6 <= d5; d7 <= d6; d8 <= d7;
        if (st && ph == 4'd0) h0s <= seq;
    end
    integer i;
    always @(posedge clk)
        if (!rs_n[0]) begin
            run <= 1'b0; flt <= 1'b0; ph <= 4'd0; seq <= 8'd0;
            for (i = 0; i < NRC; i = i + 1) sk[i] <= 10'd0;
        end else begin
            if (tx_v) run <= 1'b1;
            if (run && !tx_v) flt <= 1'b1;
            if (st) begin
                ph <= (ph == 4'd9) ? 4'd0 : ph + 1'b1;
                if (ph == 4'd0) seq <= seq + 1'b1;
            end
            for (i = 0; i < NRC; i = i + 1) sk[i] <= st ? (10'd1 << ph) : 10'd0;
        end
    // ---------------- chunk window: chunk k = {d1, d0}[591 - 8k -: 520]; chunk 0 = {60'b0, h0, d0[511:72]}
    // With the bridge, it is the old d1 epoch. Keep the chunk window on those
    // original consecutive beats while the PMA data path gains the extra edge.
    wire [1023:0] wd = {REL ? d_bridge : d1, d0};
    wire [519:0]  src [0:9];
    genvar gk, gb;
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_src
        if (gk == 0) begin : g0
            assign src[gk] = {60'b0, h0, d0[511:72]};
        end else begin : gn
            assign src[gk] = wd[591 - 8 * gk -: 520];
        end
    end endgenerate
    // CH_STAGE: the 10-way chunk mux drives one local D bank, not four distant
    // cq copies. Keep the new state boundary; cq fanout remains four.
    wire [519:0] ch_feed [0:3];
    wire [519:0] relay_feed [0:3];
    generate if (REL) begin : g_ch_relay
        // Each source-side relay owns one regional destination. These flops
        // split the original broadcast flight into two clocked hops.
        (* keep *) reg [519:0] q [0:3];
        for (genvar rr = 0; rr < 4; rr = rr + 1) begin : g_q
            always @(posedge clk) q[rr] <= ch_n;
            assign relay_feed[rr] = (CH_MUT == 8 && rr == 0) ? ch_n : q[rr];
        end
    end else begin : g_no_ch_relay
        for (genvar rr = 0; rr < 4; rr = rr + 1) begin : g_q
            assign relay_feed[rr] = ch_n;
        end
    end endgenerate
    // Four physical capture banks keep the existing CH_STAGE edge. Each bank
    // feeds only its own parity region, replacing the long four-region star.
    generate if (CHS && CH_REGION4 != 0) begin : g_ch_region
        (* keep *) reg [519:0] mid [0:3];
        for (genvar cr = 0; cr < 4; cr = cr + 1) begin : g_mid
            always @(posedge clk)
                mid[cr] <= relay_feed[cr] ^ ((CH_MUT == 6 || (CH_MUT == 7 && cr == 0)) ? 520'b1 : 520'b0);
            assign ch_feed[cr] = mid[cr];
        end
    end else if (CHS) begin : g_ch_stage
        (* keep *) reg [519:0] mid;
        always @(posedge clk) mid <= ch_n ^ ((CH_MUT == 6) ? 520'b1 : 520'b0);
        for (genvar cr = 0; cr < 4; cr = cr + 1) begin : g_feed
            assign ch_feed[cr] = mid;
        end
    end else begin : g_no_ch_stage
        for (genvar cr = 0; cr < 4; cr = cr + 1) begin : g_feed
            assign ch_feed[cr] = ch_n;
        end
    end endgenerate
    reg  [519:0] ch_q;
    wire [519:0] ch_n;
    generate for (gb = 0; gb < 520; gb = gb + 1) begin : g_chm
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = src[gk][gb];
        end
        assign ch_n[gb] = |(s & sk[gb / 130]);
    end endgenerate
    // ---------------- parity: window parts registered (wb), state loop rem
    wire [299:0] e_ar, e_p0, e_p1;
    reg  [299:0] rem_q, pp0, pp1, wb, par;
`include "ot_s81_kp4_enc_mat.svh"
    // Control flags follow the parity path; FF adds one stage before pp.
    // Non-FF flag indices retain the LA1/LA2 schedule below.
    reg  [5:0] f0, f9;                   // [0] = ch stage, [1] = pp stage, [2] = wb stage, [3] = rem (par load)
                                         // LA = 2: [3] = A w stage, [4] = rem after the pair (par load)
    reg  [4:0] fe;                       // LA = 2: even chunk (first of a pair), stages as f0[3:0]
    (* keep *) reg [3:0] f0w;            // chunk-0 flag at the wb stage, 4 copies (75 rem bits each)
    always @(posedge clk) begin
        ch_q <= ch_n;
        wb <= pp0 ^ pp1;
    end
    generate if (FFS) begin : g_ff
        // Four physical copies own disjoint 75-bit parity regions. They capture
        // the same chunk edge as ch_q and reduce the matrix input fanout by four.
        (* keep *) reg [519:0] cq [0:3];
        wire [299:0] fp [0:7];
        reg [299:0] fq [0:7];
        genvar r, c;
        for (r=0; r<4; r=r+1) begin : g_cq
            always @(posedge clk) cq[r] <= ch_feed[r];
        end
        if (FLD) begin : g_fold
            // ev[c][r]: the chunk in cq is even (first of a pair), one copy per (slice c, parity region r), captured
            // on the cq edge: CH_STAGE -> fe[0] (chunk in mid), else the d0 phase (chunk in ch_n).
            wire evn = CHS ? fe[REL] : (sk[0][0] | sk[0][2] | sk[0][4] | sk[0][6] | sk[0][8]);
            (* keep *) reg [3:0] ev [0:7];
            wire [299:0] fb [0:7];
            wire [299:0] fa [0:7];
            wire [299:0] fo [0:7];
            integer q;
            always @(posedge clk)
                if (!rs_n[1]) begin for (q = 0; q < 8; q = q + 1) ev[q] <= 4'd0; end
                else begin
                    for (q = 0; q < 8; q = q + 1) ev[q] <= {4{evn}};
                    if (MUT == 4) ev[5][3] <= 1'b0;
                end
`include "ot_s81_kp4_enc_ffa_mat.svh"
            for (c=0; c<8; c=c+1) begin : g_fsel
                for (genvar o=0; o<300; o=o+1) begin : g_o
                    assign fp[c][o] = fb[c][o] ^ (ev[c][o / 75] ? (fa[c][o] ^ ((MUT == 6 && c == 0 && o == 0) ? 1'b1 : 1'b0)) : fo[c][o]);
                end
            end
        end else begin : g_nofold
`include "ot_s81_kp4_enc_ff_mat.svh"
        end
        for (c=0; c<8; c=c+1) begin : g_fq
            always @(posedge clk) fq[c] <= fp[c] ^ ((MUT == 2 && c == 0) ? 300'b1 : 300'b0);
        end
        always @(posedge clk) begin
            pp0 <= fq[0] ^ fq[1] ^ fq[2] ^ fq[3];
            pp1 <= fq[4] ^ fq[5] ^ fq[6] ^ fq[7];
        end
    end else begin : g_nff
        always @(posedge clk) begin pp0 <= e_p0; pp1 <= e_p1; end
    end endgenerate
    always @(posedge clk)
        if (!rs_n[1]) begin f0 <= 6'd0; f9 <= 6'd0; fe <= 5'd0; f0w <= 4'd0; end
        else begin
            f0 <= {f0[4:0], sk[0][0]};
            f9 <= {f9[4:0], sk[0][9]};
            fe <= {fe[3:0], sk[0][0] | sk[0][2] | sk[0][4] | sk[0][6] | sk[0][8]};
            f0w <= {4{f0[1+FFS]}};
        end
    genvar gr;
    generate if (LA == 2) begin : g_la2
        // pair p = chunks (2p, 2p + 1).  wb = w_k at T_k = t_k + 3; wp = A w_k partials at T_k + 1; v = A w_k ^ w_(k+1)
        // at T_k + 2; rp = A^2 R partials (R stable two cycles); R written at T_2p + 2 when fv, from 0 at chunk 0 (f0v).
        wire [299:0] l2_r0, l2_r1, l2_r2, l2_r3, l2_w0, l2_w1, l2_w2, l2_w3;
`include "ot_s81_kp4_enc_la2_mat.svh"
        reg  [299:0] rp0, rp1, rp2, rp3, v;
        (* keep *) reg [3:0] fv, f0v;    // even-chunk / chunk-0 flag at the v stage, 4 copies (75 rem bits each)
        always @(posedge clk) begin
            rp0 <= l2_r0; rp1 <= l2_r1; rp2 <= l2_r2; rp3 <= l2_r3;
        end
        if (FLD) begin : g_vfold
            // wb = A w_k (even k) one cycle before w_(k+1): v = A w_k ^ w_(k+1) with no A cone here.
            reg [299:0] wbd;
            always @(posedge clk) begin
                wbd <= wb;
                v <= ((MUT == 5) ? 300'b0 : wbd) ^ wb;
            end
        end else begin : g_vwp
            reg [299:0] wp0, wp1, wp2, wp3;
            always @(posedge clk) begin
                wp0 <= l2_w0; wp1 <= l2_w1; wp2 <= l2_w2; wp3 <= l2_w3;
                v <= wp0 ^ wp1 ^ wp2 ^ wp3 ^ wb;
            end
        end
        if (CHS) begin : g_ch_flags
            // mid has the old flag-bank semantics, including synchronous reset.
            // Final flags are pure one-edge delays, so reset edges shift too.
            (* keep *) reg [3:0] f0_mid, fv_mid;
            (* keep *) reg [3:0] f0_relay, fv_relay;
            always @(posedge clk) begin
                if (!rs_n[1]) begin fv_mid <= 4'd0; f0_mid <= 4'd0; end
                else begin fv_mid <= {4{fe[3+FFS]}}; f0_mid <= {4{f0[3+FFS]}}; end
                fv_relay <= fv_mid; f0_relay <= f0_mid;
                fv <= (CH_MUT == 2) ? {4{fe[3+FFS]}} : (REL ? fv_relay : fv_mid);
                f0v <= (CH_MUT == 1) ? {4{f0[3+FFS]}} : (REL ? f0_relay : f0_mid);
            end
        end else begin : g_original_flags
            always @(posedge clk)
                if (!rs_n[1]) begin fv <= 4'd0; f0v <= 4'd0; end
                else begin fv <= {4{fe[3+FFS]}}; f0v <= {4{f0[3+FFS]}}; end
        end
        for (gr = 0; gr < 300; gr = gr + 1) begin : g_rem
            always @(posedge clk)
                if (fv[gr / 75]) rem_q[gr] <= (f0v[gr / 75] ? 1'b0 : (rp0[gr] ^ rp1[gr] ^ rp2[gr] ^ rp3[gr])) ^ v[gr];
        end
    end else begin : g_la1
        for (gr = 0; gr < 300; gr = gr + 1) begin : g_rem
            always @(posedge clk) rem_q[gr] <= (f0w[gr / 75] ? 1'b0 : e_ar[gr]) ^ wb[gr];
        end
    end endgenerate
    // parity of the frame: rem after chunk 9, rem[0] (rem_q[9:0], the x^29 side) transmitted first (MUT 1: symbol 7
    // inverted)
    wire [299:0] rem_tx;
    generate for (gr = 0; gr < NP; gr = gr + 1) begin : g_ptx
        assign rem_tx[299 - 10 * gr -: 10] = rem_q[10 * gr +: 10] ^ ((MUT == 1 && gr == 7) ? 10'h3FF : 10'h000);
    end endgenerate
    wire par_load_base = (LA == 2) ? f9[4+((MUT == 3) ? 0 : FFS)] : f9[3];
    reg par_load_mid;
    reg par_load_relay;
    always @(posedge clk) par_load_mid <= par_load_base;
    always @(posedge clk) par_load_relay <= par_load_mid;
    wire par_load = (CHS && CH_MUT != 3) ? (REL ? par_load_relay : par_load_mid) : par_load_base;
    always @(posedge clk) if (par_load) par <= rem_tx;
    // ---------------- PMA words: word w = {d5, d4} at a fixed offset (cycle t_w + 5; d5 = beat w, d4 = beat w + 1)
    reg  [9:0] so [0:6];                 // one-hot beat index delayed 1..7 (so[4]/[5]/[6] = d5/d6/d7)
    (* keep *) reg [9:0] sw [0:NRO-1];   // so[3] delayed once more: the word select at the d5 stage, NRO copies
    reg        o_v, p_v_internal;
    wire [9:0] sw_use [0:NRO-1];
    generate if (CHS) begin : g_ch_out
        (* keep *) reg [9:0] sw_mid [0:NRO-1];
        (* keep *) reg [9:0] sw_relay [0:NRO-1];
        reg pv_mid, fault_mid;
        reg pv_relay, fault_relay;
        for (genvar r = 0; r < NRO; r = r + 1) begin : g_sw_mid
            always @(posedge clk) begin sw_mid[r] <= sw[r]; sw_relay[r] <= sw_mid[r]; end
            assign sw_use[r] = REL ? sw_relay[r] : sw_mid[r];
        end
        always @(posedge clk) begin
            pv_mid <= p_v_internal; fault_mid <= flt;
            pv_relay <= pv_mid; fault_relay <= fault_mid;
        end
        assign p_v = (CH_MUT == 5) ? p_v_internal : (REL ? pv_relay : pv_mid);
        assign fault = REL ? fault_relay : fault_mid;
    end else begin : g_original_out
        for (genvar r = 0; r < NRO; r = r + 1) begin : g_sw_orig
            assign sw_use[r] = sw[r];
        end
        assign p_v = p_v_internal;
        assign fault = flt;
    end endgenerate
    always @(posedge clk)
        if (!rs_n[2]) begin
            for (i = 0; i < 7; i = i + 1) so[i] <= 10'd0;
            for (i = 0; i < NRO; i = i + 1) sw[i] <= 10'd0;
            o_v <= 1'b0; p_v_internal <= 1'b0;
        end else begin
            so[0] <= sk[1]; so[1] <= so[0]; so[2] <= so[1]; so[3] <= so[2]; so[4] <= so[3]; so[5] <= so[4]; so[6] <= so[5];
            for (i = 0; i < NRO; i = i + 1) sw[i] <= (LA == 2) ? so[4+FFS] : so[3];
            if ((LA == 2) ? so[5+FFS][0] : so[4][0]) o_v <= 1'b1;
            p_v_internal <= o_v || ((LA == 2) ? so[5+FFS][0] : so[4][0]);
        end
    // LA1: {d5,d4}; LA2: {d6,d5}; LA2+FF: {d7,d6}. FF moves parity and the PMA phase together.
    wire [511:0]  oa = CHS ? d8 : (FFS ? d7 : ((LA == 2) ? d6 : d5));
    wire [511:0]  ob = CHS ? d7 : (FFS ? d6 : ((LA == 2) ? d5 : d4));
    reg [7:0] h0s_out_mid;
    reg [7:0] h0s_out_relay;
    always @(posedge clk) h0s_out_mid <= h0s;
    always @(posedge clk) h0s_out_relay <= h0s_out_mid;
    wire [19:0] h0_out = (CHS && CH_MUT != 4) ? {12'hA5C, (REL ? h0s_out_relay : h0s_out_mid)} : h0;
    wire [1023:0] wo = {oa, ob};
    wire [543:0]  wsrc [0:9];
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_wsrc
        if (gk == 0) begin : g0
            assign wsrc[gk] = {h0_out, oa, ob[511:500]};
        end else if (gk == 9) begin : g9
            assign wsrc[gk] = {oa[243:0], par};
        end else begin : gn
            assign wsrc[gk] = wo[1043 - 32 * gk -: 544];
        end
    end endgenerate
    generate for (gb = 0; gb < 544; gb = gb + 1) begin : g_om
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = wsrc[gk][gb];
        end
        always @(posedge clk) p_d[gb] <= |(s & sw_use[gb / 32]);
    end endgenerate
endmodule
