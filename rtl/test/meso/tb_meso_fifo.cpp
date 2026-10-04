// Dual-clock Verilator bench of ot_meso_fifo (rtl/common/ot_meso_fifo.sv), built with -DOT_MESO_DEBUG.
// Time base: picoseconds (double).  Both clocks have period T = 833.333 ps (1.2 GHz).  The read clock's rising edges
// sit at m*T + PHASE + wander(m) + jitter; the write clock's at n*T + jitter.  Wander is a slow sinusoid of
// amplitude +wander (ps) and period +wperiod (cycles); +drift (ps a cycle) adds an unbounded ramp (fault test).
// Edges of the two clocks closer than +meta ps are processed in random order (a metastable sample resolving
// either way); this is DIGITAL ONLY, not an MTBF or analog phase-window proof.
//
// Physical window checker (both rings): at every rising edge where a ring's reader is placed and not faulted, the
// slot it consumes must hold the write of exactly the expected counter value, written >= +lagmin ps earlier (the
// STA budget of the data arcs); and a write must never land within +holdps after a consuming edge of that slot.
// Scoreboard: every word {epoch, seq, hash x 14} is checked bit-exact; within a writer epoch delivery is in order
// from seq 0 without gap; epochs strictly increase; the last epoch drains completely; no fault unless +expfault=1,
// and with +expfault=1 the fault must come before any window violation.
// Latency (sparse mode): accept edge -> consumer take edge, in periods; the register stage replaced is 1 period.
#include "Vot_meso_fifo.h"
#include "verilated.h"
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <map>

static const double T = 1e12 / 1.2e9;
static uint64_t rs_;
static uint32_t rnd() { rs_ ^= rs_ << 13; rs_ ^= rs_ >> 7; rs_ ^= rs_ << 17; return (uint32_t)(rs_ >> 11); }
static double urand() { return (rnd() & 0xFFFFFF) / double(0x1000000); }
static bool chance(double p) { return urand() < p; }
static uint32_t hsh(uint32_t e, uint32_t s, uint32_t i) {
    uint32_t h = e * 0x9E3779B1u ^ s * 0x85EBCA77u ^ (i + 1) * 0xC2B2AE3Du;
    h ^= h >> 15; h *= 0x2C1B3C6Du; h ^= h >> 13; h *= 0x297A2D39u; h ^= h >> 16; return h;
}
static std::string arg(int argc, char** argv, const char* k, const char* d) {
    std::string p = std::string("+") + k + "=";
    for (int i = 1; i < argc; i++) if (!strncmp(argv[i], p.c_str(), p.size())) return argv[i] + p.size();
    return d;
}
static double now = 0;
double sc_time_stamp() { return now; }
static long errors = 0, window_viol = 0;
#define FAIL(...) do { if (errors < 10) { printf("ERROR t=%.1fps: ", now); printf(__VA_ARGS__); printf("\n"); } errors++; } while (0)

#ifndef DEPTH_
#define DEPTH_ 4
#endif
static const int D = DEPTH_;
static const int NW = 16;   // 512 / 32

struct Ring {               // physical window bookkeeping for one ring
    double t_wr[64]; int cnt_wr[64]; double t_rd[64];
    double min_lag = 1e18, max_lag = -1e18; long checks = 0;
    void init() { for (int i = 0; i < 64; i++) { t_wr[i] = -1e18; cnt_wr[i] = -1; t_rd[i] = -1e18; } }
};

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    const std::string mode = arg(argc, argv, "mode", "random");
    const long cycles = atol(arg(argc, argv, "cycles", "200000").c_str());
    rs_ = 0x9E3779B97F4A7C15ull ^ (uint64_t)atol(arg(argc, argv, "seed", "1").c_str()) * 0x100000001B3ull;
    const double phase = atof(arg(argc, argv, "phase", "0").c_str());          // ps, 0..T
    const double wander = atof(arg(argc, argv, "wander", "0").c_str());        // ps amplitude
    const double wperiod = atof(arg(argc, argv, "wperiod", "50000").c_str());  // cycles
    const double drift = atof(arg(argc, argv, "drift", "0").c_str());          // ps a cycle
    const double jitter = atof(arg(argc, argv, "jitter", "5").c_str());        // ps peak, uniform
    const double meta = atof(arg(argc, argv, "meta", "20").c_str());
    const double lagmin = atof(arg(argc, argv, "lagmin", "356.667").c_str());  // T/2 - 60 ps
    const double holdps = atof(arg(argc, argv, "holdps", "60").c_str());
    const int expfault = atoi(arg(argc, argv, "expfault", "0").c_str());
    const int credits = atoi(arg(argc, argv, "credits", "8").c_str());
    const std::string wph = arg(argc, argv, "wph", "rand");                   // wander phase at cycle 0 (rad)
    const double wphase0 = wph == "rand" ? urand() * 2 * M_PI : atof(wph.c_str());

    double pw = 0.7, pr = 0.7, preset = 0; bool sparse = false, stream = false, bp = false;
    if (mode == "sparse") sparse = true;
    else if (mode == "stream") { stream = true; pw = 1; pr = 1; }
    else if (mode == "random") { pw = 0.7; pr = 0.7; }
    else if (mode == "bp") bp = true;
    else if (mode == "reset") { pw = 0.8; pr = 0.8; preset = 0.0005; }
    else if (mode == "drift") { pw = 0.8; pr = 0.9; }
    else { printf("bad mode\n"); return 2; }

    Vot_meso_fifo* d = new Vot_meso_fifo;
    Ring dr, cr; dr.init(); cr.init();
    // writer bench state
    int wrst_left = 7, rrst_left = 9;
    uint32_t w_epoch = 0, w_seq = 0; bool w_live_prev = false;
    std::map<uint32_t, uint32_t> acc_per_epoch;
    std::vector<double> t_acc;           // accept time per seq of the current epoch (sparse latency)
    // reader bench state
    long r_last_e = -1, r_last_s = -1, delivered = 0, accepted = 0, resets = 0;
    std::map<uint32_t, uint32_t> del_per_epoch;
    std::vector<double> lat; std::map<int, long> lat_edges;
    long take_cycles = 0, takes = 0, first_take_cyc = -1;
    double t_fault = -1, t_first_viol = -1;
    double d_lag0 = -1, c_lag0 = -1;     // first in-window lag after placement (static phase placement)
    int bp_burst = 0; bool bp_rdy = true; int sparse_gap = 0;
    long wcyc = 0, rcyc = 0;
    bool draining = false; long drain_at = cycles; long end_at = cycles + 400;
    long r_edges_since = 0;  // rising read edges counter for edge-count latency
    std::vector<long> acc_redge;

    d->wclk = 0; d->rclk = 0; d->wrst_n = 0; d->rrst_n = 0; d->w_v = 0; d->r_rdy = 0;
    for (int i = 0; i < NW; i++) d->w_d[i] = 0;
    d->eval();

    auto wrise_t = [&](long n) { return n * T + (urand() * 2 - 1) * jitter; };
    auto rrise_t = [&](long m) {
        double wv = wander * sin(2 * M_PI * m / wperiod + wphase0) + drift * m;
        return m * T + phase + T + wv + (urand() * 2 - 1) * jitter;   // + T keeps the first read edge positive
    };
    double tw_r = wrise_t(0), tw_f = tw_r + T / 2, tr_r = rrise_t(0), tr_f = tr_r + T / 2;
    bool w_hi = false, r_hi = false;   // next event of each clock: rise when low, fall when high

    auto set_wd = [&]() {
        d->w_d[0] = w_seq; d->w_d[1] = w_epoch;
        for (int i = 2; i < NW; i++) d->w_d[i] = hsh(w_epoch, w_seq, i);
    };
    set_wd();

    while (wcyc < end_at && rcyc < end_at) {
        double tw = w_hi ? tw_f : tw_r, tr = r_hi ? tr_f : tr_r;
        bool do_w = tw <= tr;
        if (fabs(tw - tr) < meta) do_w = chance(0.5);
        if (do_w) {
            now = tw;
            if (!w_hi) {           // ---------------- write rising edge
                bool fire = d->w_v && d->w_rdy;
                bool run_ring = true;                  // rings are free-running
                int wc = d->dbg_wc;
                bool c_on = d->dbg_ws == 3 || d->dbg_ws == 2;
                int cp = d->dbg_cp;
                bool wf = d->w_fault;
                // credit ring consumption check (reader = write side)
                if (c_on && !wf) {
                    int idx = cp & (D - 1);
                    double lag = now - cr.t_wr[idx];
                    cr.checks++;
                    if (cr.cnt_wr[idx] != cp || lag < lagmin) {
                        window_viol++; if (t_first_viol < 0) t_first_viol = now;
                        if (!expfault) FAIL("credit ring window: slot %d holds cnt %d want %d lag %.1f", idx, cr.cnt_wr[idx], cp, lag);
                    } else { if (lag < cr.min_lag) cr.min_lag = lag; if (lag > cr.max_lag) cr.max_lag = lag; if (c_lag0 < 0) c_lag0 = lag; }
                    cr.t_rd[idx] = now;
                }
                if (run_ring) {    // data ring write: hold check against the last consuming read edge
                    int idx = wc & (D - 1);
                    if (now - dr.t_rd[idx] < holdps) {
                        window_viol++; if (t_first_viol < 0) t_first_viol = now;
                        if (!expfault) FAIL("data ring hold: slot %d rewritten %.1f ps after read", idx, now - dr.t_rd[idx]);
                    }
                    dr.t_wr[idx] = now; dr.cnt_wr[idx] = wc;
                }
                if (fire) {
                    accepted++; acc_per_epoch[w_epoch]++;
                    if (sparse) { t_acc.push_back(now); acc_redge.push_back(r_edges_since); }
                    w_seq++;
                }
                d->wclk = 1; d->eval();
                wcyc++;
                // epoch bookkeeping: leaving RUN or a local reset ends the epoch
                bool live = d->w_live;
                if (w_live_prev && !live) { w_epoch++; w_seq = 0; t_acc.clear(); acc_redge.clear(); }
                w_live_prev = live;
                // drive next-cycle inputs
                if (wrst_left > 0) { wrst_left--; d->wrst_n = 0; } else d->wrst_n = 1;
                if (!draining && preset > 0 && chance(preset)) {
                    wrst_left = 3 + rnd() % 20; d->wrst_n = 0; resets++;
                    if (w_live_prev) { w_epoch++; w_seq = 0; } w_live_prev = false;
                }
                if (d->wrst_n == 0 && w_seq != 0) { w_epoch++; w_seq = 0; }
                bool v;
                if (draining) v = false;
                else if (sparse) { if (sparse_gap > 0) { sparse_gap--; v = false; } else v = true; }
                else v = chance(pw);
                if (sparse && fire) sparse_gap = 8 + rnd() % 24;
                d->w_v = v; set_wd();
                d->eval();
                if (wcyc == drain_at) draining = true;
                w_hi = true; tw_f = tw_r + T / 2 + (urand() * 2 - 1) * jitter;
            } else {
                d->wclk = 0; d->eval();
                w_hi = false; tw_r = wrise_t(wcyc);
            }
        } else {
            now = tr;
            if (!r_hi) {           // ---------------- read rising edge
                bool take = d->r_v && d->r_rdy;
                bool run_ring = true;
                int cc = d->dbg_cc;
                bool d_on = d->dbg_rs == 3 || d->dbg_rs == 2;
                int rp = d->dbg_rp;
                bool rf = d->r_fault;
                if (d_on && !rf) {
                    int idx = rp & (D - 1);
                    double lag = now - dr.t_wr[idx];
                    dr.checks++;
                    if (dr.cnt_wr[idx] != rp || lag < lagmin) {
                        window_viol++; if (t_first_viol < 0) t_first_viol = now;
                        if (!expfault) FAIL("data ring window: slot %d holds cnt %d want %d lag %.1f", idx, dr.cnt_wr[idx], rp, lag);
                    } else { if (lag < dr.min_lag) dr.min_lag = lag; if (lag > dr.max_lag) dr.max_lag = lag; if (d_lag0 < 0) d_lag0 = lag; }
                    dr.t_rd[idx] = now;
                }
                if (run_ring) {
                    int idx = cc & (D - 1);
                    if (now - cr.t_rd[idx] < holdps) {
                        window_viol++; if (t_first_viol < 0) t_first_viol = now;
                        if (!expfault) FAIL("credit ring hold: slot %d rewritten %.1f ps after read", idx, now - cr.t_rd[idx]);
                    }
                    cr.t_wr[idx] = now; cr.cnt_wr[idx] = cc;
                }
                if (take) {
                    uint32_t s = d->r_d[0], e = d->r_d[1];
                    bool ok = true;
                    for (int i = 2; i < NW; i++) if (d->r_d[i] != hsh(e, s, i)) ok = false;
                    if (!ok) FAIL("payload corrupt e=%u s=%u", e, s);
                    if ((long)e < r_last_e) FAIL("epoch replay %u after %ld", e, r_last_e);
                    else if ((long)e == r_last_e) { if ((long)s != r_last_s + 1) FAIL("order e=%u s=%u after %ld", e, s, r_last_s); }
                    else if (s != 0) FAIL("new epoch %u starts at seq %u", e, s);
                    r_last_e = e; r_last_s = s; delivered++; del_per_epoch[e]++;
                    if (sparse && e == w_epoch && s < t_acc.size()) {
                        lat.push_back((now - t_acc[s]) / T);
                        lat_edges[(int)(r_edges_since + 1 - acc_redge[s])]++;
                    }
                    if (first_take_cyc < 0) first_take_cyc = rcyc;
                    if (!draining) { takes++; take_cycles = rcyc - first_take_cyc + 1; }
                }
                if (rf && t_fault < 0) t_fault = now;
                d->rclk = 1; d->eval();
                rcyc++; r_edges_since++;
                if (rrst_left > 0) { rrst_left--; d->rrst_n = 0; } else d->rrst_n = 1;
                if (!draining && preset > 0 && chance(preset)) { rrst_left = 3 + rnd() % 20; d->rrst_n = 0; resets++; }
                bool rdy;
                if (draining || sparse || stream) rdy = true;
                else if (bp) { if (bp_burst <= 0) { bp_rdy = !bp_rdy; bp_burst = 1 + rnd() % (bp_rdy ? 40 : 25); } bp_burst--; rdy = bp_rdy; }
                else rdy = chance(pr);
                d->r_rdy = rdy;
                d->eval();
                r_hi = true; tr_f = tr_r + T / 2 + (urand() * 2 - 1) * jitter;
            } else {
                d->rclk = 0; d->eval();
                r_hi = false; tr_r = rrise_t(rcyc);
            }
        }
        if (d->w_fault && t_fault < 0) t_fault = now;
    }
    bool faulted = d->r_fault || d->w_fault;
    if (!expfault && faulted) FAIL("fault asserted (r_fault=%d w_fault=%d) at %.1f", d->r_fault, d->w_fault, t_fault);
    if (expfault) {
        if (!faulted) FAIL("expected a drift fault, none asserted");
        if (t_first_viol >= 0 && (t_fault < 0 || t_first_viol < t_fault)) FAIL("window violated at %.1f before fault at %.1f", t_first_viol, t_fault);
    } else {
        // conservation: final epoch drained completely
        uint32_t a = acc_per_epoch.count(w_epoch) ? acc_per_epoch[w_epoch] : 0;
        uint32_t b = del_per_epoch.count(w_epoch) ? del_per_epoch[w_epoch] : 0;
        if (a != b) FAIL("final epoch %u: accepted %u delivered %u", w_epoch, a, b);
        if (!preset && w_epoch != 0) FAIL("unexpected epoch change without reset (%u)", w_epoch);
    }
    double lmin = 1e9, lmax = -1e9, lsum = 0;
    for (double x : lat) { lmin = std::min(lmin, x); lmax = std::max(lmax, x); lsum += x; }
    printf("{\"mode\":\"%s\",\"phase_ps\":%.2f,\"wander_ps\":%.1f,\"drift_ps_per_cycle\":%.4f,\"cycles\":%ld,"
           "\"accepted\":%ld,\"delivered\":%ld,\"resets\":%ld,\"epochs\":%u,"
           "\"data_lag_ps\":[%.1f,%.1f],\"credit_lag_ps\":[%.1f,%.1f],\"data_lag0_ps\":%.1f,\"credit_lag0_ps\":%.1f,\"window_checks\":%ld,\"window_violations\":%ld,"
           "\"fault\":%d,\"t_fault_ps\":%.1f,\"t_first_violation_ps\":%.1f,"
           "\"latency_periods\":{\"n\":%zu,\"min\":%.4f,\"mean\":%.4f,\"max\":%.4f},\"latency_edges\":{",
           mode.c_str(), phase, wander, drift, cycles, accepted, delivered, resets, w_epoch,
           dr.min_lag, dr.max_lag, cr.min_lag, cr.max_lag, d_lag0, c_lag0, dr.checks + cr.checks, window_viol,
           faulted ? 1 : 0, t_fault, t_first_viol, lat.size(), lat.empty() ? 0 : lmin,
           lat.empty() ? 0 : lsum / lat.size(), lat.empty() ? 0 : lmax);
    bool first = true;
    for (auto& kv : lat_edges) { printf("%s\"%d\":%ld", first ? "" : ",", kv.first, kv.second); first = false; }
    printf("},\"throughput_words_per_cycle\":%.5f,\"credits\":%d,\"errors\":%ld}\n",
           take_cycles > 0 ? double(takes) / take_cycles : 0.0, credits, errors);
    delete d;
    return errors ? 1 : 0;
}
