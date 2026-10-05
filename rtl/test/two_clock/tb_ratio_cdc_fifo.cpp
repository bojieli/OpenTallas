// Dual-clock Verilator bench of ot_ratio_cdc_fifo (rtl/common/ot_ratio_cdc_fifo.sv).
// Time base: one tick = one 3.6 GHz VCO period (2500/9 ps).  The fast (1.2 GHz) clock rises every 3 ticks, the
// slow (0.9 GHz) clock every 4 ticks starting at tick PHASE; coincident edges are evaluated as one ideal edge.
// DIR=f2s: writer on fast, reader on slow.  DIR=s2f: writer on slow, reader on fast.
// Every word carries {epoch:16, seq:32, check:16}; the scoreboard requires, over the whole run:
//   * payload integrity (check field) -- a stale or corrupted slot is caught;
//   * within a writer epoch, delivery in order from seq 0 with no gap and no duplicate;
//   * epochs strictly increasing at the reader (no replay of an old epoch after a reset);
//   * no write accepted while wrst_n is low, no valid while rrst_n is low;
//   * words lost only to a reset: an epoch's undelivered tail may be discarded only if it ended by a reset;
//     after the final drain every accepted word of the last epoch is delivered.
// Usage: tb +dir=f2s|s2f +mode=sparse|saturate|random|reset|backpressure +words=N +seed=S +phase=P
#include "Vot_ratio_cdc_fifo.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>

static const double TICK_PS = 2500.0 / 9.0;
static uint64_t rs;
static uint32_t rnd() { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return (uint32_t)(rs >> 11); }
static bool chance(double p) { return (rnd() % 1000000) < (uint32_t)(p * 1e6); }
static uint16_t chk(uint32_t e, uint32_t s) { uint32_t h = e * 0x9E3779B1u ^ s * 0x85EBCA77u; h ^= h >> 15; h *= 0x2C1B3C6Du; h ^= h >> 13; return (uint16_t)h; }
static uint64_t mk(uint32_t e, uint32_t s) { return ((uint64_t)(e & 0xFFFF) << 48) | ((uint64_t)s << 16) | chk(e & 0xFFFF, s); }
static std::string arg(int argc, char** argv, const char* k, const char* d) {
    std::string p = std::string("+") + k + "=";
    for (int i = 1; i < argc; i++) if (!strncmp(argv[i], p.c_str(), p.size())) return argv[i] + p.size();
    return d;
}
static int errors = 0;
#define FAIL(...) do { if (errors < 20) { printf("ERROR t=%.0fps: ", now * TICK_PS); printf(__VA_ARGS__); printf("\n"); } errors++; } while (0)

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::string dir = arg(argc, argv, "dir", "f2s"), mode = arg(argc, argv, "mode", "random");
    long words = atol(arg(argc, argv, "words", "100000").c_str());
    rs = 0x9E3779B97F4A7C15ull ^ (uint64_t)atol(arg(argc, argv, "seed", "1").c_str()) * 0x100000001B3ull;
    int phase = atoi(arg(argc, argv, "phase", "0").c_str());
    const bool f2s = dir == "f2s";
    const int wper = f2s ? 3 : 4, rper = f2s ? 4 : 3;
    const int woff = f2s ? 0 : phase, roff = f2s ? phase : 0;
    const double wps = wper * TICK_PS, rps = rper * TICK_PS;
    double pw = 1.0, pr = 1.0, preset = 0.0;
    bool sparse = false, bp = false;
    if (mode == "sparse") sparse = true;
    else if (mode == "saturate") { pw = 1.0; pr = 1.0; }
    else if (mode == "random") { pw = 0.6; pr = 0.6; }
    else if (mode == "reset") { pw = 0.7; pr = 0.7; preset = 0.002; }
    else if (mode == "backpressure") { bp = true; }
    else { printf("bad mode\n"); return 2; }

    Vot_ratio_cdc_fifo* d = new Vot_ratio_cdc_fifo;
    long now = 0;
    // bench state
    int wrst = 6, rrst = 8;                // remaining reset cycles per side (sync resets, start asserted)
    bool presenting = false; uint64_t pres_word = 0; long pres_tick = 0;
    uint32_t w_epoch = 0, w_seq = 0; bool w_live_prev = false; bool epoch_open = false;
    std::vector<long> acc_tick;            // accept tick per seq of the current writer epoch
    uint32_t r_last_e = 0; long r_last_s = -1; bool r_any = false;
    long delivered = 0, accepted = 0, flushed = 0, resets_w = 0, resets_r = 0;
    bool in_flight = false; long gap = 0;
    std::vector<double> lat; lat.reserve(sparse ? words : 1);
    long first_take_tick = -1, last_take_tick = -1, takes_window = 0;
    int bp_burst = 0; bool bp_ready = true;
    std::vector<uint32_t> epoch_acc;       // words accepted per writer epoch
    std::vector<uint32_t> epoch_ended_by_reset;
    epoch_acc.push_back(0); epoch_ended_by_reset.push_back(0);
    // per-epoch delivered count
    std::vector<uint32_t> epoch_del; epoch_del.push_back(0);
    bool reset_seen_epoch = false;         // a reset was asserted (either side) since this writer epoch began
    long max_ticks = words * 400 + 100000;
    bool draining = false; long drain_start = 0;

    d->wclk = 0; d->rclk = 0; d->wrst_n = 0; d->rrst_n = 0; d->w_v = 0; d->w_d = 0; d->r_rdy = 0; d->eval();
    for (now = 0; now < max_ticks; now++) {
        bool we = (now - woff) >= 0 && ((now - woff) % wper) == 0;
        bool re = (now - roff) >= 0 && ((now - roff) % rper) == 0;
        d->wclk = 0; d->rclk = 0; d->eval();
        if (!we && !re) continue;
        // ---- pre-edge sampling (values the flops see at this edge) ----
        bool wfire = we && d->w_v && d->w_rdy;
        bool rtake = re && d->r_v && d->r_rdy;
        uint64_t rword = d->r_d;
        if (we && !d->wrst_n && d->w_rdy) FAIL("w_rdy while wrst_n low");
        if (re && !d->rrst_n && d->r_v) FAIL("r_v while rrst_n low");
        if (wfire) {
            if ((uint32_t)(pres_word >> 48) != (w_epoch & 0xFFFF) || ((pres_word >> 16) & 0xFFFFFFFF) != w_seq) FAIL("bench tag");
            acc_tick.push_back(now); w_seq++; accepted++; epoch_acc[w_epoch]++;
            presenting = false;
        }
        if (rtake) {
            uint32_t e = (uint32_t)(rword >> 48), s = (uint32_t)(rword >> 16);
            if ((uint16_t)rword != chk(e, s)) FAIL("payload check (stale/corrupt) e=%u s=%u", e, s);
            if (r_any && e == (r_last_e & 0xFFFF)) { if ((long)s != r_last_s + 1) FAIL("order/gap/dup in epoch %u: %ld -> %u", e, r_last_s, s); }
            else { if (r_any && e <= (r_last_e & 0xFFFF)) FAIL("epoch replay %u after %u", e, r_last_e); if (s != 0) FAIL("epoch %u starts at seq %u", e, s); }
            if (e >= epoch_del.size()) FAIL("future epoch %u", e); else epoch_del[e]++;
            if (e == (w_epoch & 0xFFFF) && s < acc_tick.size()) {
                if (sparse) lat.push_back((now - acc_tick[s]) * TICK_PS);
            } else if (e == (w_epoch & 0xFFFF)) FAIL("delivered unaccepted word");
            r_any = true; r_last_e = e; r_last_s = s; delivered++; in_flight = false;
            if (first_take_tick < 0) first_take_tick = now;
            last_take_tick = now; takes_window++;
        }
        // ---- the edge ----
        d->wclk = we; d->rclk = re; d->eval();
        // ---- post-edge: bench updates the inputs of the domains that ticked ----
        if (we) {
            bool live = d->w_live;
            if (w_live_prev && !live) {         // writer epoch ended (left RUN)
                epoch_ended_by_reset[w_epoch] = reset_seen_epoch;
                w_epoch++; w_seq = 0; acc_tick.clear(); epoch_acc.push_back(0); epoch_ended_by_reset.push_back(0);
                epoch_del.push_back(0); reset_seen_epoch = false; presenting = false; in_flight = false;
            }
            w_live_prev = live;
            if (wrst > 0) { wrst--; d->wrst_n = 0; } else d->wrst_n = 1;
            if (!draining && preset > 0 && chance(preset)) { wrst = 1 + rnd() % 5; resets_w++; reset_seen_epoch = true; d->wrst_n = 0; wrst--; }
            if (!presenting && !draining && accepted < words) {
                bool go;
                if (sparse) { if (gap > 0) { gap--; go = false; } else go = !in_flight; }
                else if (bp) go = chance(rnd() % 2 ? 1.0 : 0.3);
                else go = chance(pw);
                if (go) { presenting = true; pres_word = mk(w_epoch, w_seq); pres_tick = now; if (sparse) { in_flight = true; gap = rnd() % 7; } }
            }
            d->w_v = presenting; d->w_d = presenting ? mk(w_epoch, w_seq) : 0;
        }
        if (re) {
            if (rrst > 0) { rrst--; d->rrst_n = 0; } else d->rrst_n = 1;
            if (!draining && preset > 0 && chance(preset)) { rrst = 1 + rnd() % 5; resets_r++; reset_seen_epoch = true; d->rrst_n = 0; rrst--; }
            bool rdy;
            if (sparse || draining) rdy = true;
            else if (bp) { if (bp_burst <= 0) { bp_ready = !bp_ready; bp_burst = 1 + rnd() % (bp_ready ? 40 : 200); } bp_burst--; rdy = bp_ready; }
            else rdy = chance(pr);
            d->r_rdy = rdy;
        }
        d->eval();
        if (!draining && accepted >= words) { draining = true; drain_start = now; }
        if (draining && now - drain_start > 2000) break;
    }
    // final epoch must be fully delivered (no reset during drain)
    if (epoch_del.size() > w_epoch && epoch_del[w_epoch] != epoch_acc[w_epoch])
        FAIL("final epoch %u: accepted %u delivered %u", w_epoch, epoch_acc[w_epoch], epoch_del[w_epoch]);
    for (uint32_t e = 0; e < w_epoch; e++) {
        if (epoch_del[e] > epoch_acc[e]) FAIL("epoch %u over-delivered", e);
        if (epoch_del[e] < epoch_acc[e]) { if (!epoch_ended_by_reset[e]) FAIL("epoch %u lost %u words without reset", e, epoch_acc[e] - epoch_del[e]); flushed += epoch_acc[e] - epoch_del[e]; }
    }
    if (preset == 0 && w_epoch != 0) FAIL("unexpected epoch change without reset (%u)", w_epoch);
    if (delivered + flushed != accepted) FAIL("conservation: accepted %ld delivered %ld flushed %ld", accepted, delivered, flushed);
    if (accepted < words) FAIL("bench did not reach %ld words (%ld)", words, accepted);
    printf("RESULT dir=%s mode=%s phase=%d words=%ld accepted=%ld delivered=%ld flushed=%ld epochs=%u resets_w=%ld resets_r=%ld",
           dir.c_str(), mode.c_str(), phase, words, accepted, delivered, flushed, w_epoch + 1, resets_w, resets_r);
    if (sparse && !lat.empty()) {
        std::sort(lat.begin(), lat.end());
        double s = 0; for (double v : lat) s += v;
        printf(" lat_ps=%.1f/%.1f/%.1f lat_dst_cycles=%.3f/%.3f/%.3f", lat.front(), s / lat.size(), lat.back(),
               lat.front() / rps, s / lat.size() / rps, lat.back() / rps);
        // distinct values
        std::vector<long> dv; for (double v : lat) { long t = lround(v / TICK_PS); if (dv.empty() || dv.back() != t) dv.push_back(t); }
        printf(" lat_ticks={"); for (size_t i = 0; i < dv.size(); i++) printf("%s%ld", i ? "," : "", dv[i]); printf("}");
    }
    if (takes_window > 1) printf(" words_per_ns=%.4f", (takes_window - 1) / ((last_take_tick - first_take_tick) * TICK_PS / 1000.0));
    printf(" errors=%d %s\n", errors, errors ? "FAIL" : "PASS");
    delete d;
    return errors ? 1 : 0;
}
