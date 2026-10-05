// Three-clock Verilator harness of tb_su_xing_top (the DS-ROM SU crossing: meso FIFO + 3:4 ratio FIFO each way).
// Time base ps (double).  One PLL: the hub's 1.2 GHz clock rises every 3 VCO ticks (TICK = 2500/9 ps) from 0, the
// 0.9 GHz serial clock every 4 ticks from +sph ticks (0..3); the field region's 1.2 GHz clock is the same frequency
// at a static phase +rph ps (0..T), the mesochronous region offset.  Coincident edges are one ideal edge.
// After every side is live: (1) sparse: one word at a time each way (random 0..6-cycle gaps), latency = source
// accept edge -> sink take edge; (2) burst: +burst words back to back each way, sink always ready: first-word
// latency, last-word arrival and the sink-side rate.  Every word is 512 bits {seq, 15 x hash(seq, i)}; delivery must
// be in order, gap-free and bit-exact, and no FIFO may fault.
#include "Vtb_su_xing_top.h"
#include "verilated.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static const double TICK = 2500.0 / 9.0, TF = 3 * TICK, TS = 4 * TICK;
static uint64_t rs_;
static uint32_t rnd() { rs_ ^= rs_ << 13; rs_ ^= rs_ >> 7; rs_ ^= rs_ << 17; return (uint32_t)(rs_ >> 11); }
static uint32_t hsh(uint32_t s, uint32_t i) { uint32_t h = s * 0x9E3779B1u ^ (i + 1) * 0xC2B2AE3Du; h ^= h >> 15; h *= 0x2C1B3C6Du; h ^= h >> 13; return h; }
static std::string arg(int argc, char** argv, const char* k, const char* d) {
    std::string p = std::string("+") + k + "=";
    for (int i = 1; i < argc; i++) if (!strncmp(argv[i], p.c_str(), p.size())) return argv[i] + p.size();
    return d;
}
static double now = 0;
double sc_time_stamp() { return now; }
static long errors = 0;
#define FAIL(...) do { if (errors < 10) { printf("ERROR t=%.1fps: ", now); printf(__VA_ARGS__); printf("\n"); } errors++; } while (0)

template <class Wd> static void put(Wd& w, uint32_t s) { w[0] = s; for (int i = 1; i < 16; i++) w[i] = hsh(s, i); }
template <class Wd> static bool chk(const Wd& w, uint32_t s) { if (w[0] != s) return false; for (int i = 1; i < 16; i++) if (w[i] != hsh(s, i)) return false; return true; }

struct Path {                       // one direction: source port in domain src, sink port in domain dst
    const char* name; long words = 0; uint32_t seq = 0, rseq = 0; bool pres = false; long gap = 0; bool inflight = false;
    std::vector<double> acc, lat; double first_take = -1, last_take = -1; long burst_takes = 0;
};

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const int sph = atoi(arg(argc, argv, "sph", "0").c_str());
    const double rph = atof(arg(argc, argv, "rph", "0").c_str());
    const long nsparse = atol(arg(argc, argv, "sparse", "2000").c_str());
    const long nburst = atol(arg(argc, argv, "burst", "160").c_str());
    rs_ = 0x9E3779B97F4A7C15ull ^ (uint64_t)atol(arg(argc, argv, "seed", "1").c_str()) * 0x100000001B3ull;
    Vtb_su_xing_top* d = new Vtb_su_xing_top;
    double th = 0, ts = sph * TICK, tr = rph;
    int rr = 12, rh = 12, rsl = 12;
    Path f{"f2s"}, s{"s2f"};
    int phase = 0;                  // 0 wait live, 1 sparse, 2 burst, 3 drain
    long live_edges = 0; double t_live = -1;
    bool fault = false;
    d->fclk_r = d->fclk_h = d->sclk = 0; d->rst_r_n = d->rst_h_n = d->rst_s_n = 0;
    d->a_v = d->b_v = 0; d->z_rdy = d->y_rdy = 1; d->eval();
    auto phase_words = [&](Path& p) { return phase == 1 ? nsparse : nburst; };
    for (long it = 0; it < 50000000; it++) {
        double t = std::min(th, std::min(ts, tr));
        now = t;
        bool eh = fabs(th - t) < 1e-3, es = fabs(ts - t) < 1e-3, er = fabs(tr - t) < 1e-3;
        // pre-edge samples: F2S source in r, sink in s; S2F source in s, sink in r
        bool af = er && d->a_v && d->a_rdy, zt = es && d->z_v && d->z_rdy;
        bool bf = es && d->b_v && d->b_rdy, yt = er && d->y_v && d->y_rdy;
        if (af) { f.acc.push_back(t); f.seq++; f.pres = false; }
        if (bf) { s.acc.push_back(t); s.seq++; s.pres = false; }
        if (zt) {
            if (!chk(d->z_d, f.rseq)) FAIL("f2s word %u corrupt / out of order (got seq %u)", f.rseq, (uint32_t)d->z_d[0]);
            if (f.rseq < f.acc.size()) f.lat.push_back(t - f.acc[f.rseq]);
            if (phase == 2) { if (f.first_take < 0) f.first_take = t; f.last_take = t; f.burst_takes++; }
            f.rseq++; f.inflight = false;
        }
        if (yt) {
            if (!chk(d->y_d, s.rseq)) FAIL("s2f word %u corrupt / out of order (got seq %u)", s.rseq, (uint32_t)d->y_d[0]);
            if (s.rseq < s.acc.size()) s.lat.push_back(t - s.acc[s.rseq]);
            if (phase == 2) { if (s.first_take < 0) s.first_take = t; s.last_take = t; s.burst_takes++; }
            s.rseq++; s.inflight = false;
        }
        d->fclk_h = eh; d->sclk = es; d->fclk_r = er; d->eval();
        if (d->fault) fault = true;
        auto drive = [&](Path& p, bool sparse_) {
            if (p.pres) return;
            if (p.seq >= (uint32_t)p.words) return;
            if (sparse_) { if (p.inflight) return; if (p.gap > 0) { p.gap--; return; } p.inflight = true; p.gap = rnd() % 7; }
            p.pres = true;
        };
        if (er) {
            if (rr > 0) rr--; d->rst_r_n = rr == 0;
            if (phase == 1 || phase == 2) drive(f, phase == 1);
            d->a_v = f.pres; if (f.pres) put(d->a_d, f.seq);
        }
        if (es) {
            if (rsl > 0) rsl--; d->rst_s_n = rsl == 0;
            if (phase == 1 || phase == 2) drive(s, phase == 1);
            d->b_v = s.pres; if (s.pres) put(d->b_d, s.seq);
        }
        if (eh) { if (rh > 0) rh--; d->rst_h_n = rh == 0; }
        d->eval();
        d->fclk_h = d->sclk = d->fclk_r = 0; d->eval();
        if (eh) th += TF;
        if (es) ts += TS;
        if (er) tr += TF;
        if (phase == 0) {
            if (d->live) { if (++live_edges > 64) { phase = 1; f.words = s.words = nsparse; t_live = t; } } else live_edges = 0;
            if (t > 2e6) { FAIL("never live"); break; }
        } else if (phase == 1) {
            if (f.rseq >= (uint32_t)nsparse && s.rseq >= (uint32_t)nsparse) {
                phase = 2; f.words = s.words = nsparse + nburst; f.inflight = s.inflight = false; f.gap = s.gap = 0;
            }
        } else if (phase == 2) {
            if (f.rseq >= (uint32_t)(nsparse + nburst) && s.rseq >= (uint32_t)(nsparse + nburst)) break;
        }
        if (t > 1e10) { FAIL("timeout"); break; }
    }
    if (fault) FAIL("FIFO fault");
    printf("RESULT sph=%d rph=%.1f t_live_ps=%.1f", sph, rph, t_live);
    for (Path* p : {&f, &s}) {
        double dst = p == &f ? TS : TF;
        if ((long)p->lat.size() < nsparse + nburst) { FAIL("%s delivered %zu of %ld", p->name, p->lat.size(), nsparse + nburst); continue; }
        std::vector<double> sp(p->lat.begin(), p->lat.begin() + nsparse);
        std::sort(sp.begin(), sp.end());
        double sum = 0; for (double v : sp) sum += v;
        double b0 = p->lat[nsparse], bl = p->lat[nsparse + nburst - 1];
        double rate = (p->burst_takes - 1) / ((p->last_take - p->first_take) / 1000.0);
        printf(" %s_sparse_ps=%.1f/%.1f/%.1f %s_sparse_dst=%.3f/%.3f/%.3f %s_burst_first_ps=%.1f %s_burst_last_ps=%.1f"
               " %s_burst_span_ps=%.1f %s_burst_words_per_ns=%.4f",
               p->name, sp.front(), sum / sp.size(), sp.back(), p->name, sp.front() / dst, sum / sp.size() / dst, sp.back() / dst,
               p->name, b0, p->name, bl, p->name, p->last_take - p->acc[nsparse], p->name, rate);
    }
    printf(" errors=%ld %s\n", errors, errors ? "FAIL" : "PASS");
    delete d;
    return errors ? 1 : 0;
}
