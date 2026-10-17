// S81-SLICE xs lockstep bench (tools/s81_slice/xs_bench.sh): the production static PQ slot (Vref = tb_s81sl_xs_ref)
// and the slice x streamer (Vxs = ot_s81sl_xs) run the same production ROM images and calendar; the reference loads x
// over its VM rows, the xs receives it as ring all-gather beats (q family quantised by the production act-quant RTL
// Vaq = ot_dsrom_aq12t; BF16 family rounded RNE exactly as the production IX loader).  Every cycle's 1,101-b frame
// word of the xs must equal the reference's, at reference time + (OFF + 3 - 8 + 1): issuer pin/delay/out edges 3, no QB align / bc relays (-8), output relay (+1).
//   tb +work=DIR      (prog.txt, meta.json, x<gid>.hex, ROM via maps in DIR; +OT_ROM_DIR=DIR is passed by the script)
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include "Vref.h"
#include "Vxs.h"
#include "Vaq.h"
#include "verilated.h"

static std::string WORK;
static int jint(const std::string& js, const std::string& key) {
    size_t p = js.find("\"" + key + "\"");
    if (p == std::string::npos) { fprintf(stderr, "meta key %s\n", key.c_str()); exit(3); }
    p = js.find(':', p);
    return atoi(js.c_str() + p + 1);
}
template <class W> static void setbits(W& w, int lo, int n, uint64_t v) {
    for (int i = 0; i < n; i++) {
        int b = lo + i;
        if ((v >> i) & 1) w[b / 32] |= (1u << (b % 32)); else w[b / 32] &= ~(1u << (b % 32));
    }
}
template <class W> static uint32_t getbits(const W& w, int lo, int n) {
    uint32_t v = 0;
    for (int i = 0; i < n; i++) { int b = lo + i; v |= ((w[b / 32] >> (b % 32)) & 1u) << i; }
    return v;
}
struct Ev { std::string k; std::vector<std::string> a; };

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    for (int i = 1; i < argc; i++) if (!strncmp(argv[i], "+work=", 6)) WORK = argv[i] + 6;
    std::ifstream mf(WORK + "/meta.json"); std::stringstream ms; ms << mf.rdbuf(); std::string meta = ms.str();
    const int OFF = jint(meta, "off"), END = jint(meta, "end_iter"), TS = jint(meta, "t_start");
    const int D = jint(meta, "expected_xs_minus_ref");
    // x vectors (FP32)
    std::vector<std::vector<uint32_t>> X(3);
    for (int g = 0; g < 3; g++) {
        std::ifstream f(WORK + "/x" + std::to_string(g) + ".hex"); std::string l;
        while (f >> l) X[g].push_back((uint32_t)strtoul(l.c_str(), 0, 16));
        if (X[g].size() != 5120) { printf("FAIL x%d size\n", g); return 3; }
    }
    // q family beats by the production act-quant (one 32-element block per valid; collected on vo in order)
    std::vector<std::vector<std::vector<uint32_t>>> QB(3, std::vector<std::vector<uint32_t>>(160));  // 8 q words + e
    {
        Vaq aq; int outn = 0, inn = 0;
        aq.rst_n = 0; aq.v = 0; aq.clk = 0; aq.eval();
        for (int c = 0; c < 4000 && outn < 480; c++) {
            aq.rst_n = c >= 8;
            aq.v = 0;
            if (c >= 16 && inn < 480) { aq.v = 1; for (int j = 0; j < 32; j++) aq.x[j] = X[inn / 160][32 * (inn % 160) + j]; inn++; }
            aq.clk = 0; aq.eval(); aq.clk = 1; aq.eval();
            if (aq.vo) {
                std::vector<uint32_t> q(9); for (int j = 0; j < 8; j++) q[j] = aq.q[j]; q[8] = aq.e & 0x3ff;
                QB[outn / 160][outn % 160] = q; outn++;
            }
        }
        int gq = outn / 160;
        if (gq != 3) { printf("FAIL act-quant vehicle produced %d gathers\n", gq); return 3; }
    }
    auto bf16 = [](uint32_t x) -> uint32_t {
        uint32_t inc = ((x >> 15) & 1) && (((x & 0x7fff) != 0) || ((x >> 16) & 1));
        return ((x >> 16) + inc) & 0xffff;
    };
    // program
    std::map<int, std::vector<Ev>> prog; int calrows = 0;
    {
        std::ifstream f(WORK + "/prog.txt"); std::string line;
        while (std::getline(f, line)) {
            std::istringstream is(line); int it; Ev e; is >> it >> e.k; std::string t;
            while (is >> t) e.a.push_back(t);
            if (e.k == "RPRIME") calrows = atoi(e.a[0].c_str());
            prog[it].push_back(e);
        }
    }
    std::map<int, std::pair<int, int>> arrive;   // gid*1000 + fam*100 + beat -> (iteration, src)   (latency report)
    Vref r; Vxs x;
    std::vector<std::vector<uint32_t>> RW, XW;
    int rfault = 0, rcal = 0, xfault_at = -1;
    int pend[4] = {0, 0, 0, 0};
    uint64_t fiss_ph = 0, fiss_np = 0, fx[5] = {0, 0, 0, 0, 0};
    for (int i = 0; i <= END; i++) {
        r.rst = i >= 16; x.rst_n = i >= 16;
        r.prime = 0; r.start = 0; r.cal_base = 0; r.cal_len = calrows;
        for (int w = 0; w < 65; w++) r.f_vm[w] = 0;
        for (int w = 0; w < 7; w++) r.f_cnt[w] = 0;
        bool go = false;
        x.is_v = 0; for (int w = 0; w < 5; w++) x.is_d[w] = 0;
        x.g_v = 0; x.g_fam = 0; x.g_idx = 0; for (int w = 0; w < 96; w++) x.g_d[w] = 0;
        if (prog.count(i)) for (auto& e : prog[i]) {
            if (e.k == "RPRIME") r.prime = 1;
            else if (e.k == "RSTART") r.start = 1;
            else if (e.k == "RGO") { go = true; fiss_ph = atoi(e.a[0].c_str()); fiss_np = atoi(e.a[1].c_str());
                for (int k = 0; k < 5; k++) fx[k] = strtoull(e.a[2 + k].c_str(), 0, 10); }
            else if (e.k == "RVM") { int g = atoi(e.a[0].c_str()), bt = atoi(e.a[1].c_str());
                setbits(r.f_vm, 0, 1, 1); for (int j = 0; j < 64; j++) setbits(r.f_vm, 1 + 32 * j, 32, X[g][64 * bt + j]); }
            else if (e.k == "RGA") pend[atoi(e.a[0].c_str())] += atoi(e.a[1].c_str());
            else if (e.k == "XIS") { x.is_v = 1; const std::string& h = e.a[0];
                for (int w = 0; w < 5; w++) x.is_d[w] = (uint32_t)strtoul(h.substr(h.size() - 8 * (w + 1), 8).c_str(), 0, 16); }
            else if (e.k == "XG") { int s = atoi(e.a[0].c_str()), fam = atoi(e.a[1].c_str()), bt = atoi(e.a[2].c_str()),
                    g = atoi(e.a[3].c_str());
                x.g_v |= 1 << s; x.g_fam |= fam << s; x.g_idx |= bt << (7 * s);
                if (fam) for (int j = 0; j < 64; j++) setbits(x.g_d, 1024 * s + 16 * j, 16, bf16(X[g][64 * bt + j]));
                else for (int h = 0; h < 2; h++) {
                    auto& q = QB[g][2 * bt + h];
                    for (int j = 0; j < 8; j++) setbits(x.g_d, 1024 * s + 266 * h + 32 * j, 32, q[j]);
                    setbits(x.g_d, 1024 * s + 266 * h + 256, 10, q[8]);
                }
                if (!arrive.count(g * 1000 + fam * 100 + bt)) arrive[g * 1000 + fam * 100 + bt] = {i, s}; }
        }
        // f_iss {f_fault, fmt 2, ops 19, obase 19, xps 19, xbase 19, np 3, ph 10, go}
        for (int w = 0; w < 3; w++) r.f_iss[w] = 0;
        setbits(r.f_iss, 0, 1, go); setbits(r.f_iss, 1, 10, fiss_ph); setbits(r.f_iss, 11, 3, fiss_np);
        setbits(r.f_iss, 14, 19, fx[0]); setbits(r.f_iss, 33, 19, fx[1]); setbits(r.f_iss, 52, 19, fx[2]);
        setbits(r.f_iss, 71, 19, fx[3]); setbits(r.f_iss, 90, 2, fx[4]);
        // return groups: up to 15 rows per group and tag per cycle
        for (int t = 0; t < 4; t++) for (int g = 0; g < 12 && pend[t] > 0; g++) {
            int n = pend[t] > 15 ? 15 : pend[t]; pend[t] -= n; setbits(r.f_cnt, 16 * g + 4 * t, 4, n);
        }
        r.clk = 0; x.clk = 0; r.eval(); x.eval();
        r.clk = 1; x.clk = 1; r.eval(); x.eval();
        std::vector<uint32_t> a(35), b(35);
        for (int w = 0; w < 35; w++) { a[w] = r.xw[w]; b[w] = x.xw_d[w]; }
        RW.push_back(a); XW.push_back(b);
        if (i > 40 && ((r.t_iss >> 2) & 1)) rfault++;
        if (i > 40 && r.cal_fault) rcal++;
        if (x.fault && xfault_at < 0) xfault_at = i;
        if (x.xw_v != (x.xw_d[0] & 1)) { printf("FAIL xw_v != xw_d[0] at %d\n", i); return 1; }
    }
    // compare every cycle: xs[i + D] == ref[i]
    int r0 = -1, x0 = -1;
    for (int i = 0; i <= END; i++) { if (r0 < 0 && (RW[i][0] & 1)) r0 = i; if (x0 < 0 && (XW[i][0] & 1)) x0 = i; }
    long cmp = 0, mism = 0, valid = 0, qw = 0, bw = 0, cfgw = 0, gow = 0, nzq = 0; int first_bad = -1;
    // every cycle from the reference stage start on (before it, both sides only flush reset transients of the
    // un-reset stream-head data registers, whose reset release is not shifted by the slice offset); every VALID word of
    // either side over the whole run
    long pre = 0, vmism = 0; std::vector<int> badlist;
    for (int i = 20; i + D <= END; i++) {
        if (i + D < 0) continue;
        bool eq = RW[i] == XW[i + D];
        if (((RW[i][0] | XW[i + D][0]) & 1) && !eq) vmism++;
        if (i < TS) { if (!eq) pre++; continue; }
        cmp++;
        if (!eq) { mism++; if (first_bad < 0) first_bad = i; if (badlist.size() < 12) badlist.push_back(i); }
        if (RW[i][0] & 1) {
            valid++;
            uint32_t qv = getbits(RW[i], 283, 1), cfg = getbits(RW[i], 1, 1), g = getbits(RW[i], 2, 1);
            bool bfw = false; for (int k = 565; k < 1101; k += 32) if (getbits(RW[i], k, (1101 - k) < 32 ? 1101 - k : 32)) bfw = true;
            if (bfw) bw++; else if (qv) { qw++; if (getbits(RW[i], 1, 32) || getbits(RW[i], 33, 32)) nzq++; }
            if (cfg) cfgw++;
            if (g) gow++;
        }
    }
    // latency: the tight gather (gid 0, q, buffer parity 0, read by phase 0 only) -- arrival pin edge -> first xs frame
    // word whose q0 / q1 reads that beat
    int lat_min = 1 << 30, lat_beat = -1; std::map<int, int> firstuse;
    int w0 = TS + 17 + OFF + jint(meta, "s0"), w1 = TS + 17 + OFF + jint(meta, "s1");
    for (int i = w0; i < w1 && i <= END; i++) {
        auto& w = XW[i];
        if (!(w[0] & 1) || !getbits(w, 283, 1)) continue;
        uint32_t sv = getbits(w, 281, 2), p = getbits(w, 270, 8), qb = getbits(w, 267, 3);
        for (int h = 0; h < 2; h++) if ((sv >> h) & 1) {
            int bt = (16 * p + 8 * h + qb) >> 1;
            if (!firstuse.count(bt)) firstuse[bt] = i;
        }
    }
    for (auto& kv : firstuse) {
        auto it = arrive.find(0 * 1000 + 0 + kv.first);
        if (it == arrive.end()) continue;
        int l = kv.second - it->second.first;
        if (l < lat_min) { lat_min = l; lat_beat = kv.first; }
    }
    printf("XS_LOCKSTEP stage_off=%d D=%d first_ref_word=%d first_xs_word=%d cycles=%ld valid=%ld q=%ld (nonzero %ld) "
           "bf=%ld cfg=%ld go=%ld mismatches=%ld ref_fault_cycles=%d ref_cal_fault=%d xs_fault_at=%d "
           "valid_word_mismatches=%ld pre_start_transient_cycles=%ld beat_to_word_latency=%d (beat %d, %zu beats used by phase 0)\n",
           OFF, D, r0, x0, cmp, valid, qw, nzq, bw, cfgw, gow, mism, rfault, rcal, xfault_at, vmism, pre, lat_min, lat_beat,
           firstuse.size());
    if (first_bad >= 0) {
        auto& a = RW[first_bad]; auto& b = XW[first_bad + D]; int nb = 0;
        printf("FIRST MISMATCH ref iter %d (xs %d):", first_bad, first_bad + D);
        for (int k = 0; k < 1101 && nb < 12; k++) if (getbits(a, k, 1) != getbits(b, k, 1)) { printf(" b%d=%u/%u", k, getbits(a, k, 1), getbits(b, k, 1)); nb++; }
        printf("\n");
    }
    for (int b : badlist) printf("MISMATCH ref iter %d\n", b);
    bool pass = mism == 0 && vmism == 0 && r0 >= 0 && x0 == r0 + D && rfault == 0 && rcal == 0 && xfault_at < 0 && qw > 0 && bw > 0 && nzq > 0;
    printf(pass ? "PASS xs_lockstep\n" : "FAIL xs_lockstep\n");
    return pass ? 0 : 1;
}
