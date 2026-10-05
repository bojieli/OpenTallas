// Verilator harness of rtl/test/qwen_sys/ot_qwen_nearhbm_sys_tb.sv (derived from rtl/test/nearhbm/tb_qwen_nearhbm_attn.cpp):
// the near-HBM attention subsystem with link-layer hub<->stack links and the HBM-service-clock crossing, exact against
// the golden (tools/qwen_nearhbm_attn_ref.py vectors).  Two clocks: clk (engine) at 1200 MHz, hclk (HBM controller,
// CK/2) at 976.5625 MHz, unrelated phases.  The HBM is modelled on hclk: per-engine in-order request queues, a byte
// bucket of BPC bytes per hclk cycle per stack (981 = 0.958 TB/s, the streaming controller's measured worst layer),
// one row per engine per hclk cycle, LAT hclk cycles of latency.
//   ./Vtb <vector dir> [hbm_latency=16] [bytes_per_hclk=981] [max_cycles=400000] [flip_period=0]
#include "Vot_qwen_nearhbm_sys_tb.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fstream>
#include <string>
#include <vector>

#ifndef NHB_R
#define NHB_R 1
#endif
#ifndef NHB_HD
#define NHB_HD 128
#endif
static const int R = NHB_R, HD = NHB_HD, NH = 8;

template <typename T> static uint64_t gbits(const T& v, int off, int w) { return (uint64_t(v) >> off) & ((w == 64) ? ~0ull : ((1ull << w) - 1)); }
static uint64_t gbits(const uint32_t* v, int off, int w) {
    uint64_t r = 0;
    for (int i = 0; i < w; i++) if ((v[(off + i) / 32] >> ((off + i) % 32)) & 1) r |= 1ull << i;
    return r;
}
static void sbit_words(uint32_t* v, int off, int w, uint64_t x) {
    for (int i = 0; i < w; i++) {
        int b = off + i;
        if ((x >> i) & 1) v[b / 32] |= 1u << (b % 32); else v[b / 32] &= ~(1u << (b % 32));
    }
}
template <typename T> static void sbits(T& v, int off, int w, uint64_t x) {
    uint64_t m = ((w == 64) ? ~0ull : ((1ull << w) - 1)) << off;
    v = (T)((uint64_t(v) & ~m) | ((x << off) & m));
}
static void sbits(uint32_t* v, int off, int w, uint64_t x) { sbit_words(v, off, w, x); }
template <std::size_t N> static uint64_t gbits(const VlWide<N>& v, int off, int w) { return gbits(v.data(), off, w); }
template <std::size_t N> static void sbits(VlWide<N>& v, int off, int w, uint64_t x) { sbit_words(v.data(), off, w, x); }

struct Req { int v, g, t; };
struct Rsp { uint64_t at; int v, g, t; };

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 2) { fprintf(stderr, "usage: Vtb DIR [lat] [bpc] [maxcyc]\n"); return 2; }
    std::string dir = argv[1];
    int LAT = argc > 2 ? atoi(argv[2]) : 16;
    int BPC = argc > 3 ? atoi(argv[3]) : 981;
    uint64_t MAXC = argc > 4 ? strtoull(argv[4], 0, 10) : 400000;
    int FLIP = argc > 5 ? atoi(argv[5]) : 0;
    // vectors
    int T = 0;
    {
        std::ifstream m(dir + "/meta.json");
        std::string s((std::istreambuf_iterator<char>(m)), std::istreambuf_iterator<char>());
        size_t p = s.find("\"ctx\":");
        T = atoi(s.c_str() + p + 6);
    }
    std::vector<uint16_t> q;
    { std::ifstream f(dir + "/q.hex"); std::string l; while (f >> l) q.push_back((uint16_t)strtoul(l.c_str(), 0, 16)); }
    std::vector<std::vector<uint8_t>> kv[2];     // [v][t*2+g] -> HD bytes
    {
        std::ifstream f(dir + "/kv.hex"); std::string l; int n = 0;
        while (f >> l) {
            std::vector<uint8_t> row(HD);
            for (int d = 0; d < HD; d++) row[d] = (uint8_t)strtoul(l.substr(2 * (HD - 1 - d), 2).c_str(), 0, 16);
            kv[n < 2 * T ? 0 : 1].push_back(row); n++;
        }
    }
    std::vector<uint32_t> gold;
    { std::ifstream f(dir + "/gold.hex"); std::string l; while (f >> l) gold.push_back((uint32_t)strtoul(l.c_str(), 0, 16)); }
    if ((int)q.size() != NH * HD || (int)kv[0].size() != 2 * T || (int)kv[1].size() != 2 * T || (int)gold.size() != NH * HD) {
        fprintf(stderr, "bad vectors q=%zu k=%zu v=%zu gold=%zu T=%d\n", q.size(), kv[0].size(), kv[1].size(), gold.size(), T);
        return 2;
    }

    Vot_qwen_nearhbm_sys_tb* top = new Vot_qwen_nearhbm_sys_tb;
    uint64_t cyc = 0, hcyc = 0;
    // time in fs: clk 833,333 fs, hclk 1,024,000 fs; hclk starts 300 ps late (unrelated phase)
    const uint64_t CP = 833333, HP = 1024000;
    uint64_t t_clk = CP, t_hclk = 300000;
    // advance to the next edge; returns which clocks rose (bit 0 clk, bit 1 hclk)
    auto step = [&]() {
        uint64_t t = std::min(t_clk, t_hclk);
        int which = (t_clk == t ? 1 : 0) | (t_hclk == t ? 2 : 0);
        top->clk = 0; top->hclk = 0; top->eval();
        top->clk = (which & 1) ? 1 : 0; top->hclk = (which & 2) ? 1 : 0; top->eval();
        if (which & 1) { t_clk += CP; cyc++; }
        if (which & 2) { t_hclk += HP; hcyc++; }
        return which;
    };
    auto tick = [&]() { while (!(step() & 1)) {} };       // to the next clk edge
    top->rst_n = 0; top->hrst_n = 0; top->start = 0; top->T = T; top->q_valid = 0; top->flip_period = FLIP;
    for (int i = 0; i < 8; i++) tick();
    top->rst_n = 1; top->hrst_n = 1; tick();
    // link training: every hub<->stack link up before the layer starts
    { uint64_t c0 = cyc; while (!top->links_up) { tick(); if (cyc - c0 > 100000) { fprintf(stderr, "links never up\n"); return 4; } } }
    for (int i = 0; i < 16; i++) tick();

    std::deque<Req> rq[4 * R];
    std::deque<Rsp> pend[4 * R];
    double tok[4] = {0, 0, 0, 0};
    int rr[4] = {0, 0, 0, 0};
    std::vector<uint32_t> out(NH * HD, 0xDEADBEEF);
    std::vector<int> got(NH * HD, 0);
    int nout = 0;
    // events
    const int NEV = 16;
    int64_t ev_first[4][NEV], hub_first[8];
    for (int s = 0; s < 4; s++) for (int b = 0; b < NEV; b++) ev_first[s][b] = -1;
    for (int b = 0; b < 8; b++) hub_first[b] = -1;
    int64_t row_first[4][2], row_last[4][2];
    for (int s = 0; s < 4; s++) for (int v = 0; v < 2; v++) { row_first[s][v] = -1; row_last[s][v] = -1; }
    int64_t out_first = -1, out_last = -1;
    uint64_t t0 = cyc;
    int fault = 0;
    uint64_t served = 0;
    // start + q beats (32 BF16 per beat)
    const int NQB = NH * HD * 16 / 512;
    int qb = -1;
    while (cyc - t0 < MAXC && nout < NH * HD) {
        // inputs for this edge
        top->start = (qb == -1);
        top->q_valid = (qb >= 0 && qb < NQB);
        if (top->q_valid) {
            top->q_beat = qb;
            for (int i = 0; i < 32; i++) sbits(top->q_data, 16 * i, 16, q[32 * qb + i]);
        }
        qb++;
        // advance to the next clk edge, serving the HBM on every hclk edge on the way
        for (;;) {
            uint64_t t = std::min(t_clk, t_hclk);
            bool h = (t_hclk == t);
            if (h) {
                // responses due at this hclk edge (one per engine)
                for (int x = 0; x < 4 * R; x++) {
                    if (!pend[x].empty() && pend[x].front().at <= hcyc) {
                        Rsp r = pend[x].front(); pend[x].pop_front();
                        sbits(top->rsp_valid, x, 1, 1);
                        const std::vector<uint8_t>& row = kv[r.v][2 * r.t + r.g];
                        for (int d = 0; d < HD; d++) sbits(top->rsp_data, (x * HD + d) * 8, 8, row[d]);
                    } else sbits(top->rsp_valid, x, 1, 0);
                }
            }
            int which = step();
            if (which & 2) {
                uint64_t now = cyc - t0;
                // requests out of the crossing at this hclk edge
                for (int x = 0; x < 4 * R; x++)
                    if (gbits(top->req_valid, x, 1)) {
                        Req r{(int)gbits(top->req_v, x, 1), (int)gbits(top->req_g, x, 1), (int)gbits(top->req_t, 13 * x, 13)};
                        if (r.t >= T || ((r.t % 512) / 128) != x / R) { fprintf(stderr, "bad request t=%d T=%d x=%d\n", r.t, T, x); return 3; }
                        rq[x].push_back(r);
                    }
                // service: byte bucket per stack per hclk cycle, round robin, one row per engine per hclk cycle
                for (int s = 0; s < 4; s++) {
                    tok[s] += BPC;
                    if (tok[s] > BPC + HD) tok[s] = BPC + HD;
                    for (int k = 0; k < R; k++) {
                        int x = s * R + (rr[s] + k) % R;
                        if (rq[x].empty() || tok[s] < HD) continue;
                        Req r = rq[x].front(); rq[x].pop_front();
                        tok[s] -= HD;
                        pend[x].push_back(Rsp{hcyc + (uint64_t)LAT, r.v, r.g, r.t});
                        served++;
                        if (row_first[s][r.v] < 0) row_first[s][r.v] = now;
                        row_last[s][r.v] = now;
                    }
                    rr[s] = (rr[s] + 1) % R;
                }
            }
            if (which & 1) break;
        }
        uint64_t now = cyc - t0;
        // events
        for (int s = 0; s < 4; s++)
            for (int b = 0; b < NEV; b++)
                if (ev_first[s][b] < 0 && gbits(top->ev_stack, 16 * s + b, 1)) ev_first[s][b] = now;
        for (int b = 0; b < 8; b++) if (hub_first[b] < 0 && ((top->ev_hub >> b) & 1)) hub_first[b] = now;
        if (top->fault) fault |= top->fault;
        if (top->sys_fault) fault |= 32;
        if (top->out_valid) {
            int g = top->out_g, beat = top->out_beat;
            int bph = HD / 16, h = 4 * g + beat / bph, d0 = (beat % bph) * 16;
            for (int l = 0; l < 16; l++) {
                int i = h * HD + d0 + l;
                out[i] = (uint32_t)gbits(top->out_data, 32 * l, 32);
                got[i]++; nout++;
            }
            if (out_first < 0) out_first = now;
            out_last = now;
        }
    }
    int mism = 0, first_bad = -1;
    for (int i = 0; i < NH * HD; i++) if (got[i] != 1 || out[i] != gold[i]) { if (first_bad < 0) first_bad = i; mism++; }
    // phase marks (latest stack)
    auto mx = [&](int b) { int64_t m = -1; for (int s = 0; s < 4; s++) if (ev_first[s][b] > m) m = ev_first[s][b]; return m; };
    auto mn = [&](int b) { int64_t m = -1; for (int s = 0; s < 4; s++) if (ev_first[s][b] >= 0 && (m < 0 || ev_first[s][b] < m)) m = ev_first[s][b]; return m; };
    int64_t kf = -1, kl = -1, vf = -1, vl = -1;
    for (int s = 0; s < 4; s++) {
        if (row_first[s][0] >= 0 && (kf < 0 || row_first[s][0] < kf)) kf = row_first[s][0];
        if (row_last[s][0] > kl) kl = row_last[s][0];
        if (row_first[s][1] >= 0 && (vf < 0 || row_first[s][1] < vf)) vf = row_first[s][1];
        if (row_last[s][1] > vl) vl = row_last[s][1];
    }
    printf("{\"ctx\": %d, \"R\": %d, \"HD\": %d, \"hbm_latency\": %d, \"bytes_per_cycle\": %d, "
           "\"outputs\": %d, \"mismatches\": %d, \"first_bad\": %d, \"fault\": %d, \"exact\": %s, "
           "\"cycles_total\": %lld, \"rows_served\": %llu, \"flip_period\": %d, \"link_crc_errors\": %u, \"link_replays\": %u, "
           "\"marks\": {\"q_ready\": %lld, \"k_first_issue\": %lld, \"k_rows_served_first\": %lld, \"k_rows_served_last\": %lld, "
           "\"k_consumed_all\": %lld, \"kdone_g0\": %lld, \"kdone_g1\": %lld, \"exp_first\": %lld, \"exp_done_g0\": %lld, "
           "\"exp_done_g1\": %lld, \"v_first_issue\": %lld, \"v_rows_served_first\": %lld, \"v_rows_served_last\": %lld, "
           "\"v_issued_all\": %lld, \"last_leaf\": %lld, \"pv_first_beat\": %lld, \"hub_M_sent\": %lld, "
           "\"hub_rz_ok_g0\": %lld, \"hub_rz_ok_g1\": %lld, \"out_first\": %lld, \"out_last\": %lld}}\n",
           T, R, HD, LAT, BPC, nout, mism, first_bad, fault, (mism == 0 && fault == 0 && nout == NH * HD) ? "true" : "false",
           (long long)out_last, (unsigned long long)served, FLIP, (unsigned)top->crc_errors, (unsigned)top->replays,
           (long long)mx(8), (long long)mn(9), (long long)kf, (long long)kl, (long long)mx(5), (long long)mx(11),
           (long long)mx(12), (long long)mn(13), (long long)mx(6), (long long)mx(7), (long long)mn(10), (long long)vf,
           (long long)vl, (long long)mx(4), (long long)mx(15), (long long)mx(14), (long long)hub_first[1],
           (long long)hub_first[4], (long long)hub_first[5], (long long)out_first, (long long)out_last);
    if (mism && first_bad >= 0)
        fprintf(stderr, "first mismatch at %d (h %d d %d): rtl %08x gold %08x\n", first_bad, first_bad / HD, first_bad % HD,
                out[first_bad], gold[first_bad]);
    top->final();
    delete top;
    return (mism == 0 && fault == 0) ? 0 : 1;
}
