// S81-XG (10-19) lockstep bench of the hardened gather sub-leaf ot_s81sl_xg (tools/s81_slice/xg_bench.sh), derived from
// the xs bench (tb_s81sl_xs.cpp): the production static PQ slot (Vref = tb_s81sl_xs_ref) and ot_s81sl_xg (Vxg = ring stop
// ot_s81sl_rstop + x streamer ot_s81sl_xs) run the same production ROM images and calendar.  Every xs gather event of the
// program (XG src fam beat gid at xs time i) enters the xg at its RING PINS as a real ring beat
// {data 1024 @21 | idx 7 @13 | src 4 @9 | hops 5 @4 | kind 3 @1 | v}:
//   src 1 (from W) -> ri_w, src 2 (from E) -> ri_e, hops 1 (deliver, no forward), at i - 2 (pin flop, gather register);
//   src 0 alternately -> own path (xf_v / xf_s / xf of beat leaf n mod 5, 4 x 276-b fragments) and -> V path (vi, 4
//   fragments), fragments at i - 6 .. i - 3 (pin flop, 4-fragment assembly, beat register, gather register).
// So the x streamer inside sees exactly the xs bench's gather pins; the frame word must match the reference at the
// same D, and the xg fault (rstop collisions + xs) must stay 0.  Own beats must also leave on the line (ro_e / ro_w,
// zero-hop sides skipped).  The xs receives it as ring all-gather beats (q family quantised by the production act-quant RTL
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
#include "Vxg.h"
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
    // +dextra=N (S81-TILES-E xg5): the DUT's x path is N edges later than main ot_s81sl_xg (xg5: rs relay + xs4 = 2)
    int DEX = 0; for (int i = 1; i < argc; i++) if (!strncmp(argv[i], "+dextra=", 8)) DEX = atoi(argv[i] + 8);
    const int D = jint(meta, "expected_xs_minus_ref") + DEX;
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
    // ---- ring-pin schedule of every gather event ----
    const int SID = jint(meta, "slice") & 15, COL = SID >> 1;   // sid = 2 * col + tier
    std::map<int, std::vector<uint32_t>> RIW, RIE, VIN, XFD; std::map<int, uint32_t> XFV, XFS;
    int n0 = 0, n_own = 0, n_v = 0, n_line = 0, own_exp_e = 0, own_exp_w = 0;
    for (auto& kv : prog) for (auto& e : kv.second) if (e.k == "XG") {
        const int i = kv.first, s = atoi(e.a[0].c_str()), fam = atoi(e.a[1].c_str()), bt = atoi(e.a[2].c_str()),
                  g = atoi(e.a[3].c_str());
        std::vector<uint32_t> b(35, 0);
        setbits(b, 0, 1, 1); setbits(b, 1, 3, fam ? 2 : 1); setbits(b, 4, 5, 1); setbits(b, 9, 4, 0); setbits(b, 13, 7, bt);
        if (fam) for (int j = 0; j < 64; j++) setbits(b, 21 + 16 * j, 16, bf16(X[g][64 * bt + j]));
        else for (int h = 0; h < 2; h++) {
            auto& q = QB[g][2 * bt + h];
            for (int j = 0; j < 8; j++) setbits(b, 21 + 266 * h + 32 * j, 32, q[j]);
            setbits(b, 21 + 266 * h + 256, 10, q[8]);
        }
        if (s == 1 || s == 2) {
            auto& M = s == 1 ? RIW : RIE;
            if (M.count(i - 2)) { printf("SETUP_FAIL line collision src %d at %d\n", s, i); return 3; }
            M[i - 2] = b; n_line++;
        } else {
            if (i - 6 < 20) { printf("SETUP_FAIL src0 beat at %d too early for the fragment path\n", i); return 3; }
            bool own = (n0 % 2) == 0; int leaf = (n0 / 2) % 5; n0++;
            for (int f = 0; f < 4; f++) {
                int t = i - 6 + f;
                if (own) {
                    if (XFV.count(t)) { printf("SETUP_FAIL own fragment collision at %d\n", t); return 3; }
                    XFV[t] = 1u << leaf; XFS[t] = f == 0 ? (1u << leaf) : 0;
                    std::vector<uint32_t> w(44, 0);
                    for (int k = 0; k < 276; k++) setbits(w, 276 * leaf + k, 1, getbits(b, 276 * f + k, 1));
                    XFD[t] = w;
                } else {
                    if (VIN.count(t)) { printf("SETUP_FAIL V fragment collision at %d\n", t); return 3; }
                    std::vector<uint32_t> w(9, 0);
                    for (int k = 0; k < 276; k++) setbits(w, k, 1, getbits(b, 276 * f + k, 1));
                    VIN[t] = w;
                }
            }
            if (own) n_own++; else n_v++;
            if (7 - COL != 0) own_exp_e++;
            if (COL != 0) own_exp_w++;
        }
    }
    int own_got_e = 0, own_got_w = 0, dl_bad = 0;
    std::map<int, std::pair<int, int>> arrive;   // gid*1000 + fam*100 + beat -> (iteration, src)   (latency report)
    Vref r; Vxg x;
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
        for (int w = 0; w < 35; w++) { x.ri_w[w] = RIW.count(i) ? RIW[i][w] : 0; x.ri_e[w] = RIE.count(i) ? RIE[i][w] : 0; }
        for (unsigned w = 0; w < sizeof(x.ci_b) / sizeof(x.ci_b[0]); ++w) x.ci_b[w] = 0;
        for (int w = 0; w < 9; w++) x.vi[w] = VIN.count(i) ? VIN[i][w] : 0;
        for (int w = 0; w < 44; w++) x.xf[w] = XFD.count(i) ? XFD[i][w] : 0;
        x.xf_v = XFV.count(i) ? XFV[i] : 0; x.xf_s = XFS.count(i) ? XFS[i] : 0;
        for (int w = 0; w < 6; w++) { x.nx_eo[w] = 0; x.nx_wo[w] = 0; }
        x.ci_dir = 0; x.sid = SID;
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
                (void)fam; (void)bt; (void)g;
                if (!arrive.count(g * 1000 + fam * 100 + bt)) arrive[g * 1000 + fam * 100 + bt] = {i - (s == 0 ? 3 : 2), s}; }
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
        // PORTFIX-DEAD D-XWV: xw_v (= xw_d[0]) is no longer a port of ot_s81sl_xg
        // own / V-assembled beats leave on the line with the default hops (E 7 - col, W col); W / E arrivals (hops 1)
        // are delivered, never forwarded; no control-plane / NX delivery for x beats
        { uint32_t ve = getbits(x.ro_e, 0, 1), ke = getbits(x.ro_e, 1, 3), he = getbits(x.ro_e, 4, 5);
          uint32_t vw = getbits(x.ro_w, 0, 1), kw = getbits(x.ro_w, 1, 3), hw = getbits(x.ro_w, 4, 5);
          if (ve) { if ((ke == 1 || ke == 2) && he == (uint32_t)(7 - COL)) own_got_e++; else dl_bad++; }
          if (vw) { if ((kw == 1 || kw == 2) && hw == (uint32_t)COL) own_got_w++; else dl_bad++; }
          if (x.dl_ev || x.dl_wv || x.dl_vv || getbits(x.nx_wi, 172, 1) || getbits(x.nx_ei, 172, 1)) dl_bad++; }
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
    printf("XG_RING sid=%d col=%d line_beats=%d own_path=%d v_path=%d own_line_e=%d/%d own_line_w=%d/%d stray=%d\n",
           SID, COL, n_line, n_own, n_v, own_got_e, own_exp_e, own_got_w, own_exp_w, dl_bad);
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
    bool pass = mism == 0 && vmism == 0 && r0 >= 0 && x0 == r0 + D && rfault == 0 && rcal == 0 && xfault_at < 0 && qw > 0 && bw > 0 && nzq > 0
                && n_own > 0 && n_v > 0 && n_line > 0 && own_got_e == own_exp_e && own_got_w == own_exp_w && dl_bad == 0;
    printf(pass ? "PASS xg_lockstep\n" : "FAIL xg_lockstep\n");
    return pass ? 0 : 1;
}
